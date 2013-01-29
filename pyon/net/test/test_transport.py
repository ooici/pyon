#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.unit_test import PyonTestCase
from pyon.util.int_test import IonIntegrationTestCase
from pyon.net.transport import NameTrio, BaseTransport, AMQPTransport, TransportError, TopicTrie, LocalRouter, ComposableTransport, LocalTransport
from pyon.core.bootstrap import get_sys_name
from pika import BasicProperties

from nose.plugins.attrib import attr
from mock import Mock, MagicMock, sentinel, patch, call, ANY
from gevent.event import Event
import time

@attr('UNIT')
class TestTransport(PyonTestCase):
    def test_all_base_methods(self):
        # coverage++
        bt = BaseTransport()
        self.assertRaises(NotImplementedError, bt.declare_exchange_impl, sentinel.exchange)
        self.assertRaises(NotImplementedError, bt.delete_exchange_impl, sentinel.exchange)
        self.assertRaises(NotImplementedError, bt.declare_queue_impl, sentinel.queue)
        self.assertRaises(NotImplementedError, bt.delete_queue_impl, sentinel.queue)
        self.assertRaises(NotImplementedError, bt.bind_impl, sentinel.exchange, sentinel.queue, sentinel.binding)
        self.assertRaises(NotImplementedError, bt.unbind_impl, sentinel.exchange, sentinel.queue, sentinel.binding)
        self.assertRaises(NotImplementedError, bt.ack_impl, sentinel.dtag)
        self.assertRaises(NotImplementedError, bt.reject_impl, sentinel.dtag)
        self.assertRaises(NotImplementedError, bt.start_consume_impl, sentinel.callback, sentinel.queue)
        self.assertRaises(NotImplementedError, bt.stop_consume_impl, sentinel.ctag)
        self.assertRaises(NotImplementedError, bt.setup_listener, sentinel.binding, sentinel.callback)
        self.assertRaises(NotImplementedError, bt.get_stats_impl, sentinel.queue)
        self.assertRaises(NotImplementedError, bt.purge_impl, sentinel.queue)
        self.assertRaises(NotImplementedError, bt.qos_impl)
        self.assertRaises(NotImplementedError, bt.publish_impl, sentinel.exchange, sentinel.rkey, sentinel.body, sentinel.props)
        self.assertRaises(NotImplementedError, bt.close)
        with self.assertRaises(NotImplementedError):
            cn = bt.channel_number
        with self.assertRaises(NotImplementedError):
            ac = bt.active
        self.assertRaises(NotImplementedError, bt.add_on_close_callback, sentinel.callback)

