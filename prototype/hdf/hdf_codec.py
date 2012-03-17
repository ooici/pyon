#!/usr/bin/env python


'''
@package prototype.science_object_codec
@file prototype/science_object_codec.py
@author David Stuebe
@author Swarbhanu Chatterjee
@brief prototype codec for the science data object

To run the encoder and decoder, please ensure that numpy and h5py are installed. Also make sure that the temporary
folder, /tmp/, is available for use. Any hdf files that need to be temporarily written to the /tmp/ folder will
be automatically cleaned at the end of the execution.

Please follow these sequence of steps to run the demo example.

1. In the pyon directory (where the pyon code base is located), run $bin/pycc
2. In the pycc interactive shell that opens up, run the following command:
    %loadpy prototype/hdf/example/encoder_decoder_demo.py
3. The output will be a numpy array of ones and with shape (4,5).

What is happening above is that the demo script, prototype/hdf/example/encoder_decoder_demo.py, is being run. If you read
the script, you will know the commands to be followed to encode a numpy array (which results in a binary string being
returned) and decode a binary string (which results in a numpy array to be read out). The demo script is essentially
an encode-decode operation.

Alternatively, if you dont want to use the script, run bin/pycc to get into the pycc interactive shell,
and...
1. Create an encoder object: $encoder = HDFEncoder()
2. Add data as an array:  $encoder.add_hdf_dataset('/myGroup/measurements/pressure', numpy.ones((10,200)))
3. Convert all the data to a binary string for easy transportation: $hdf_string = encoder.encoder_close()

4. Create a decoder object: $decoder = HDFDecoder(hdf_string)
5. Read the array out of the decoder: $decoder.read_hdf_dataset('/myGroup/measurements/pressure')

'''


import uuid
import hashlib
import os
from pyon.util.log import log
from pyon.core.exception import IonException
from pyon.util.file_sys import FS, FileSystem

class ScienceObjectTransportException(IonException):
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
        pass

def random_name():
    """
    Return a random name to be used for the hdf file that needs to be written to disk or virtual memory during the
    encoding process.

    @retval random string
    """
    return hashlib.sha1(str(uuid.uuid4())).hexdigest().upper()[:8]


class HDFEncoderException(ScienceObjectTransportException):
    """
    Exception class for HDFEncoder exceptions. This class inherits from ScienceObjectTransportException
    and implements the __str__() method.
    """
    def __str__(self):
        return str(self.get_status_code()) + " - " + "EncoderError: " + str(self.get_error_message())

class HDFDecoderException(ScienceObjectTransportException):
    """
    Exception class for HDFDecoder exceptions. This class inherits from ScienceObjectTransportException
    and implements the __str__() method.
    """
    def __str__(self):
        return str(self.get_status_code()) + " - " + "DecoderError: " + str(self.get_error_message())

class HDFEncoder(object):
    """
    Implementation of the HDFEncoder object. This class is used to accept an numpy array and user specified datagroup
    tree and return a binary string. This binary string is a binary representation of an hdf file holding the data.
    There are no side effects. The hdf file written to disk (or to virtual memory) during the entire process is cleaned
    up on exit.
    """
    def __init__(self, name = None):
        """
        @param name The name of the dataset
        """
        # generate a random name for the filename if it has not been provided.
        self.filename = FileSystem.get_url(fs=FS.TEMP, filename=name or random_name(), ext='encoder.hdf5')

        # Using inline imports to put off making hdf/numpy required dependencies
        import h5py

        # open an hdf file on disk - in /tmp to write data to since we can't yet do in memory
        log.debug("Creating h5py file object for the encoder at %s" % self.filename)
        if os.path.isfile(self.filename):
            # if file exists, then append to it
            self.h5pyfile = h5py.File(self.filename, mode = 'r+', driver='core')
        else:
            # if file does not already exist, write a new one
            self.h5pyfile = h5py.File(self.filename, mode = 'w', driver='core')
        assert self.h5pyfile, 'No h5py file object created.'

        ### Remove exception handeling for now...
