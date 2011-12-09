#!/usr/bin/env python
import unittest
from unittest.case import SkipTest
from nose.plugins.attrib import attr
from zope.interface import interface
from zope.interface.declarations import implements
from zope.interface.interface import Interface
from pyon.core import exception
from pyon.net import endpoint
from pyon.net.channel import BaseChannel, SendChannel, RecvChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel
from gevent import event, GreenletExit
from pyon.net.messaging import NodeB
from pyon.service.service import BaseService
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from pyon.util.async import wait, spawn
from mock import Mock
from pika import channel as pchannel

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
        





if __name__ == "__main__":
    unittest.main()

