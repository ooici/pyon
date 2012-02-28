#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

import unittest
from pyon.net.channel import BaseChannel, SendChannel, RecvChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel, ChannelError, ChannelShutdownMessage, ListenChannel, PublisherChannel
from gevent import queue
from pyon.util.unit_test import PyonTestCase
from mock import Mock, sentinel, patch
from pika import channel as pchannel
from pika import BasicProperties
from nose.plugins.attrib import attr
from pyon.net.transport import NameTrio, BaseTransport

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

        ch._transport = Mock()
        ch._amq_chan = Mock()

        ch._declare_exchange('hello')
        self.assertTrue(ch._transport.declare_exchange_impl.called)
        self.assertIn(ch._amq_chan,     ch._transport.declare_exchange_impl.call_args[0])
        self.assertIn('hello',          ch._transport.declare_exchange_impl.call_args[0])
        self.assertIn('exchange_type',  ch._transport.declare_exchange_impl.call_args[1])
        self.assertIn('durable',        ch._transport.declare_exchange_impl.call_args[1])
        self.assertIn('auto_delete',    ch._transport.declare_exchange_impl.call_args[1])

    def test_attach_underlying_channel(self):
        ch = BaseChannel()
        ch.attach_underlying_channel(sentinel.amq_chan)

        self.assertEquals(ch._amq_chan, sentinel.amq_chan)

    @patch('pyon.net.channel.log', Mock())  # to avoid having to put it in signature
    def test_close(self):
        # with close callback
        cbmock = Mock()
        ch = BaseChannel(close_callback=cbmock)
        ch.close()

        cbmock.assert_called_once_with(ch)

        # without close callback
        ac = Mock() #pchannel.Channel)  # cannot use this because callbacks is populated dynamically
        ch = BaseChannel()
        ch._amq_chan = ac
        
        ch.close()
        ac.close.assert_called_once_with()
        self.assertEquals(ac.callbacks.remove.call_count, 4)

    def test_on_channel_open(self):
        ch = BaseChannel()

        ac = Mock(pchannel.Channel)
        ch.on_channel_open(ac)

        ac.add_on_close_callback.assert_called_once_with(ch.on_channel_close)
        self.assertEquals(ch._amq_chan, ac)

    def test_on_channel_close(self):
        # er this just does logging, make the calls anyway for coverage.
        ch = BaseChannel()
        ch._amq_chan = Mock()
        ch._amq_chan.channel_number = 1

        ch.on_channel_close(0, 'hi')
        ch.on_channel_close(1, 'onoes')

    def test_get_channel_id(self):
        ch = BaseChannel()

        self.assertTrue(ch.get_channel_id() is None)

        ch._amq_chan = Mock()
        self.assertEquals(ch.get_channel_id(), ch._amq_chan.channel_number)


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
        ac = Mock(pchannel.Channel)
        self.ch._amq_chan = ac

        # test sending in params
        self.ch._send(NameTrio('xp', 'namen'), 'daten')

        # get our props
        self.assertTrue(ac.basic_publish.called)
        self.assertIn('exchange', ac.basic_publish.call_args[1])
        self.assertIn('routing_key', ac.basic_publish.call_args[1])
        self.assertIn('body', ac.basic_publish.call_args[1])
        self.assertIn('immediate', ac.basic_publish.call_args[1])
        self.assertIn('mandatory', ac.basic_publish.call_args[1])
        self.assertIn('properties', ac.basic_publish.call_args[1])

        props = ac.basic_publish.call_args[1].get('properties')
        self.assertIsInstance(props, BasicProperties)
        self.assertTrue(hasattr(props, 'headers'))
        self.assertEquals(props.headers, {})

        # try another call to _send with a header
        self.ch._send(NameTrio('xp', 'namen'), 'daten', headers={'custom':'val'})

        # make sure our property showed up
        props = ac.basic_publish.call_args[1].get('properties')
        self.assertIn('custom', props.headers)
        self.assertEquals(props.headers['custom'], 'val')