@attr('UNIT')
class TestComposableTransport(PyonTestCase):
    def test_init(self):
        left = Mock()
        right = Mock()
        ct = ComposableTransport(left, right, *ComposableTransport.common_methods)

        self.assertEquals(ct._transports, [left, right])
        self.assertEquals(ct._methods, {'declare_exchange_impl': left.declare_exchange_impl,
                                        'delete_exchange_impl' : left.delete_exchange_impl,
                                        'declare_queue_impl'   : left.declare_queue_impl,
                                        'delete_queue_impl'    : left.delete_queue_impl,
                                        'bind_impl'            : left.bind_impl,
                                        'unbind_impl'          : left.unbind_impl,
                                        'purge_impl'           : left.purge_impl,
                                        'setup_listener'       : left.setup_listener,

                                        'ack_impl'             : right.ack_impl,
                                        'reject_impl'          : right.reject_impl,
                                        'start_consume_impl'   : right.start_consume_impl,
                                        'stop_consume_impl'    : right.stop_consume_impl,
                                        'get_stats_impl'       : right.get_stats_impl,
                                        'qos_impl'             : right.qos_impl,
                                        'publish_impl'         : right.publish_impl, })

    def test_overlay(self):
        left = Mock()
        ct = ComposableTransport(left, None)

        self.assertEquals(ct._transports, [left])

        right = Mock()

        ct.overlay(right, 'brambles')
        self.assertIn('brambles', ct._methods)
        self.assertEquals(ct._methods['brambles'], right.brambles)

    def test_overlay_multiple_times(self):
        left = Mock()
        ct = ComposableTransport(left, None)

        middle = Mock()
        ct.overlay(middle, 'wallof')
        right = Mock()
        ct.overlay(right, 'wallof')

        self.assertEquals(ct._transports, [left, middle, right])
        self.assertIn('wallof', ct._methods)
        self.assertEquals(ct._methods['wallof'], right.wallof)

    def test_overlay_and_call_all_methods(self):
        left = Mock()
        right = Mock()
        ct = ComposableTransport(left, right, *ComposableTransport.common_methods)

        ct.declare_exchange_impl(sentinel.exchange)
        ct.delete_exchange_impl(sentinel.exchange)
        ct.declare_queue_impl(sentinel.queue)
        ct.delete_queue_impl(sentinel.queue)
        ct.bind_impl(sentinel.exchange, sentinel.queue, sentinel.binding)
        ct.unbind_impl(sentinel.exchange, sentinel.queue, sentinel.binding)
        ct.ack_impl(sentinel.dtag)
        ct.reject_impl(sentinel.dtag)
        ct.start_consume_impl(sentinel.callback, sentinel.queue)
        ct.stop_consume_impl(sentinel.ctag)
        ct.setup_listener(sentinel.binding, sentinel.callback)
        ct.get_stats_impl(sentinel.queue)
        ct.purge_impl(sentinel.queue)
        ct.qos_impl()
        ct.publish_impl(sentinel.exchange, sentinel.rkey, sentinel.body, sentinel.props)

        left.declare_exchange_impl.assert_called_once_with(sentinel.exchange)
        left.delete_exchange_impl.assert_called_once_with(sentinel.exchange)
        left.declare_queue_impl.assert_called_once_with(sentinel.queue)
        left.delete_queue_impl.assert_called_once_with(sentinel.queue)
        left.bind_impl.assert_called_once_with(sentinel.exchange, sentinel.queue, sentinel.binding)
        left.unbind_impl.assert_called_once_with(sentinel.exchange, sentinel.queue, sentinel.binding)
        left.purge_impl.assert_called_once_with(sentinel.queue)
        left.setup_listener.assert_called_once_with(sentinel.binding, sentinel.callback)

        right.ack_impl.assert_called_once_with(sentinel.dtag)
        right.reject_impl.assert_called_once_with(sentinel.dtag, requeue=False)
        right.start_consume_impl.assert_called_once_with(sentinel.callback, sentinel.queue, no_ack=False, exclusive=False)
        right.stop_consume_impl.assert_called_once_with(sentinel.ctag)
        right.get_stats_impl.assert_called_once_with(sentinel.queue)
        right.qos_impl.assert_called_once_with(prefetch_size=0, prefetch_count=0, global_=False)
        right.publish_impl.assert_called_once_with(sentinel.exchange, sentinel.rkey, sentinel.body, sentinel.props, immediate=False, mandatory=False, durable_msg=False)

        # assert non-calls on other side
        self.assertEquals(right.declare_exchange_impl.call_count, 0)
        self.assertEquals(right.delete_exchange_impl.call_count, 0)
        self.assertEquals(right.declare_queue_impl.call_count, 0)
        self.assertEquals(right.delete_queue_impl.call_count, 0)
        self.assertEquals(right.bind_impl.call_count, 0)
        self.assertEquals(right.unbind_impl.call_count, 0)
        self.assertEquals(right.purge_impl.call_count, 0)
        self.assertEquals(right.setup_listener.call_count, 0)

        self.assertEquals(left.ack_impl.call_count, 0)
        self.assertEquals(left.reject_impl.call_count, 0)
        self.assertEquals(left.start_consume_impl.call_count, 0)
        self.assertEquals(left.stop_consume_impl.call_count, 0)
        self.assertEquals(left.get_stats_impl.call_count, 0)
        self.assertEquals(left.qos_impl.call_count, 0)
        self.assertEquals(left.publish_impl.call_count, 0)

    def test_close(self):
        left = Mock()
        right = Mock()
        ct = ComposableTransport(left, right)

        ct.close()

        left.close.assert_called_once_with()
        right.close.assert_called_once_with()

    def test_close_with_callbacks(self):
        left = Mock()
        right = Mock()
        ct = ComposableTransport(left, right)
        cb = Mock()

        ct.add_on_close_callback(cb)
        self.assertEquals(ct._close_callbacks, [cb])

        ct.close()

        left.close.assert_called_once_with()
        right.close.assert_called_once_with()

        cb.assert_called_once_with(ct, 200, "Closed OK")

    def test_channel_number(self):
        left = Mock()
        right = Mock()
        ct = ComposableTransport(left, right)

        self.assertEquals(ct.channel_number, right.channel_number)

    def test_active(self):
        left = Mock()
        right = Mock()
        left.active = True
        right.active = True
        ct = ComposableTransport(left, right)

        self.assertTrue(ct.active)

    def test_active_one_not(self):
        left = Mock()
        right = Mock()
        left.active = False
        right.active = True
        ct = ComposableTransport(left, right)

        self.assertFalse(ct.active)

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

    def test__sync_call_with_close_indicating_error(self):
        tp = AMQPTransport(Mock())

        def async_func(*args, **kwargs):
            tp._client.add_on_close_callback.call_args[0][0](sentinel.ch, sentinel.arg)

        self.assertRaises(TransportError, tp._sync_call, async_func, 'callback')
        tp._client.transport.connection.mark_bad_channel.assert_called_once_with(tp._client.channel_number)

    @patch('pyon.net.transport.log')
    def test__on_underlying_close(self, mocklog):
        client = Mock()
        tp = AMQPTransport(client)
        cb = Mock()
        tp.add_on_close_callback(cb)

        tp._on_underlying_close(200, sentinel.text)

        cb.assert_called_once_with(tp, 200, sentinel.text)
        self.assertEquals(mocklog.debug.call_count, 1)
        self.assertIn(sentinel.text, mocklog.debug.call_args[0])

        self.assertEquals(client.callbacks.remove.call_count, 4)
        self.assertEquals(client.callbacks.remove.call_args_list, [call(client.channel_number, 'Basic.GetEmpty'),
                                                                   call(client.channel_number, 'Channel.Close'),
                                                                   call(client.channel_number, '_on_basic_deliver'),
                                                                   call(client.channel_number, '_on_basic_get')])

    @patch('pyon.net.transport.log')
    def test__on_underlying_close_error(self, mocklog):
        tp = AMQPTransport(Mock())

        tp._on_underlying_close(404, sentinel.text)

        self.assertEquals(mocklog.error.call_count, 1)
        self.assertIn(sentinel.text, mocklog.error.call_args[0])
        self.assertEquals(mocklog.debug.call_count, 0)

    def test_active(self):
        tp = AMQPTransport(Mock())
        tp._client.closing = None
        self.assertTrue(tp.active)

    def test_active_no_client(self):
        tp = AMQPTransport(Mock())
        tp._client = None

        self.assertFalse(tp.active)

    def test_active_closing(self):
        tp = AMQPTransport(Mock())
        tp._client.closing = True

        self.assertFalse(tp.active)

    def test_close(self):
        client = Mock()
        tp = AMQPTransport(client)
        tp.close()

        client.close.assert_called_once_with()

    def test_close_while_locked(self):
        tp = AMQPTransport(Mock())
        tp.lock = True

        tp.close()

        self.assertEquals(tp._client.close.call_count, 0)
        self.assertEquals(tp._client.callbacks.remove.call_count, 0)

    def test_channel_number(self):
        client = Mock()
        tp = AMQPTransport(client)
        self.assertEquals(tp.channel_number, client.channel_number)

    def test_add_on_close_callback(self):
        tp = AMQPTransport(Mock())
        tp.add_on_close_callback(sentinel.one)
        tp.add_on_close_callback(sentinel.two)

        self.assertEquals(tp._close_callbacks, [sentinel.one, sentinel.two])