#        except IOError:
#            log.exception("Error opening file for the HDFEncoder! ")
#            raise HDFEncoderException("Error while trying to open file. ")
#        except AssertionError as err:
#            log.exception(err.message)
#            raise HDFEncoderException(err.message)


    def assert_valid_name(self, name):
        """
        Checks valid user input regarding name.
        An example of a valid user input for the name is '/myGroup/measurements/temperature'

        @param name The inputted name
        @retval name The checked name
        """
        # Return Value
        # ------------
        # name: ''
        #

        assert name, 'No name provided for group or dataset!'
        name = name.strip() # remove leading and trailing white spaces
        assert ' ' not in name, 'Whitespace not allowed within group or dataset names! Got name: "%s"' % name
        return name

    def create_pathname(self, name):
        """
        Creates a list that holds the datagroup tree components. Returns name of the dataset.

        @param name
        @retval tree_list
        @retval dataset
        """
        # Return Value
        # ------------
        # (tree_list: [], dataset: '')
        #
        def filter_blanks(n):
            return n is not ''

        tree_list =  name.split('/') # return a list of datagroup, datasubgroups and the dataset
        tree_list = filter(filter_blanks, tree_list)
        dataset = tree_list.pop()
        return tree_list, dataset

    def create_group_tree(self, name):
        """
        Creates a group tree structure and returns the names of the dataset and the lowest subgroup to hang the array on

        @param name
        @retval lowest_subgroup
        @retval dataset
        """
        # Return Value
        # ------------
        # (lowest_subgroup: '', dataset: '')
        #
        # Using inline imports to put off making hdf/numpy required dependencies

        #try:
        name = self.assert_valid_name(name)
        tree_list, dataset = self.create_pathname(name)
        #except AssertionError as err:
        #    log.debug("The group/subgroup/dataset could not be created because of invalid name.")
        #    raise HDFEncoderException(err.message)

        # if list is empty, hang the array in a group called data directly underneath '/',
        # otherwise, keep popping group names from the list of names and create them using h5py
        #try:
        lowest_subgroup = self.h5pyfile.get('/')
        group = lowest_subgroup

        for group_name in tree_list:
            g = group.get(group_name) # if the group doesnt already exist in the file
            if g is None:
                group = group.create_group(group_name) # use group methods for creating a new subgroup
            else:
                group = g
        lowest_subgroup = group
        #except Exception as exc:
        #    log.debug('Error while creating group/subgroup/dataset using h5py.')
        #    raise HDFEncoderException(exc.message)

        return lowest_subgroup, dataset



    def add_hdf_dataset(self, name, nparray):
        """
        Add a numpy array to the hdf file that is temporarily used to store the data.
        This method uses the provided string in name to build a datagroup path in the hdf file

        @param name The name contains the datagroup tree and the dataset name. Ex: '/mygroup/measurements/temperature'
        @param nparray
        @retval success Boolean to indicate successful adding of dataset to the
        @todo later make the path more flexible to create groups as needed...
        """
        # Return Value
        # ------------
        # {success: true}
        #

        # Using inline imports to put off making hdf/numpy required dependencies
        import numpy


        #try:
        assert isinstance(nparray, numpy.ndarray), '2nd argument of method add_hdf_dataset() is not a numpy array!'
        # check that that the input arguments are of the type they are supposed to be
        assert isinstance(name, basestring), '1st argument of method add_hdf_dataset() is not a string!'
        #except AssertionError as err:
        #    log.debug('Name and array assertion failed in add_hdf_dataset method.')
        #    raise HDFEncoderException(err.message)
        lowest_subgroup, name_of_dataset = self.create_group_tree(name)

        #try:
        assert lowest_subgroup, 'No datagroup.'
        assert name_of_dataset, 'No dataset name. provided.'

        assert lowest_subgroup.get(name_of_dataset) is None, 'The dataset %s already exists in the file.' % name_of_dataset

        # create a dataset and hang it under the just created group...
        shape = nparray.shape
        dataset = lowest_subgroup.create_dataset(name_of_dataset,
            shape,
            nparray.dtype.str,
            compression='gzip',
            compression_opts=4,
            maxshape=([None for rank in range(len(shape))])
            )

        assert dataset, 'Unable to create dataset.'
        # write the array in the dataset
        dataset.write_direct(nparray)
        #except AssertionError as err:
        #    log.debug(err.message)
        #    raise HDFEncoderException(err.message)
        #except Exception as exc:
        #    log.debug('Error writing dataset to HDFFile during encoding.')
        #    raise HDFEncoderException(exc.message)

        return True

    def encoder_close(self):
        """
        /wrap the hdf_to_string() method so that first the open h5py file object is closed and the the hdf_to_string()
        method is called so that the latter can convert the temporary hdf file to a binary string.

        @retval hdf_string
        """
        # Return Value
        # ------------
        # hdf_string: ''
        #
        #try:
        self.h5pyfile.close()
        #except IOError:
        #    log.debug('Error closing hdf file.')
        #    raise HDFEncoderException("Error closing file.")
        return self.hdf_to_string()

    def hdf_to_string(self):
        """
        Convert the temporary hdf file holding the data into a binary string. Cleanup by deleting the hdf file and
        return the binary string.

        @retval hdf_string
        """
        # Return Value
        # ------------
        # hdf_string: ''
        #
        try:
            # open the hdf5 file using python 'open()'
            f = open(self.filename, mode='rb')
            # read the binary string representation of the file
            hdf_string = f.read()
            f.close()
        except IOError:
            log.exception("Error opening binary file for reading out hdfstring in HDFEncoder. ")
            raise HDFEncoderException("Error while trying to open file. ")
        finally:
            FileSystem.unlink(self.filename)
        return hdf_string


