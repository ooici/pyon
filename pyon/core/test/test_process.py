#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from pyon.core.process import GreenProcess, PythonProcess, GreenProcessSupervisor
from pyon.test.pyontest import PyonTestCase
from unittest import SkipTest

import time

class ProcessTest(PyonTestCase):
    def setUp(self):
        self.counter = 0

    def increment(self, amount=1):
        self.counter += amount

    def test_green(self):
        self.counter = 0
        proc = GreenProcess(self.increment, 2)
        proc.start()
        self.assertEqual(self.counter, 0)
        proc.join()
        self.assertEqual(self.counter, 2)

    def test_supervisor(self):
        self.counter = 0
        sup = GreenProcessSupervisor()
        sup.start()
        proc = sup.spawn(('green', self.increment), amount=2)
        self.assertEqual(self.counter, 0)
        sup.join_children()
        self.assertEqual(self.counter, 2)

    def test_supervisor_shutdown(self):
        """ Test shutdown joining/forcing with timeouts. """
        sup = GreenProcessSupervisor()
        sup.start()

        import gevent
        self.assertIs(time.sleep, gevent.hub.sleep)

        # Test that it takes at least the given timeout to join_children, but not much more
        proc_sleep_secs, proc_count = 0.01, 5
        [sup.spawn(('green', time.sleep), proc_sleep_secs) for i in xrange(5)]
        elapsed = sup.shutdown(proc_sleep_secs)
        self.assertGreaterEqual(elapsed, proc_sleep_secs)
        self.assertLess(elapsed, proc_sleep_secs*3)

        # Test that a small timeout forcibly shuts down without waiting
        wait_secs = 0.0001
        [sup.spawn(('green', time.sleep), proc_sleep_secs) for i in xrange(5)]
        elapsed = sup.shutdown(wait_secs)
        self.assertGreaterEqual(elapsed, wait_secs)
        self.assertLess(elapsed, proc_sleep_secs)

        # Test that no timeout waits until all finished
        [sup.spawn(('green', time.sleep), proc_sleep_secs) for i in xrange(5)]
        elapsed = sup.shutdown()
        self.assertGreaterEqual(elapsed, proc_sleep_secs)

    def test_python(self):
        raise SkipTest('Need a better test here')
        self.counter = 0
        proc = PythonProcess(self.increment, 2)
        proc.start()
        self.assertEqual(self.counter, 0)
        proc.join()
        self.assertEqual(self.counter, 2)