@attr('UNIT')
class TestAMQPTransportCommonMethods(PyonTestCase):

    def setUp(self):
        self.tp = AMQPTransport(MagicMock())
        self.tp._sync_call = Mock()

    def test_declare_exchange_impl(self):
        self.tp.declare_exchange_impl(sentinel.exchange)

        self.tp._sync_call.assert_called_once_with(self.tp._client.exchange_declare,
                                                   'callback',
                                                   exchange=sentinel.exchange,
                                                   type='topic',
                                                   durable=False,
                                                   auto_delete=True,
                                                   arguments={})

    @patch('pyon.net.transport.os', new_callable=MagicMock)
    def test_declare_exchange_impl_queue_blame(self, osmock):
        osmock.environ.get.return_value = True
        osmock.environ.__getitem__.return_value = sentinel.testid

        self.tp.declare_exchange_impl(sentinel.exchange)

        self.tp._sync_call.assert_called_once_with(self.tp._client.exchange_declare,
                                                   'callback',
                                                   exchange=sentinel.exchange,
                                                   type='topic',
                                                   durable=False,
                                                   auto_delete=True,
                                                   arguments={'created-by':sentinel.testid})

    def test_delete_exchange_impl(self):
        self.tp.delete_exchange_impl(sentinel.exchange)
        self.tp._sync_call.assert_called_once_with(self.tp._client.exchange_delete,
                                                   'callback',
                                                   exchange=sentinel.exchange)

    def test_declare_queue_impl(self):
        retqueue = self.tp.declare_queue_impl(sentinel.queue)

        self.tp._sync_call.assert_called_once_with(self.tp._client.queue_declare,
                                                   'callback',
                                                   queue=sentinel.queue,
                                                   auto_delete=True,
                                                   durable=False,
                                                   arguments={})

        self.assertEquals(retqueue, self.tp._sync_call.return_value.method.queue)

    @patch('pyon.net.transport.os', new_callable=MagicMock)
    def test_declare_queue_impl_queue_blame(self, osmock):
        osmock.environ.get.return_value = True
        osmock.environ.__getitem__.return_value = sentinel.testid

        retqueue = self.tp.declare_queue_impl(sentinel.queue)

        self.tp._sync_call.assert_called_once_with(self.tp._client.queue_declare,
                                                   'callback',
                                                   queue=sentinel.queue,
                                                   durable=False,
                                                   auto_delete=True,
                                                   arguments={'created-by':sentinel.testid})

        self.assertEquals(retqueue, self.tp._sync_call.return_value.method.queue)

    def test_delete_queue(self):
        self.tp.delete_queue_impl(sentinel.queue)

        self.tp._sync_call.assert_called_once_with(self.tp._client.queue_delete,
                                                   'callback',
                                                   queue=sentinel.queue)

    def test_bind_impl(self):
        self.tp.bind_impl(sentinel.exchange, sentinel.queue, sentinel.binding)

        self.tp._sync_call.assert_called_once_with(self.tp._client.queue_bind,
                                                   'callback',
                                                   queue=sentinel.queue,
                                                   exchange=sentinel.exchange,
                                                   routing_key=sentinel.binding)

    def test_unbind_impl(self):
        self.tp.unbind_impl(sentinel.exchange, sentinel.queue, sentinel.binding)

        self.tp._sync_call.assert_called_once_with(self.tp._client.queue_unbind,
                                                   'callback',
                                                   queue=sentinel.queue,
                                                   exchange=sentinel.exchange,
                                                   routing_key=sentinel.binding)

    def test_ack_impl(self):
        self.tp.ack_impl(sentinel.dtag)

        self.tp._client.basic_ack.assert_called_once_with(sentinel.dtag)

    def test_reject_impl(self):
        self.tp.reject_impl(sentinel.dtag)

        self.tp._client.basic_reject.assert_called_once_with(sentinel.dtag, requeue=False)

    def test_start_consume_impl(self):
        rettag = self.tp.start_consume_impl(sentinel.callback, sentinel.queue)

        self.tp._client.basic_consume.assert_called_once_with(sentinel.callback,
                                                              queue=sentinel.queue,
                                                              no_ack=False,
                                                              exclusive=False)

        self.assertEquals(rettag, self.tp._client.basic_consume.return_value)

    def test_stop_consume_impl(self):
        self.tp.stop_consume_impl(sentinel.ctag)

        self.tp._sync_call.assert_called_once_with(self.tp._client.basic_cancel,
                                                   'callback',
                                                   sentinel.ctag)

    @patch('pyon.net.transport.sleep', Mock())      # patch to make sleep() be a mock call and therefore superfast
    def test_stop_consume_remains_in_consumers(self):
        self.tp._client._consumers = [sentinel.ctag]
        self.assertRaises(TransportError, self.tp.stop_consume_impl, sentinel.ctag)

    @patch('pyon.net.transport.sleep')
    def test_stop_consume_eventually_removed(self, sleepmock):
        self.tp._client._consumers.__contains__.side_effect = [True, False, False] # is checked once more at exit of method

        self.tp.stop_consume_impl(sentinel.ctag)
        sleepmock.assert_called_once_with(1)

    def test_setup_listener(self):
        cb = Mock()
        self.tp.setup_listener(sentinel.binding, cb)

        cb.assert_called_once_with(self.tp, sentinel.binding)

    def test_get_stats_impl(self):
        mo = Mock()
        self.tp._sync_call.return_value = mo
        ret = self.tp.get_stats_impl(sentinel.queue)

        self.tp._sync_call.assert_called_once_with(self.tp._client.queue_declare,
                                                   'callback',
                                                   queue=sentinel.queue,
                                                   passive=True)

        self.assertEquals(ret, (mo.method.message_count, mo.method.consumer_count))

    def test_purge_impl(self):
        self.tp.purge_impl(sentinel.queue)

        self.tp._sync_call.assert_called_once_with(self.tp._client.queue_purge,
                                                   'callback',
                                                   queue=sentinel.queue)

    def test_qos_impl(self):
        self.tp.qos_impl()

        self.tp._sync_call.assert_called_once_with(self.tp._client.basic_qos,
                                                   'callback',
                                                   prefetch_size=0,
                                                   prefetch_count=0,
                                                   global_=False)

    @patch('pyon.net.transport.BasicProperties')
    def test_publish_impl(self, bpmock):
        self.tp.publish_impl(sentinel.exchange, sentinel.routing_key, sentinel.body, sentinel.properties)

        self.tp._client.basic_publish.assert_called_once_with(exchange=sentinel.exchange,
                                                              routing_key=sentinel.routing_key,
                                                              body=sentinel.body,
                                                              properties=bpmock(headers=sentinel.properties,
                                                                                delivery_mode=None),
                                                              immediate=False,
                                                              mandatory=False)

    @patch('pyon.net.transport.BasicProperties')
    def test_publish_impl_durable(self, bpmock):
        self.tp.publish_impl(sentinel.exchange, sentinel.routing_key, sentinel.body, sentinel.properties, durable_msg=True)

        self.tp._client.basic_publish.assert_called_once_with(exchange=sentinel.exchange,
                                                              routing_key=sentinel.routing_key,
                                                              body=sentinel.body,
                                                              properties=bpmock(headers=sentinel.properties,
                                                                                delivery_mode=2),
                                                              immediate=False,
                                                              mandatory=False)

