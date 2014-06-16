#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'

from pyon.ion.process import IonProcessThread
from pyon.ion.endpoint import ProcessRPCServer
from gevent.event import AsyncResult, Event
from gevent.coros import Semaphore
from gevent.timeout import Timeout
from pyon.util.unit_test import PyonTestCase
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.context import LocalContextMixin
from pyon.core.exception import IonException, NotFound, ContainerError, Timeout as IonTimeout
from pyon.util.async import spawn
from mock import sentinel, Mock, MagicMock, ANY, patch
from nose.plugins.attrib import attr
from pyon.net.endpoint import RPCClient
from pyon.ion.service import BaseService
from interface.objects import ProcessStateEnum
import time
import os
import unittest

@attr('UNIT', group='coi')
class ProcessTest(PyonTestCase):

    class ExpectedFailure(StandardError):
        pass

    def _make_service(self):
        """
        Test helper to make a passable service.
        """
        svc           = LocalContextMixin()
        svc.id        = "test_id"
        svc.name      = "test_svc"
        svc.container = Mock()
        svc.container.context = LocalContextMixin()

        return svc

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
        mocklistener.listen.assert_called_once_with(thread_name=ANY)
        self.assertEqual(mocklistener.routing_call, p._routing_call)

        p._notify_stop()

        mocklistener.close.assert_called_once_with()

        p.stop()

    @unittest.skip("must be retooled to work with new listener spawn rules")
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
        svc = self._make_service()
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
        svc = self._make_service()
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

    def test_known_error(self):

        # IonExceptions and TypeErrors get forwarded back intact
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)
        self.addCleanup(p.stop)

        def proc_call():
            raise NotFound("didn't find it")

        def client_call(p=None, ar=None):
            try:
                ca = p._routing_call(proc_call, None)
                ca.get(timeout=5)

            except IonException as e:
                ar.set(e)

        ar = AsyncResult()
        gl_call = spawn(client_call, p=p, ar=ar)

        e = ar.get(timeout=5)

        self.assertIsInstance(e, NotFound)

    def test_unknown_error(self):

        # Unhandled exceptions get handled and then converted to ContainerErrors
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)
        self.addCleanup(p.stop)

        def proc_call():
            raise self.ExpectedError("didn't find it")

        def client_call(p=None, ar=None):
            try:
                ca = p._routing_call(proc_call, None)
                ca.get(timeout=5)

            except IonException as e:
                ar.set(e)

        ar = AsyncResult()
        gl_call = spawn(client_call, p=p, ar=ar)

        e = ar.get(timeout=5)

        self.assertIsInstance(e, ContainerError)
        self.assertEquals(len(p._errors), 1)

    def test_has_pending_call(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)

        ar = p._routing_call(sentinel.call, MagicMock())
        self.assertTrue(p.has_pending_call(ar))

    def test_has_pending_call_with_no_call(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)

        ar = p._routing_call(sentinel.call, MagicMock())
        # pretend we've processed it
        p._ctrl_queue.get()

        self.assertFalse(p.has_pending_call(ar))

    def test__cancel_pending_call(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)

        ar = p._routing_call(sentinel.call, MagicMock())
        val = p._cancel_pending_call(ar)

        self.assertTrue(val)
        self.assertTrue(ar.ready())

    def test__cancel_pending_call_with_no_call(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)

        ar = p._routing_call(sentinel.call, MagicMock())
        # pretend we've processed it
        p._ctrl_queue.get()

        val = p._cancel_pending_call(ar)

        self.assertFalse(val)

    def test__interrupt_control_thread(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)
        self.addCleanup(p.stop)

        # put a call in that will never finish
        waitar = AsyncResult()      # test specific, wait for this to indicate we're being processed/hung
        callar = AsyncResult()      # test specific, an ar that is just waited on by the spin call
        def spin(inar, outar):
            outar.set(True)
            inar.wait()

        ar = p._routing_call(spin, MagicMock(), callar, waitar)

        # wait until we get notice we're being processed
        waitar.get(timeout=2)

        # interrupt it
        p._interrupt_control_thread()

        # the ar we got back from routing_call will not be set, it never finished the call
        self.assertFalse(ar.ready())

        # to prove we're unblocked, run another call through the control thread
        ar2 = p._routing_call(callar.set, MagicMock(), sentinel.val)
        ar2.get(timeout=2)
        self.assertTrue(callar.ready())
        self.assertEquals(callar.get(), sentinel.val)

    def test__control_flow_cancelled_call(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)
        self.addCleanup(p.stop)

        # put a call in that will never finish
        waitar = AsyncResult()      # test specific, wait for this to indicate we're being processed/hung
        callar = AsyncResult()      # test specific, an ar that is just waited on by the spin call (eventually set in this test)
        def spin(inar, outar):
            outar.set(True)
            inar.wait()

        ar = p._routing_call(spin, MagicMock(), callar, waitar)

        # schedule a second call that we're going to cancel
        futurear = AsyncResult()
        ar2 = p._routing_call(futurear.set, MagicMock(), sentinel.val)

        # wait until we get notice we're being processed
        waitar.get(timeout=2)

        # cancel the SECOND call
        p.cancel_or_abort_call(ar2)

        # prove we didn't interrupt the current proc by allowing it to continue
        callar.set()
        ar.get(timeout=2)

        # now the second proc will get queued and never called because it is cancelled
        self.assertRaises(Timeout, futurear.get, timeout=2)
        self.assertTrue(ar2.ready())

    def test__control_flow_expired_call(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)
        self.addCleanup(p.stop)

        def make_call(call, ctx, val):
            ar = p._routing_call(call, ctx, val)
            return ar.get(timeout=10)

        ctx = { 'reply-by' : 0 }        # no need for real time, as it compares by CURRENT >= this value
        futurear = AsyncResult()
        with patch('pyon.ion.process.greenlet') as gcm:
            waitar = AsyncResult()
            gcm.getcurrent().kill.side_effect = lambda *a, **k: waitar.set()

            ar = p._routing_call(futurear.set, ctx, sentinel.val)

            waitar.get(timeout=10)

            # futurear is not set
            self.assertFalse(futurear.ready())

            # neither is the ar we got back from routing_call
            self.assertFalse(ar.ready())

            # we should've been killed, though
            self.assertEquals(gcm.getcurrent().kill.call_count, 1)
            self.assertIsInstance(gcm.getcurrent().kill.call_args[1]['exception'], IonTimeout)

        # put a new call through (to show unblocked)
        futurear2 = AsyncResult()
        ar2 = p._routing_call(futurear2.set, MagicMock(), sentinel.val2)
        ar2.get(timeout=2)

    def test_heartbeat_no_listeners(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)
        self.addCleanup(p.stop)

        hb = p.heartbeat()

        self.assertEquals((True, True, True), hb)
        self.assertEquals(0, p._heartbeat_count)
        self.assertIsNone(p._heartbeat_op)

    def test_heartbeat_with_listeners(self):
        mocklistener = Mock(spec=ProcessRPCServer)
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[mocklistener], service=svc)
        readyev = Event()
        readyev.set()
        mocklistener.get_ready_event.return_value = readyev

        def fake_listen(evout, evin):
            evout.set(True)
            evin.wait()

        listenoutev = AsyncResult()
        listeninev = Event()

        mocklistener.listen = lambda *a, **kw: fake_listen(listenoutev, listeninev)

        p.start()
        p.get_ready_event().wait(timeout=5)
        p.start_listeners()

        listenoutev.wait(timeout=5)         # wait for listen loop to start

        self.addCleanup(listeninev.set)     # makes listen loop fall out on shutdown
        self.addCleanup(p.stop)

        # now test heartbeat!
        hb = p.heartbeat()

        self.assertEquals((True, True, True), hb)
        self.assertEquals(0, p._heartbeat_count)
        self.assertIsNone(p._heartbeat_op)

    def test_heartbeat_listener_dead(self):
        mocklistener = Mock(spec=ProcessRPCServer)
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[mocklistener], service=svc)
        readyev = Event()
        readyev.set()
        mocklistener.get_ready_event.return_value = readyev

        def fake_listen(evout, evin):
            evout.set(True)
            evin.wait()

        listenoutev = AsyncResult()
        listeninev = Event()

        p.start()
        p.get_ready_event().wait(timeout=5)
        p.start_listeners()

        listenoutev.wait(timeout=5)         # wait for listen loop to start

        self.addCleanup(listeninev.set)     # makes listen loop fall out on shutdown
        self.addCleanup(p.stop)

        listeninev.set()                    # stop the listen loop
        p.thread_manager.children[1].join(timeout=5)        # wait for listen loop to terminate

        hb = p.heartbeat()

        self.assertEquals((False, True, True), hb)
        self.assertEquals(0, p._heartbeat_count)
        self.assertIsNone(p._heartbeat_op)

    def test_heartbeat_ctrl_thread_dead(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)
        self.addCleanup(p.stop)

        p._ctrl_thread.stop()

        hb = p.heartbeat()

        self.assertEquals((True, False, True), hb)
        self.assertEquals(0, p._heartbeat_count)
        self.assertIsNone(p._heartbeat_op)

    def test_heartbeat_with_current_op(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)
        p._ctrl_thread.ev_exit.set()            # prevent heartbeat loop in proc's target

        def fake_op(evout, evin):
            evout.set(True)
            evin.wait()

        listenoutev = AsyncResult()
        listeninev = Event()

        self.addCleanup(listeninev.set)     # allow graceful termination
        self.addCleanup(p.stop)

        ar = p._routing_call(fake_op, None, listenoutev, listeninev)

        listenoutev.wait(timeout=5)         # wait for ctrl thread to run our op

        hb = p.heartbeat()

        self.assertEquals((True, True, True), hb)
        self.assertEquals(1, p._heartbeat_count)
        self.assertEquals(ar, p._heartbeat_op)
        self.assertIsNotNone(p._heartbeat_time)
        self.assertIsNotNone(p._heartbeat_stack)

        self.assertIn("evin.wait", str(p._heartbeat_stack))

    def test_heartbeat_with_current_op_multiple_times(self):
        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)
        p._ctrl_thread.ev_exit.set()            # prevent heartbeat loop in proc's target

        def fake_op(evout, evin):
            evout.set(True)
            evin.wait()

        listenoutev = AsyncResult()
        listeninev = Event()

        self.addCleanup(listeninev.set)     # allow graceful termination
        self.addCleanup(p.stop)

        ar = p._routing_call(fake_op, None, listenoutev, listeninev)

        listenoutev.wait(timeout=5)         # wait for ctrl thread to run our op

        for x in xrange(5):
            hb = p.heartbeat()

        self.assertEquals((True, True, True), hb)
        self.assertEquals(5, p._heartbeat_count)
        self.assertEquals(ar, p._heartbeat_op)

    def test_heartbeat_current_op_over_limit(self):
        self.patch_cfg('pyon.ion.process.CFG', {'cc':{'timeout':{'heartbeat_proc_count_threshold':2}}})

        svc = self._make_service()
        p = IonProcessThread(name=sentinel.name, listeners=[], service=svc)
        p.start()
        p.get_ready_event().wait(timeout=5)
        p._ctrl_thread.ev_exit.set()            # prevent heartbeat loop in proc's target

        def fake_op(evout, evin):
            evout.set(True)
            evin.wait()

        listenoutev = AsyncResult()
        listeninev = Event()

        self.addCleanup(listeninev.set)     # allow graceful termination
        self.addCleanup(p.stop)

        ar = p._routing_call(fake_op, None, listenoutev, listeninev)

        listenoutev.wait(timeout=5)         # wait for ctrl thread to run our op

        # make sure it's over the threshold
        for x in xrange(3):
            hb = p.heartbeat()

        self.assertEquals((True, True, False), hb)

