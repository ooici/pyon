#!/usr/bin/env python


'''
@package prototype.science_object_codec
@file prototype/science_object_codec.py
@author David Stuebe
@brief prototype codec for the science data object
'''

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





class HdfEncoder(object):

    def __init__(self):
        pass
        # open an hdf file on disk - in /tmp to write data to since we can't yet do in memory

    def add_hdf_dataset(self, name, nparray):
        """
        add another numpy array to the hdf file using the name as the path in the hdf file
        @TODO later make the path more flexible to create groups as needed...
        """

        return None

    def close(self):
        """
        Adding data is complete - return the string containing the hdf file and data
        """

        return hdf_string


class HDFDecoder(object):

    def __init__(self, hfd_string):
        pass
        # save an hdf string to disk - in /tmp to so we can open it as an hdf file and read data from it

    def read_hdf_dataset(self, name):
        """
        read the hdf dataset at this location in to an array
        @TODO allow this method to take a data space argument to map the memory shape
        @TODO later make the path more flexible to create groups as needed...
        """

        # hdf open

        # allocate array
        # read

        # hdf close

        return nparray


