#!/usr/bin/env python
import unittest
from unittest.case import SkipTest
from nose.plugins.attrib import attr
from zope.interface import interface
from zope.interface.declarations import implements
from zope.interface.interface import Interface
from pyon.core import exception
from pyon.net import endpoint
from pyon.net.channel import BaseChannel, SendChannel, RecvChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel, ChannelError, ChannelShutdownMessage, ListenChannel
from gevent import event, GreenletExit, queue
from pyon.net.messaging import NodeB
from pyon.service.service import BaseService
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from pyon.util.async import wait, spawn
from mock import Mock, sentinel, patch
from pika import channel as pchannel
from pika import BasicProperties

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

class TestBaseChannel(IonIntegrationTestCase):

    def test_init(self):
        ch = BaseChannel()
        self.assertIsNone(ch._close_callback)

        ch = BaseChannel(close_callback=15)
        self.assertEquals(ch._close_callback, 15)

    def test_declare_exchange_point(self):
        # make sure no xp param results in assertion
        ch = BaseChannel()
        self.assertRaises(AssertionError, ch._declare_exchange_point, None)

        # test it for real
        ac = Mock(spec=pchannel.Channel)
        def cbparam(*args, **kwargs):
            cbkwarg = kwargs.get('callback')
            cbkwarg(kwargs.get('exchange'))
            return kwargs.get('exchange')
        ac.exchange_declare.side_effect = cbparam

        ch._amq_chan = ac

        ch._declare_exchange_point('hello')
        self.assertTrue(ac.exchange_declare.called)
        self.assertIn('exchange',       ac.exchange_declare.call_args[1])
        self.assertIn('type',           ac.exchange_declare.call_args[1])
        self.assertIn('durable',        ac.exchange_declare.call_args[1])
        self.assertIn('auto_delete',    ac.exchange_declare.call_args[1])
        self.assertIn('hello',          ac.exchange_declare.call_args[1].itervalues())

    def test_attach_underlying_channel(self):
        ch = BaseChannel()
        ch.attach_underlying_channel(27)

        self.assertEquals(ch._amq_chan, 27)

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

class TestSendChannel(IonIntegrationTestCase):
    def setUp(self):
        self.ch = SendChannel()

    def test_connect(self):
        self.ch.connect(('xp', 'key'))
        self.assertEquals(self.ch._send_name, ('xp', 'key'))
        self.assertEquals(self.ch._exchange, 'xp')

    def test_send(self):
        _sendmock = Mock()
        self.ch._send = _sendmock
        self.ch.connect(('xp', 'key'))

        self.ch.send('data', {'header':88})
        _sendmock.assert_called_once_with(('xp', 'key'), 'data', headers={'header':88})

    def test__send(self):
        ac = Mock(pchannel.Channel)
        self.ch._amq_chan = ac

        # test sending in params
        self.ch._send(('xp', 'namen'), 'daten')

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
        self.ch._send(('xp', 'namen'), 'daten', headers={'custom':'val'})

        # make sure our property showed up
        props = ac.basic_publish.call_args[1].get('properties')
        self.assertIn('custom', props.headers)
        self.assertEquals(props.headers['custom'], 'val')

