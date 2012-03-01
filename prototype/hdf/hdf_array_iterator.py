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

def acquire_data( hdf_files = None, var_names=None, buffer_size = None, slice_=(), concatenate_block_size = None):

    arrays_out = {}

    # the numpy arrays will be stored here as a list to begin with

    # the default dataset names that are going to be used for input...
    default_var_names = ['temperature', 'conductivity', 'salinity', 'pressure']

    assert hdf_files, NotFound('No hdf_files provided to extract data from!')
    assert buffer_size, NotFound('No buffer_size provided.')

    import h5py, numpy

    def check_for_dataset(nodes):
        """
        A function to check for datasets in an hdf file and collect them
        """
        for node in nodes:
            if isinstance(node, h5py._hl.dataset.Dataset):
                list_of_h5py_datasets.append(node)
            elif isinstance( node , h5py._hl.group.Group):
                check_for_dataset(node.values())


    for hdf_file in hdf_files:

        # refresh the h5py dataset list
        list_of_h5py_datasets = []

        log.debug('Reading file: %s' % hdf_file)

        # make a file object
        f = h5py.File(hdf_file,'r')

        # get the list of groups or datasets if there are no groups in the file
        values = f.values()

        # checking for datasets in the hdf file
        check_for_dataset(values)

        log.debug('list_of_h5py_datasets: %s' % list_of_h5py_datasets)
        #--------------------------------------------------------------------------------
        # Use the ArrayIterator so that the arrays come in buffer sized chunks
        #--------------------------------------------------------------------------------

        # var_name = 'conductivity'
        if var_names is None:
            vars = default_var_names
        else:
            vars = [] + var_names

        if not isinstance(slice_, tuple): slice_ = (slice_,)

        for vn in vars:

            for dataset in list_of_h5py_datasets:

                str = dataset.name # in general this dataset name will have the grp/subgrp names also in it

                if str.rsplit('/', 1)[1] == vn: # strip off the grp and subgrp names

                    # the shape of the dataset is the same as the shape of the numpy array it contains
                    ndims = len(dataset.shape)

                    # Ensure the slice_ is the appropriate length
                    if len(slice_) < ndims:
                        slice_ += (slice(None),) * (ndims-len(slice_))

                    arri = ArrayIterator(dataset, buffer_size)[slice_]

                    for d in arri:
                        if d.dtype.char is "S":
                            # Obviously, we can't get the range of values for a string data type!
                            rng = None
                        elif isinstance(d, numpy.ma.masked_array):
                            # TODO: This is a temporary fix because numpy 'nanmin' and 'nanmax'
                            # are currently broken for masked_arrays:
                            # http://mail.scipy.org/pipermail/numpy-discussion/2011-July/057806.html
                            dc=d.compressed()
                            if dc.size == 0:
                                rng = None
                            else:
                                rng = (numpy.nanmin(dc), numpy.nanmax(dc))
                        else:
                            rng = (numpy.nanmin(d), numpy.nanmax(d))

                        if concatenate_block_size:

                            if vn in arrays_out:
                                if arrays_out[vn].size < concatenate_block_size:
                                    arrays_out[vn] = numpy.concatenate((arrays_out[vn], d), axis = 0)
                                else:
                                    indices_left = concatenate_block_size - arrays_out[vn].size

                                    arrays_out[vn] = numpy.concatenate((arrays_out[vn], d[:indices_left]), axis = 0)

                                    temp_array = d[indices_left:]

                                    # yields variable_name, the current slice, range, the sliced data,
                                    # the dictionary holding the concatenated arrays by variable name
                                    log.warn('size of array[%s]: %s' % (vn,arrays_out[vn].size))
                                    yield vn, arri.curr_slice, rng, d, arrays_out, arrays_out[vn]

                                    arrays_out[vn] = temp_array
                            else:
                                arrays_out[vn] = d

                        # if no concatenate_block_size is provided
                        else:

                            # to have the same yielded values as when the concatenate_block_size
                            # is provided, we need to make sure that an empty dictionary goes out for arrays_out
                            # and the arrays_out[vn] values are None

                            # its good to keep the same interface and that is why we are yielding the same
                            # number of output parameters for all cases of concatenate_block_size

                            yield vn, arri.curr_slice, rng, d, None, None



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