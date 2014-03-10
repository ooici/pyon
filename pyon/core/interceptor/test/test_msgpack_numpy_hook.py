#!/usr/bin/env python

'''
@author David Stuebe
@file pyon/core/interceptor/test/test_msgpack_numpy_hook.py
@description test for raw msgpack hook
'''


from nose.tools import *
import unittest

import collections
import time
import numpy
import random
from msgpack import packb, unpackb
import hashlib

from pyon.core.interceptor.encode import encode_ion, decode_ion


def sha1(buf):
    return hashlib.sha1(buf).hexdigest().upper()

count =0

class PackRunBase(object):

    _decoder = None
    _encoder = None

    types = collections.OrderedDict(
        [

            ('boolean',('bool',random.randint,(0, 1)) ),

            ('|S1',('|S1', lambda o: chr(count) , (None,) ) ),
            ('|S16',('|S16', lambda o: chr(count)*16 , (None,) ) ),

            ('int8',('int8',random.randint,(-(1 << 7), (1 << 7)-1)) ),
            ('int16',('int16',random.randint,(-(1 << 15), (1 << 15)-1)) ),
            ('int32',('int32',random.randint,(-(1 << 31), (1 << 31)-1)) ),
            ('int64',('int64',random.randint,(-(1 << 63), (1 << 63)-1)) ),

            ('uint8',('uint8',random.randint,(0, (1 << 8)-1)) ),
            ('uint16',('uint16',random.randint,(0, (1 << 16)-1)) ),
            ('uint32',('uint32',random.randint,(0, (1 << 32)-1)) ),
            ('uint64',('uint64',random.randint,(0, (1 << 64)-1)) ),


            ('float16_eps',('float16',lambda o: numpy.float16("1.0")+o ,(numpy.finfo('float16').eps,)) ),
            ('float16_epsneg',('float16',lambda o: 1-o ,(numpy.finfo('float16').epsneg,)) ),
            ('float16',('float16',numpy.random.uniform,(numpy.finfo('float16').min, numpy.finfo('float16').max)) ),

            ('float32_eps',('float32',lambda o: 1+o ,(numpy.finfo('float32').eps,)) ),
            ('float32_epsneg',('float32',lambda o: 1-o ,(numpy.finfo('float32').epsneg,)) ),
            ('float32',('float32',numpy.random.uniform,(numpy.finfo('float32').min, numpy.finfo('float32').max)) ),

            ('float64_eps',('float64',lambda o: 1+o ,(numpy.finfo('float64').eps,)) ),
            ('float64_epsneg',('float64',lambda o: 1-o ,(numpy.finfo('float64').epsneg,)) ),
            ('float64',('float64',numpy.random.uniform,(numpy.finfo('float64').min, numpy.finfo('float64').max)) ),

            ('complex64',('complex64',lambda a,b: numpy.complex(numpy.random.uniform(a,b), numpy.random.uniform(a,b)) ,(numpy.finfo('float32').min, numpy.finfo('float32').max)) ),
            ('complex128',('complex128',lambda a,b: numpy.complex(numpy.random.uniform(a,b), numpy.random.uniform(a,b)) ,(numpy.finfo('float64').min, numpy.finfo('float64').max)) ),


            ('object',('object',lambda o: {count:chr(count)*8}, (None,)))

        ]
    )

    shapes = ((1,),(3,4), (9,12,18), (10,10,10,10),)
    #shapes = ((100,100,10,10),)


    def __init__(self, *args, **kwargs):

        self._decoder = decode_ion
        self._encoder = encode_ion

    def test_all(self):

        for shape in self.shapes:
            print "========================"
            print "========================"
            print "========================"
            for type_name,(type, func, args) in self.types.iteritems():
                print "Running type: %s, shape: %s" % (type_name, str(shape))
                self.run_it(self._encoder, self._decoder, type, func, args, shape)


    def run_it(self, encoder, decoder, type, func, args, shape):

        array = numpy.zeros(shape, type)


        count = 0
        for x in numpy.nditer(array, flags=['refs_ok'], op_flags=['readwrite']):
            count +=1
            x[...] = func(*args)

        tic = time.time()
        msg = packb(array, default=encoder)
        new_array = unpackb(msg,object_hook=decoder)
        toc = time.time() - tic

        print 'Binary Size: "%d", Time: %s' % (len(msg), toc)

        assert_true((array == new_array).all())

        if type is not 'object':
            # Do a second check - based on sha1...
            assert_equals(sha1(array.tostring()), sha1(new_array.tostring()))


class NumpyMsgPackTestCase(unittest.TestCase, PackRunBase ):

    def __init__(self,*args, **kwargs):
        unittest.TestCase.__init__(self,*args, **kwargs)
        PackRunBase.__init__(self,*args, **kwargs)



if __name__ == '__main__':

    pb = PackRunBase()

    pb.test_all()

