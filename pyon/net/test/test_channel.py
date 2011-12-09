#!/usr/bin/env python
import unittest
from unittest.case import SkipTest
from nose.plugins.attrib import attr
from zope.interface import interface
from zope.interface.declarations import implements
from zope.interface.interface import Interface
from pyon.core import exception
from pyon.net import endpoint
from pyon.net.channel import BaseChannel, SendChannel, RecvChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel, ChannelError
from gevent import event, GreenletExit
from pyon.net.messaging import NodeB
from pyon.service.service import BaseService
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from pyon.util.async import wait, spawn
from mock import Mock, sentinel
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
        raise SkipTest("not yet")

    def test_stop_consume(self):
        ac = Mock(pchannel.Channel)
        self.ch._amq_chan = ac

        # we're not consuming, so this should raise
        self.assertRaises(ChannelError, self.ch.stop_consume)

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

if __name__ == "__main__":
    unittest.main()

