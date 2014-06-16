#!/usr/bin/env python

__author__ = 'Adam R. Smith'


from pyon.core.thread import PyonThreadManager, PyonThread
from pyon.core.exception import ContainerError
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from unittest import SkipTest
from nose.plugins.attrib import attr

import time

@attr('UNIT', group='process')
class ProcessTest(PyonTestCase):
    def setUp(self):
        self.counter = 0

    def increment(self, amount=1):
        self.counter += amount

    def test_proc(self):
        self.counter = 0
        proc = PyonThread(self.increment, 2)
        proc.start()
        self.assertEqual(self.counter, 0)
        time.sleep(0.2)
        proc.join()
        self.assertGreaterEqual(self.counter, 2)

    def test_supervisor(self):
        self.counter = 0
        sup = PyonThreadManager()
        sup.start()
        proc = sup.spawn(self.increment, amount=2)
        self.assertEqual(self.counter, 0)
        time.sleep(0.2)
        sup.join_children()
        self.assertGreaterEqual(self.counter, 2)

    def test_supervisor_shutdown(self):
        """ Test shutdown joining/forcing with timeouts. """
        sup = PyonThreadManager()
        sup.start()

        import gevent
        self.assertIs(time.sleep, gevent.hub.sleep)

        # Test that it takes at least the given timeout to join_children, but not much more
        proc_sleep_secs, proc_count = 0.01, 5
        [sup.spawn(time.sleep, seconds=proc_sleep_secs) for i in xrange(5)]
        elapsed = sup.shutdown(2*proc_sleep_secs)
        # MM, 1/12: Ok, I loosened the timing boundaries. Do the tests still work?
        # Enabled 0.2s of slack for all tests

        self.assertLess(elapsed - proc_sleep_secs, 0.2)

        # this could be trouble
        self.assertLess(elapsed, 0.2 + proc_sleep_secs*3)

        # Test that a small timeout forcibly shuts down without waiting
        wait_secs = 0.0001
        [sup.spawn(time.sleep, seconds=proc_sleep_secs) for i in xrange(5)]
        elapsed = sup.shutdown(wait_secs)
        self.assertLess(elapsed - wait_secs, 0.2)

        # this could be trouble too
        self.assertLess(elapsed, 0.2 + proc_sleep_secs)

        # Test that no timeout waits until all finished
        [sup.spawn(time.sleep, seconds=proc_sleep_secs) for i in xrange(5)]
        elapsed = sup.shutdown()
        self.assertLess(elapsed - proc_sleep_secs, 0.2)

    def test_ensure_ready(self):
        # GreenProcess by default will signal ready immediately, but we can still pass it through to make sure it's ok
        sup = PyonThreadManager()
        sup.start()

        proc = sup.spawn(self.increment, amount=5)
        sup.ensure_ready(proc)

        self.assertEqual(self.counter, 5)

    def test_ensure_ready_failed_proc(self):
        # yes the error we print is intentional and annoying, sorry

        def failboat():
            self.increment(5, 1)    # too many params, will fail

        sup = PyonThreadManager()
        sup.start()

        proc = sup.spawn(failboat)
        self.assertRaises(ContainerError, sup.ensure_ready, proc)


