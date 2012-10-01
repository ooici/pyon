#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.unit_test import PyonTestCase
from pyon.util.int_test import IonIntegrationTestCase
from pyon.net.transport import NameTrio, BaseTransport, AMQPTransport, TransportError, TopicTrie, LocalRouter
from pyon.core.bootstrap import get_sys_name

from nose.plugins.attrib import attr
from mock import Mock, MagicMock, sentinel
from gevent.event import Event
import time

@attr('UNIT')
class TestTransport(PyonTestCase):
    pass

@attr('UNIT')
class TestAMQPTransport(PyonTestCase):

    def setUp(self):
        pass

    def test__sync_call_no_ret_value(self):

        def async_func(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam()

        tp = AMQPTransport(Mock())
        rv = tp._sync_call(async_func, 'callback')
        self.assertIsNone(rv)

    def test__sync_call_with_ret_value(self):
        def async_func(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam(sentinel.val)

        tp = AMQPTransport(Mock())
        rv = tp._sync_call(async_func, 'callback')
        self.assertEquals(rv, sentinel.val)

    def test__sync_call_with_mult_rets(self):
        def async_func(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam(sentinel.val, sentinel.val2)

        tp = AMQPTransport(Mock())
        rv = tp._sync_call(async_func, 'callback')
        self.assertEquals(rv, (sentinel.val, sentinel.val2))

    def test__sync_call_with_kwarg_rets(self):
        def async_func(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam(sup=sentinel.val, sup2=sentinel.val2)

        tp = AMQPTransport(Mock())
        rv = tp._sync_call(async_func, 'callback')
        self.assertEquals(rv, {'sup':sentinel.val, 'sup2':sentinel.val2})

    def test__sync_call_with_normal_and_kwarg_rets(self):
        def async_func(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam(sentinel.arg, sup=sentinel.val, sup2=sentinel.val2)

        tp = AMQPTransport(Mock())
        rv = tp._sync_call(async_func, 'callback')
        self.assertEquals(rv, (sentinel.arg, {'sup':sentinel.val, 'sup2':sentinel.val2}))

    def test__sync_call_with_error(self):
        tp = AMQPTransport(Mock())

        def async_func(*args, **kwargs):
            raise TransportError('haha')

        self.assertRaises(TransportError, tp._sync_call, async_func, 'callback')

@attr('UNIT')
class TestTopicTrie(PyonTestCase):
    def setUp(self):
        self.tt = TopicTrie()

    def test_many_matches(self):
        self.tt.add_topic_tree('a.b.c', sentinel.p1)
        self.tt.add_topic_tree('a.*.c', sentinel.p2)
        self.tt.add_topic_tree('*.b.c', sentinel.p3)
        self.tt.add_topic_tree('a.b.*', sentinel.p4)
        self.tt.add_topic_tree('*.*.c', sentinel.p5)
        self.tt.add_topic_tree('a.#',   sentinel.wild)
        self.tt.add_topic_tree('a.#.c', sentinel.middle_wild)

        self.assertEquals({sentinel.p1, sentinel.p2, sentinel.p3, sentinel.p4, sentinel.p5, sentinel.wild, sentinel.middle_wild},
                          set(self.tt.get_all_matches('a.b.c')))

        self.assertEquals({sentinel.p2, sentinel.p5, sentinel.wild, sentinel.middle_wild},
                          set(self.tt.get_all_matches('a.d.c')))

        self.assertEquals({sentinel.wild, sentinel.middle_wild},
                          set(self.tt.get_all_matches('a.b.b.b.b.b.b.c')))

        self.assertEquals({sentinel.wild},
                          set(self.tt.get_all_matches('a.b.b.b.b.b.b')))

@attr('UNIT')
class TestLocalRouter(PyonTestCase):

    def setUp(self):
        self.lr = LocalRouter(get_sys_name())
        self.lr.start()
        self.addCleanup(self.lr.stop)

        # make a hook so we can tell when a message gets routed
        self.ev = Event()
        def new_route(*args, **kwargs):
            self.ev.set()
            self.lr._oldroute(*args, **kwargs)
        self.lr._oldroute = self.lr._route
        self.lr._route = new_route

    def test_publish_to_unknown_exchange(self):
        self.assertEquals(len(self.lr.errors), 0)
        self.lr.publish('ex', 'rkey', 'body', 'props')
        self.ev.wait(timeout=10)
        self.assertEquals(len(self.lr.errors), 1)

    def test_publish_to_known_exchange(self):
        # declare exchange
        self.lr.declare_exchange('known')

        # send message
        self.lr.publish('known', 'rkey', 'body', 'props')

        # wait for route
        self.ev.wait(timeout=10)

        # message is binned but no errors
        self.assertEquals(len(self.lr.errors), 0)

    def test_publish_to_queue(self):
        # declare exchange/queue/binding
        self.lr.declare_exchange('known')
        self.lr.declare_queue('iamqueue')
        self.lr.bind('known', 'iamqueue', 'binzim')
        self.assertEquals(self.lr._queues['iamqueue'].qsize(), 0)

        # send message
        self.lr.publish('known', 'binzim', 'body', 'props')

        # wait for route
        self.ev.wait(timeout=10)

        # should be sitting in a queue waiting
        self.assertEquals(self.lr._queues['iamqueue'].qsize(), 1)
        #self.assertIn(('known', 'binzim', 'body', 'props'), self.lr._queues['iamqueue'])

    def test_publish_to_many_queues(self):
        # declare exchange/queue/binding
        self.lr.declare_exchange('known')
        self.lr.declare_queue('q1')
        self.lr.bind('known', 'q1', 'a.*')

        self.lr.declare_queue('q2')
        self.lr.bind('known', 'q2', 'a.b')

        self.lr.declare_queue('q3')
        self.lr.bind('known', 'q3', '*.b')

        # send message
        self.lr.publish('known', 'a.b', 'body', 'props')

        # wait for route
        self.ev.wait(timeout=10)

        # should be in 3 queues
        for q in ['q1','q2','q3']:
            self.assertEquals(self.lr._queues[q].qsize(), 1)
            #self.assertIn(('known', 'a.b', 'body', 'props'), self.lr._queues[q])

    def test_publish_to_queue_with_multiple_matching_binds_only_makes_one_message(self):
        # exchange/queue/bindings
        self.lr.declare_exchange('known')
        self.lr.declare_queue('iamqueue')
        self.lr.bind('known', 'iamqueue', 'a.*')
        self.lr.bind('known', 'iamqueue', 'a.b')
        self.lr.bind('known', 'iamqueue', '*.b')

        self.assertEquals(self.lr._queues['iamqueue'].qsize(), 0)

        # send message
        self.lr.publish('known', 'a.b', 'body', 'props')

        # wait for route
        self.ev.wait(timeout=10)

        # should be in the queue
        self.assertEquals(self.lr._queues['iamqueue'].qsize(), 1)
        #self.assertIn(('known', 'a.b', 'body', 'props'), self.lr._queues['iamqueue'])

    def test_publish_with_binds_and_unbinds(self):
        # declare exchange/queue
        self.lr.declare_exchange('known')
        self.lr.declare_queue('ein')

        self.assertEquals(self.lr._queues['ein'].qsize(), 0)

        # send message
        self.lr.publish('known', 'ein', 'body', 'props')

        # wait for route
        self.ev.wait(timeout=10)
        self.ev.clear() # we need to use again

        # not bound, so doesn't go into the queue
        self.assertEquals(self.lr._queues['ein'].qsize(), 0)

        # bind now
        self.lr.bind('known', 'ein', 'ein')

        # send message
        self.lr.publish('known', 'ein', 'body', 'props')

        # wait for route
        self.ev.wait(timeout=10)
        self.ev.clear() # we need to use again

        # should be in queue
        self.assertEquals(self.lr._queues['ein'].qsize(), 1)

        # send again
        self.lr.publish('known', 'ein', 'body', 'props')

        # wait for route
        self.ev.wait(timeout=10)
        self.ev.clear() # we need to use again

        # now 2 in queue
        self.assertEquals(self.lr._queues['ein'].qsize(), 2)

        # unbind
        self.lr.unbind('known', 'ein', 'ein')

        # send again
        self.lr.publish('known', 'ein', 'body', 'props')

        # wait for route
        self.ev.wait(timeout=10)
        self.ev.clear() # we need to use again

        # still 2 in queue
        self.assertEquals(self.lr._queues['ein'].qsize(), 2)



