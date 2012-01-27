'''
@author Luke Campbell <lcampbell@asascience.com>
@file pyon/core/interceptor/test/interceptor_test.py
@description test lib for interceptor
'''
import unittest
from pyon.core.interceptor.codec import CodecInterceptor
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

        a = np.array([(90,8010,3,14112,3.14159265358979323846264)],dtype='float32')
        invoke = Invocation()
        invoke.message = a
        codec = CodecInterceptor()

        mangled = codec.outgoing(invoke)

        received = codec.incoming(mangled)

        b = received.message
        comp = (a==b)
        self.assertTrue(comp.all())
    @unittest.skipIf(not _have_numpy,'No numpy')
    def test_packed_numpy(self):
        a = np.array([(90,8010,3,14112,3.14159265358979323846264)],dtype='float32')
        invoke = Invocation()
        invoke.message = {'double stuffed':[a,a,a]}
        codec = CodecInterceptor()

        mangled = codec.outgoing(invoke)

        received = codec.incoming(mangled)

        b = received.message
        c = b.get('double stuffed')
        for d in c:
            e = (a==d)
            self.assertTrue(e.all())