@attr('UNIT')
class TestRecvChannel(PyonTestCase):
    def setUp(self):
        self.ch = RecvChannel()

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

    def test__destroy_queue_no_recv_name(self):
        self.assertRaises(AssertionError, self.ch.destroy_listener)

    def test__destroy_queue(self):
        self.ch._recv_name = NameTrio(sentinel.xp, sentinel.queue)

        self.ch._transport = Mock(BaseTransport)
        self.ch._amq_chan = sentinel.amq_chan

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

        self.ch._transport = Mock(BaseTransport)
        self.ch._amq_chan = sentinel.amq_chan

        self.ch._destroy_binding()

        self.assertTrue(self.ch._transport.unbind_impl.called)
        self.assertIn('queue', self.ch._transport.unbind_impl.call_args[1])
        self.assertIn('exchange', self.ch._transport.unbind_impl.call_args[1])
        self.assertIn('binding', self.ch._transport.unbind_impl.call_args[1])

        self.assertIn(sentinel.queue, self.ch._transport.unbind_impl.call_args[1].itervalues())
        self.assertIn(sentinel.xp, self.ch._transport.unbind_impl.call_args[1].itervalues())
        self.assertIn(sentinel.binding, self.ch._transport.unbind_impl.call_args[1].itervalues())

    def test_start_consume(self):
        ac = Mock(pchannel.Channel)
        self.ch._amq_chan = ac

        ac.basic_consume.return_value = sentinel.consumer_tag

        # set up recv name for queue
        self.ch._recv_name = NameTrio(sentinel.xp, sentinel.queue)

        self.ch.start_consume()

        self.assertTrue(self.ch._consuming)
        self.assertEquals(self.ch._consumer_tag, sentinel.consumer_tag)

        ac.basic_consume.assert_called_once_with(self.ch._on_deliver, queue=sentinel.queue, no_ack=self.ch._consumer_no_ack, exclusive=self.ch._consumer_exclusive)

    def test_start_consume_already_started(self):
        self.ch._consuming = True
        self.assertRaises(ChannelError, self.ch.start_consume)

    @patch('pyon.net.channel.log')
    def test_start_consume_with_consumer_tag_and_auto_delete(self, mocklog):
        ac = Mock(pchannel.Channel)
        self.ch._amq_chan = ac

        # set up recv name for queue
        self.ch._recv_name = NameTrio(sentinel.xp, sentinel.queue)

        self.ch._consumer_tag = sentinel.consumer_tag
        self.ch._queue_auto_delete = True

        self.ch.start_consume()
        self.assertTrue(mocklog.warn.called)

    def test_stop_consume(self):
        ac = Mock(pchannel.Channel)
        self.ch._amq_chan = ac

        # pretend we're consuming
        self.ch._consuming = True

        # callback sideffect!
        def basic_cancel_side(*args, **kwargs):
            cbparam = kwargs.get('callback')
            cbparam()

        ac.basic_cancel.side_effect = basic_cancel_side

        # set a sentinel as our consumer tag
        self.ch._consumer_tag = sentinel.consumer_tag

        # now make the call
        self.ch.stop_consume()

        self.assertFalse(self.ch._consuming)
        self.assertTrue(ac.basic_cancel.called)
        self.assertIn(sentinel.consumer_tag, ac.basic_cancel.call_args[0])

    def test_stop_consume_havent_started(self):
        # we're not consuming, so this should raise
        self.assertRaises(ChannelError, self.ch.stop_consume)

    def test_recv(self):
        # replace recv_queue with a mock obj
        rqmock = Mock(spec=queue.Queue)
        self.ch._recv_queue = rqmock

        rqmock.get.return_value = sentinel.recv

        m = self.ch.recv()

        self.assertEquals(m, sentinel.recv)

        self.assertTrue(rqmock.get.called)

    def test_recv_shutdown(self):
        # replace recv_queue with a mock obj
        rqmock = Mock(spec=queue.Queue)
        self.ch._recv_queue = rqmock

        rqmock.get.return_value = ChannelShutdownMessage()

        self.assertRaises(ChannelClosedError, self.ch.recv)

    @patch('pyon.net.channel.BaseChannel')
    @patch('pyon.net.channel.ChannelShutdownMessage')
    @patch('pyon.net.channel.log', Mock())  # to avoid having to put it in signature
    def test_close_impl(self, mockshutdown, mockbasechannel):

        # no auto stop consuming, no auto delete of queue without recv_name set
        # should have a shutdown message inserted
        mockrq = Mock(spec=queue.Queue)
        self.ch._recv_queue = mockrq

        self.ch.close_impl()

        # odd test quirk: have to assert mockshutdown was called once here (by close_impl),
        # before i can test that put was called with it, becuase i have to call it again just
        # to get the return value of it.
        mockshutdown.assert_called_once_with()
        mockrq.put.assert_called_once_with(mockshutdown())

        mockbasechannel.close_impl.assert_called_once_with(self.ch)

    @patch('pyon.net.channel.BaseChannel')
    @patch('pyon.net.channel.log', Mock())  # to avoid having to put it in signature
    def test_close_impl_stops_consuming(self, mockbasechannel):
        self.ch._consuming = True
        scmock = Mock()

        self.ch.stop_consume = scmock

        self.ch.close_impl()
        scmock.assert_called_once_with()

    def test_declare_queue(self):
        self.ch._transport = Mock(BaseTransport)
        self.ch._amq_chan = sentinel.amq_chan

        # needs a recv name
        self.ch._recv_name = (NameTrio(str(sentinel.xp)))

        qd = self.ch._declare_queue(str(sentinel.queue))    # can't join a sentinel

        self.assertTrue(self.ch._transport.declare_queue_impl.called)
        self.assertIn('queue', self.ch._transport.declare_queue_impl.call_args[1])
        self.assertIn('auto_delete', self.ch._transport.declare_queue_impl.call_args[1])
        self.assertIn('durable', self.ch._transport.declare_queue_impl.call_args[1])

        composed = ".".join([str(sentinel.xp), str(sentinel.queue)])
        self.assertIn(composed, self.ch._transport.declare_queue_impl.call_args[1].itervalues())
        self.assertIn(self.ch._queue_auto_delete, self.ch._transport.declare_queue_impl.call_args[1].itervalues())
        self.assertIn(self.ch._queue_durable, self.ch._transport.declare_queue_impl.call_args[1].itervalues())

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

        self.ch._amq_chan = Mock()
        self.ch._transport = Mock()

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
        rqmock = Mock(spec=queue.Queue)
        self.ch._recv_queue = rqmock

        # now we can call!
        self.ch._on_deliver(sentinel.chan, m, h, sentinel.body)

        # assert the call
        rqmock.put.assert_called_once_with((sentinel.body, h.headers, sentinel.delivery_tag))

        # assert the headers look ok
        self.assertIn(sentinel.exists, rqmock.put.call_args[0][0][1].itervalues())

    def test_ack(self):
        ac = Mock(spec=pchannel.Channel)
        self.ch._amq_chan = ac

        self.ch.ack(sentinel.delivery_tag)

        ac.basic_ack.assert_called_once_with(sentinel.delivery_tag)

    def test_reject(self):
        ac = Mock(spec=pchannel.Channel)
        self.ch._amq_chan = ac

        def side(*args, **kwargs):
            cb = kwargs.get('callback')
            cb()

        ac.basic_reject.side_effect = side

        self.ch.reject(sentinel.delivery_tag, requeue=True)

        self.assertTrue(ac.basic_reject.called)
        self.assertIn(sentinel.delivery_tag, ac.basic_reject.call_args[0])
        self.assertIn('requeue', ac.basic_reject.call_args[1])
        self.assertIn(True, ac.basic_reject.call_args[1].itervalues())

