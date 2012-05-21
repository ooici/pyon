#!/usr/bin/env python

'''
@package ion.services.dm.ingestion
@file ion/services/dm/inventory/hdf_array_iterator.py
@author Swarbhanu Chatterjee
@brief HDFArrayIterator. Used in replay. Accepts a certain number of hdf files. Extracts the arrays out of them. Uses the ArrayIterator to
resize the arrays into blocks that are of the right size so that they do not have to be read into memory.
'''

from operator import mul
from pyon.core.exception import NotFound, BadRequest
from pyon.public import log
import itertools

def acquire_data( hdf_files = None, var_names=None, concatenate_size = None, bounds = None):


    import h5py, numpy

    if hdf_files is None:
        raise NotFound('No open_hdf_files provided to extract data from.')
    if var_names is None:
        raise NotFound('Variable names where not provided.')
    if concatenate_size is None:
        raise NotFound('The concatenation size was not provided')

    open_files = []

    try:
        for hdf_file in hdf_files:
            #-------------------------------------------------------------------------------------------------------
            # make a file object
            #-------------------------------------------------------------------------------------------------------
            try:
                file = h5py.File(hdf_file,'r')
            except IOError as ioe:
                log.exception('Unable to open file: "%s"', hdf_file)

                # Try again?
                try:
                    file = h5py.File(hdf_file,'r')

                except:
                    log.exception('Still Unable to open file: "%s" !', hdf_file)

                    # If we are only opening one file - we must fail - but otherwise for now, just let it go!
                    if len(hdf_files) == 1:
                        raise ioe



            open_files.append(file)

        gen = _acquire_hdf_data(open_hdf_files=open_files, var_names=var_names, concatenate_size=concatenate_size, bounds=bounds)

        # run the generator yielding to the caller
        for item in gen:
            yield item

    finally:
        # always clean up!
        for file in open_files:
            file.close()


def _acquire_hdf_data( open_hdf_files = None, var_names=None, concatenate_size = None, bounds = None):


    import h5py, numpy

    out_dict = {}


    def check_for_dataset(nodes, var_names):
        """
        A function to check for datasets in an hdf file and collect them
        """

        import h5py

        for node in nodes:

            if isinstance(node, h5py._hl.dataset.Dataset):

                #-------------------------------------------------------------------------------------------------------
                # if the name of the dataset (without grp/subgrp name) is one of the supplied variable names of interest,
                # update the dictionary for relevant datasets
                #-------------------------------------------------------------------------------------------------------

                dataset_name = node.name.rsplit('/', 1)[1]
                dataset = node

                if dataset_name in var_names:
                    dict_of_h5py_datasets[dataset_name] = dataset

            elif isinstance( node , h5py._hl.group.Group):
                check_for_dataset(node.values(), var_names)


    ### Declare a variable to hold array iterators:
    dataset_lists_by_name ={}

    for file in open_hdf_files:

        #-------------------------------------------------------------------------------------------------------
        # refresh the h5py dataset list
        #-------------------------------------------------------------------------------------------------------

        dict_of_h5py_datasets = {}
        chopped_end = {}

        log.debug('Reading file: %s' % file)

        #-------------------------------------------------------------------------------------------------------
        # get the list of groups or datasets if there are no groups in the file
        #-------------------------------------------------------------------------------------------------------

        nodes = file.values()

        #-------------------------------------------------------------------------------------------------------
        # checking for datasets in the hdf file whose names appear in the list of variable names supplied
        #-------------------------------------------------------------------------------------------------------

        check_for_dataset(nodes, var_names)
        log.debug('dict_of_h5py_datasets: %s' % dict_of_h5py_datasets)

        #-------------------------------------------------------------------------------------------------------
        # if no relevant dataset was found in the hdf file, then skip that file
        #-------------------------------------------------------------------------------------------------------

        if not dict_of_h5py_datasets:
            continue

        #-------------------------------------------------------------------------------------------------------
        # Iterate over the supplied variable names
        #-------------------------------------------------------------------------------------------------------

        for vname in var_names:

            #-------------------------------------------------------------------------------------------------------
            # fetch the dataset
            #-------------------------------------------------------------------------------------------------------

            dataset = dict_of_h5py_datasets.get(vname, None)

            #-------------------------------------------------------------------------------------------------------
            # if this variable is not in a dataset in the hdf file, skip this variable name for this hdf file
            #-------------------------------------------------------------------------------------------------------

            if dataset:
                # Add it to the list of datasets for this variable
                dset_list = dataset_lists_by_name.get(vname,[])
                dset_list.append(dataset)
                dataset_lists_by_name[vname] = dset_list


    array_iterators_by_name = {}

    if len(dataset_lists_by_name.keys()) == 0:
        raise NotFound('No dataset for the variables provided were found in the hdf files.')

    for vname, dset_list in dataset_lists_by_name.iteritems():

        # Create the dataset list object that behaves like a dataset
        virtual_dset = VirtualDataset(dset_list)

        if bounds:

            check_bounds(bounds, virtual_dset)

            iarray = ArrayIterator(virtual_dset, concatenate_size)[bounds]
        else:
            iarray = ArrayIterator(virtual_dset, concatenate_size)


        array_iterators_by_name[vname] = iarray

    log.warn(array_iterators_by_name)

    names = array_iterators_by_name.keys()
    iarrays = array_iterators_by_name.values() # Get the list of array iterators


    log.warn('Len iarrays: %d' % len(iarrays))
    for ichunks in itertools.izip_longest(*iarrays):

        log.warn('Len ichunks: %d' % len(ichunks))

        for name, chunk, iarray in itertools.izip(names, ichunks, iarrays):

            out_dict[name] = {'current_slice' : iarray.curr_slice,
                            'range' : (numpy.nanmin(chunk), numpy.nanmax(chunk)),
                            'values' : chunk}

        yield out_dict



