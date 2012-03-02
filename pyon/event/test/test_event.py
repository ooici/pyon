#!/usr/bin/env python
from pyon.datastore.datastore import DatastoreManager

__author__ = 'Dave Foster <dfoster@asascience.com>, Michael Meisinger'
__license__ = 'Apache 2.0'

import time

from mock import Mock, sentinel, patch
from nose.plugins.attrib import attr
from gevent import event, queue
from unittest import SkipTest

from pyon.core import bootstrap
from pyon.event.event import EventPublisher, EventError, get_events_exchange_point, EventSubscriber, EventRepository
from pyon.net.messaging import NodeB
from pyon.util.async import spawn
from pyon.util.containers import get_ion_ts
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import IonUnitTestCase

from interface.objects import Event, ResourceLifecycleEvent

@attr('UNIT')
class TestEventPublisher(IonUnitTestCase):

    def setUp(self):
        self._node = Mock(spec=NodeB)
        self._pub = EventPublisher(node=self._node)

    def test_init(self):
        self.assertEquals(self._pub._send_name.exchange, "%s.pyon.events" % bootstrap.get_sys_name())
        self.assertEquals(self._pub._send_name.queue, None)

        pub = EventPublisher(node=self._node, xp=sentinel.xp)
        self.assertEquals(pub._send_name.exchange, sentinel.xp)
        self.assertEquals(pub._send_name.queue, None)

    def test__topic_no_origin(self):
        self.assertRaises(AssertionError, self._pub._topic, None)

    def test__topic(self):
        topic = self._pub._topic(sentinel.origin)
        self.assertIn(str(sentinel.origin), topic)
        self.assertIn(str(self._pub.event_name), topic)

        self.assertEquals(topic, "%s.%s" % (self._pub.event_name, str(sentinel.origin)))

    def test__topic_new_event_name(self):
        self._pub.event_name = sentinel.event_name

        topic2 = self._pub._topic(sentinel.origin2)
        self.assertEquals(topic2, "%s.%s" % (str(sentinel.event_name), str(sentinel.origin2)))

    def test__set_event_msg_fields_no_args(self):
        msg = Mock()     # Mock has a __dict__ member so this works

        pre_dict = str(msg.__dict__)
        unused = self._pub._set_event_msg_fields(msg, {})

        self.assertEquals(len(unused), 0)
        self.assertEquals(str(pre_dict), str(msg.__dict__))

    def test__set_event_msg_fields_args_not_in_msg(self):
        msg = Mock()

        pre_dict = str(msg.__dict__)
        unused = self._pub._set_event_msg_fields(msg, {'field': sentinel.value, 'field2': sentinel.value2})

        self.assertEquals(len(unused), 2)
        self.assertIn('field', unused)
        self.assertIn('field2', unused)

        self.assertEquals(str(pre_dict), str(msg.__dict__))

    def test__set_event_msg_fields(self):
        msg = Mock()
        msg.field = sentinel.old_value
        msg.field2 = sentinel.old_value2
        msg.field3 = sentinel.old_value3

        pre_dict = str(msg.__dict__)
        unused = self._pub._set_event_msg_fields(msg, {'field': sentinel.value, 'field2': sentinel.value2})

        self.assertEquals(len(unused), 0)
        self.assertNotEquals(str(pre_dict), str(msg.__dict__))

        self.assertEquals(msg.field, sentinel.value)
        self.assertEquals(msg.field2, sentinel.value2)
        self.assertEquals(msg.field3, sentinel.old_value3)

    @patch('pyon.event.event.bootstrap')
    def test_create_event_default_timestamp(self, mockobj):
        m = Mock()
        m.ts_created = sentinel.old_ts_created
        mockobj.IonObject.return_value = m

        ev = self._pub.create_event()
        mockobj.IonObject.assert_called_once_with(self._pub.msg_type)

        self.assertTrue(hasattr(ev, 'ts_created'))
        self.assertNotEquals(ev.ts_created, sentinel.old_ts_created)
        self.assertIsInstance(ev.ts_created, float)

    @patch('pyon.event.event.bootstrap')
    def test_create_event_with_kwargs(self, mockobj):
        m = Mock()
        m.ts_created = sentinel.old_ts_created
        m.field = sentinel.old_value
        mockobj.IonObject.return_value = m

        ev = self._pub.create_event(field=sentinel.value)
        mockobj.IonObject.assert_called_once_with(self._pub.msg_type)

        self.assertEquals(m.field, sentinel.value)

    @patch('pyon.event.event.bootstrap')
    def test_create_event_unknown_kwargs(self, mockobj):
        m = Mock()
        m.ts_created = sentinel.old_ts_created
        mockobj.IonObject.return_value = m

        with self.assertRaises(EventError) as cm:
            self._pub.create_event(extra=sentinel.extra)

        self.assertIn('extra', cm.exception.message)

    def test_publish_event_no_origin(self):
        self.assertRaises(AssertionError, self._pub.publish_event, sentinel.event_msg)

    def test_publish_event(self):
        self._pub.publish = Mock()

        self._pub.publish_event(sentinel.event_msg, origin=sentinel.origin)
        self._pub.publish.assert_called_once_with(sentinel.event_msg, to_name=(get_events_exchange_point(), self._pub._topic(sentinel.origin)))
        self._pub.publish().close.assert_called_once_with()

    def test_publish_event_with_event_repo(self):
        self._pub.publish = Mock()
        self._pub.event_repo = Mock()

        self._pub.publish_event(sentinel.event_msg, origin=sentinel.origin)

        self._pub.event_repo.put_event.assert_called_once_with(sentinel.event_msg)

    def test_create_and_publish_event(self):
        self._pub.create_event = Mock()
        self._pub.create_event.return_value = sentinel.event_msg
        self._pub.publish_event = Mock()

        self._pub.create_and_publish_event(origin=sentinel.origin, field=sentinel.value, field2=sentinel.value2)

        self._pub.create_event.assert_called_once_with(origin=sentinel.origin, field=sentinel.value, field2=sentinel.value2)
        self._pub.publish_event.assert_called_once_with(sentinel.event_msg, origin=sentinel.origin)

