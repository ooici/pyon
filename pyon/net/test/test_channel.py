#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'


from mock import Mock, sentinel, patch, MagicMock
from gevent.event import Event
from gevent import spawn
from gevent.queue import Queue
import Queue as PQueue
import time
from nose.plugins.attrib import attr

from pyon.util.unit_test import PyonTestCase
from pyon.core import bootstrap
from pyon.core.bootstrap import CFG
from pyon.net.channel import BaseChannel, SendChannel, RecvChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel, ChannelError, ChannelShutdownMessage, ListenChannel, PublisherChannel
from pyon.net.transport import NameTrio, BaseTransport, AMQPTransport
from pyon.util.int_test import IonIntegrationTestCase


@attr('UNIT')
class TestBaseChannel(PyonTestCase):

    def test_init(self):
        ch = BaseChannel()
        self.assertIsNone(ch._close_callback)

        ch = BaseChannel(close_callback=sentinel.closecb)
        self.assertEquals(ch._close_callback, sentinel.closecb)

    def test_declare_exchange_point(self):
        # make sure no xp param results in assertion
        ch = BaseChannel()
        self.assertRaises(AssertionError, ch._declare_exchange, None)

        transport = Mock()
        ch.on_channel_open(transport)

        ch._declare_exchange('hello')
        self.assertTrue(transport.declare_exchange_impl.called)
        self.assertIn('hello',          transport.declare_exchange_impl.call_args[0])
        self.assertIn('exchange_type',  transport.declare_exchange_impl.call_args[1])
        self.assertIn('durable',        transport.declare_exchange_impl.call_args[1])
        self.assertIn('auto_delete',    transport.declare_exchange_impl.call_args[1])

    @patch('pyon.net.channel.log', Mock())  # to avoid having to put it in signature
    def test_close(self):

        # without close callback
        transport = Mock()
        ch = BaseChannel()
        ch.on_channel_open(transport)
        ch._fsm.current_state = ch.S_ACTIVE
        
        ch.close()
        transport.close.assert_called_once_with()

    def test_close_with_callback(self):
        # with close callback
        cbmock = Mock()
        ch = BaseChannel(close_callback=cbmock)
        ch._fsm.current_state = ch.S_ACTIVE
        ch.close()

        cbmock.assert_called_once_with(ch)


    def test_on_channel_open(self):
        ch = BaseChannel()

        transport = Mock()
        ch.on_channel_open(transport)

        transport.add_on_close_callback.assert_called_once_with(ch.on_channel_close)
        self.assertEquals(ch._transport, transport)

    def test_on_channel_close(self):
        ch = BaseChannel()
        ch.on_channel_open(Mock())
        ch._transport.channel_number = 1

        ch.on_channel_close(ch, 0, 'hi')
        self.assertIsNone(ch._transport)

    def test_on_channel_closed_with_error_callback(self):
        ch = BaseChannel()
        ch.on_channel_open(Mock())
        ch._transport.channel_number = 1

        closemock = Mock()
        ch.set_closed_error_callback(closemock)

        ch.on_channel_close(ch, 1, 'hi')

        closemock.assert_called_once_with(ch, 1, 'hi')

    @patch('pyon.net.channel.log')
    def test_on_channel_close_with_error_in_error_callback(self, logmock):
        ch = BaseChannel()
        ch.on_channel_open(Mock())
        ch._transport.channel_number = 1

        closemock = Mock()
        closemock.side_effect = StandardError
        ch.set_closed_error_callback(closemock)

        ch.on_channel_close(ch, 1, 'hi')

        self.assertEquals(logmock.warn.call_count, 1)

    def test_get_channel_id(self):
        ch = BaseChannel()

        self.assertTrue(ch.get_channel_id() is None)

        ch.on_channel_open(Mock())
        self.assertEquals(ch.get_channel_id(), ch._transport.channel_number)

    def test__ensure_transport(self):
        ch = BaseChannel()
        with self.assertRaises(ChannelError):
            with ch._ensure_transport():
                pass

