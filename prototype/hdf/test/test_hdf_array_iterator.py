#!/usr/bin/env python

'''
@file ion/services/dm/ingestion/test/test_ingestion.py
@author Swarbhanu Chatterjee
@test ion.services.dm.ingestion.ingestion_management_service test suite to cover all ingestion mgmt service code
'''

from prototype.hdf.hdf_array_iterator import acquire_data


@attr('INT', group='dm')
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

    def tearDown(self):
        """
        Cleanup. Delete Subscription, Stream, Process Definition
        """
        self._stop_container()

    def test_acquire_data_from_multiple_files(self):
        """
        Test whether data can be acquired from multiple hdf5 files
        """

        generator = acquire_data(hdf_files = ['data.hdf5','measurements.hdf5'], var_name = None, buffer_size = 50, slice_= (slice(1,100)), concatenate_block_size = 12  )

        out = generator.next()

        # assert that the dataset 'salinity' in the first hdf5 file has been opened

        self.assertTrue('salinity' in out[4])

        out = generator.next()

        # assert that the second hdf5 file has been opened and one of its datasets has been opened
        self.assertTrue(('temperature' in out[4]) or ('conductivity' in out[4]) )


    def test_acquire_data_from_multiple_datasets(self):
        """
        Test whether data can be acquired from multiple datasets from an hdf5 file
        """

        generator = acquire_data(hdf_files = ['measurements.hdf5'], var_name = None, buffer_size = 50, slice_= (slice(1,100)), concatenate_block_size = 12  )

        out = generator.next()

        # assert that the dataset 'salinity' in the first hdf5 file has been opened

        self.assertTrue(('temperature' in out[4]) and ('conductivity' in out[4]))

    def test_acquire_data_with_var_name(self):
        """
        Test whether supplying a var_name confines the selection to be of only that var_name
        """

        generator = acquire_data(hdf_files = ['measurements.hdf5'], var_name = 'conductivity', buffer_size = 3, slice_= (slice(1,100)), concatenate_block_size = 12  )

        out = generator.next()

        # assert that the dataset 'salinity' in the first hdf5 file has been opened

        self.assertTrue('conductivity' in out[4])

        self.assertTrue(not ('temperature' in out[4]))

    def test_buffer_size(self):
        """
        Test that the chunk of data that is read from the hdf file is of the size buffer_size
        """

        buffer_size = 3

        generator = acquire_data(hdf_files = ['measurements.hdf5'], var_name = 'conductivity', buffer_size = buffer_size, slice_= (slice(1,100)), concatenate_block_size = 12  )

        out = generator.next()

        arr = out[3]

        self.assertEquals(arr.size, buffer_size)


    def test_concatenate_block_size(self):
        """
        Test that the concatenated arrays are of size concatenate_block_size
        """

        pass