class FakeService(BaseService):
    """
    Class to use for testing below.
    """
    name = 'fake_service'
    dependencies = []

    def takes_too_long(self, noticear=None):
        if noticear is not None:
            noticear.set(True)
        ar = AsyncResult()
        ar.wait()

@attr('INT', group='coi')
@unittest.skip("no active tests, 18 oct 2012")
class TestProcessInt(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()
        self.pid = self.container.spawn_process('fake', 'pyon.ion.test.test_process', 'FakeService')
        self.fsclient = RPCClient(to_name='fake_service')

    @unittest.skip("timeouts removed 18 oct 2012")
    def test_timeout_with_messaging(self):
        with self.assertRaises(IonTimeout) as cm:
            self.fsclient.request({}, op='takes_too_long', timeout=5)

        self.assertIn('execute in allotted time', cm.exception.message)

    @unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False), "Test reaches into container, doesn't work with CEI")
    @unittest.skip("heartbeat failing process is disabled")
    def test_heartbeat_failure(self):
        self.patch_cfg('pyon.ion.process.CFG', {'cc':{'timeout':{'heartbeat_proc_count_threshold':2, 'heartbeat':1.0}}})

        svc = self.container.proc_manager.procs[self.pid]
        ip = svc._process
        stopar = AsyncResult()
        self.container.proc_manager.add_proc_state_changed_callback(lambda *args: stopar.set(args))

        noticear = AsyncResult()        # notify us when the call has been made
        ar = ip._routing_call(svc.takes_too_long, None, noticear=noticear)

        noticear.get(timeout=10)        # wait for the call to be made

        # heartbeat a few times so we trigger the failure soon
        for x in xrange(2):
            ip.heartbeat()

        # wait for ip thread to kick over
        ip._ctrl_thread.join(timeout=5)

        # now wait for notice proc got canned
        stopargs = stopar.get(timeout=5)

        self.assertEquals(stopargs, (svc, ProcessStateEnum.FAILED, self.container))

        # should've shut down, no longer in container's process list
        self.assertEquals(len(self.container.proc_manager.procs), 0)

