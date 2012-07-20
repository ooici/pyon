#!/usr/bin/env python

from pyon.net.channel import BaseChannel, SendChannel, RecvChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel, ChannelError, ChannelShutdownMessage, ListenChannel, PublisherChannel
from gevent import queue, spawn
from pyon.util.unit_test import PyonTestCase
from mock import Mock, sentinel, patch
from pika import channel as pchannel
from pika import BasicProperties
from nose.plugins.attrib import attr
from pyon.net.transport import NameTrio, BaseTransport
from pyon.util.fsm import ExceptionFSM
from pyon.util.int_test import IonIntegrationTestCase
import time
from gevent.event import Event
import Queue as PQueue
from gevent.queue import Queue
from unittest import skip
from pyon.core import bootstrap
from pyon.net.conversation import Conversation, ConversationEndpoint, Principal
from gevent.event import AsyncResult
from pyon.net.messaging import NodeB

@attr('UNIT')
class TestConversation(PyonTestCase):
    def setUp(self):
        self.conv  = Conversation('test_protocol')

    def test_init_properties(self):
        self.assertIsNotNone(self.conv .id)
        self.assertIsNotNone(self.conv .protocol)

    def test_init_without_id(self):
        conversation_with_auto_generated_id = Conversation('test_protocol')
        self.assertIsNotNone(conversation_with_auto_generated_id.id)

    def test_init_with_id(self):
        cid = 1234
        conversation_with_id = Conversation('test_protocol', cid)
        self.assertEqual(conversation_with_id.id, cid)

    def test_has_role(self):
        test_role = 'test_role'
        self.assertFalse(self.conv .has_role(test_role))
        self.conv ._conv_table[test_role] = 'test_role_name'
        self.assertTrue(self.conv .has_role(test_role))

    def test_add_to_conv_table(self):
        """
        We need to check that:
        1. For each entity of type EventAsync in the table, a set is called
        2. For each entity that is not EventAsync a proper value is set
        """

        #test data
        test_role_with_async = 'test_role_async'
        test_role_existing = 'test_role_general'
        test_role_new = 'test_role_new'
        role_address_for_existing = 'rumi-PC1'
        role_address_for_new = 'rumi-PC2'
        event = Mock(spec=AsyncResult)

        # test case 1. Value of type AsyncResult exists
        self.conv ._conv_table = {test_role_with_async: event, test_role_existing: 'ala-bala'}
        self.conv [test_role_with_async] = role_address_for_existing
        event.set.assert_called_once_with(role_address_for_existing)

        # test case 2.1. Value exist, but is not AsyncResult => it is overriden
        self.conv [test_role_existing] = role_address_for_existing
        self.assertEqual(self.conv ._conv_table[test_role_existing], role_address_for_existing)

        # test case 2.2. Value does not exist
        self.conv [test_role_new] = role_address_for_new
        self.assertEqual(self.conv ._conv_table[test_role_new], role_address_for_new)



    def test_get_from_conv_table(self):
        """
        We need to check that:
        1. Get always return an value
        2. If the entity already exist its value is return immediately
        3. If an entity does not exist we block while the value is available and then return it
        """
        #test data and mock objects
        test_role_with_async = 'test_role_async'
        test_role_with_async_value = 'rumi-PC-async'
        test_role_general = 'test_role_general'
        test_role_general_value = 'rumi-PC'
        event = Mock(spec=AsyncResult)
        self.conv ._conv_table = {test_role_with_async: event,
                                  test_role_general: test_role_general_value}

        # test existing value
        value = self.conv [test_role_general]
        self.assertEqual(value, test_role_general_value)

        def event_get():
            return test_role_with_async_value
        # test async value
        event.get.side_effect = event_get
        value = self.conv [test_role_with_async]
        event.get.assert_called_once()
        print 'value is" %s' %value
        self.assertEqual(value, test_role_with_async_value)

        # TODO:How to test a value that does not exist???

class TestPrincipal(PyonTestCase):
    def setUp(self):
        self.node = Mock(spec = NodeB)
        self.name_exchange, self.name_queue = 'rumi-exchange', 'rumi-queue'
        self.name = NameTrio(self.name_exchange, self.name_queue)
        self.principal = Principal(self.node, self.name)

    def test_start_conversation(self):
        protocol = 'test_protocol'
        role = 'test_role'

        endpoint = self.principal.start_conversation(protocol, role)
        self.assertIsInstance(endpoint, ConversationEndpoint)

        self.assertEqual(endpoint._conv.protocol , protocol)
        self.assertEqual(endpoint._self_role , role)
        self.assertIsNotNone(endpoint._recv_greenlet)




@attr('UNIT')
class TestConversationEndpoint(PyonTestCase):
    pass
