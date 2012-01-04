#!/usr/bin/env python

'''
@file ion/services/dm/distribution/test/test_pubsub.py
@author Swarbhanu Chatterjee
@test ion.services.dm.distribution.pubsub_management_service Unit test suite to cover all pub sub mgmt service code
'''

from mock import Mock, sentinel, patch
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
from pyon.core.exception import NotFound
import unittest

import h5py
import numpy
import uuid
import hashlib

from prototype.hdf.science_object_codec import HDFDecoder
from prototype.hdf.science_object_codec import HDFEncoder


@attr('UNIT', group='dm')
class TestScienceObjectCodec(PyonTestCase):
    """
    Test class for science object codec.
    """
    known_array = numpy.ones((10,20))
    known_hdf_as_string = ''
    dataset_name = 'mydataset'
    rootgrp_name = 'myrootgroup'
    grp_name = 'mygroup'
    path_to_dataset =rootgrp_name + '/' + grp_name + '/' + dataset_name
    filename = ''

    #filename = '/tmp/known_hdf.hdf5'


    def setUp(self):

        # a known array to compare against during tests
        self.known_array = numpy.ones((10,20))

        TestScienceObjectCodec.filename = '/tmp/' + self.random_name() + 'test.hdf5'

        # Write an hdf file with known values to compare against
        h5pyfile = h5py.File(TestScienceObjectCodec.filename, mode = 'w', driver='core')
        grp = h5pyfile.create_group(TestScienceObjectCodec.rootgrp_name)
        subgrp = grp.create_group(TestScienceObjectCodec.grp_name)
        dataset = subgrp.create_dataset(TestScienceObjectCodec.dataset_name, self.known_array.shape, self.known_array.dtype.str, maxshape=(None,None))
        dataset.write_direct(self.known_array)
        h5pyfile.close()

        # convert the hdf file into a binary string
        f = open(TestScienceObjectCodec.filename, mode='rb')
        # read the binary string representation of the file
        TestScienceObjectCodec.known_hdf_as_string = f.read() # this is a known string to compare against during tests
        f.close()

    def random_name(self):
        return hashlib.sha1(str(uuid.uuid4())).hexdigest().upper()[:8]

    def test_decode_known_and_compare(self):

        # create a decoder and read a numpy array from it
        hdfdecoder = HDFDecoder(TestScienceObjectCodec.known_hdf_as_string)
        nparray = hdfdecoder.read_hdf_dataset(TestScienceObjectCodec.path_to_dataset)

        # compare the read numpy array to a known value from the stringed input
        # If the two arrays are the same, the boolean below should be an array of false values
        # Comparing two arrays results in an array of boolean values...
        # so to get a single boolean result, we have to do the following:
        false_condition = nparray != TestScienceObjectCodec.known_array
        # the stmt below asserts that the two read and known numpy arrays are the same
        assert not(false_condition.all()), 'The decoded array and known array are different.'

    def test_encode_known_and_compare(self):

        # Create an encoder and add some (one) dataset/array
        hdfencoder = HDFEncoder()
        hdfencoder.add_hdf_dataset(TestScienceObjectCodec.path_to_dataset, TestScienceObjectCodec.known_array)
        # Serialize to string and compare to a know value
        hdf_string = hdfencoder.encoder_close()

        assert hdf_string==TestScienceObjectCodec.known_hdf_as_string, 'String obtained after encoding data \
        in hdf is different from known value'

    def test_decode_bad_string(self):
        # assert raises a known error if the string fed in is not that of an hdf file
        # create a decoder and feed in a bad string.. this should raise an error
        pass
        # hdfdecoder = HDFDecoder('foo')


    def test_encode_decode(self):
        # encode some arrays
        hdfencoder = HDFEncoder() # put array into the encoder
        hdfencoder.add_hdf_dataset(TestScienceObjectCodec.path_to_dataset, TestScienceObjectCodec.known_array)
        # get the string out from encoder
        hdf_string = hdfencoder.encoder_close()

        # Compare the arrays
        hdfdecoder = HDFDecoder(hdf_string)  # put string in decoder...
        nparray = hdfdecoder.read_hdf_dataset(TestScienceObjectCodec.path_to_dataset) # get array out
        # If the two arrays are the same, the boolean below should be an array of false values
        false_condition = nparray != TestScienceObjectCodec.known_array
        # now assert that the two read and known numpy arrays are the same
        assert not(false_condition.all()), 'Encode-decode sequence resulted in array mismatch.'

    def test_decode_encode(self):

        # decode an existing hdf file and read out an array
        hdfdecoder = HDFDecoder(TestScienceObjectCodec.known_hdf_as_string) # put known string in decoder...
        nparray = hdfdecoder.read_hdf_dataset(TestScienceObjectCodec.path_to_dataset) # get array out

        # encode the array and get the binary string containing the encoded hdf file
        hdfencoder = HDFEncoder() # put the array in the encoder...
        hdfencoder.add_hdf_dataset(TestScienceObjectCodec.path_to_dataset, TestScienceObjectCodec.known_array)
        hdf_string = hdfencoder.encoder_close() # get string out

        # compare the two strings
        assert hdf_string == TestScienceObjectCodec.known_hdf_as_string, 'Decode-encode sequence resulted in string mismatch'

    def test_add_hdf_dataset(self):

        # test adding a name and an array
        testencoder = HDFEncoder()
        testencoder.add_hdf_dataset('test_dataset', TestScienceObjectCodec.known_array)
        testencoder.encoder_close()

    def test_add_hdf_dataset_with_bad_name(self):
        # test adding a bad name and an array
        testencoder = HDFEncoder()
        with self.assertRaises(AssertionError):
            self.dataset = testencoder.add_hdf_dataset('bad name', TestScienceObjectCodec.known_array)
        testencoder.encoder_close()

    def test_add_hdf_dataset_with_bad_array(self):
        # test adding a name and a something other than an array
        testencoder = HDFEncoder()
        with self.assertRaises(AssertionError):
            testencoder.add_hdf_dataset(TestScienceObjectCodec.dataset_name,'bad array')
        testencoder.encoder_close()

    def test_hdf_to_string(self):
        # open the hdf5 file using python 'open()'
        f = open(TestScienceObjectCodec.filename, mode='rb')
        # read the binary string representation of the file
        hdf_string = f.read()
        f.close()
        assert hdf_string==TestScienceObjectCodec.known_hdf_as_string, 'hdf_to_string conversion failed.'




