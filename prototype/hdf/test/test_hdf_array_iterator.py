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
from pyon.util.unit_test import IonUnitTestCase
from pyon.core.exception import NotFound, BadRequest

from pyon.util.file_sys import FS, FileSystem
from pyon.util.containers import DotDict
from mock import Mock, patch
import unittest




@attr('UNIT', group='dm')
class HDFArrayIteratorUnitTest(IonUnitTestCase):

    @unittest.skip('Unskip once numpy and h5py are imported in the module rather than the method')
    @patch('prototype.hdf.hdf_array_iterator.acquire_data.h5py')
    @patch('prototype.hdf.hdf_array_iterator._acquire_hdf_data', Mock(side_effect=TypeError))
    def test_acquire_data_closes_files_when_exception(self, h5mock):
        self.assertRaises(TypeError, acquire_data(['anything'], [], [], []))
        h5mock.File.close.assert_called_once_with()


@attr('INT', group='dm')
class HDFArrayIteratorTest_1d(IonIntegrationTestCase):

    def setUp(self):

        import numpy, h5py

        FileSystem(DotDict())

        #--------------------------------------------------------------------
        # Create an hdf file for testing
        #--------------------------------------------------------------------

        self.salinity = [0,]*3
        self.temperature = [0,]*3
        self.pressure = [0,]*3

        self.salinity[0] = numpy.arange(50)
        self.salinity[1] = numpy.arange(50) + 50
        self.salinity[2] = numpy.arange(50) + 100

        self.temperature[0] = numpy.random.normal(size=50)
        self.temperature[1] = numpy.random.normal(size=50)
        self.temperature[2] = numpy.random.normal(size=50)

        self.pressure[0] = numpy.random.uniform(low=0.0, high=1.0, size=50)
        self.pressure[1] = numpy.random.uniform(low=0.0, high=1.0, size=50)
        self.pressure[2] = numpy.random.uniform(low=0.0, high=1.0, size=50)

        # provide the check_pieces mathod the size of the dataset so that it can do its checking..
        self.sl = slice(0,150)

        self.fnames = [0,]*3
        for i in range(0,3):
            self.fnames[i] = FileSystem.get_url(FS.TEMP, 'data%d.hdf5' % (i+1))

        for fname, s, t, p in zip(self.fnames, self.salinity, self.temperature, self.pressure):
            file = h5py.File(fname, 'w')

            grp1 = file.create_group('fields')
            dset1 = grp1.create_dataset("salinity", data=s)
            dset2 = grp1.create_dataset("temperature", data=t)
            dset3 = grp1.create_dataset("pressure", data=p)

            file.close()


        # Concatenate the test values for comparison:

        self.t_result = numpy.concatenate((self.temperature[0],self.temperature[1],self.temperature[2]), axis = 0)
        self.s_result = numpy.concatenate((self.salinity[0],self.salinity[1],self.salinity[2]), axis = 0)
        self.p_result = numpy.concatenate((self.pressure[0],self.pressure[1],self.pressure[2]), axis = 0)



    def tearDown(self):
        """
        Cleanup. Delete Subscription, Stream, Process Definition
        """

        for fname in self.fnames:
            FileSystem.unlink(fname)

    def check_pieces_3_variables_1d(self, generator, sl, concatenate_size):


        start = sl.start
        stop = sl.start + concatenate_size
        end = sl.stop

        #        with self.assertRaises(StopIteration):

        while start < end - concatenate_size:

            out = generator.next()

            truth1 = out['temperature']['values'] == self.t_result[start:stop]
            truth2 = out['salinity']['values'] == self.s_result[start:stop]
            truth3 = out['pressure']['values'] == self.p_result[start:stop]

            self.assertTrue(truth1.all())
            self.assertTrue(truth2.all())
            self.assertTrue(truth3.all())

            start += concatenate_size
            stop += concatenate_size

        out = generator.next()

        truth1 = out['temperature']['values'] == self.t_result[start:end]
        truth2 = out['salinity']['values'] == self.s_result[start:end]
        truth3 = out['pressure']['values'] == self.p_result[start:end]

        if type(truth1) == bool: # this means that all the other variables, truth2 and truth 3 are also boolean
            self.assertTrue(truth1)
            self.assertTrue(truth2)
            self.assertTrue(truth3)

        else: # this means that truth1, truth2, and truth3 are numpy arrays with values True or False
            self.assertTrue(truth1.all())
            self.assertTrue(truth2.all())
            self.assertTrue(truth3.all())

        # check that trying to iterate again will yield a StopIteration
        with self.assertRaises(StopIteration):
            out = generator.next()

    def test_concatenate_size(self):

        #--------------------------------------------------------------------------------------
        # Test with a concatenate size greater than the length of the virtual dataset
        #--------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names = ['temperature', 'salinity', 'pressure'],
            concatenate_size = 175
        )

        out = generator.next()
        # assert the result...
        truth1 = out['temperature']['values'] == self.t_result
        truth2 = out['salinity']['values'] == self.s_result
        truth3 = out['pressure']['values'] == self.p_result

        self.assertTrue(truth1.all())
        self.assertTrue(truth2.all())
        self.assertTrue(truth3.all())

        with self.assertRaises(StopIteration):
            out = generator.next()

        #--------------------------------------------------------------------------------------------------------------------------
        # Test with a concatenate size less than the length of the virtual dataset such that mod(length, concatenate_size) == 0
        #--------------------------------------------------------------------------------------------------------------------------

        concatenate_size = 25

        generator = acquire_data(hdf_files = self.fnames,
            var_names = ['temperature', 'salinity', 'pressure'],
            concatenate_size = concatenate_size
        )

        self.check_pieces_3_variables_1d(generator, self.sl, concatenate_size)

        #--------------------------------------------------------------------------------------------------------------------------
        # Test with a concatenate size less than the length of the virtual dataset such that mod(length, concatenate_size) != 0
        #--------------------------------------------------------------------------------------------------------------------------

        sl = slice(3,63)
        concatenate_size = 26

        generator = acquire_data(hdf_files = self.fnames,
            var_names = ['temperature', 'salinity', 'pressure'],
            concatenate_size = concatenate_size,
            bounds=(sl)
        )

        # assert the result...
        self.check_pieces_3_variables_1d(generator, sl, concatenate_size)

    def test_var_names(self):

        # Test with no names
        # assert an error?

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  None,
            concatenate_size = 26,
            bounds = (slice(63,120))
        )

        with self.assertRaises(NotFound):
            out = generator.next()

        #---------------------------------------------------------------------------------------------------
        # Test with all names
        #---------------------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity', 'pressure'],
            concatenate_size = 26,
            bounds = (slice(63,120))
        )
        out = generator.next()

        # assert result

        truth1 = out['temperature']['values'] == self.t_result[63:89]
        truth2 = out['salinity']['values'] == self.s_result[63:89]
        truth3 = out['pressure']['values'] == self.p_result[63:89]

        self.assertTrue(truth1.all())
        self.assertTrue(truth2.all())
        self.assertTrue(truth3.all())

        #---------------------------------------------------------------------------------------------------
        # Test with some names
        #---------------------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity'],
            concatenate_size = 26,
            bounds = (slice(63,120))
        )
        out = generator.next()

        # assert result

        truth1 = out['temperature']['values'] == self.t_result[63:89]
        truth2 = out['salinity']['values'] == self.s_result[63:89]

        self.assertTrue(truth1.all())
        self.assertTrue(truth2.all())

        self.assertTrue('pressure' not in out)


        #---------------------------------------------------------------------------------------------------
        # Test with name not in dataset
        #---------------------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['biological_quotient'],
            concatenate_size = 26,
            bounds = (slice(63,120))
        )

        # assert an error

        with self.assertRaises(NotFound):
            out = generator.next()

    def test_bounds(self):

        #---------------------------------------------------------------------------------------------------
        # Test with bad input not a slice and not a tuple...
        #---------------------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity'],
            concatenate_size = 26,
            bounds = 's'
        )

        # Assert an error.

        with self.assertRaises(BadRequest):
            out = generator.next()

        #@todo can we make the error more transparent to the use - easier to correct their mistake?

        #---------------------------------------------------------------------------------------------------
        # Test with 2 tuple of slices on the 1d dataset
        #---------------------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity'],
            concatenate_size = 26,
            bounds = (slice(63,120), slice(63,120))
        )

        # Assert an error.

        with self.assertRaises(BadRequest):
            out = generator.next()

        #---------------------------------------------------------------------------------------------------
        # Test with bounds greater than the dataset length
        #---------------------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity'],
            concatenate_size = 200,
            bounds = (slice(0,200))
        )

        out = generator.next()

        # Assert result is the whole dataset

        truth1 = out['temperature']['values'] == self.t_result
        truth2 = out['salinity']['values'] == self.s_result

        self.assertTrue(truth1.all())
        self.assertTrue(truth2.all())

        # try to get the stop iteration by iterating again

        with self.assertRaises(StopIteration):
            out = generator.next()

        #---------------------------------------------------------------------------------------------------
        # Test with normal bounds slice
        #---------------------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity', 'pressure'],
            concatenate_size = 60,
            bounds = (slice(30,80))
        )
        out = generator.next()

        # assert result

        truth1 = out['temperature']['values'] == self.t_result[30:80]
        truth2 = out['salinity']['values'] == self.s_result[30:80]

        self.assertTrue(truth1.all())
        self.assertTrue(truth2.all())

        with self.assertRaises(StopIteration):
            out = generator.next()

        #---------------------------------------------------------------------------------------------------
        # Test with no bounds
        #---------------------------------------------------------------------------------------------------

        concatenate_size = 60

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity', 'pressure'],
            concatenate_size = concatenate_size
        )
        # assert result

        self.check_pieces_3_variables_1d(generator, self.sl, concatenate_size)

        #---------------------------------------------------------------------------------------------------
        # Test with concatenate larger than bounds slice
        #---------------------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity', 'pressure'],
            concatenate_size = 60,
            bounds = (slice(30,50))
        )
        out = generator.next()

        # assert result

        truth1 = out['temperature']['values'] == self.t_result[30:50]
        truth2 = out['salinity']['values'] == self.s_result[30:50]
        truth3 = out['pressure']['values'] == self.p_result[30:50]

        self.assertTrue(truth1.all())
        self.assertTrue(truth2.all())
        self.assertTrue(truth3.all())

        with self.assertRaises(StopIteration):
            out = generator.next()

        #---------------------------------------------------------------------------------------------------
        # Test with concatenate smaller than bounds slice
        #---------------------------------------------------------------------------------------------------

        sl = slice(30,100)
        concatenate_size = 10

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity', 'pressure'],
            concatenate_size = concatenate_size,
            bounds = (sl)
        )

        # assert result

        self.check_pieces_3_variables_1d(generator, sl, concatenate_size)