@attr('UNIT')
class TestNameTrio(PyonTestCase):
    def test_init(self):
        nt = NameTrio(sentinel.exchange, sentinel.queue, sentinel.binding)
        self.assertEquals(nt._exchange, sentinel.exchange)
        self.assertEquals(nt._queue, sentinel.queue)
        self.assertEquals(nt._binding, sentinel.binding)

    def test_init_tuple_exchange(self):
        nt = NameTrio((sentinel.exchange, sentinel.queue, sentinel.binding))
        self.assertEquals(nt._exchange, sentinel.exchange)
        self.assertEquals(nt._queue, sentinel.queue)
        self.assertEquals(nt._binding, sentinel.binding)

    def test_init_tuple_not_full(self):
        nt = NameTrio((sentinel.exchange,))
        self.assertEquals(nt._exchange, sentinel.exchange)
        self.assertEquals(nt._queue, None)
        self.assertEquals(nt._binding, None)

    def test_init_tuple_queue(self):
        nt = NameTrio(queue=(sentinel.exchange, sentinel.queue))
        self.assertEquals(nt._exchange, sentinel.exchange)
        self.assertEquals(nt._queue, sentinel.queue)
        self.assertEquals(nt._binding, None)

    def test_init_tuples_both(self):
        # exchange kwarg has priority over queue kwarg
        nt = NameTrio(exchange=(sentinel.exchange1,), queue=(sentinel.exchange2,sentinel.queue))
        self.assertEquals(nt._exchange, sentinel.exchange1)
        self.assertEquals(nt._queue, None)
        self.assertEquals(nt._binding, None)

    def test_str(self):
        nt = NameTrio(sentinel.exchange, sentinel.queue, sentinel.binding)
        strnt = str(nt)

        self.assertIn(str(sentinel.exchange), strnt)
        self.assertIn(str(sentinel.queue), strnt)
        self.assertIn(str(sentinel.binding), strnt)

    def test_props(self):
        nt = NameTrio(sentinel.exchange, sentinel.queue, sentinel.binding)
        self.assertEquals(nt.exchange, sentinel.exchange)
        self.assertEquals(nt.queue, sentinel.queue)
        self.assertEquals(nt.binding, sentinel.binding)

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


    def test__connect_addr(self):
        self.assertEquals(self.lr._connect_addr, "inproc://%s" % get_sys_name())

    def test__child_failed(self):
        self.lr.gl_ioloop = Mock()

        fail = Mock()
        self.lr._child_failed(fail)

        self.lr.gl_ioloop.kill.assert_called_once_with(exception=fail.exception,
                                                       block=False)

    def test__run_ioloop(self):
        self.lr._gl_pool = Mock()
        self.lr._run_ioloop()

        self.lr._gl_pool.join.assert_called_once_with()

    def test_declare_exchange(self):
        self.lr.declare_exchange(sentinel.exchange)

        self.assertIn(sentinel.exchange, self.lr._exchanges)
        self.assertIsInstance(self.lr._exchanges[sentinel.exchange], TopicTrie)

    def test_declare_exchange_existing(self):
        tt = TopicTrie()
        self.lr._exchanges[sentinel.exchange] = tt

        self.lr.declare_exchange(sentinel.exchange)
        self.assertEquals(tt, self.lr._exchanges[sentinel.exchange])

    def test_delete_exchange(self):
        self.lr.declare_exchange(sentinel.exchange)
        self.lr.delete_exchange(sentinel.exchange)

        self.assertEquals(self.lr._exchanges, {})

    def test_declare_queue(self):
        self.lr.declare_queue(sentinel.queue)
        self.assertIn(sentinel.queue, self.lr._queues)

    def test_declare_queue_made_up(self):
        q = self.lr.declare_queue('')
        self.assertIn("q-", q)
        self.assertIn(q, self.lr._queues)

    def test_delete_queue(self):
        self.lr.declare_queue(sentinel.queue)
        self.lr.delete_queue(sentinel.queue)
        self.assertNotIn(sentinel.queue, self.lr._queues)

    def test_delete_queue_deletes_bindings(self):
        self.lr.declare_exchange(sentinel.exchange)
        self.lr.declare_queue(sentinel.queue)
        self.lr.bind(sentinel.exchange, sentinel.queue, 'binder')

        self.lr.delete_queue(sentinel.queue)
        self.assertNotIn(sentinel.queue, self.lr._queues)
        self.assertNotIn(sentinel.queue, self.lr._bindings_by_queue)

    def test_start_consume(self):
        self.lr._gl_pool = Mock()
        self.lr.declare_queue(sentinel.queue)
        ctag = self.lr.start_consume(sentinel.callback, sentinel.queue)

        self.assertIn(sentinel.queue, self.lr._consumers)
        self.assertIn(ctag, self.lr._consumers_by_ctag)

        self.assertEquals(self.lr._consumers[sentinel.queue], [(ctag,
                                                                sentinel.callback,
                                                                False,
                                                                False,
                                                                self.lr._gl_pool.spawn.return_value)])

    def test_stop_consume(self):
        self.lr._gl_pool = Mock()
        self.lr.declare_queue(sentinel.queue)
        ctag = self.lr.start_consume(sentinel.callback, sentinel.queue)

        self.lr.stop_consume(ctag)

        self.assertNotIn(ctag, self.lr._consumers_by_ctag)
        self.lr._gl_pool.spawn().join.assert_called_once_with(timeout=5)
        self.lr._gl_pool.spawn().kill.assert_called_once_with()
        self.assertEquals(len(self.lr._consumers[sentinel.queue]), 0)

    def test__run_consumer(self):
        propsmock = Mock()
        propsmock.copy.return_value = sentinel.props
        gqueue = Mock()
        m = (sentinel.exchange, sentinel.routing_key, sentinel.body, propsmock)
        gqueue.get.side_effect = [m,
                                  LocalRouter.ConsumerClosedMessage()]
        cb = Mock()
        self.lr._generate_dtag=Mock(return_value=sentinel.dtag)

        self.lr._run_consumer(sentinel.ctag, sentinel.queue, gqueue, cb)

        self.assertEquals(cb.call_count, 1)
        self.assertEquals(cb.call_args[0][0], self.lr)
        self.assertEquals(dict(cb.call_args[0][1]), {'consumer_tag': sentinel.ctag,
                                                     'delivery_tag': sentinel.dtag,
                                                     'redelivered': False,
                                                     'exchange': sentinel.exchange,
                                                     'routing_key': sentinel.routing_key})
        self.assertEquals(dict(cb.call_args[0][2]), {'headers':sentinel.props})
        self.assertEquals(cb.call_args[0][3], sentinel.body)

        self.assertIn((sentinel.ctag, sentinel.queue, m), self.lr._unacked.itervalues())

    def test__generate_ctag(self):
        self.lr._ctag_pool = Mock()
        self.lr._ctag_pool.get_id.return_value = sentinel.ctagid

        self.assertEquals(self.lr._generate_ctag(), "zctag-%s" % str(sentinel.ctagid))

    def test__return_ctag(self):
        self.lr._ctag_pool = Mock()

        self.lr._return_ctag("m-5")

        self.lr._ctag_pool.release_id.assert_called_once_with(5)

    def test__generate_and_return_ctag(self):
        ctag = self.lr._generate_ctag()
        ctagnum = int(ctag.split("-")[-1])
        self.assertIn(ctagnum, self.lr._ctag_pool._ids_in_use)

        self.lr._return_ctag(ctag)
        self.assertIn(ctagnum, self.lr._ctag_pool._ids_free)
        self.assertNotIn(ctagnum, self.lr._ctag_pool._ids_in_use)

    def test__generate_dtag(self):
        dtag = self.lr._generate_dtag(sentinel.ctag, sentinel.cnt)

        self.assertIn(str(sentinel.ctag), dtag)
        self.assertIn(str(sentinel.cnt), dtag)

    def test_ack(self):
        self.lr._unacked[sentinel.dtag] = True

        self.lr.ack(sentinel.dtag)
        self.assertEquals(len(self.lr._unacked), 0)

    def test_reject(self):
        self.lr._unacked[sentinel.dtag] = (None, None, None)

        self.lr.reject(sentinel.dtag)
        self.assertEquals(len(self.lr._unacked), 0)

    def test_reject_requeue(self):
        q = Mock()
        self.lr._queues[sentinel.queue] = q
        self.lr._unacked[sentinel.dtag] = (None, sentinel.queue, sentinel.m)

        self.lr.reject(sentinel.dtag, requeue=True)
        self.assertEquals(len(self.lr._unacked), 0)
        q.put.assert_called_once_with(sentinel.m)

    def test_transport_close(self):
        # no body in localrouter method
        pass

    def test_get_stats(self):
        self.lr.declare_queue(sentinel.queue)
        self.lr._queues[sentinel.queue].put(sentinel.m)

        mc, cc = self.lr.get_stats(sentinel.queue)

        self.assertEquals((mc, cc), (1, 0))

    def test_get_stats_with_consumers(self):
        self.lr.declare_queue(sentinel.queue)
        self.lr._queues[sentinel.queue].put(sentinel.m)
        self.lr._consumers[sentinel.queue] = [sentinel.ctag]

        mc, cc = self.lr.get_stats(sentinel.queue)

        self.assertEquals((mc, cc), (1, 1))

    def test_purge(self):
        self.lr.declare_queue(sentinel.queue)
        self.lr._queues[sentinel.queue].put(sentinel.m)
        self.assertEquals(self.lr._queues[sentinel.queue].qsize(), 1)

        self.lr.purge(sentinel.queue)

        self.assertEquals(self.lr._queues[sentinel.queue].qsize(), 0)