class HDFDecoder(object):
    """
    Implementation of the HDFDecoder object. This class is used to accept a binary string and return a numpy array.
    The binary string is the binary representation of an hdf file, which contains data. The numpy array that is returned
    is the data. There are no side effects. The binary string needs to written into disk or virtual memory temporarily
    for the data to be extracted. But the temporary file is deleted during cleanup at the end before the array is
    returned.
    """

    def __init__(self, hdf_string):
        """
        @param hdf_string
        """
        #try:
        assert isinstance(hdf_string, basestring), 'The input for instantiating the HDFDecoder object is not a string'
        #except AssertionError as err:
        #    raise HDFDecoderException(err.message)

        #self.filename = FileSystem.get_url(fs=FS.TEMP, filename=hashlib.sha1(hdf_string).hexdigest(), ext='_decoder.hdf5')

        f = FileSystem.mktemp(ext='.hdf5')

        # save an hdf string to disk - in /tmp to so we can open it as an hdf file and read data from it
        f.write(hdf_string)
        f.close()

        self._list_of_datasets = []

        self.filename = f.name
        #except IOError:
        #    log.debug("Error opening binary file for writing hdfstring in HDFDecoder. ")
        #    raise HDFDecoderException("Error while trying to open file. ")

    def __del__(self):
        # This is dangerous - I don't like implementing del!!!

        # Clean up files!
        FileSystem.unlink(self.filename)


    def list_datasets(self):

        if not self._list_of_datasets:
            import h5py
            h5pyfile = h5py.File(self.filename, mode = 'r', driver='core')

            h5pyfile.visit(self._list_of_datasets.append)

            h5pyfile.close()

        return self._list_of_datasets




    def get_hdf_groups(self):
        #try:
        import h5py
        h5pyfile = h5py.File(self.filename, mode = 'r', driver='core')
        #except IOError:
        #    log.debug("Error opening file for the HDFDecoder")
        #   raise HDFDecoderException("Error while trying to open file.")

        root_group = h5pyfile[h5pyfile.name]
        list_of_groups = []
        root_group.visit(list_of_groups.append)

        h5pyfile.close()

        return list_of_groups

    def read_hdf_dataset(self, name):
        """
        read the hdf dataset at this location in to an array

        @param name This should be of the form: '/group/subgroup/subsubgroup/dataset'
        @retval nparray Numpy array that holds data
        """
        # Return Value
        # ------------
        # nparray: numpy.ndarray
        #

        # Using inline imports to put off making hdf/numpy required dependencies
        import h5py
        import numpy

        #try:
        # assert that the input field is a string
        assert isinstance(name, basestring),\
        'HDFDecoder read error: The name provided for the group tree and dataset is not a string!'
        #except AssertionError as err:
        #    raise HDFDecoderException(err.message)

        # if a data group name is not provided, use the default data group name, 'data'
        if name.find('/')==-1:
            name = 'data/' + name

        # open hdf file using h5py
        #try:
        h5pyfile = h5py.File(self.filename, mode = 'r', driver='core')
        #except IOError:
        #    log.debug("Error opening file for the HDFDecoder! ")
        #   raise HDFDecoderException("Error while trying to open file. ")

        # read array from the hdf file
        nparray = numpy.array(h5pyfile['/' + name])

        # hdf close
        h5pyfile.close()

        # Do not remove the file here!

        return nparray

    #@todo Do resource clean up on the file - in a close method or some other way?