@attr('INT', group='dm')
class HDFArrayIteratorTest_2d(IonIntegrationTestCase):

    def setUp(self):

        import h5py, numpy

        #--------------------------------------------------------------------
        # Create an hdf file for testing
        #--------------------------------------------------------------------

        self.salinity = [0,]*3
        self.temperature = [0,]*3
        self.pressure = [0,]*3

        self.salinity[0] = numpy.arange(50).reshape(5,10)
        self.salinity[1] = numpy.arange(50).reshape(5,10) + 50
        self.salinity[2] = numpy.arange(50).reshape(5,10) + 100

        self.temperature[0] = numpy.random.normal(size=50).reshape(5,10)
        self.temperature[1] = numpy.random.normal(size=50).reshape(5,10)
        self.temperature[2] = numpy.random.normal(size=50).reshape(5,10)

        self.pressure[0] = numpy.random.uniform(low=0.0, high=1.0, size=50).reshape(5,10)
        self.pressure[1] = numpy.random.uniform(low=0.0, high=1.0, size=50).reshape(5,10)
        self.pressure[2] = numpy.random.uniform(low=0.0, high=1.0, size=50).reshape(5,10)

        # Concatenate the test values for comparison:

        self.t_result = numpy.concatenate((self.temperature[0],self.temperature[1],self.temperature[2]), axis = 0)
        self.s_result = numpy.concatenate((self.salinity[0],self.salinity[1],self.salinity[2]), axis = 0)
        self.p_result = numpy.concatenate((self.pressure[0],self.pressure[1],self.pressure[2]), axis = 0)

        # provide the check_pieces mathod the size of the dataset so that it can do its checking..
        self.slice_tuple = (slice(0,5),slice(0,10))

        self.fnames = ['data1.hdf5', 'data2.hdf5', 'data3.hdf5']

        for fname, s, t, p in zip(self.fnames, self.salinity, self.temperature, self.pressure):
            file = h5py.File(fname, 'w')

            grp1 = file.create_group('fields')
            dset1 = grp1.create_dataset("salinity", data=s)
            dset2 = grp1.create_dataset("temperature", data=t)
            dset3 = grp1.create_dataset("pressure", data=p)

            file.close()


    def tearDown(self):
        """
        Cleanup. Delete Subscription, Stream, Process Definition
        """

        for fname in self.fnames:
            os.remove(fname)

    def check_pieces_3_variables_2d(self, generator, slice_tuple , concatenate_size):
        """
        This method checks that the concatenated blocks are what they should be.
        """

        # Unpack the start and stop for each dimension from the slices

        # we need to keep track of the indices in the vertical dimension only, since the
        # concatenated blocks returned by the hdf_array_iterator are always going to be
        # (whole) valid matrices...
        # i.e. it will never return, [[1,2,3,4],[5,6,7,8],[9,10]], since that is not a matrix
        # instead it will chop it off the the form that is a valid matrix:
        # [[1,2,3,4],[5,6,7,8]]

        # therefore, we will also update the concatenate_size so that it is perfectly divisible by the
        # the number of entries in teh x dimension


        # calculate the vertical_start, vertical_stop indices in the y dimension... thats the only dimension we need to keep
        # track of because of the above mentioned reason

        print (concatenate_size)

        num_entries_x = slice_tuple[1].stop - slice_tuple[1].start

        vertical_start, vertical_end = (slice_tuple[0].start, slice_tuple[0].stop)
        vertical_stop = min(vertical_start + concatenate_size / num_entries_x, vertical_end)


        # since the hdf_array_iterator only provides complete valid matrices, we update
        # the concatenate_size being actually used

        concatenate_size = concatenate_size - concatenate_size % num_entries_x

        print ("vertical_start: %s, vertical_stop: %s, concatenate_size: %s" % (vertical_start,vertical_stop, concatenate_size))
        print ("vertical_end: %s" % vertical_end)
        print ("num_entries_x: %s" % num_entries_x)


        while vertical_stop < vertical_end:

            out = generator.next()

            y_stop = min(vertical_stop, vertical_end)

            truth1 = out['temperature']['values'] == self.t_result[vertical_start: y_stop , : min(concatenate_size, num_entries_x)]
            truth2 = out['salinity']['values'] == self.s_result[vertical_start: y_stop, : min(concatenate_size, num_entries_x)]
            truth3 = out['pressure']['values'] == self.p_result[vertical_start: y_stop, : min(concatenate_size, num_entries_x)]

            print ("checking here!")
            print ("%s==%s" % (out['temperature']['values'], self.t_result[vertical_start:vertical_stop, : min(concatenate_size, num_entries_x)]))
            self.assertTrue(truth1.all())
            self.assertTrue(truth2.all())
            self.assertTrue(truth3.all())

            vertical_start  = vertical_stop
            vertical_stop += concatenate_size / num_entries_x


    def test_concatenate_size(self):

        #--------------------------------------------------------------------------------------
        # Test with a concatenate size greater than the length of the virtual dataset
        #--------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names = ['temperature', 'salinity', 'pressure'],
            concatenate_size = 175
        )

        out = generator.next()

        # assert the result...
        truth1 = out['temperature']['values'] == self.t_result
        truth2 = out['salinity']['values'] == self.s_result
        truth3 = out['pressure']['values'] == self.p_result

        self.assertTrue(truth1.all())
        self.assertTrue(truth2.all())
        self.assertTrue(truth3.all())

        with self.assertRaises(StopIteration):
            out = generator.next()

        #--------------------------------------------------------------------------------------------------------------------------
        # Test with a concatenate size less than the length of the virtual dataset such that mod(length, concatenate_size) == 0
        #--------------------------------------------------------------------------------------------------------------------------

        concatenate_size = 14

        generator = acquire_data(hdf_files = self.fnames,
            var_names = ['temperature', 'salinity', 'pressure'],
            concatenate_size = concatenate_size
        )

        self.check_pieces_3_variables_2d(generator, self.slice_tuple, concatenate_size)

        #--------------------------------------------------------------------------------------------------------------------------
        # Test with a concatenate size less than the length of the virtual dataset such that mod(length, concatenate_size) != 0
        #--------------------------------------------------------------------------------------------------------------------------

        bounds = (slice(2,4), slice(2,8)) # on the x axis, choose indices 3..9, on the y axis, choose indices 2..7
        #@todo calculate the slice_tuple
        # slice_tuple =
        concatenate_size = 26

        generator = acquire_data(hdf_files = self.fnames,
            var_names = ['temperature', 'salinity', 'pressure'],
            concatenate_size = concatenate_size,
            bounds=bounds
        )

        # assert the result...
        self.check_pieces_3_variables_2d(generator, bounds, concatenate_size)