@attr('UNIT')
class TestSendChannel(PyonTestCase):
    def setUp(self):
        self.ch = SendChannel()

    def test_connect(self):
        self.ch.connect(NameTrio('xp', 'key'))
        self.assertTrue(hasattr(self.ch._send_name, 'exchange'))
        self.assertTrue(hasattr(self.ch._send_name, 'queue'))
        self.assertEquals(self.ch._send_name.exchange, 'xp')
        self.assertEquals(self.ch._send_name.queue, 'key')
        self.assertEquals(self.ch._exchange, 'xp')

    def test_send(self):
        _sendmock = Mock()
        self.ch._send = _sendmock
        np = NameTrio('xp', 'key')
        self.ch.connect(np)

        self.ch.send('data', {'header':sentinel.headervalue})
        _sendmock.assert_called_once_with(np, 'data', headers={'header':sentinel.headervalue})

    def test__send(self):
        transport = Mock()
        transport.channel_number = sentinel.channel_number
        self.ch.on_channel_open(transport)

        # test sending in params
        self.ch._send(NameTrio('xp', 'namen'), 'daten')

        # get our props
        self.assertTrue(transport.publish_impl.called)
        self.assertIn('exchange', transport.publish_impl.call_args[1])
        self.assertIn('routing_key', transport.publish_impl.call_args[1])
        self.assertIn('body', transport.publish_impl.call_args[1])
        self.assertIn('immediate', transport.publish_impl.call_args[1])
        self.assertIn('mandatory', transport.publish_impl.call_args[1])
        self.assertIn('properties', transport.publish_impl.call_args[1])

        props = transport.publish_impl.call_args[1].get('properties')
        self.assertEquals(props, {})

        # try another call to _send with a header
        self.ch._send(NameTrio('xp', 'namen'), 'daten', headers={'custom':'val'})

        # make sure our property showed up
        props = transport.publish_impl.call_args[1].get('properties')
        self.assertIn('custom', props)
        self.assertEquals(props['custom'], 'val')

