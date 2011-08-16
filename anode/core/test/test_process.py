#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from anode.core.process import GreenProcess, PythonProcess, GreenProcessSupervisor

import unittest
import time

class ProcessTest(unittest.TestCase):
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
        proc = sup.spawn(type='green', target=self.increment, amount=2)
        self.assertEqual(self.counter, 0)
        sup.join_children()
        self.assertEqual(self.counter, 2)

    def test_supervisor_shutdown(self):
        """ Test shutdown joining/forcing with timeouts. """
        sup = GreenProcessSupervisor()
        sup.start()

        # Test that it takes at least the given timeout to join_children, but not much more
        proc_sleep_secs = 0.001
        [sup.spawn('green', time.sleep, proc_sleep_secs)]
        elapsed = sup.shutdown(proc_sleep_secs)
        self.assertGreaterEqual(elapsed, proc_sleep_secs)
        self.assertLess(elapsed, proc_sleep_secs*1.5)

        # Test that a small timeout forcibly shuts down without waiting
        wait_secs = 0.000001
        [sup.spawn('green', time.sleep, proc_sleep_secs)]
        elapsed = sup.shutdown(wait_secs)
        self.assertGreaterEqual(elapsed, wait_secs)
        self.assertLess(elapsed, proc_sleep_secs)

        # Test that no timeout waits until all finished
        [sup.spawn('green', time.sleep, proc_sleep_secs)]
        elapsed = sup.shutdown()
        self.assertGreaterEqual(elapsed, proc_sleep_secs)

    def test_python(self):
        raise unittest.SkipTest('Need a better test here')
        self.counter = 0
        proc = PythonProcess(self.increment, 2)
        proc.start()
        self.assertEqual(self.counter, 0)
        proc.join()
        self.assertEqual(self.counter, 2)

if __name__ == '__main__':
    unittest.main()
