#!/usr/bin/env python

'''
@file ion/services/dm/distribution/test/test_pubsub.py
@author Swarbhanu Chatterjee
@test ion.services.dm.distribution.pubsub_management_service Unit test suite to cover all pub sub mgmt service code
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

import uuid
import hashlib
import os

from prototype.hdf.science_object_codec import HDFEncoder, HDFDecoder
from prototype.hdf.science_object_codec import HDFEncoderException, HDFDecoderException
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
        pass

    @unittest.skipIf(no_numpy_h5py,'numpy and/or h5py not imported')
    def create_known(self):
        # a known array to compare against during tests
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

    @unittest.skipIf(no_numpy_h5py,'numpy and/or h5py not imported')
    def test_decode_known_and_compare(self):

        # create a decoder and read a numpy array from it
        hdfdecoder = HDFDecoder(self.known_hdf_as_string)
        nparray = hdfdecoder.read_hdf_dataset(self.path_to_dataset)

        # compare the read numpy array to a known value from the stringed input
        self.assertEqual(nparray.tostring(),self.known_array.tostring())

    def test_encode_known_and_compare(self):

        # Create an encoder and add some (one) dataset/array
        hdfencoder = HDFEncoder()
        hdfencoder.add_hdf_dataset(self.path_to_dataset, self.known_array)
        # Serialize to string and compare to a know value
        hdf_string = hdfencoder.encoder_close()

        self.assertEqual(hdf_string,self.known_hdf_as_string)

    def test_encode_withfilename_and_compare(self):

        # Create an encoder and add some (one) dataset/array
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
        # encode some arrays
        hdfencoder = HDFEncoder() # put array into the encoder
        hdfencoder.add_hdf_dataset(self.path_to_dataset, self.known_array)
        # get the string out from encoder
        hdf_string = hdfencoder.encoder_close()

        # Compare the arrays
        hdfdecoder = HDFDecoder(hdf_string)  # put string in decoder...
        nparray = hdfdecoder.read_hdf_dataset(self.path_to_dataset) # get array out

        self.assertEqual(nparray.tostring(), self.known_array.tostring()) # works for arbitrarily shaped arrays

    def test_decode_encode(self):

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

        # test adding a name and an array
        testencoder = HDFEncoder()
        testencoder.add_hdf_dataset('test_dataset', self.known_array)
        testencoder.encoder_close()

        # now check that the data has been correctly added into the hdf file


    def test_add_hdf_dataset_with_bad_name(self):
        # test adding a bad name and an array
        testencoder = HDFEncoder()
        with self.assertRaises(HDFEncoderException):
            self.dataset = testencoder.add_hdf_dataset('bad name', self.known_array)
        testencoder.encoder_close()

    def test_add_hdf_dataset_with_bad_array(self):
        # test adding a name and a something other than an array
        testencoder = HDFEncoder()
        with self.assertRaises(HDFEncoderException):
            testencoder.add_hdf_dataset(self.dataset_name,'bad array')
        testencoder.encoder_close()