@attr('UNIT')
class TestRecvChannel(PyonTestCase):
    def setUp(self):
        self.ch = RecvChannel()

    def _create_channel(self):
        """
        Test helper method, creates mocked up broker interaction.
        """
        ch = RecvChannel()
        ch._declare_exchange = Mock()
        ch._declare_queue = Mock()
        ch._declare_queue.return_value = sentinel.anon_queue
        ch._bind = Mock()
        return ch

    def test_setup_listener(self):
        # sub in mocks for _declare_exchange, _declare_queue, _bind
        mxp = Mock()
        mdq = Mock()
        mdq.return_value = sentinel.anon_queue
        mb = Mock()

        def create_channel():
            ch = RecvChannel()
            ch._declare_exchange = mxp
            ch._declare_queue = mdq
            ch._bind = mb
            return ch
        
        ch = create_channel()

        self.assertFalse(ch._setup_listener_called)

        # call setup listener, defining xp, queue, binding
        ch.setup_listener(NameTrio(sentinel.xp, sentinel.queue, sentinel.binding))

        self.assertTrue(hasattr(ch, '_recv_name'))
        self.assertTrue(hasattr(ch._recv_name, 'exchange'))
        self.assertTrue(hasattr(ch._recv_name, 'queue'))
        self.assertEquals(ch._recv_name.exchange, sentinel.xp)
        self.assertEquals(ch._recv_name.queue, sentinel.queue)

        mxp.assert_called_once_with(sentinel.xp)
        mdq.assert_called_once_with(sentinel.queue)
        mb.assert_called_once_with(sentinel.binding)
        
        # you can only call setup_listener once
        self.assertTrue(ch._setup_listener_called)
        
        # calling it again does nothing, does not touch anything
        ch.setup_listener(NameTrio(sentinel.xp2, sentinel.queue2))

        self.assertTrue(hasattr(ch._recv_name, 'exchange'))
        self.assertTrue(hasattr(ch._recv_name, 'queue'))
        self.assertEquals(ch._recv_name.exchange, sentinel.xp)
        self.assertEquals(ch._recv_name.queue, sentinel.queue)
        mxp.assert_called_once_with(sentinel.xp)
        mdq.assert_called_once_with(sentinel.queue)
        mb.assert_called_once_with(sentinel.binding)

        # call setup listener, passing a custom bind this time
        ch = create_channel()
        ch.setup_listener(NameTrio(sentinel.xp2, sentinel.queue2), binding=sentinel.binding)

        mxp.assert_called_with(sentinel.xp2)
        mdq.assert_called_with(sentinel.queue2)
        mb.assert_called_with(sentinel.binding)

        # call setup_listener, use anonymous queue name and no binding (will get return value we set above)
        ch = create_channel()
        ch.setup_listener(NameTrio(sentinel.xp3))

        mxp.assert_called_with(sentinel.xp3)
        mdq.assert_called_with(None)
        mb.assert_called_with(sentinel.anon_queue)

        # call setup_listener with anon queue name but with binding
        ch = create_channel()
        ch.setup_listener(NameTrio(sentinel.xp4), binding=sentinel.binding2)

        mxp.assert_called_with(sentinel.xp4)
        mdq.assert_called_with(None)
        mb.assert_called_with(sentinel.binding2)

    def test_setup_listener_existing_recv_name(self):
        ch = self._create_channel()

        recv_name = NameTrio(sentinel.xp, sentinel.queue, sentinel.binding)
        ch._recv_name = recv_name

        ch.setup_listener()
        self.assertEquals(ch._recv_name, recv_name)

    def test_setup_listener_existing_recv_name_with_differing_name(self):
        ch = self._create_channel()

        recv_name = NameTrio(sentinel.xp, sentinel.queue, sentinel.binding)
        ch._recv_name = recv_name

        ch.setup_listener(name=NameTrio(sentinel.xp, sentinel.queue, sentinel.notbinding))
        self.assertNotEquals(ch._recv_name, recv_name)

        self.assertEquals(ch._recv_name.exchange, sentinel.xp)
        self.assertEquals(ch._recv_name.queue, sentinel.queue)
        self.assertEquals(ch._recv_name.binding, sentinel.notbinding)

    def test__destroy_queue_no_recv_name(self):
        self.assertRaises(AssertionError, self.ch.destroy_listener)

    def test__destroy_queue(self):
        self.ch._recv_name = NameTrio(sentinel.xp, sentinel.queue)

        self.ch.on_channel_open(Mock(BaseTransport))

        self.ch.destroy_listener()

        self.assertTrue(self.ch._transport.delete_queue_impl.called)
        self.assertIn('queue', self.ch._transport.delete_queue_impl.call_args[1])
        self.assertIn(sentinel.queue, self.ch._transport.delete_queue_impl.call_args[1].itervalues())

    def test_destroy_listener(self):
        m = Mock()
        self.ch._destroy_queue = m

        self.ch.destroy_listener()
        m.assert_called_once_with()

    def test__destroy_binding_no_recv_name_or_binding(self):
        self.assertRaises(AssertionError, self.ch._destroy_binding)

    def test__destroy_binding(self):
        self.ch._recv_name = NameTrio(sentinel.xp, sentinel.queue)
        self.ch._recv_binding = sentinel.binding

        self.ch.on_channel_open(Mock(BaseTransport))

        self.ch._destroy_binding()

        self.assertTrue(self.ch._transport.unbind_impl.called)
        self.assertIn('queue', self.ch._transport.unbind_impl.call_args[1])
        self.assertIn('exchange', self.ch._transport.unbind_impl.call_args[1])
        self.assertIn('binding', self.ch._transport.unbind_impl.call_args[1])

        self.assertIn(sentinel.queue, self.ch._transport.unbind_impl.call_args[1].itervalues())
        self.assertIn(sentinel.xp, self.ch._transport.unbind_impl.call_args[1].itervalues())
        self.assertIn(sentinel.binding, self.ch._transport.unbind_impl.call_args[1].itervalues())

    def test_start_consume(self):
        transport = MagicMock()
        self.ch.on_channel_open(transport)
        self.ch._fsm.current_state = self.ch.S_ACTIVE

        transport.start_consume_impl.return_value = sentinel.consumer_tag

        # set up recv name for queue
        self.ch._recv_name = NameTrio(sentinel.xp, sentinel.queue)

        self.ch.start_consume()

        self.assertTrue(self.ch._consuming)
        self.assertEquals(self.ch._fsm.current_state, self.ch.S_ACTIVE)
        self.assertEquals(self.ch._consumer_tag, sentinel.consumer_tag)

        transport.start_consume_impl.assert_called_once_with(self.ch._on_deliver, queue=sentinel.queue, no_ack=self.ch._consumer_no_ack, exclusive=self.ch._consumer_exclusive)

    def test_start_consume_already_started(self):
        self.ch._on_start_consume = Mock()
        self.ch._consuming = True

        self.ch.start_consume()     # noops due to consuming flag already on

        self.assertFalse(self.ch._on_start_consume.called)

    @patch('pyon.net.channel.log')
    def test_start_consume_with_consumer_tag_and_auto_delete(self, mocklog):
        transport = AMQPTransport(Mock())
        self.ch.on_channel_open(transport)
        self.ch._fsm.current_state = self.ch.S_ACTIVE

        # set up recv name for queue
        self.ch._recv_name = NameTrio(sentinel.xp, sentinel.queue)
        self.ch._consumer_tag = sentinel.consumer_tag
        self.ch._queue_auto_delete = True

        self.ch.start_consume()
        self.assertTrue(mocklog.warn.called)

    def test_stop_consume(self):
        transport = MagicMock()
        self.ch.on_channel_open(transport)

        # pretend we're consuming
        self.ch._fsm.current_state = self.ch.S_ACTIVE
        self.ch._consuming = True

        # set a sentinel as our consumer tag
        self.ch._consumer_tag = sentinel.consumer_tag

        # now make the call
        self.ch.stop_consume()

        self.assertEquals(self.ch._fsm.current_state, self.ch.S_ACTIVE)
        self.assertFalse(self.ch._consuming)
        self.assertTrue(transport.stop_consume_impl.called)
        self.assertIn(sentinel.consumer_tag, transport.stop_consume_impl.call_args[0])

    def test_stop_consume_havent_started(self):
        self.ch._on_stop_consume = Mock()

        self.ch.stop_consume()

        self.assertFalse(self.ch._on_stop_consume.called)

    def test_stop_consume_raises_warning_with_auto_delete(self):
        transport = AMQPTransport(Mock())
        transport.stop_consume_impl = Mock()
        self.ch.on_channel_open(transport)
        #transport.channel_number = sentinel.channel_number

        self.ch._consumer_tag = sentinel.consumer_tag
        self.ch._recv_name = NameTrio(sentinel.ex, sentinel.queue, sentinel.binding)
        self.ch._fsm.current_state = self.ch.S_ACTIVE
        self.ch._consuming = True

        #self.ch._ensure_transport = MagicMock()
        self.ch._queue_auto_delete = True

        self.ch.stop_consume()

        self.assertTrue(self.ch._transport.stop_consume_impl.called)
        self.assertIn(self.ch._consumer_tag, self.ch._transport.stop_consume_impl.call_args[0])

    def test_recv(self):
        # replace recv_queue with a mock obj
        rqmock = Mock(spec=RecvChannel.SizeNotifyQueue)
        self.ch._recv_queue = rqmock

        rqmock.get.return_value = sentinel.recv

        m = self.ch.recv()

        self.assertEquals(m, sentinel.recv)

        self.assertTrue(rqmock.get.called)

    def test_recv_shutdown(self):
        # replace recv_queue with a mock obj
        rqmock = Mock(spec=RecvChannel.SizeNotifyQueue)
        self.ch._recv_queue = rqmock

        rqmock.get.return_value = ChannelShutdownMessage()

        self.assertRaises(ChannelClosedError, self.ch.recv)

    @patch('pyon.net.channel.BaseChannel')
    @patch('pyon.net.channel.ChannelShutdownMessage')
    @patch('pyon.net.channel.log', Mock())  # to avoid having to put it in signature
    def test_close_impl(self, mockshutdown, mockbasechannel):

        # no auto stop consuming, no auto delete of queue without recv_name set
        # should have a shutdown message inserted
        mockrq = Mock(spec=RecvChannel.SizeNotifyQueue)
        self.ch._recv_queue = mockrq

        self.ch.close_impl()

        # odd test quirk: have to assert mockshutdown was called once here (by close_impl),
        # before i can test that put was called with it, becuase i have to call it again just
        # to get the return value of it.
        mockshutdown.assert_called_once_with()
        mockrq.put.assert_called_once_with(mockshutdown())

        mockbasechannel.close_impl.assert_called_once_with(self.ch)

    def test_declare_queue(self):
        self.ch.on_channel_open(Mock(BaseTransport))

        # needs a recv name
        self.ch._recv_name = (NameTrio(str(sentinel.xp)))

        qd = self.ch._declare_queue(str(sentinel.queue))    # can't join a sentinel

        self.assertTrue(self.ch._transport.declare_queue_impl.called)
        self.assertIn('queue', self.ch._transport.declare_queue_impl.call_args[1])
        self.assertIn('auto_delete', self.ch._transport.declare_queue_impl.call_args[1])
        self.assertIn('durable', self.ch._transport.declare_queue_impl.call_args[1])

        composed = ".".join([str(sentinel.xp), str(sentinel.queue)])
        self.assertIn(composed, self.ch._transport.declare_queue_impl.call_args[1].itervalues())
        self.assertIn(self.ch.queue_auto_delete, self.ch._transport.declare_queue_impl.call_args[1].itervalues())
        self.assertIn(self.ch.queue_durable, self.ch._transport.declare_queue_impl.call_args[1].itervalues())

        # should have set recv_name
        self.assertTrue(hasattr(self.ch._recv_name, 'exchange'))
        self.assertTrue(hasattr(self.ch._recv_name, 'queue'))
        self.assertEquals(self.ch._recv_name.exchange, str(sentinel.xp))    # we passed in str() versions
        self.assertEquals(self.ch._recv_name.queue, self.ch._transport.declare_queue_impl())
        self.assertEquals(qd, self.ch._transport.declare_queue_impl())

    def test__bind_no_name(self):
        self.assertRaises(AssertionError, self.ch._bind, sentinel.binding)

    def test__bind(self):
        self.ch._recv_name = NameTrio(sentinel.xp, sentinel.queue)

        self.ch.on_channel_open(Mock())

        self.ch._bind(sentinel.binding)

        self.assertTrue(self.ch._transport.bind_impl.called)
        self.assertIn('queue', self.ch._transport.bind_impl.call_args[1])
        self.assertIn('exchange', self.ch._transport.bind_impl.call_args[1])
        self.assertIn('binding', self.ch._transport.bind_impl.call_args[1])

        self.assertIn(sentinel.queue, self.ch._transport.bind_impl.call_args[1].itervalues())
        self.assertIn(sentinel.xp, self.ch._transport.bind_impl.call_args[1].itervalues())
        self.assertIn(sentinel.binding, self.ch._transport.bind_impl.call_args[1].itervalues())

    def test__on_deliver(self):
        # mock up the method frame (delivery_tag is really only one we care about)
        m = Mock()
        m.consumer_tag  = sentinel.consumer_tag
        m.delivery_tag  = sentinel.delivery_tag
        m.redelivered   = sentinel.redelivered
        m.exchange      = sentinel.exchange
        m.routing_key   = sentinel.routing_key

        # mock up the header-frame
        h = Mock()
        h.headers = { 'this_exists': sentinel.exists }

        # use a mock for the recv queue
        rqmock = Mock(spec=RecvChannel.SizeNotifyQueue)
        self.ch._recv_queue = rqmock

        # now we can call!
        self.ch._on_deliver(sentinel.chan, m, h, sentinel.body)

        # assert the call
        rqmock.put.assert_called_once_with((sentinel.body, h.headers, sentinel.delivery_tag))

        # assert the headers look ok
        self.assertIn(sentinel.exists, rqmock.put.call_args[0][0][1].itervalues())

    def test_ack(self):
        transport = Mock()
        transport.channel_number = sentinel.channel_number
        self.ch.on_channel_open(transport)

        self.ch.ack(sentinel.delivery_tag)

        transport.ack_impl.assert_called_once_with(sentinel.delivery_tag)

    def test_reject(self):
        transport = Mock()
        transport.channel_number = sentinel.channel_number
        self.ch.on_channel_open(transport)

        self.ch.reject(sentinel.delivery_tag, requeue=True)

        transport.reject_impl.assert_called_once_with(sentinel.delivery_tag, requeue=True)

    def test_reset(self):
        self.ch.reset()
        self.assertEquals(self.ch._fsm.current_state, self.ch.S_INIT)

    def test_reset_when_consuming(self):
        # have to setup a lot here, can't just mock
        # _on_stop_consume because the FSM holds onto it
        transport = MagicMock()
        self.ch.on_channel_open(transport)

        # pretend we're consuming
        self.ch._fsm.current_state = self.ch.S_ACTIVE
        self.ch._consuming = True

        # set a sentinel as our consumer tag
        self.ch._consumer_tag = sentinel.consumer_tag

        self.ch.reset()

        self.assertEquals(self.ch._fsm.current_state, self.ch.S_ACTIVE)
        self.assertTrue(transport.stop_consume_impl.called)

    def test_get_stats(self):
        transport = Mock()
        self.ch.on_channel_open(transport)
        self.ch._recv_name = NameTrio(sentinel.ex, sentinel.queue)

        self.ch.get_stats()

        self.ch._transport.get_stats_impl.assert_called_once_with(queue=sentinel.queue)

    def test_purge(self):
        transport = Mock()
        self.ch.on_channel_open(transport)
        self.ch._recv_name = NameTrio(sentinel.ex, sentinel.queue)

        self.ch._purge()

        self.ch._transport.purge_impl.assert_called_once_with(queue=sentinel.queue)

