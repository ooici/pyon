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




class HDFEncoder(object):
    """
    For the HDFEncoder object:
        Numpy array goes in, binary string goes out...
    """
    def __init__(self):

        # generate a random name for the filename
        self.filename = '/tmp/' + self.random_name() + 'encoder.hdf5'
        # open an hdf file on disk - in /tmp to write data to since we can't yet do in memory
        try:
            self.h5pyfile = h5py.File(self.filename, mode = 'w', driver='core')
        except IOError as err:
            print "Error opening file for the HDFEncoder!", err
            sys.exit()

    def random_name(self):
        return hashlib.sha1(str(uuid.uuid4())).hexdigest().upper()[:8]

    def create_group_tree(self, name):
        """
        Creates a group tree structure and returns the names of the dataset and the subgroup to hang it on
        """

        name = name.strip() # remove leading and trailing white spaces
        assert name, 'No name provided for group or dataset!'
        assert ' ' not in name, 'Whitespace not allowed within group or dataset names!'
        list =  name.split('/') # return a list of datagroup, datasubgroups and the dataset
        assert list, 'No dataset name provided. List after splitting name at / is empty.'
        dataset = list.pop()

        # if list is empty, hang the array in a group called data directly underneath '/',
        # otherwise, keep popping group names from the list of names and create them using h5py
        if not list:
            lowest_subgroup = self.h5pyfile.create_group('data') # the data is attached to '/data'
        else:
            group = []
            group.append(self.h5pyfile.create_group(list.pop(0)))
            if list:
                for group_name in list:
                    group.append(group.pop().create_group(group_name))
            lowest_subgroup = group.pop()

        return lowest_subgroup, dataset


    def add_hdf_dataset(self, name, nparray):
        """
        add another numpy array to the hdf file using the name as the path in the hdf file
        @TODO later make the path more flexible to create groups as needed...
        """

        assert isinstance(nparray, numpy.ndarray), '2nd argument of method add_hdf_dataset() is not a numpy array!'

        # check that that the input arguments are of the type they are supposed to be
        assert isinstance(name, basestring), '1st argument of method add_hdf_dataset() is not a string!'

        # later we should parse the name and get the part pertaining to dataset below...
        lowest_subgroup, name_of_dataset = self.create_group_tree(name)

        # create a dataset and hang it under the just created group...
        dataset = lowest_subgroup.create_dataset(name_of_dataset, nparray.shape, nparray.dtype.str, maxshape=(None,None))

        # write the array in the dataset
        dataset.write_direct(nparray)

        return None

    def hdf_to_string(self):
        # open the hdf5 file using python 'open()'
        try:
            f = open(self.filename, mode='rb')
            # read the binary string representation of the file
            hdf_string = f.read()
            f.close()
        except:
            print "Error opening binary file for reading out hdfstring in HDFEncoder."
            sys.exit()

        return hdf_string

    def encoder_close(self):
        self.h5pyfile.close()
        return self.hdf_to_string()


class HDFDecoder(object):
    """
    For the HDFDecoder object:
        Binary string goes in, numpy array goes out...
    """
    def __init__(self, hdf_string):
        # save an hdf string to disk - in /tmp to so we can open it as an hdf file and read data from it
        assert isinstance(hdf_string, basestring), 'The input for instantiating the HDFDecoder object is not a string'

        self.filename = '/tmp/' + self.random_name() + 'decoder.hdf5'

        try:
            f = open(self.filename, mode='wb')
            f.write(hdf_string)
            f.close()
        except:
            print "Error opening binary file for writing hdfstring into file in HDFDecoder."
            sys.exit()

    def random_name(self):
        return hashlib.sha1(str(uuid.uuid4())).hexdigest().upper()[:8]

    def read_hdf_dataset(self, name):
        """
        read the hdf dataset at this location in to an array
        @TODO allow this method to take a data space argument to map the memory shape

        the input variable 'name' should be of the form: '/group/subgroup/subsubgroup/dataset'
        """
        # assert that the input field is a string
        assert isinstance(name, basestring),\
        'HDFDecoder read error: The name provided for the group tree and dataset is not a string!'

        # open hdf file using h5py
        try:
            h5pyfile = h5py.File(self.filename, mode = 'r', driver='core')
        except:
            print "Error opening hdf5 file in HDFDecoder."
            sys.exit()

        # read array from the hdf file
        nparray = numpy.array(h5pyfile['/' + name])

        # hdf close
        h5pyfile.close()

        return nparray


