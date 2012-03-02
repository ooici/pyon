#!/usr/bin/env python

'''
@file prototype/hdf/test/test_hdf_array_iterator.py
@author Swarbhanu Chatterjee
@test prototype.hdf.test.test_hdf_array_iterator.py test suite for hdf_array_iterator.py
'''

import os
from prototype.hdf.hdf_array_iterator import acquire_data

from nose.plugins.attrib import attr
from pyon.util.int_test import IonIntegrationTestCase
import unittest

@attr('UNIT', group='dm')
class HDFArrayIteratorTest(IonIntegrationTestCase):

    def setUp(self):

        import h5py, numpy

        #--------------------------------------------------------------------
        # Create an hdf file for testing
        #--------------------------------------------------------------------

        a = numpy.arange(50)

        file = h5py.File('data.hdf5', 'w')

        dset = file.create_dataset("salinity", data=a)

        file.close()

        #--------------------------------------------------------------------
        # Create another file for testing
        #--------------------------------------------------------------------

        a = numpy.arange(30)

        b = numpy.arange(100)

        file = h5py.File('measurements.hdf5', 'w')

        dset = file.create_dataset("temperature", data=a)
        dset2 = file.create_dataset("conductivity", data = b)

        file.close()

        #--------------------------------------------------------------------
        # Create a file for testing recursively searching down the group tree in hdf files
        # seeking out_dict the datasets
        #--------------------------------------------------------------------

        a = numpy.arange(30)

        b = numpy.arange(100)

        file = h5py.File('recursive_searching.hdf5', 'w')

        grp1 = file.create_group('fields')
        grp2 = file.create_group('other_fields')

        dset3 = grp1.create_dataset("altitude", data=a)
        dset4 = grp2.create_dataset("depth", data = b)

        file.close()


    def tearDown(self):
        """
        Cleanup. Delete Subscription, Stream, Process Definition
        """

        os.remove('measurements.hdf5')
        os.remove('data.hdf5')
        os.remove('recursive_searching.hdf5')

    def test_acquire_data_from_multiple_files(self):
        """
        Test whether data can be acquired from multiple hdf5 files
        """

        generator = acquire_data(hdf_files = ['data.hdf5','measurements.hdf5'],
                                var_names = None,
                                concatenate_block_size = 50,
                                bounds = None
                                )

        out_dict = generator.next()

        # assert that the dataset 'salinity' in the first hdf5 file has been opened

        self.assertTrue('salinity' in out_dict['arrays_out_dict'])

        out_dict = generator.next()

        # assert that the second hdf5 file has been opened and one of its datasets has been opened
        self.assertTrue(('temperature' in out_dict['arrays_out_dict']) or ('conductivity' in out_dict['arrays_out_dict']) )

    def test_acquire_data_from_multiple_datasets(self):
        """
        Test whether data can be acquired from multiple datasets from an hdf5 file
        """

        generator = acquire_data(hdf_files = ['measurements.hdf5'],
                                     var_names = None,
                                     concatenate_block_size = 50,
                                     bounds = None
                                )

        out_dict = generator.next() # the first time next() is called loads up the temperature data.

        # now that the temperature data has been exhausted since we chose a very large buffer_size,
        # calling generator.next() will load up the conductivity data
        out_dict = generator.next()

        # assert that the dataset 'salinity' in the first hdf5 file has been opened

        self.assertTrue(('temperature' in out_dict['arrays_out_dict']) and ('conductivity' in out_dict['arrays_out_dict']))

    def test_acquire_data_with_var_names(self):
        """
        Test whether supplying a var_name confines the selection to be of only that var_name
        """

        generator = acquire_data(hdf_files = ['measurements.hdf5'],
            var_names = ['temperature', 'conductivity'],
            concatenate_block_size = 50,
            bounds = None
        )
        out_dict = generator.next()
        self.assertTrue('temperature' is out_dict['variable_name'])


        out_dict = generator.next()
        self.assertTrue('conductivity' is out_dict['variable_name'])

        self.assertTrue('conductivity' in out_dict['arrays_out_dict'])
        self.assertTrue('temperature' in out_dict['arrays_out_dict'])

        self.assertTrue(not ('salinity' in out_dict['arrays_out_dict']))

    @unittest.skip("todo")
    def test_buffer_size(self):
        """
        Test that the chunk of data that is read from the hdf file is of the size buffer_size
        """

        buffer_size = 3

        generator = acquire_data(hdf_files = ['measurements.hdf5'], var_names = None, buffer_size = buffer_size, slice_= (slice(1,100)), concatenate_block_size = 12  )

        out_dict = generator.next()

        arr = out_dict[3]

        self.assertEquals(arr.size, buffer_size)

    @unittest.skip("todo")
    def test_too_large_buffer_size(self):
        """
        Test that providing a very large buffer size is okay
        """

        buffer_size = 1000

        generator = acquire_data(hdf_files = ['data.hdf5'], var_names = ['conductivity'], buffer_size = buffer_size, slice_= (slice(1,100)), concatenate_block_size = 12  )

        with self.assertRaises(StopIteration):
            out_dict = generator.next()

    @unittest.skip("todo")
    def test_concatenate_block_size(self):
        """
        Test that the concatenated arrays are of size concatenate_block_size
        """

        buffer_size = 10
        concatenate_block_size = 20

        generator = acquire_data(hdf_files = ['measurements.hdf5'], var_names = ['temperature'], buffer_size = buffer_size, slice_= (slice(1,100)), concatenate_block_size = concatenate_block_size  )

        #------------------------------------------------------------------------------------------------
        # call next() once.....
        #------------------------------------------------------------------------------------------------

        out_dict = generator.next()

        arrays_out = out_dict['arrays_out_dict']
        self.assertTrue(arrays_out['temperature'].size < concatenate_block_size)

        #------------------------------------------------------------------------------------------------
        # call next() for the second time.....
        #------------------------------------------------------------------------------------------------

        out_dict = generator.next()

        arrays_out = out_dict['arrays_out_dict']

        # Assert that the arrays_out has now been clipped to the concatenate_block_size
        self.assertEquals(arrays_out['temperature'].size, concatenate_block_size)

        #------------------------------------------------------------------------------------------------
        # call next() for the third time..... Now, since the array_out_dict['temperature'] array gets more data
        # it should get refreshed
        #------------------------------------------------------------------------------------------------

        out_dict = generator.next()

        arrays_out = out_dict['arrays_out_dict']
        self.assertTrue(arrays_out['temperature'].size < buffer_size)

    @unittest.skip("todo")
    def test_slice(self):
        """
        Test that providing an arbitrary slice works
        """

        buffer_size = 10
        concatenate_block_size = 20
        slice_size = 3

        generator = acquire_data(hdf_files = ['measurements.hdf5'], var_names = ['temperature'], buffer_size = buffer_size, slice_= (slice(1, slice_size+1)), concatenate_block_size = concatenate_block_size  )

        #------------------------------------------------------------------------------------------------
        # call next() once.....
        #------------------------------------------------------------------------------------------------

        out_dict = generator.next()

        arrays_out = out_dict['arrays_out_dict']

        self.assertEquals(arrays_out['temperature'].size, slice_size)

    @unittest.skip("todo")
    def test_recursively_search_for_dataset(self):
        """
        Test that in a file with grps and sub grps, with the datasets attached as leaves in the end, those datasets can be reached
        """

        generator = acquire_data(hdf_files = ['recursive_searching.hdf5'], var_names = ['altitude', 'depth'], buffer_size = 50, slice_= (slice(1,100)), concatenate_block_size = 12  )

        out_dict = generator.next() # the first time next() is called loads up the temperature data.

        # now that the temperature data has been exhausted since we chose a very large buffer_size,
        # calling generator.next() will load up the conductivity data
        out_dict = generator.next()

        # assert that the dataset 'salinity' in the first hdf5 file has been opened

        print ("arrays_out: %s" % out_dict['arrays_out_dict'])

        self.assertTrue(('altitude' in out_dict['arrays_out_dict']) and ('depth' in out_dict['arrays_out_dict']))



