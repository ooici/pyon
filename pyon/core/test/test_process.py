#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from pyon.core.process import GreenProcess, PythonProcess, GreenProcessSupervisor
from pyon.core.exception import ContainerError
from pyon.util.int_test import IonIntegrationTestCase
from unittest import SkipTest
from nose.plugins.attrib import attr

import time

@attr('UNIT', group='process')
class ProcessTest(IonIntegrationTestCase):
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
        elapsed = sup.shutdown(2*proc_sleep_secs)
        # MM, 1/12: Ok, I loosened the timing boundaries. Do the tests still work?
        # Enabled 0.2s of slack for all tests

        self.assertLess(elapsed - proc_sleep_secs, 0.2)

        # this could be trouble
        self.assertLess(elapsed, 0.2 + proc_sleep_secs*3)

        # Test that a small timeout forcibly shuts down without waiting
        wait_secs = 0.0001
        [sup.spawn(('green', time.sleep), proc_sleep_secs) for i in xrange(5)]
        elapsed = sup.shutdown(wait_secs)
        self.assertLess(elapsed - wait_secs, 0.2)

        # this could be trouble too
        self.assertLess(elapsed, 0.2 + proc_sleep_secs)

        # Test that no timeout waits until all finished
        [sup.spawn(('green', time.sleep), proc_sleep_secs) for i in xrange(5)]
        elapsed = sup.shutdown()
        self.assertLess(elapsed - proc_sleep_secs, 0.2)

    def test_python(self):
        raise SkipTest('Need a better test here')
        self.counter = 0
        proc = PythonProcess(self.increment, 2)
        proc.start()
        self.assertEqual(self.counter, 0)
        proc.join()
        self.assertEqual(self.counter, 2)

    def test_ensure_ready(self):
        # GreenProcess by default will signal ready immediately, but we can still pass it through to make sure it's ok
        sup = GreenProcessSupervisor()
        sup.start()

        proc = sup.spawn(('green', self.increment), amount=5)
        sup.ensure_ready(proc)

        self.assertEqual(self.counter, 5)

    def test_ensure_ready_timeout(self):
        # we have to make a process with a get_ready_event that never fires
        class SlowGreenProcess(GreenProcess):
            def get_ready_event(self):
                from gevent.event import Event
                return Event()
            def target(self, *args, **kwargs):
                return "The goggles, they do nothing"

        sup = GreenProcessSupervisor()
        sup.start()

        proc = sup.spawn(SlowGreenProcess)
        self.assertRaises(ContainerError, sup.ensure_ready, proc, timeout=1)

    def test_ensure_ready_failed_proc(self):
        # yes the error we print is intentional and annoying, sorry

        def failboat():
            self.increment(5, 1)    # too many params, will fail

        sup = GreenProcessSupervisor()
        sup.start()

        proc = sup.spawn(('green', failboat))
        self.assertRaises(ContainerError, sup.ensure_ready, proc)