@attr('UNIT')
@patch('pyon.net.channel.SendChannel')
class TestPublisherChannel(PyonTestCase):

    # @TODO: have to do this because i'm patching the class, anything to be done?
    def test_verify_service(self, mocksendchannel):
        PyonTestCase.test_verify_service(self)

    def test_init(self, mocksendchannel):
        pubchan = PublisherChannel()

    def test_send_no_name(self, mocksendchannel):
        pubchan = PublisherChannel()
        self.assertRaises(AssertionError, pubchan.send, sentinel.data)

    def test_send(self, mocksendchannel):
        depmock = Mock()
        pubchan = PublisherChannel()
        pubchan._declare_exchange = depmock

        pubchan._send_name = NameTrio(sentinel.xp, sentinel.routing_key)

        pubchan.send(sentinel.data)

        depmock.assert_called_once_with(sentinel.xp)
        mocksendchannel.send.assert_called_once_with(pubchan, sentinel.data, headers=None)

@attr('UNIT')
@patch('pyon.net.channel.SendChannel')
class TestBidirClientChannel(PyonTestCase):

    # @TODO: have to do this because i'm patching the class, anything to be done?
    def test_verify_service(self, mocksendchannel):
        PyonTestCase.test_verify_service(self)

    def setUp(self):
        self.ch = BidirClientChannel()

    def test__send_with_reply_to(self, mocksendchannel):

        self.ch._recv_name = NameTrio(sentinel.xp, sentinel.queue)

        self.ch._send(sentinel.name, sentinel.data, headers={sentinel.header_key: sentinel.header_value})

        mocksendchannel._send.assert_called_with(self.ch,
                                                 sentinel.name,
                                                 sentinel.data,
                                                 headers={sentinel.header_key: sentinel.header_value, 'reply-to': '%s,%s' % (sentinel.xp, sentinel.queue)})


    def test__send_with_no_reply_to(self, mocksendchannel):

        # must set recv_name
        self.ch._recv_name = NameTrio(sentinel.xp, sentinel.queue)

        self.ch._send(sentinel.name, sentinel.data)

        mocksendchannel._send.assert_called_with(self.ch, sentinel.name, sentinel.data, headers={'reply-to':"%s,%s" % (sentinel.xp, sentinel.queue)})