class TestRecvChannel(IonIntegrationTestCase):
    def setUp(self):
        self.ch = RecvChannel()

    def test_setup_listener(self):
        # sub in mocks for _declare_exchange_point, _declare_queue, _bind
        mxp = Mock()
        mdq = Mock()
        mdq.return_value = 'amq-1234'
        mb = Mock()

        self.ch._declare_exchange_point = mxp
        self.ch._declare_queue = mdq
        self.ch._bind = mb

        # call setup listener, defining xp, queue, default binding (will get our return value above) becuase there's no meat to _declare_queue
        self.ch.setup_listener(('xp', 'bum'))

        self.assertTrue(hasattr(self.ch, '_recv_name'))
        self.assertEquals(self.ch._recv_name, ('xp', 'bum'))

        mxp.assert_called_once_with('xp')
        mdq.assert_called_once_with('bum')
        mb.assert_called_once_with('amq-1234')

        # call setup listener, passing a custom bind this time
        self.ch.setup_listener(('xp2', 'bum2'), binding='notbum')

        mxp.assert_called_with('xp2')
        mdq.assert_called_with('bum2')
        mb.assert_called_with('notbum')

        # call setup_listener, use anonymous queue name and no binding (will get return value we set above)
        self.ch.setup_listener(('xp3', None))

        mxp.assert_called_with('xp3')
        mdq.assert_called_with(None)
        mb.assert_called_with('amq-1234')

        # call setup_listener with anon queue name but with binding
        self.ch.setup_listener(('xp4', None), binding='known')

        mxp.assert_called_with('xp4')
        mdq.assert_called_with(None)
        mb.assert_called_with('known')

    def test_start_consume(self):
        ac = Mock(pchannel.Channel)
        self.ch._amq_chan = ac

        ac.basic_consume.return_value = sentinel.consumer_tag

        # set up recv name for queue
        self.ch._recv_name = (sentinel.xp, sentinel.queue)

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
        self.ch._recv_name = (sentinel.xp, sentinel.queue)

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
    def test_close_impl_stops_consuming(self, mockbasechannel):
        self.ch._consuming = True
        scmock = Mock()

        self.ch.stop_consume = scmock

        self.ch.close_impl()
        scmock.assert_called_once_with()

    @patch('pyon.net.channel.BaseChannel')
    def test_close_impl_deletes_queue(self, mockbasechannel):
        ac = Mock(pchannel.Channel)

        # make callback sideeffect for blocking_cb
        def side(*args, **kwargs):
            cb = kwargs.get('callback')
            cb()

        ac.queue_delete.side_effect = side

        self.ch._amq_chan = ac

        self.ch._queue_auto_delete = False
        self.ch._recv_name = (sentinel.xp, sentinel.queue)

        self.ch.close_impl()

        self.assertTrue(ac.queue_delete.called)
        self.assertIn(sentinel.queue, ac.queue_delete.call_args[1].itervalues())
        self.assertIn('queue', ac.queue_delete.call_args[1])

    def test_declare_queue(self):
        # sideeffect that passes a result back (important here)
        framemock = Mock()
        framemock.method.queue = sentinel.queue

        def side(*args, **kwargs):
            cb = kwargs.get('callback')
            cb(framemock)

        ac = Mock(spec=pchannel.Channel)
        self.ch._amq_chan = ac

        ac.queue_declare.side_effect = side

        # needs a recv name
        self.ch._recv_name = (str(sentinel.xp), None)

        qd = self.ch._declare_queue(str(sentinel.queue))    # can't join a sentinel

        self.assertTrue(ac.queue_declare.called)
        self.assertIn('queue', ac.queue_declare.call_args[1])
        self.assertIn('auto_delete', ac.queue_declare.call_args[1])
        self.assertIn('durable', ac.queue_declare.call_args[1])

        composed = ".".join([str(sentinel.xp), str(sentinel.queue)])
        self.assertIn(composed, ac.queue_declare.call_args[1].itervalues())
        self.assertIn(self.ch._queue_auto_delete, ac.queue_declare.call_args[1].itervalues())
        self.assertIn(self.ch._queue_durable, ac.queue_declare.call_args[1].itervalues())

        # should have set recv_name
        self.assertEquals(self.ch._recv_name, (str(sentinel.xp), sentinel.queue))
        self.assertEquals(qd, sentinel.queue)

    def test__bind_no_name(self):
        self.assertRaises(AssertionError, self.ch._bind, sentinel.binding)

    def test__bind(self):
        self.ch._recv_name = (sentinel.xp, sentinel.queue)

        def side(*args, **kwargs):
            cb = kwargs.get('callback')
            cb()

        ac = Mock(spec=pchannel.Channel)
        ac.queue_bind.side_effect = side
        self.ch._amq_chan = ac

        self.ch._bind(sentinel.binding)

        self.assertTrue(ac.queue_bind.called)
        self.assertIn('queue', ac.queue_bind.call_args[1])
        self.assertIn('exchange', ac.queue_bind.call_args[1])
        self.assertIn('routing_key', ac.queue_bind.call_args[1])

        self.assertIn(sentinel.queue, ac.queue_bind.call_args[1].itervalues())
        self.assertIn(sentinel.xp, ac.queue_bind.call_args[1].itervalues())
        self.assertIn(sentinel.binding, ac.queue_bind.call_args[1].itervalues())

    def test__on_deliver(self):
        # mock up the method frame (delivery_tag is really only one we care about)
        m = Mock()
        m.consumer_tag  = sentinel.consumer_tag
        m.delivery_tag  = sentinel.delivery_tag
        m.redelivered   = sentinel.redelivered
        m.exchange      = sentinel.exchange
        m.routing_key   = sentinel.routing_key

        # mock up the headers (they get merged down)
        h = Mock()
        h.this_exists = sentinel.exists
        h.headers = { 'this_also_exists': sentinel.also_exists }

        # use a mock for the recv queue
        rqmock = Mock(spec=queue.Queue)
        self.ch._recv_queue = rqmock

        # now we can call!
        self.ch._on_deliver(sentinel.chan, m, h, sentinel.body)

        # build what we expect from the header merging (is this proper?)
        headers = h.__dict__
        headers.update(h.headers)

        # assert the call
        rqmock.put.assert_called_once_with((sentinel.body, headers, sentinel.delivery_tag))

        # assert the headers look ok
        self.assertIn(sentinel.exists, rqmock.put.call_args[0][0][1].itervalues())
        self.assertIn(sentinel.also_exists, rqmock.put.call_args[0][0][1].itervalues())

    def test_ack(self):
        ac = Mock(spec=pchannel.Channel)
        self.ch._amq_chan = ac

        self.ch.ack(sentinel.delivery_tag)

        ac.basic_ack.assert_called_once_with(sentinel.delivery_tag)