def check_bounds(bounds, virtual_dset):
    """
    A method that checks the validity of user provided bounds
    """

    if type(bounds) != tuple and type(bounds) != slice:
        raise BadRequest('The provided parameter, bounds, is not a tuple as expected.')
    if type(bounds) == tuple and len(bounds) > len(virtual_dset.shape):
        raise BadRequest('The provided parameter, bounds, is trying to restrict more dimensions '
                         'than the how many are actually present in the data.')


class VirtualDataset(object):


    def __init__(self, var_list):

        import h5py, numpy

        self._vars = []

        self._records = 0

        self._starts = []
        self._stops = []


        agg_shape = None
        for var in var_list:

            vv = {}
            vv['data'] = var

            shape = var.shape
            vv['shape'] = shape

            # set the agg shape if not already set
            agg_shape = agg_shape or shape[1:]
            # assert that it is the same
            assert agg_shape == shape[1:]

            vv['records'] = shape[0]

            self._starts.append(self._records)

            self._records += shape[0]

            self._stops.append(self._records - 1 )

            self._vars.append(vv)

        self._agg_shape = agg_shape

        self._shape = (self._records, ) + self._agg_shape





    def __getitem__(self, index):
        import h5py, numpy

        assert len(index) == len(self.shape)

        get_start = index[0].start

        get_stop = index[0].stop

        assert get_stop > get_start

        agg_slices = index[1:]

        for start, stop, var in zip(self._starts, self._stops, self._vars):

            if stop < get_start:
                continue

            if start > get_stop:
                continue

            elif start <= get_start and stop >= get_start:
                # found the first of several chunks

                slc = slice(get_start-start, get_stop - start)

                aggregate = var['data'][(slc,) + agg_slices]


            elif start > get_start and start < get_stop:
                # this is the last bit of the chunk

                slc = slice(0, get_stop - start)

                new = var['data'][(slc,) + agg_slices]
                aggregate = numpy.concatenate((aggregate, new))


        return aggregate


    @property
    def __array_interface__(self):
        raise RuntimeError('Shit - I need array_interface!')

    @property
    def shape(self):
        return self._shape

    @property
    def size(self):
        # No good built in product function. http://stackoverflow.com/questions/2104782/returning-the-product-of-a-list
        res = 1
        for dim in self.shape:
            res *= dim
        return res

    def __iter__(self):
        # Skip arrays with degenerate dimensions
        raise RuntimeError('Shit - I need iter!')



#----------------------------------------------------------------------------------------------------------------------------
# Copied below ArrayIterator class written by Chris Mueller since eoi-services has not yet been included in my repositories
#----------------------------------------------------------------------------------------------------------------------------