@attr('UNIT')
class TestListenChannel(PyonTestCase):

    def setUp(self):
        self.ch = ListenChannel()

    def test__create_accepted_channel(self):
        newch = self.ch._create_accepted_channel(sentinel.transport, sentinel.msg)
        self.assertIsInstance(newch, ListenChannel.AcceptedListenChannel)
        self.assertEquals(newch._transport, sentinel.transport)

    def test_accept(self):
        rmock = Mock()
        rmock.return_value = sentinel.msg

        cacmock = Mock()
        transport = Mock()

        self.ch.recv = rmock
        self.ch._recv_queue.await_n = MagicMock()
        self.ch._create_accepted_channel = cacmock
        self.ch.on_channel_open(transport)
        self.ch._fsm.current_state = self.ch.S_ACTIVE
        self.ch._consuming = True

        retch = self.ch.accept()
        self.assertEquals(self.ch._fsm.current_state, self.ch.S_ACCEPTED)
        cacmock.assert_called_once_with(transport, [sentinel.msg])
        retch._recv_queue.put.assert_called_once_with(sentinel.msg)

        # we've mocked all the working machinery of accept's return etc, so we must manually exit accept
        # as if we've ack'd/reject'd
        self.ch.exit_accept()

        self.assertEquals(self.ch._fsm.current_state, self.ch.S_ACTIVE)
        self.assertTrue(self.ch._consuming)

    def test_close_while_accepted(self):
        rmock = Mock()
        rmock.return_value = sentinel.msg

        cacmock = Mock()
        transport = Mock()

        self.ch.recv = rmock
        self.ch._recv_queue.await_n = MagicMock()
        self.ch._create_accepted_channel = cacmock
        self.ch.on_channel_open(transport)
        self.ch._fsm.current_state = self.ch.S_ACTIVE
        self.ch._consuming = True

        # to test close to make sure nothing happened
        self.ch.close_impl = Mock()

        # stub out stop consume reaction
        self.ch._on_stop_consume = Mock()

        retch = self.ch.accept()
        self.assertEquals(self.ch._fsm.current_state, self.ch.S_ACCEPTED)

        self.ch.close()

        # ensure nothing close-like got called!
        self.assertFalse(self.ch.close_impl.called)
        self.assertFalse(self.ch._on_stop_consume.called)
        self.assertEquals(self.ch._fsm.current_state, self.ch.S_CLOSING)

        # we've mocked all the working machinery of accept's return etc, so we must manually exit accept
        # as if we've ack'd/reject'd
        self.ch.exit_accept()

        self.assertTrue(self.ch.close_impl.called)
        self.assertTrue(self.ch._on_stop_consume.called)
        self.assertEquals(self.ch._fsm.current_state, self.ch.S_CLOSED)
        self.assertFalse(self.ch._consuming)

    def test_stop_consume_while_accepted(self):
        rmock = Mock()
        rmock.return_value = sentinel.msg

        cacmock = Mock()
        transport = Mock()

        self.ch.recv = rmock
        self.ch._recv_queue.await_n = MagicMock()
        self.ch._create_accepted_channel = cacmock
        self.ch.on_channel_open(transport)
        self.ch._fsm.current_state = self.ch.S_ACTIVE
        self.ch._consuming = True

        # to test stop_consume reaction
        self.ch._on_stop_consume = Mock()

        retch = self.ch.accept()
        self.assertEquals(self.ch._fsm.current_state, self.ch.S_ACCEPTED)

        self.ch.stop_consume()

        # we've stopped consuming, no state transition
        self.assertFalse(self.ch._consuming)
        self.assertTrue(self.ch._on_stop_consume.called)
        self.assertEquals(self.ch._fsm.current_state, self.ch.S_ACCEPTED)

        # we've mocked all the working machinery of accept's return etc, so we must manually exit accept
        # as if we've ack'd/reject'd
        self.ch.exit_accept()

        self.assertEquals(self.ch._fsm.current_state, self.ch.S_ACTIVE)

    def test_AcceptedListenChannel_close_does_not_close_underlying_amqp_channel(self):
        transport = Mock()
        newch = self.ch._create_accepted_channel(transport, sentinel.msg)

        newch.close()
        self.assertEquals(transport.close.call_count, 0)

