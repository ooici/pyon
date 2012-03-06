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
from pyon.core.exception import NotFound, BadRequest
import h5py, numpy


@attr('INT', group='dm')
class HDFArrayIteratorTest_1d(IonIntegrationTestCase):

    def setUp(self):


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

        self.fnames = ['data1.hdf5', 'data2.hdf5', 'data3.hdf5']

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
            os.remove(fname)


    def test_concatenate_size(self):

        #--------------------------------------------------------------------------------------
        # Test with a concatenate size greater than the length of the virtual dataset
        #--------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names = ['temperature', 'salinity'],
            concatenate_size = 175
        )

        # assert the result...
        out = generator.next()

        truth = out['temperature']['values'] == self.t_result
        self.assertTrue(truth.all())
        self.assertEquals(str(out['salinity']['values']), str(salinity[63:89]) )

        #---------------------------------------------------------------------------------------------------
        # Test with a concatenate size less than the length of the virtual dataset such that mod(length, concatenate_size) == 0
        #---------------------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names = ['temperature', 'salinity'],
            concatenate_size = 25
        )

        # assert the result...
        out = generator.next()

        temperature = numpy.concatenate((self.temperature[0],self.temperature[1],self.temperature[2]), axis = 0)
        salinity = numpy.concatenate((self.salinity[0],self.salinity[1],self.salinity[2]), axis = 0)

        self.assertEquals(str(out['temperature']['values']), str(temperature[63:120]))
        self.assertEquals(str(out['salinity']['values']), str(salinity[63:120]) )

        #---------------------------------------------------------------------------------------------------
        # Test with a concatenate size less than the length of the virtual dataset such that mod(length, concatenate_size) != 0
        #---------------------------------------------------------------------------------------------------

        generator = acquire_data(hdf_files = self.fnames,
            var_names = ['temperature', 'salinity'],
            concatenate_size = 26,
        )

        # assert the result...
        out = generator.next()

        temperature = numpy.concatenate((self.temperature[0],self.temperature[1],self.temperature[2]), axis = 0)
        salinity = numpy.concatenate((self.salinity[0],self.salinity[1],self.salinity[2]), axis = 0)

        self.assertEquals(str(out['temperature']['values']), str(temperature[63:89]))
        self.assertEquals(str(out['salinity']['values']), str(salinity[63:89]) )


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




        self.assertEquals(str(out['temperature']['values']), str(temperature[63:89]))
        self.assertEquals(str(out['salinity']['values']), str(salinity[63:89]) )
        self.assertEquals(str(out['pressure']['values']), str(pressure[63:89]))

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

        temperature = numpy.concatenate((self.temperature[0],self.temperature[1],self.temperature[2]), axis = 0)
        salinity = numpy.concatenate((self.salinity[0],self.salinity[1],self.salinity[2]), axis = 0)


        self.assertEquals(str(out['temperature']['values']), str(temperature[63:89]))
        self.assertEquals(str(out['salinity']['values']), str(salinity[63:89]) )

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

        # Test with bad input not a slice and not a tuple...

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity'],
            concatenate_size = 26,
            bounds = 's'
        )

        # Assert an error.

        with self.assertRaises(BadRequest):
            out = generator.next()

        #@todo can we make the error more transparent to the use - easier to correct their mistake?

        # Test with 2 tuple of slices on the 1d dataset

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity'],
            concatenate_size = 26,
            bounds = (slice(63,120), slice(63,120))
        )

        # Assert an error.

        with self.assertRaises(BadRequest):
            out = generator.next()

        # Test with bounds greater than the dataset length

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity'],
            concatenate_size = 200,
            bounds = (slice(0,200))
        )

        out = generator.next()

        # Assert result is the whole dataset

        temperature = numpy.concatenate((self.temperature[0],self.temperature[1],self.temperature[2]), axis = 0)
        salinity = numpy.concatenate((self.salinity[0],self.salinity[1],self.salinity[2]), axis = 0)


        self.assertEquals(str(out['temperature']['values']), str(temperature))
        self.assertEquals(str(out['salinity']['values']), str(salinity) )

        # Test with normal bounds slice

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity', 'pressure'],
            concatenate_size = 60,
            bounds = (slice(30,80))
        )
        out = generator.next()

        # assert result

        temperature = numpy.concatenate((self.temperature[0],self.temperature[1],self.temperature[2]), axis = 0)
        salinity = numpy.concatenate((self.salinity[0],self.salinity[1],self.salinity[2]), axis = 0)
        pressure = numpy.concatenate((self.pressure[0],self.pressure[1],self.pressure[2]), axis = 0)


        self.assertEquals(str(out['temperature']['values']), str(temperature[30:80]))
        self.assertEquals(str(out['salinity']['values']), str(salinity[30:80]) )
        self.assertEquals(str(out['pressure']['values']), str(pressure[30:80]))

        # Test with no bounds
        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity', 'pressure'],
            concatenate_size = 60,
            bounds = None
        )
        out = generator.next()

        # assert result

        temperature = numpy.concatenate((self.temperature[0],self.temperature[1],self.temperature[2]), axis = 0)
        salinity = numpy.concatenate((self.salinity[0],self.salinity[1],self.salinity[2]), axis = 0)
        pressure = numpy.concatenate((self.pressure[0],self.pressure[1],self.pressure[2]), axis = 0)


        self.assertEquals(str(out['temperature']['values']), str(temperature[0:60]))
        self.assertEquals(str(out['salinity']['values']), str(salinity[0:60]) )
        self.assertEquals(str(out['pressure']['values']), str(pressure[0:60]))


        # Test with concatenate larger than bounds slice

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity', 'pressure'],
            concatenate_size = 60,
            bounds = (slice(30,50))
        )
        out = generator.next()

        # assert result

        temperature = numpy.concatenate((self.temperature[0],self.temperature[1],self.temperature[2]), axis = 0)
        salinity = numpy.concatenate((self.salinity[0],self.salinity[1],self.salinity[2]), axis = 0)
        pressure = numpy.concatenate((self.pressure[0],self.pressure[1],self.pressure[2]), axis = 0)


        self.assertEquals(str(out['temperature']['values']), str(temperature[30:50]))
        self.assertEquals(str(out['salinity']['values']), str(salinity[30:50]) )
        self.assertEquals(str(out['pressure']['values']), str(pressure[30:50]))

        # Test with concatenate smaller than bounds slice

        generator = acquire_data(hdf_files = self.fnames,
            var_names =  ['temperature', 'salinity', 'pressure'],
            concatenate_size = 10,
            bounds = (slice(30,100))
        )
        out = generator.next()

        # assert result

        temperature = numpy.concatenate((self.temperature[0],self.temperature[1],self.temperature[2]), axis = 0)
        salinity = numpy.concatenate((self.salinity[0],self.salinity[1],self.salinity[2]), axis = 0)
        pressure = numpy.concatenate((self.pressure[0],self.pressure[1],self.pressure[2]), axis = 0)


        self.assertEquals(str(out['temperature']['values']), str(temperature[30:40]))
        self.assertEquals(str(out['salinity']['values']), str(salinity[30:40]) )
        self.assertEquals(str(out['pressure']['values']), str(pressure[30:40]))

    def test_files_close(self):

        # Test that files are closed when method compelete normally
        ## How?

        # Test that files are close when acquire data fails too!
        ## how?
        pass



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


    def simple_test(self):



        generator = acquire_data(hdf_files = self.fnames,
            var_names = ['temperature', 'salinity'],
            concatenate_size = 25,
            bounds = None #(slice(63,150))
        )


        for d in generator:
            print 'Hello!', d