@attr('UNIT')
class TestEventSubscriber(IonUnitTestCase):
    def setUp(self):
        self._node = Mock(spec=NodeB)
        self._cb = lambda *args, **kwargs: False
        self._sub = EventSubscriber(node=self._node, callback=self._cb)

    def test_init(self):
        self.assertEquals(self._sub._recv_name.exchange, "%s.pyon.events" % bootstrap.get_sys_name())
        self.assertEquals(self._sub._recv_name.queue, None)
        self.assertEquals(self._sub._binding, "*.#")
        self.assertEquals(self._sub._callback, self._cb)

    def test_init_with_xp(self):
        sub = EventSubscriber(node=self._node, callback=self._cb, xp_name=sentinel.xp)
        self.assertEquals(sub._recv_name.exchange, sentinel.xp)
        self.assertEquals(sub._recv_name.queue, None)

    def test_init_with_event_name(self):
        sub = EventSubscriber(node=self._node, callback=self._cb, event_name=sentinel.event_name)
        self.assertEquals(sub._binding, "%s.#" % str(sentinel.event_name))

    def test_init_with_origin(self):
        sub = EventSubscriber(node=self._node, callback=self._cb, event_name=sentinel.event_name, origin=sentinel.origin)
        self.assertEquals(sub._binding, "%s.%s" % (str(sentinel.event_name), str(sentinel.origin)))

    def test_init_with_queue_name(self):
        sub = EventSubscriber(node=self._node, callback=self._cb, xp_name=sentinel.xp, queue_name=str(sentinel.queue))
        self.assertEquals(sub._recv_name.exchange, sentinel.xp)
        self.assertEquals(sub._recv_name.queue, "%s.%s" % (bootstrap.get_sys_name(), str(sentinel.queue)))

    def test_init_with_queue_name_with_sysname(self):
        queue_name = "%s-dacshund" % bootstrap.get_sys_name()
        sub = EventSubscriber(node=self._node, callback=self._cb, xp_name=sentinel.xp, queue_name=queue_name)
        self.assertEquals(sub._recv_name.exchange, sentinel.xp)
        self.assertEquals(sub._recv_name.queue, queue_name)

    def test__topic(self):
        self.assertEquals(self._sub._topic(None), "*.#")

    def test__topic_with_name(self):
        self._sub._event_name = "pancakes"
        self.assertEquals(self._sub._topic(None), "pancakes.#")

    def test__topic_with_origin(self):
        self.assertEquals(self._sub._topic(sentinel.origin), "*.%s" % str(sentinel.origin))

    def test__topic_with_name_and_origin(self):
        self._sub._event_name = "pancakes"
        self.assertEquals(self._sub._topic(sentinel.origin), "pancakes.%s" % str(sentinel.origin))