@attr('UNIT')
class TestLocalTransport(PyonTestCase):
    def setUp(self):
        self.broker = Mock()
        self.lt = LocalTransport(self.broker, sentinel.ch_number)

    def test_redirect_calls(self):
        self.lt.declare_exchange_impl(sentinel.exchange)
        self.lt.delete_exchange_impl(sentinel.exchange)
        self.lt.declare_queue_impl(sentinel.queue)
        self.lt.delete_queue_impl(sentinel.queue)
        self.lt.bind_impl(sentinel.exchange, sentinel.queue, sentinel.binding)
        self.lt.unbind_impl(sentinel.exchange, sentinel.queue, sentinel.binding)
        self.lt.publish_impl(sentinel.exchange, sentinel.routing_key, sentinel.body, sentinel.properties)
        self.lt.start_consume_impl(sentinel.callback, sentinel.queue)
        self.lt.stop_consume_impl(sentinel.consumer_tag)
        self.lt.ack_impl(sentinel.delivery_tag)
        self.lt.reject_impl(sentinel.delivery_tag)
        self.lt.get_stats_impl(sentinel.queue)
        self.lt.purge_impl(sentinel.queue)

        self.broker.declare_exchange.assert_called_once_with(sentinel.exchange)
        self.broker.delete_exchange.assert_called_once_with(sentinel.exchange)
        self.broker.declare_queue.assert_called_once_with(sentinel.queue)
        self.broker.delete_queue.assert_called_once_with(sentinel.queue)
        self.broker.bind.assert_called_once_with(sentinel.exchange, sentinel.queue, sentinel.binding)
        self.broker.unbind.assert_called_once_with(sentinel.exchange, sentinel.queue, sentinel.binding)
        self.broker.publish.assert_called_once_with(sentinel.exchange, sentinel.routing_key, sentinel.body, sentinel.properties, immediate=False, mandatory=False)
        self.broker.start_consume.assert_called_once_with(sentinel.callback, sentinel.queue, no_ack=False, exclusive=False)
        self.broker.stop_consume.assert_called_once_with(sentinel.consumer_tag)
        self.broker.ack.assert_called_once_with(sentinel.delivery_tag)
        self.broker.reject.assert_called_once_with(sentinel.delivery_tag, requeue=False)
        self.broker.get_stats(sentinel.queue)
        self.broker.purge(sentinel.queue)

    def test_close(self):
        self.lt.close()

        self.broker.transport_close.assert_called_once_with(self.lt)
        self.assertFalse(self.lt._active)

    def test_close_with_callbacks(self):
        m = Mock()
        self.lt.add_on_close_callback(m)

        self.lt.close()

        m.assert_called_once_with(self.lt, 200, "Closed ok")

    def test_add_on_close_callback(self):
        self.lt.add_on_close_callback(sentinel.callback)
        self.assertIn(sentinel.callback, self.lt._close_callbacks)

    def test_active(self):
        self.lt._active = sentinel.active
        self.assertEquals(self.lt.active, sentinel.active)

    def test_channel_number(self):
        self.assertEquals(self.lt.channel_number, sentinel.ch_number)

    def test_qos_impl(self):
        # no body in LocalTransport method
        pass



