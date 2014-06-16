#!/usr/bin/env python

__author__ = 'Adam R. Smith'


from pyon.util.async import blocking_cb, AsyncDispatcher, get_pythread, AsyncResult, ThreadJob, AsyncTask, ThreadExit, ThreadPool
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
import gevent
import time
import unittest

class Timer(object):
    '''
    Simple context manager to measure the time to execute a block of code
    '''
    def __init__(self):
        object.__init__(self)
        self.dt = None

    def __enter__(self):
        self._t = time.time()
        return self

    def __exit__(self, type, value, traceback):
        self.dt = time.time() - self._t



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

    def clib_timeout(self, n=5):
        clib = self.load_clib()
        clib.sleep(int(n))
        return n

    def test_async_dispatcher(self):
        # Verify that the clib based sleep works correctly and doesn't raise
        with Timer() as timer:
            self.clib_timeout(2)
        self.assertTrue(timer.dt >= 2)

        # Verify that we can't concurrently use gevent and a clib's sleep
        with Timer() as timer:
            gevent.spawn(self.clib_timeout, 2)
            gevent.sleep(2)
            # Don't even need to join the thread
        # If it was concurrent delta-t will be less than 10
        self.assertTrue(timer.dt >= 4)

        # Syncing with gevent
        with Timer() as timer, AsyncDispatcher(self.clib_timeout, 2) as dispatcher:
            gevent.sleep(2)
            dispatcher.wait(10)

        # Proof that they run concurrently and the clib call doesn't block gevent
        self.assertTrue(timer.dt < 3)

    def dispatch(self, ar, callback, *args, **kwargs):
        try:
            retval = callback(*args, **kwargs)
            ar.set(retval)
        except Exception as e:
            ar.set_exception(e)

    #@unittest.skip("Conceptual test, no need to run everytime")
    def test_pyblock(self):
        '''
        Test to show that gevent can become blocked by python
        '''
        with Timer() as timer:
            # This usually blocks for about 10s on my machine
            gevent.spawn(self.pyblock, 49979687)
            gevent.sleep(0) # Gentle yield to the spawned thread

        # If gevent didn't get blocked then timer.dt would be a fraction of a second
        self.assertTrue(timer.dt > 5)



    def pyblock(self, n):
        '''
        A naive primality test. 
        Provides proof that pure python can block gevent by not yielding
        '''
        i = 2
        while i < n:
            if n % i == 0:
                return i
            i+= 1
        return None


    def delayed_set(self, ar, n):
        '''
        A greenlet task to wait a few then set an ar
        '''
        gevent.sleep(n)
        ar.set(True)

    def test_thread_pool(self):
        '''
        Test that verifies the capabilities of the thread pool don't block gevent
        '''
        pool = ThreadPool()

        # apply_sync for 5 threads all run concurrently
        with Timer() as timer:
            results = []
            for i in xrange(5):
                ar = pool.apply_async(self.clib_timeout, 2)
                results.append(ar)

            for r in results:
                r.wait(10)
                
        self.assertTrue(timer.dt < 3)


        # apply for one thread doesn't block gevent
        with Timer() as timer:
            # Launch a greenlet that sets an ar after 5s
            sync_ar = gevent.event.AsyncResult()
            gevent.spawn(self.delayed_set, sync_ar, 2)
            # Blocks the current gevent thread while waiting for the result
            v = pool.apply(self.clib_timeout, 2)
            # If the pool blocks gevent the time for both actions will be greater than 10
            self.assertEquals(v, 2)
            self.assertTrue(sync_ar.wait(5))

        self.assertTrue(timer.dt < 3)

        # Pool size
        pool.resize(2)
        with Timer() as timer:
            arg_list = [(2,), (2,), (2,), (2,)]
            pool.map(self.clib_timeout, arg_list)
        self.assertTrue(timer.dt < 5)

        pool.resize(4) # Bump up the pool size

        arg_list = [(2,), (2,), (2,), (2,)]
        # Pause each of the 4 workers for two seconds
        pool.map_async(self.clib_timeout, arg_list)

        # Now immediately resize to two
        with Timer() as timer:
            pool.resize(2, sync=True)
        self.assertTrue(timer.dt > 2 and timer.dt < 3)

        pool.resize(4)
        with self.assertRaises(SystemError):
            arg_list = [(2,), (2,), (2,), (2,)]
            pool.map_async(self.clib_timeout, arg_list)
            pool.close(sync=True, timeout=1)

