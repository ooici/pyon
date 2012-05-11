#!/usr/bin/env python


'''
@author Luke Campbell <lcampbell@asascience.com>
@file pyon/core/interceptor/test/interceptor_test.py
@description test lib for interceptor
'''
import unittest
from pyon.core.interceptor.encode import EncodeInterceptor
from pyon.core.interceptor.interceptor import Invocation
from pyon.util import log
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr

try:
    import numpy as np
    _have_numpy = True
except ImportError as e:
    _have_numpy = False

@attr('UNIT')
class InterceptorTest(PyonTestCase):
    @unittest.skipIf(not _have_numpy,'No numpy')
    def test_numpy_codec(self):

        a = np.array([90,8010,3,14112,3.14159265358979323846264],dtype='float32')

        invoke = Invocation()
        invoke.message = a
        codec = EncodeInterceptor()

        mangled = codec.outgoing(invoke)

        received = codec.incoming(mangled)

        b = received.message
        self.assertTrue((a==b).all())

        # Rank 1, length 1 works:
        a = np.array([90,8010,3,14112,3.14159265358979323846264],dtype='float32')
        mangled = codec.outgoing(invoke)

        received = codec.incoming(mangled)

        b = received.message
        self.assertTrue((a==b).all())

        # Rank 0 array raises Value Error because numpy tolist does not return a list
        a = np.array(3.14159265358979323846264,dtype='float32')

        invoke = Invocation()
        invoke.message = a

        self.assertRaises(ValueError, codec.outgoing, invoke)

    @unittest.skipIf(not _have_numpy,'No numpy')
    def test_packed_numpy(self):
        a = np.array([(90,8010,3,14112,3.14159265358979323846264)],dtype='float32')
        invoke = Invocation()
        invoke.message = {'double stuffed':[a,a,a]}
        codec = EncodeInterceptor()

        mangled = codec.outgoing(invoke)

        received = codec.incoming(mangled)

        b = received.message
        c = b.get('double stuffed')
        for d in c:
            self.assertTrue((a==d).all())

    def test_set(self):

        a = {'s':set([1,2,3]),'l':[1,2,3],'t':(1,2,3)}

        invoke = Invocation()
        invoke.message = a
        codec = EncodeInterceptor()

        mangled = codec.outgoing(invoke)

        received = codec.incoming(mangled)

        b = received.message

        # We only get lists back - damn you msgpack!
        only_lists = {'s':set([1,2,3]),'l':[1,2,3],'t':[1,2,3]}
        self.assertEquals(only_lists,b)