@attr('UNIT')
@patch('pyon.net.channel.SendChannel')
class TestPublisherChannel(PyonTestCase):

    # @TODO: have to do this because i'm patching the class, anything to be done?
    def test_verify_service(self, mocksendchannel):
        PyonTestCase.test_verify_service(self)

    def test_init(self, mocksendchannel):
        pubchan = PublisherChannel()
        self.assertFalse(pubchan._declared)

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
        self.assertTrue(pubchan._declared)

        # call send again, to show declare is not called again
        pubchan.send(sentinel.data2)
        depmock.assert_called_once_with(sentinel.xp)
        self.assertEquals(mocksendchannel.send.call_count, 2)
        mocksendchannel.send.assert_called_with(pubchan, sentinel.data2, headers=None)

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
        newch = self.ch._create_accepted_channel(sentinel.amq_chan, sentinel.msg)
        self.assertIsInstance(newch, ListenChannel.AcceptedListenChannel)
        self.assertEquals(newch._amq_chan, sentinel.amq_chan)

    def test_accept(self):
        rmock = Mock()
        rmock.return_value = sentinel.msg

        cacmock = Mock()

        self.ch.recv = rmock
        self.ch._create_accepted_channel = cacmock
        self.ch._amq_chan = sentinel.amq_chan

        retch = self.ch.accept()

        cacmock.assert_called_once_with(sentinel.amq_chan, sentinel.msg)
        retch._recv_queue.put.assert_called_once_with(sentinel.msg)

@attr('UNIT')
class TestSusbcriberChannel(PyonTestCase):
    """
    SubscriberChannel is a blank for now
    """
    pass

@attr('UNIT')
class TestServerChannel(PyonTestCase):

    def test__create_accepted_channel(self):
        ch = ServerChannel()

        # this is not all that great
        msg = [None, {'reply-to':'one,two'}]

        newch = ch._create_accepted_channel(sentinel.amq_chan, msg)

        self.assertIsInstance(newch, ServerChannel.BidirAcceptChannel)
        self.assertEquals(newch._amq_chan, sentinel.amq_chan)
        self.assertTrue(hasattr(newch._send_name, 'exchange'))
        self.assertTrue(hasattr(newch._send_name, 'queue'))
        self.assertEquals(newch._send_name.exchange, 'one')
        self.assertEquals(newch._send_name.queue, 'two')

if __name__ == "__main__":
    unittest.main()

