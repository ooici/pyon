#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from pyon.util.async import blocking_cb, AsyncDispatcher, get_pythread, AsyncResult, ThreadJob, AsyncQueue, AsyncTask, ThreadExit, ThreadPool
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
import gevent
import time
import unittest

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
        t0 = time.time()
        g = gevent.spawn(self.pyblock, 49979687) # usually blocks for about 10s on my machine
        gevent.sleep(0) # Gentle yield
        t1 = time.time() 
        self.assertTrue((t1-t0) > 5)



    def pyblock(self, n):
        i = 2
        while i < n:
            if n % i == 0:
                return i
            i+= 1
        return None


    def test_gevent(self):
        pythread = get_pythread()
        ar = AsyncResult()
        t0 = time.time()
        thread = pythread.start_new_thread(self.dispatch, (ar, self.clib_timeout, 5))
        gevent.sleep(5)
        v = ar.wait(10)
        t1 = time.time()
        self.assertTrue((t1-t0) < 6)

    def test_thread_queue(self):
        job_queue = AsyncQueue()
        task = AsyncTask(self.clib_timeout, 5)
        job_worker = ThreadJob(job_queue)
        job_queue.put(task)
        job_queue.put(ThreadExit())
        pythread = get_pythread()
        thread = pythread.start_new_thread(job_worker.run, tuple())

        v = task.ar.wait(10)
        print v

    def test_thread_pool(self):
        pool = ThreadPool()
        t0 = time.time()
        results = []
        for i in xrange(5):
            ar = pool.apply_async(self.clib_timeout, 5)
            results.append(ar)

        for r in results:
            r.wait(10)
            
        t1 = time.time()
        print (t1 - t0)
        pool.close()