class ArrayIterator(object):
    """
    Buffered iterator for big arrays.

    This class creates a buffered iterator for reading big arrays in small
    contiguous blocks. The class is useful for objects stored in the
    filesystem. It allows iteration over the object *without* reading
    everything in memory; instead, small blocks are read and iterated over.

    The class can be used with any object that supports multidimensional
    slices, like variables from Scientific.IO.NetCDF, pynetcdf and ndarrays.

    """

    def __init__(self, var, buf_size=None):
        self.var = var
        self.buf_size = buf_size

        self.start = [0 for dim in var.shape]
        self.stop = [dim for dim in var.shape]
        self.step = [1 for dim in var.shape]

        self.curr_slice = 'Not set yet!'

    def __getitem__(self, index):
        """
        Return a new arrayterator.

        """
        # Fix index, handling ellipsis and incomplete slices.
        if not isinstance(index, tuple): index = (index,)
        fixed = []
        length, dims = len(index), len(self.shape)
        for slice_ in index:
            if slice_ is Ellipsis:
                fixed.extend([slice(None)] * (dims-length+1))
                length = len(fixed)
            elif isinstance(slice_, (int, long)):
                fixed.append(slice(slice_, slice_+1, 1))
            else:
                fixed.append(slice_)
        index = tuple(fixed)
        if len(index) < dims:
            index += (slice(None),) * (dims-len(index))

        # Return a new arrayterator object.
        out = self.__class__(self.var, self.buf_size)
        for i, (start, stop, step, slice_) in enumerate(
            zip(self.start, self.stop, self.step, index)):

            log.debug('type of out: %s' % type(out))
            log.debug('slice_: %s' % str(slice_))

            out.start[i] = start + (slice_.start or 0)
            out.step[i] = step * (slice_.step or 1)
            out.stop[i] = start + (slice_.stop or stop-start)
            out.stop[i] = min(stop, out.stop[i])
        return out

    @property
    def __array_interface__(self):
        slice_ = tuple(slice(*t) for t in zip(
            self.start, self.stop, self.step))
        data = self.var[slice_].copy()
        return {
            'version': 3,
            'shape': self.shape,
            'typestr': data.dtype.str,
            'data': data,
            }

    @property
    def flat(self):
        for block in self:
            for value in block.flat:
                yield value

    @property
    def shape(self):
        return tuple(max(0, ((stop-start-1)//step+1))
        for start, stop, step in
        zip(self.start, self.stop, self.step))

    def __iter__(self):
        # Skip arrays with degenerate dimensions
        if [dim for dim in self.shape if dim <= 0]:
            log.warn("StopIteration called because of degernate dimensions")
            raise StopIteration

        start = self.start[:]
        stop = self.stop[:]
        step = self.step[:]
        ndims = len(self.var.shape)

        while 1:
            count = self.buf_size or reduce(mul, self.shape)

            # iterate over each dimension, looking for the
            # running dimension (ie, the dimension along which
            # the blocks will be built from)
            rundim = 0
            for i in range(ndims-1, -1, -1):
            # if count is zero we ran out of elements to read
                # along higher dimensions, so we read only a single position
                if count == 0:
                    stop[i] = start[i]+1
                elif count <= self.shape[i]:  # limit along this dimension
                    stop[i] = start[i] + count*step[i]
                    rundim = i
                else:
                    stop[i] = self.stop[i]  # read everything along this dimension
                stop[i] = min(self.stop[i], stop[i])
                count = count//self.shape[i]

            # yield a block
            slice_ = tuple(slice(*t) for t in zip(start, stop, step))
            self.curr_slice = slice_
            yield self.var[slice_]

            # If this is a scalar variable, bail out
            if ndims == 0:
                log.warn("StopIteration called because ndims is 0")
                raise StopIteration

            # Update start position, taking care of overflow to other dimensions
            start[rundim] = stop[rundim]  # start where we stopped
            for i in range(ndims-1, 0, -1):
                if start[i] >= self.stop[i]:
                    start[i] = self.start[i]
                    start[i-1] += self.step[i-1]
            if start[0] >= self.stop[0]:
                log.warn("StopIteration called because array was exhausted")
                raise StopIteration