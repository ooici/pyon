#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from mock import sentinel, Mock
from nose.plugins.attrib import attr
from pyon.ion.process import IonProcessThread
from pyon.util.int_test import IonIntegrationTestCase
from pyon.ion.endpoint import ProcessRPCServer
from gevent.event import AsyncResult, Event
from gevent.coros import Semaphore
from pyon.util.unit_test import PyonTestCase
import time
from pyon.util.context import LocalContextMixin

@attr('UNIT', group='process')
class ProcessTest(PyonTestCase):

    class ExpectedFailure(StandardError):
        pass

    def test_spawn_proc_with_no_listeners(self):
        p = IonProcessThread(name=sentinel.name, listeners=[])
        p.start()
        p.get_ready_event().wait(timeout=5)

        self.assertEquals(len(p.thread_manager.children), 1)

        p._notify_stop()

        self.assertTrue(p.thread_manager.children[0].proc.dead)

        p.stop()

    def test_spawn_proc_with_one_listener(self):
        mocklistener = Mock(spec=ProcessRPCServer)
        p = IonProcessThread(name=sentinel.name, listeners=[mocklistener])
        readyev = Event()
        readyev.set()
        mocklistener.get_ready_event.return_value = readyev
        p.start()
        p.get_ready_event().wait(timeout=5)
        p.start_listeners()

        self.assertEquals(len(p.thread_manager.children), 2)
        mocklistener.listen.assert_called_once_with()
        self.assertEqual(mocklistener.routing_call, p._routing_call)

        p._notify_stop()

        mocklistener.close.assert_called_once_with()

        p.stop()

    def test_spawn_with_listener_failure(self):
        mocklistener = Mock(spec=ProcessRPCServer)
        mocklistener.listen.side_effect = self.ExpectedFailure
        readyev = Event()
        readyev.set()
        mocklistener.get_ready_event.return_value = readyev

        p = IonProcessThread(name=sentinel.name, listeners=[mocklistener])
        p.start()
        p.get_ready_event().wait(timeout=5)
        p.start_listeners()

        # the exception is linked to the main proc inside the IonProcess, so that should be dead now
        self.assertTrue(p.proc.dead)
        self.assertIsInstance(p.proc.exception, self.ExpectedFailure)

        # stopping will raise an error as proc died already
        self.assertRaises(self.ExpectedFailure, p._notify_stop)

        # make sure control flow proc died though
        self.assertTrue(p.thread_manager.children[-1].proc.dead)

        p.stop()

    def test__routing_call(self):
        svc = LocalContextMixin()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)

        ar = AsyncResult()
        p._routing_call(ar.set, None, value=sentinel.callarg)

        v = ar.get(timeout=5)
        self.assertEquals(v, sentinel.callarg)

        p._notify_stop()
        p.stop()

    def test_competing__routing_call(self):
        svc = LocalContextMixin()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)

        sem = Semaphore()

        # define a callable method that tries to grab a shared semaphore
        def thecall(ar=None):

            semres = sem.acquire(blocking=False)
            if not semres:
                raise StandardError("Could not get semaphore, routing_call/control flow is broken!")

            # make this take a sec
            time.sleep(1)

            # make sure we release
            sem.release()

            # set the ar
            ar.set(True)

        # schedule some calls (in whatever order)
        ar1 = AsyncResult()
        ar2 = AsyncResult()
        ar3 = AsyncResult()

        p._routing_call(thecall, None, ar=ar3)
        p._routing_call(thecall, None, ar=ar1)
        p._routing_call(thecall, None, ar=ar2)

        # wait on all the ARs to be set
        ar1.get(timeout=5)
        ar2.get(timeout=5)
        ar3.get(timeout=5)

        # just getting here without throwing an exception is the true test!

        p._notify_stop()
        p.stop()