@attr('UNIT')
class TestSubscriberChannel(PyonTestCase):

    def test_close_does_delete_if_anonymous_and_not_auto_delete(self):
        transport = AMQPTransport(Mock())
        ch = SubscriberChannel()
        ch.on_channel_open(transport)
        ch._queue_auto_delete = False
        ch._destroy_queue = Mock()
        ch._recv_name = NameTrio(sentinel.exchange, 'amq.gen-ABCD')

        ch.close_impl()
        ch._destroy_queue.assert_called_once_with()

    def test_close_does_not_delete_if_named(self):
        ch = SubscriberChannel()
        ch._queue_auto_delete = False
        ch._destroy_queue = Mock()
        ch._recv_name = NameTrio(sentinel.exchange, 'some-named-queue')

        ch.close_impl()
        self.assertFalse(ch._destroy_queue.called)

    def test_close_does_not_delete_if_anon_but_auto_delete(self):
        ch = SubscriberChannel()
        ch._queue_auto_delete = True
        ch._destroy_queue = Mock()
        ch._recv_name = NameTrio(sentinel.exchange, 'amq.gen-ABCD')

        ch.close_impl()
        self.assertFalse(ch._destroy_queue.called)

@attr('UNIT')
class TestServerChannel(PyonTestCase):

    def test__create_accepted_channel(self):
        ch = ServerChannel()

        # this is not all that great
        msg = [[None, {'reply-to':'one,two'}]]

        newch = ch._create_accepted_channel(sentinel.transport, msg)

        self.assertIsInstance(newch, ServerChannel.BidirAcceptChannel)
        self.assertEquals(newch._transport, sentinel.transport)
        self.assertTrue(hasattr(newch._send_name, 'exchange'))
        self.assertTrue(hasattr(newch._send_name, 'queue'))
        self.assertEquals(newch._send_name.exchange, 'one')
        self.assertEquals(newch._send_name.queue, 'two')

