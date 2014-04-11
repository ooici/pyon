#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'
import gevent
import time

from pyon.util.async import blocking_cb, AsyncDispatcher
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr

@attr('UNIT')
class AsyncTest(IonIntegrationTestCase):
    def i_call_callbacks(self, cb):
        cb(1, 2, 3, foo='bar')

    def test_blocking(self):
        a, b, c, misc = blocking_cb(self.i_call_callbacks, cb_arg='cb')
        self.assertEqual((a, b, c, misc), (1, 2, 3, {'foo': 'bar'}))


@attr('UNIT')
class TestThreads(PyonTestCase):

    def load_clib(self):
        from ctypes import cdll, util
        try:
            clib = cdll.LoadLibrary(util.find_library('c'))
        except OSError as e:
            if 'image not found' in e.message:
                clib = cdll.LoadLibrary('libc.dylib') # The mac edge case
            else:
                raise
        return clib

    def clib_timeout(self):
        clib = self.load_clib()
        clib.sleep(5)

    def test_true_block(self):
        t0 = time.time()
        self.clib_timeout()
        t1 = time.time()

        self.assertTrue((t1 - t0) >= 5)

        t0 = time.time()
        g = gevent.spawn(self.clib_timeout)
        gevent.sleep(5)
        g.join()
        t1 = time.time()
        # If it was concurrent delta-t will be less than 10
        self.assertTrue((t1 - t0) >= 10)

        # Syncing with gevent
        t0 = time.time()
        with AsyncDispatcher(self.clib_timeout) as dispatcher:
            gevent.sleep(5)
            dispatcher.wait(10)
        t1 = time.time()

        # Proof that they run concurrently and the clib call doesn't block gevent
        self.assertTrue((t1 - t0) < 6)


        