@attr('INT')
class TestEvents(IonIntegrationTestCase):

    class TestEventPublisher(EventPublisher):
        event_name = "TESTEVENT"
    class TestEventSubscriber(EventSubscriber):
        event_name = "TESTEVENT"

    def setUp(self):
        self._listens = []
        self._start_container()

    def tearDown(self):
        for x in self._listens:
            x.kill()
        self._stop_container()

    def _listen(self, sub):
        """
        Pass in a subscriber here, this will make it listen in a background greenlet.
        """
        gl = spawn(sub.listen)
        self._listens.append(gl)
        sub._ready_event.wait(timeout=5)

        return gl

    def test_pub_and_sub(self):
        ar = event.AsyncResult()
        def cb(*args, **kwargs):
            ar.set(args)
        sub = self.TestEventSubscriber(node=self.container.node, callback=cb, origin="specific")
        pub = self.TestEventPublisher(node=self.container.node)

        self._listen(sub)
        pub.create_and_publish_event(origin="specific", description="hello")

        evmsg, evheaders = ar.get(timeout=5)

        self.assertEquals(evmsg.description, "hello")
        self.assertAlmostEquals(evmsg.ts_created, time.time(), delta=5000)

    def test_pub_with_event_repo(self):
        pub = self.TestEventPublisher(node=self.container.node, event_repo=self.container.event_repository)
        pub.create_and_publish_event(origin="specifics", description="hallo")

        evs = self.container.event_repository.find_events(origin='specifics')
        self.assertEquals(len(evs), 1)

    def test_pub_on_different_origins(self):
        ar = event.AsyncResult()
        gq = queue.Queue()
        self.count = 0

        def cb(*args, **kwargs):
            self.count += 1
            gq.put(args[0])
            if self.count == 3:
                ar.set()

        sub = self.TestEventSubscriber(node=self.container.node, callback=cb)
        pub = self.TestEventPublisher(node=self.container.node)

        self._listen(sub)

        pub.create_and_publish_event(origin="one", description="1")
        pub.create_and_publish_event(origin="two", description="2")
        pub.create_and_publish_event(origin="three", description="3")

        ar.get(timeout=5)

        res = []
        for x in xrange(self.count):
            res.append(gq.get(timeout=5))

        self.assertEquals(len(res), 3)
        self.assertEquals(res[0].description, "1")
        self.assertEquals(res[1].description, "2")
        self.assertEquals(res[2].description, "3")

    def test_base_subscriber_as_catchall(self):
        ar = event.AsyncResult()
        gq = queue.Queue()
        self.count = 0

        def cb(*args, **kwargs):
            self.count += 1
            gq.put(args[0])
            if self.count == 2:
                ar.set()

        sub = EventSubscriber(node=self.container.node, callback=cb)
        pub1 = self.TestEventPublisher(node=self.container.node)
        pub2 = EventPublisher(node=self.container.node)

        self._listen(sub)

        pub1.create_and_publish_event(origin="some", description="1")
        pub2.create_and_publish_event(origin="other", description="2")

        ar.get(timeout=5)

        res = []
        for x in xrange(self.count):
            res.append(gq.get(timeout=5))

        self.assertEquals(len(res), 2)
        self.assertEquals(res[0].description, "1")
        self.assertEquals(res[1].description, "2")

    def test_subscriber_listening_for_specific_origin(self):
        ar = event.AsyncResult()
        self.count = 0
        def cb(*args, **kwargs):
            self.count += 1
            ar.set(args[0])

        sub = self.TestEventSubscriber(node=self.container.node, origin="specific", callback=cb)
        pub = self.TestEventPublisher(node=self.container.node)

        self._listen(sub)

        pub.create_and_publish_event(origin="notspecific", description="1")
        pub.create_and_publish_event(origin="notspecific", description="2")
        pub.create_and_publish_event(origin="specific", description="3")
        pub.create_and_publish_event(origin="notspecific", description="4")

        evmsg = ar.get(timeout=5)
        self.assertEquals(self.count, 1)
        self.assertEquals(evmsg.description, "3")

@attr('UNIT',group='datastore')
class TestEventRepository(IonUnitTestCase):
    def test_event_repo(self):
        if bootstrap.CFG.system.mockdb:
            raise SkipTest("only works with CouchDB views")

        dsm = DatastoreManager()

        event_repo = EventRepository(dsm)
        event_repo1 = EventRepository(dsm)

        event1 = Event(origin="resource1")
        event_id, _ = event_repo.put_event(event1)

        event1r = event_repo.get_event(event_id)
        self.assertEquals(event1.origin, event1r.origin)

        ts = 1328680477138
        events2 = []
        for i in xrange(5):
            ev = Event(origin="resource2", ts_created=str(ts + i))
            event_id, _ = event_repo.put_event(ev)
            events2.append((ev,event_id))

        events_r = event_repo.find_events(origin='resource2')
        self.assertEquals(len(events_r), 5)

        events_r = event_repo.find_events(origin='resource2', reverse_order=True)
        self.assertEquals(len(events_r), 5)

        events_r = event_repo.find_events(origin='resource2', max_results=3)
        self.assertEquals(len(events_r), 3)

        events_r = event_repo.find_events(origin='resource2', start_ts=str(ts+3))
        self.assertEquals(len(events_r), 2)

        events_r = event_repo.find_events(origin='resource2', end_ts=str(ts+2))
        self.assertEquals(len(events_r), 3)

        events_r = event_repo.find_events(origin='resource2', start_ts=str(ts+3), end_ts=str(ts+4))
        self.assertEquals(len(events_r), 2)

        events_r = event_repo.find_events(start_ts=str(ts+3), end_ts=str(ts+4))
        self.assertEquals(len(events_r), 2)


        event3 = ResourceLifecycleEvent(origin="resource3")
        event_id, _ = event_repo.put_event(event3)

        events_r = event_repo.find_events(event_type="ResourceLifecycleEvent")
        self.assertEquals(len(events_r), 1)