@attr('INT')
class TestChannelInt(IonIntegrationTestCase):
    def setUp(self):
        self.patch_cfg('pyon.ion.exchange.CFG', {'container':{'messaging':{'server':{'primary':'amqp', 'priviledged':None}},
                                                              'datastore':CFG['container']['datastore']},
                                                 'server':CFG['server']})
        self._start_container()

    #@skip('Not working consistently on buildbot')
    def test_consume_one_message_at_a_time(self):
        # end to end test for CIDEVCOI-547 requirements
        #    - Process P1 is producing one message every 5 seconds
        #    - Process P2 is producing one other message every 3 seconds
        #    - Process S creates a auto-delete=False queue without a consumer and without a binding
        #    - Process S binds this queue through a pyon.net or container API call to the topic of process P1
        #    - Process S waits a bit
        #    - Process S checks the number of messages in the queue
        #    - Process S creates a consumer, takes one message off the queue (non-blocking) and destroys the consumer
        #    - Process S waits a bit (let messages accumulate)
        #    - Process S creates a consumer, takes a message off and repeates it until no messges are left (without ever blocking) and destroys the consumer
        #    - Process S waits a bit (let messages accumulate)
        #    - Process S creates a consumer, takes a message off and repeates it until no messges are left (without ever blocking). Then requeues the last message and destroys the consumer
        #    - Process S creates a consumer, takes one message off the queue (non-blocking) and destroys the consumer.
        #    - Process S sends prior message to its queue (note: may be tricky without a subscription to yourself)
        #    - Process S changes the binding of queue to P1 and P2
        #    - Process S removes all bindings of queue
        #    - Process S deletes the queue
        #    - Process S exists without any residual resources in the broker
        #    - Process P1 and P1 get terminated without any residual resources in the broker
        #
        #    * Show this works with the ACK or no-ACK mode
        #    * Do the above with semi-abstracted calles (some nicer boilerplate)

        def every_five():
            p = self.container.node.channel(PublisherChannel)
            p._send_name = NameTrio(bootstrap.get_sys_name(), 'routed.5')
            counter = 0

            while not self.publish_five.wait(timeout=5):
                p.send('5,' + str(counter))
                counter+=1

        def every_three():
            p = self.container.node.channel(PublisherChannel)
            p._send_name = NameTrio(bootstrap.get_sys_name(), 'routed.3')
            counter = 0

            while not self.publish_three.wait(timeout=3):
                p.send('3,' + str(counter))
                counter+=1

        self.publish_five = Event()
        self.publish_three = Event()
        self.five_events = Queue()
        self.three_events = Queue()

        gl_every_five = spawn(every_five)
        gl_every_three = spawn(every_three)

        def listen(lch):
            """
            The purpose of the this listen method is to trigger waits in code below.
            By setting up a listener that subscribes to both 3 and 5, and putting received
            messages into the appropriate gevent-queues client side, we can assume that
            the channel we're actually testing with get_stats etc has had the message delivered
            too.
            """
            lch._queue_auto_delete = False
            lch.setup_listener(NameTrio(bootstrap.get_sys_name(), 'alternate_listener'), 'routed.3')
            lch._bind('routed.5')
            lch.start_consume()

            while True:
                try:
                    newchan = lch.accept()
                    m, h, d = newchan.recv()
                    count = m.rsplit(',', 1)[-1]
                    if m.startswith('5,'):
                        self.five_events.put(int(count))
                        newchan.ack(d)
                    elif m.startswith('3,'):
                        self.three_events.put(int(count))
                        newchan.ack(d)
                    else:
                        raise StandardError("unknown message: %s" % m)

                except ChannelClosedError:
                    break

        lch = self.container.node.channel(SubscriberChannel)
        gl_listen = spawn(listen, lch)

        def do_cleanups(gl_e5, gl_e3, gl_l, lch):
            self.publish_five.set()
            self.publish_three.set()
            gl_e5.join(timeout=5)
            gl_e3.join(timeout=5)

            lch.stop_consume()
            lch._destroy_queue()
            lch.close()
            gl_listen.join(timeout=5)

        self.addCleanup(do_cleanups, gl_every_five, gl_every_three, gl_listen, lch)

        ch = self.container.node.channel(RecvChannel)
        ch._recv_name = NameTrio(bootstrap.get_sys_name(), 'test_queue')
        ch._queue_auto_delete = False

        # #########
        # THIS TEST EXPECTS OLD BEHAVIOR OF NO QOS, SO SET A HIGH BAR
        # #########
        ch._transport.qos_impl(prefetch_count=9999)

        def cleanup_channel(thech):
            thech._destroy_queue()
            thech.close()

        self.addCleanup(cleanup_channel, ch)

        # declare exchange and queue, no binding yet
        ch._declare_exchange(ch._recv_name.exchange)
        ch._declare_queue(ch._recv_name.queue)
        ch._purge()

        # do binding to 5 pub only
        ch._bind('routed.5')

        # wait for one message
        self.five_events.get(timeout=10)

        # ensure 1 message, 0 consumer
        self.assertTupleEqual((1, 0), ch.get_stats())

        # start a consumer
        ch.start_consume()
        time.sleep(0.1)
        self.assertEquals(ch._recv_queue.qsize(), 1)       # should have been delivered to the channel, waiting for us now

        # receive one message with instant timeout
        m, h, d = ch.recv(timeout=0)
        self.assertEquals(m, "5,0")
        ch.ack(d)

        # we have no more messages, should instantly fail
        self.assertRaises(PQueue.Empty, ch.recv, timeout=0)

        # stop consumer
        ch.stop_consume()

        # wait until next 5 publish event
        self.five_events.get(timeout=10)

        # start consumer again, empty queue
        ch.start_consume()
        time.sleep(0.1)
        while True:
            try:
                m, h, d = ch.recv(timeout=0)
                self.assertTrue(m.startswith('5,'))
                ch.ack(d)
            except PQueue.Empty:
                ch.stop_consume()
                break

        # wait for new message
        self.five_events.get(timeout=10)

        # consume and requeue
        ch.start_consume()
        time.sleep(0.1)
        m, h, d = ch.recv(timeout=0)
        self.assertTrue(m.startswith('5,'))
        ch.reject(d, requeue=True)

        # rabbit appears to deliver this later on, only when we've got another message in it
        # wait for another message publish
        num = self.five_events.get(timeout=10)
        self.assertEquals(num, 3)
        time.sleep(0.1)

        expect = ["5,2", "5,3"]
        while True:
            try:
                m, h, d = ch.recv(timeout=0)
                self.assertTrue(m.startswith('5,'))
                self.assertEquals(m, expect.pop(0))

                ch.ack(d)
            except PQueue.Empty:
                ch.stop_consume()
                self.assertListEqual(expect, [])
                break

        # let's change the binding to the 3 now, empty the testqueue first (artifact of test)
        while not self.three_events.empty():
            self.three_events.get(timeout=0)

        # we have to keep the exchange around - it will likely autodelete.
        ch2 = self.container.node.channel(RecvChannel)
        ch2.setup_listener(NameTrio(bootstrap.get_sys_name(), "another_queue"))

        ch._destroy_binding()
        ch._bind('routed.3')

        ch2._destroy_queue()
        ch2.close()

        self.three_events.get(timeout=10)
        ch.start_consume()
        time.sleep(0.1)
        self.assertEquals(ch._recv_queue.qsize(), 1)

        m, h, d = ch.recv(timeout=0)
        self.assertTrue(m.startswith('3,'))
        ch.ack(d)

        # wait for a new 3 to reject
        self.three_events.get(timeout=10)
        time.sleep(0.1)

        m, h, d = ch.recv(timeout=0)
        ch.reject(d, requeue=True)

        # recycle consumption, should get the requeued message right away?
        ch.stop_consume()
        ch.start_consume()
        time.sleep(0.1)

        self.assertEquals(ch._recv_queue.qsize(), 1)

        m2, h2, d2 = ch.recv(timeout=0)
        self.assertEquals(m, m2)

        ch.stop_consume()


@attr('INT')
class TestChannelIntLocalTransport(TestChannelInt):
    def setUp(self):
        self.patch_cfg('pyon.ion.exchange.CFG', {'container':{'messaging':{'server':{'primary':'localrouter', 'priviledged':None}},
                                                              'datastore':CFG['container']['datastore']},
                                                 'server':CFG['server']})
        self._start_container()

