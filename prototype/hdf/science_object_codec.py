#!/usr/bin/env python


'''
@package prototype.science_object_codec
@file prototype/science_object_codec.py
@author David Stuebe
@author Swarbhanu Chatterjee
@brief prototype codec for the science data object
'''


import h5py
import numpy
import uuid
import hashlib
import sys
from pyon.public import log
from pyon.core.exception import IonException, BadRequest

class ScienceObjectTransportException(Exception):
    """
    Exception class for science object transport library
    """


class ScienceObjectTransport(object):

    def __init__(self, science_object=None):

        self._science_object = science_object

        self._metadata_packets = {}

        self._data_packets = {}


    def encode(self):
        """
        Produce a packet based on the state of the data object
        """

        if self._science_object is None:
            raise ScienceObjectTransportException('Can not encode without a science object to operate on.')


        packet = None
        return packet


    def decode(self, packet):
        """
        Can be a metadata packet or a supplement. Create or update the content of the science object.
        """

class HDFException(Exception):
    """
    HDFEncoder specific exceptions
    """
    status_code = -1

    def __init__(self, message=''):
        self.message = message

    def get_status_code(self):
        return self.status_code

    def get_error_message(self):
        return self.message

class HDFEncoderException(HDFException):
    """
    HDFEncoder specific exceptions
    """
    def __str__(self):
        return str(self.get_status_code()) + " - " + "EncoderError: " + str(self.get_error_message())

class HDFDecoderException(HDFException):
    """
    HDFDecoder specific exceptions
    """
    def __str__(self):
        return str(self.get_status_code()) + " - " + "DecoderError: " + str(self.get_error_message())

class HDFEncoder(object):
    """
    For the HDFEncoder object:
        Numpy array goes in, binary string goes out...
    """
    def __init__(self, name = None):

        # generate a random name for the filename
        if name is None:
            self.filename = '/tmp/' + self.random_name() + 'encoder.hdf5'
        else:
            self.filename = '/tmp/' + name

        # open an hdf file on disk - in /tmp to write data to since we can't yet do in memory
        try:
            log.debug("Creating h5py file object for the encoder at %s" % self.filename)
            self.h5pyfile = h5py.File(self.filename, mode = 'w', driver='core')
        except IOError:
            log.debug("Error opening file for the HDFEncoder!")
            raise HDFEncoderException("Error while trying to open file")


    def random_name(self):
        return hashlib.sha1(str(uuid.uuid4())).hexdigest().upper()[:8]

    def assert_valid_name(self, name):
        log.debug("Checking for valid datagroup/dataset name")
        assert name, 'No name provided for group or dataset!'
        name = name.strip() # remove leading and trailing white spaces
        assert ' ' not in name, 'Whitespace not allowed within group or dataset names!'
        return name

    def create_pathname(self, name):
        tree_list =  name.split('/') # return a list of datagroup, datasubgroups and the dataset
        dataset = tree_list.pop()
        return tree_list, dataset

    def create_group_tree(self, name):
        """
        Creates a group tree structure and returns the names of the dataset and the subgroup to hang it on
        """
        try:
            name = self.assert_valid_name(name)
            tree_list, dataset = self.create_pathname(name)
        except AssertionError as err:
            log.debug("The group/subgroup/dataset could not be created because of invalid name.")
            raise HDFEncoderException(err.message)

        # if list is empty, hang the array in a group called data directly underneath '/',
        # otherwise, keep popping group names from the list of names and create them using h5py
        try:
            group = []
            if not tree_list:
                lowest_subgroup = self.h5pyfile.create_group('data') # dataset takes a default name, 'data'
            else:
                group.append(self.h5pyfile.create_group(tree_list.pop(0))) # use the h5pyfile create_group method
                for group_name in tree_list:
                    group.append(group.pop().create_group(group_name)) # use group methods for creating subgroup
                lowest_subgroup = group.pop()
        except Exception as exc:
            log.debug('Error while creating group/subgroup/dataset using h5py.')
            raise HDFEncoderException(exc.message)

        return lowest_subgroup, dataset


    def add_hdf_dataset(self, name, nparray):
        """
        add another numpy array to the hdf file using the name as the path in the hdf file
        @TODO later make the path more flexible to create groups as needed...
        """
        try:
            assert isinstance(nparray, numpy.ndarray), '2nd argument of method add_hdf_dataset() is not a numpy array!'
            # check that that the input arguments are of the type they are supposed to be
            assert isinstance(name, basestring), '1st argument of method add_hdf_dataset() is not a string!'
        except AssertionError as err:
            log.debug('Error adding array to its proper place in the h5py file data tree structure.')
            raise HDFEncoderException(err.message)
        # later we should parse the name and get the part pertaining to dataset below...
        lowest_subgroup, name_of_dataset = self.create_group_tree(name)

        try:
            # create a dataset and hang it under the just created group...
            dataset = lowest_subgroup.create_dataset(name_of_dataset, nparray.shape, nparray.dtype.str, maxshape=(None,None))
            # write the array in the dataset
            dataset.write_direct(nparray)
        except Exception as exc:
            log.debug('Error writing data in hdf file using the HDFEncoder.')
            raise HDFEncoderException(exc.message)

        return None

    def hdf_to_string(self):
        # open the hdf5 file using python 'open()'
        try:
            f = open(self.filename, mode='rb')
            # read the binary string representation of the file
            hdf_string = f.read()
            f.close()
        except IOError:
            log.debug("Error opening binary file for reading out hdfstring in HDFEncoder.")
            raise HDFEncoderException("Error while trying to open file")
        return hdf_string

    def encoder_close(self):
        try:
            self.h5pyfile.close()
        except IOError:
            log.debug('Error closing hdf file.')
            raise HDFEncoderException("Error closing file.")
        return self.hdf_to_string()


class HDFDecoder(object):
    """
    For the HDFDecoder object:
        Binary string goes in, numpy array goes out...
    """
    def __init__(self, hdf_string):
        # save an hdf string to disk - in /tmp to so we can open it as an hdf file and read data from it
        try:
            assert isinstance(hdf_string, basestring), 'The input for instantiating the HDFDecoder object is not a string'
        except AssertionError as err:
            raise HDFDecoderException(err.message)

        self.filename = '/tmp/' + hashlib.sha1(hdf_string).hexdigest() + '_decoder.hdf5'

        try:
            f = open(self.filename, mode='wb')
            f.write(hdf_string)
            f.close()
        except IOError:
            log.debug("Error opening binary file for writing hdfstring in HDFDecoder.")
            raise HDFDecoderException("Error while trying to open file")

    def read_hdf_dataset(self, name):
        """
        read the hdf dataset at this location in to an array
        @TODO allow this method to take a data space argument to map the memory shape

        the input variable 'name' should be of the form: '/group/subgroup/subsubgroup/dataset'
        """
        # assert that the input field is a string
        try:
            assert isinstance(name, basestring),\
            'HDFDecoder read error: The name provided for the group tree and dataset is not a string!'
        except AssertionError as err:
            raise HDFDecoderException(err.message)

        # if a data group name is not provided, use the default data group name, 'data'
        if name.find('/')==-1:
            name = 'data/' + name

        # open hdf file using h5py
        try:
            h5pyfile = h5py.File(self.filename, mode = 'r', driver='core')
        except IOError:
            log.debug("Error opening file for the HDFDecoder!")
            raise HDFDecoderException("Error while trying to open file")

        # read array from the hdf file
        nparray = numpy.array(h5pyfile['/' + name])

        # hdf close
        h5pyfile.close()

        return nparray


