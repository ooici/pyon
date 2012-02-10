#!/usr/bin/env python

'''
@file prototype/hdf/test_science_object_codec.py
@author Swarbhanu Chatterjee
'''

from mock import Mock, sentinel, patch
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
from pyon.public import log
from pyon.core.exception import NotFound
import unittest

try:
    import h5py
    import numpy
except ImportError:
    log.warn('h5py and numpy have not been installed. Some features of the science object transport framework will not work!')
    no_numpy_h5py = True
    from unittest import SkipTest
    raise SkipTest('Numpy not installed')

import uuid
import hashlib
import os, os.path, glob

from prototype.hdf.hdf_codec import HDFEncoder, HDFDecoder
from prototype.hdf.hdf_codec import HDFEncoderException, HDFDecoderException
no_numpy_h5py = False

@attr('UNIT', group='dm')
class TestScienceObjectCodec(PyonTestCase):
    """
    Test class for science object codec.
    """
    dataset_name = 'mydataset'
    rootgrp_name = 'myrootgroup'
    grp_name = 'mygroup'
    path_to_dataset =rootgrp_name + '/' + grp_name + '/' + dataset_name

    #filename = '/tmp/known_hdf.hdf5'
    def __init__(self, *args, **kwargs):
        self.create_known()
        PyonTestCase.__init__(self,*args,**kwargs)

    def setUp(self):
        pass


    def tearDown(self):
        rm_filepath = '/tmp/*hdf5'
        r = glob.glob(rm_filepath)
        for i in r:
            os.remove(i)
        pass

    @unittest.skipIf(no_numpy_h5py,'numpy and/or h5py not imported')
    def create_known(self):
        """
        A known array to compare against during tests
        """
        ##############################################################
        # The contents for this method should not be changed because
        # the known values should remain constant.
        ############################################################
        self.known_array = numpy.ones((10,20))

        self.filename = '/tmp/testHDFEncoderDecoder.hdf5'

        # Write an hdf file with known values to compare against
        h5pyfile = h5py.File(self.filename, mode = 'w', driver='core')
        grp = h5pyfile.create_group(self.rootgrp_name)
        subgrp = grp.create_group(self.grp_name)
        dataset = subgrp.create_dataset(self.dataset_name, self.known_array.shape, self.known_array.dtype.str, maxshape=(None,None))
        dataset.write_direct(self.known_array)
        h5pyfile.close()

        # convert the hdf file into a binary string
        f = open(self.filename, mode='rb')
        # read the binary string representation of the file
        self.known_hdf_as_string = f.read() # this is a known string to compare against during tests
        f.close()
        # cleaning up
        os.remove(self.filename)

    def random_name(self):
        return hashlib.sha1(str(uuid.uuid4())).hexdigest().upper()[:8]

    def add_two_datasets_read_compare(self, filename, dataset_name1, dataset_name2):
        array1 = numpy.ones((4,5))
        array2 = numpy.ones((2,3))

        # first create the file
        hdfencoder = HDFEncoder(filename)
        hdfencoder.add_hdf_dataset(dataset_name1, array1)
        hdfstring = hdfencoder.encoder_close()

        # now open the file and add another branch
        hdfencoder = HDFEncoder(filename)
        hdfencoder.add_hdf_dataset(dataset_name2, array2)
        hdfstring = hdfencoder.encoder_close()

        hdfdecoder = HDFDecoder(hdfstring)
        # Read the first dataset
        array_decoded_1 =  hdfdecoder.read_hdf_dataset(dataset_name1)

        hdfdecoder = HDFDecoder(hdfstring)
        # Read the second dataset
        array_decoded_2 = hdfdecoder.read_hdf_dataset(dataset_name2)

        self.assertEqual(array1.tostring(), array_decoded_1.tostring())
        self.assertEqual(array2.tostring(), array_decoded_2.tostring())


    @unittest.skipIf(no_numpy_h5py,'numpy and/or h5py not imported')
    def test_decode_known_and_compare(self):
        """
        Create a decoder and read a numpy array from it
        """

        hdfdecoder = HDFDecoder(self.known_hdf_as_string)
        nparray = hdfdecoder.read_hdf_dataset(self.path_to_dataset)

        # compare the read numpy array to a known value from the stringed input
        self.assertEqual(nparray.tostring(),self.known_array.tostring())

    def test_encode_known_and_compare(self):
        """
        Create an encoder and add some (one) dataset/array
        """

        hdfencoder = HDFEncoder()
        hdfencoder.add_hdf_dataset(self.path_to_dataset, self.known_array)
        # Serialize to string and compare to a know value
        hdf_string = hdfencoder.encoder_close()

        self.assertEqual(hdf_string,self.known_hdf_as_string)

    def test_encode_with_filename_and_compare(self):
        """
        Create an encoder and add some (one) dataset/array
        """

        testfilename = '/tmp/testFile.hdf5'
        hdfencoder = HDFEncoder(testfilename)
        hdfencoder.add_hdf_dataset(self.path_to_dataset, self.known_array)
        # get the string out from encoder
        hdf_string = hdfencoder.encoder_close()

        self.assertEqual(hdf_string,self.known_hdf_as_string)

        hdfdecoder = HDFDecoder(self.known_hdf_as_string)
        nparray = hdfdecoder.read_hdf_dataset(self.path_to_dataset)

        self.assertEqual(nparray.tostring(), self.known_array.tostring())

    def test_decode_bad_string(self):
        # assert raises a known error if the string fed in is not that of an hdf file
        # create a decoder and feed in a bad string.. this should raise an error
        pass

    def test_encode_decode(self):
        """
        Encode some arrays
        """

        hdfencoder = HDFEncoder() # put array into the encoder
        hdfencoder.add_hdf_dataset(self.path_to_dataset, self.known_array)
        # get the string out from encoder
        hdf_string = hdfencoder.encoder_close()

        # Compare the arrays
        hdfdecoder = HDFDecoder(hdf_string)  # put string in decoder...
        nparray = hdfdecoder.read_hdf_dataset(self.path_to_dataset) # get array out

        self.assertEqual(nparray.tostring(), self.known_array.tostring()) # works for arbitrarily shaped arrays

    def test_decode_encode(self):
        """
        Try a decode-encode sequence and compare if its the same string
        """

        # decode an existing hdf file and read out an array
        hdfdecoder = HDFDecoder(self.known_hdf_as_string) # put known string in decoder...
        nparray = hdfdecoder.read_hdf_dataset(self.path_to_dataset) # get array out

        # encode the array and get the binary string containing the encoded hdf file
        hdfencoder = HDFEncoder() # put the array in the encoder...
        hdfencoder.add_hdf_dataset(self.path_to_dataset, self.known_array)
        hdf_string = hdfencoder.encoder_close() # get string out

        # compare the two strings
        self.assertEqual(hdf_string,self.known_hdf_as_string)

    def test_add_hdf_dataset(self):
        """
        Test adding a name and an array
        """

        testencoder = HDFEncoder()
        testencoder.add_hdf_dataset('test_dataset', self.known_array)
        testencoder.encoder_close()

    def test_add_hdf_dataset_with_bad_name(self):
        """
        Test adding a bad name and an array
        """

        testencoder = HDFEncoder()
        with self.assertRaises(HDFEncoderException):
            self.dataset = testencoder.add_hdf_dataset('bad name', self.known_array)
        testencoder.encoder_close()

    def test_add_hdf_dataset_with_bad_array(self):
        """
        Test adding a name and a something other than an array
        """

        testencoder = HDFEncoder()
        with self.assertRaises(HDFEncoderException):
            testencoder.add_hdf_dataset(self.dataset_name,'bad array')
        testencoder.encoder_close()

    def test_add_branch_to_existing_file_and_compare(self):
        """
        Test adding a branch to an existing group tree in a file
        """

        filename = '/tmp/testHDFEncoder.hdf5'
        dataset_name1 = 'rootgroup/mygroup/mysubgroup/subsubgroup/data/temperature'
        dataset_name2 = 'rootgroup/mygroup/data/subsubgroup/pressure'

        self.add_two_datasets_read_compare(filename, dataset_name1, dataset_name2)

    def test_add_datasets_to_same_group(self):
        """
        Test adding datasets to the same leaf in the group tree
        """

        filename = '/tmp/testHDFEncoder.hdf5'
        dataset_name1 = 'rootgroup/mygroup/mysubgroup/subsubgroup/data/temperature'
        dataset_name2 = 'rootgroup/mygroup/mysubgroup/subsubgroup/data/pressure'

        self.add_two_datasets_read_compare(filename, dataset_name1, dataset_name2)

    def test_add_hdf_dataset_to_file_having_one_already(self):
        """
        Test adding a dataset to a file when a dataset with the same name already exists in it
        """

        filename = '/tmp/testHDFEncoder.hdf5'
        dataset_name1 = 'rootgroup/mygroup/mysubgroup/subsubgroup/data/temperature'
        dataset_name2 = 'rootgroup/mygroup/mysubgroup/subsubgroup/data/temperature'

        with self.assertRaises(HDFEncoderException):
            self.add_two_datasets_read_compare(filename, dataset_name1, dataset_name2)








