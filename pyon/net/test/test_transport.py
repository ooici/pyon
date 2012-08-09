#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.unit_test import PyonTestCase
from pyon.net.transport import NameTrio, BaseTransport, AMQPTransport, TransportError, TopicTrie

from nose.plugins.attrib import attr
from mock import Mock, MagicMock, sentinel

@attr('UNIT')
class TestTransport(PyonTestCase):
    pass

@attr('UNIT')
class TestAMQPTransport(PyonTestCase):

    def setUp(self):
        self.client = MagicMock()

    def test__sync_call_no_ret_value(self):

        def async_func(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam()

        tp = AMQPTransport()
        rv = tp._sync_call(self.client, async_func, 'callback')
        self.assertIsNone(rv)

    def test__sync_call_with_ret_value(self):
        def async_func(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam(sentinel.val)

        tp = AMQPTransport()
        rv = tp._sync_call(self.client, async_func, 'callback')
        self.assertEquals(rv, sentinel.val)

    def test__sync_call_with_mult_rets(self):
        def async_func(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam(sentinel.val, sentinel.val2)

        tp = AMQPTransport()
        rv = tp._sync_call(self.client, async_func, 'callback')
        self.assertEquals(rv, (sentinel.val, sentinel.val2))

    def test__sync_call_with_kwarg_rets(self):
        def async_func(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam(sup=sentinel.val, sup2=sentinel.val2)

        tp = AMQPTransport()
        rv = tp._sync_call(self.client, async_func, 'callback')
        self.assertEquals(rv, {'sup':sentinel.val, 'sup2':sentinel.val2})

    def test__sync_call_with_normal_and_kwarg_rets(self):
        def async_func(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam(sentinel.arg, sup=sentinel.val, sup2=sentinel.val2)

        tp = AMQPTransport()
        rv = tp._sync_call(self.client, async_func, 'callback')
        self.assertEquals(rv, (sentinel.arg, {'sup':sentinel.val, 'sup2':sentinel.val2}))

    def test__sync_call_with_error(self):
        tp = AMQPTransport()

        def async_func(*args, **kwargs):
            raise TransportError('haha')

        self.assertRaises(TransportError, tp._sync_call, self.client, async_func, 'callback')

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


