#!/usr/bin/env python


__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.event.event import EventPublisher, EventError, get_events_exchange_point, EventSubscriber
from pyon.net.messaging import NodeB
from pyon.util.unit_test import PyonTestCase
from mock import Mock, sentinel, patch
from nose.plugins.attrib import attr
from pyon.core import bootstrap

@attr('UNIT')
class TestEventPublisher(PyonTestCase):

    def setUp(self):
        self._node = Mock(spec=NodeB)
        self._pub = EventPublisher(node=self._node)

    def test_init(self):
        self.assertEquals(self._pub.name, ("%s.pyon.events" % bootstrap.sys_name, None))

        pub = EventPublisher(node=self._node, xp=sentinel.xp)
        self.assertEquals(pub.name, (sentinel.xp, None))

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

    def test_create_and_publish_event(self):
        self._pub.create_event = Mock()
        self._pub.create_event.return_value = sentinel.event_msg
        self._pub.publish_event = Mock()

        self._pub.create_and_publish_event(origin=sentinel.origin, field=sentinel.value, field2=sentinel.value2)

        self._pub.create_event.assert_called_once_with(field=sentinel.value, field2=sentinel.value2)
        self._pub.publish_event.assert_called_once_with(sentinel.event_msg, origin=sentinel.origin)

@attr('UNIT')
class TestEventSubscriber(PyonTestCase):
    def setUp(self):
        self._node = Mock(spec=NodeB)
        self._cb = lambda *args, **kwargs: False
        self._sub = EventSubscriber(node=self._node, callback=self._cb)

    def test_init(self):
        self.assertEquals(self._sub.name, ("%s.pyon.events" % bootstrap.sys_name, None))
        self.assertEquals(self._sub._binding, "*.#")
        self.assertEquals(self._sub._callback, self._cb)

    def test_init_with_xp(self):
        sub = EventSubscriber(node=self._node, callback=self._cb, xp_name=sentinel.xp)
        self.assertEquals(sub.name, (sentinel.xp, None))

    def test_init_with_event_name(self):
        sub = EventSubscriber(node=self._node, callback=self._cb, event_name=sentinel.event_name)
        self.assertEquals(sub._binding, "%s.#" % str(sentinel.event_name))

    def test_init_with_origin(self):
        sub = EventSubscriber(node=self._node, callback=self._cb, event_name=sentinel.event_name, origin=sentinel.origin)
        self.assertEquals(sub._binding, "%s.%s" % (str(sentinel.event_name), str(sentinel.origin)))

    def test_init_with_queue_name(self):
        sub = EventSubscriber(node=self._node, callback=self._cb, xp_name=sentinel.xp, queue_name=str(sentinel.queue))
        self.assertEquals(sub.name, (sentinel.xp, "%s.%s" % (bootstrap.sys_name, str(sentinel.queue))))

    def test_init_with_queue_name_with_sysname(self):
        queue_name = "%s-dacshund" % bootstrap.sys_name
        sub = EventSubscriber(node=self._node, callback=self._cb, xp_name=sentinel.xp, queue_name=queue_name)
        self.assertEquals(sub.name, (sentinel.xp, queue_name))

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