class TestPubChannel(IonIntegrationTestCase):
    """
    PubChannel currently doesnt have any meat
    """
    pass

@patch('pyon.net.channel.SendChannel')
class TestBidirClientChannel(IonIntegrationTestCase):

    def setUp(self):
        self.ch = BidirClientChannel()

    def test__send_with_reply_to(self, mocksendchannel):

        self.ch._send(sentinel.name, sentinel.data, headers=sentinel.headers,
                                                    content_type=sentinel.content_type,
                                                    content_encoding=sentinel.content_encoding,
                                                    message_type=sentinel.message_type,
                                                    reply_to=(sentinel.xp_replyto, sentinel.queue_replyto),
                                                    correlation_id=sentinel.correlation_id,
                                                    message_id=sentinel.message_id)

        mocksendchannel._send.assert_called_with(self.ch, sentinel.name, sentinel.data, headers=sentinel.headers,
                                                                               content_type=sentinel.content_type,
                                                                               content_encoding=sentinel.content_encoding,
                                                                               message_type=sentinel.message_type,
                                                                               reply_to=(sentinel.xp_replyto, sentinel.queue_replyto),
                                                                               correlation_id=sentinel.correlation_id,
                                                                               message_id=sentinel.message_id)


    def test__send_with_no_reply_to(self, mocksendchannel):

        # must set recv_name
        self.ch._recv_name = (sentinel.xp, sentinel.queue)

        self.ch._send(sentinel.name, sentinel.data)

        mocksendchannel._send.assert_called_with(self.ch, sentinel.name, sentinel.data, headers=None,
                                                                               content_type=None,
                                                                               content_encoding=None,
                                                                               message_type='rr-data',
                                                                               reply_to="%s,%s" % self.ch._recv_name,
                                                                               correlation_id=None,
                                                                               message_id=None)

class TestListenChannel(IonIntegrationTestCase):

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


class TestSusbcriberChannel(IonIntegrationTestCase):
    """
    SubscriberChannel is a blank for now
    """
    pass

class TestServerChannel(IonIntegrationTestCase):

    def test__create_accepted_channel(self):
        ch = ServerChannel()

        # this is not all that great
        msg = [None, {'reply_to':'one,two'}]

        newch = ch._create_accepted_channel(sentinel.amq_chan, msg)

        self.assertIsInstance(newch, ServerChannel.BidirAcceptChannel)
        self.assertEquals(newch._amq_chan, sentinel.amq_chan)
        self.assertEquals(newch._send_name, ('one', 'two'))


if __name__ == "__main__":
    unittest.main()

