#!/usr/bin/env python

__author__ = 'Stephen Henrie'
__license__ = 'Apache 2.0'

from pyon.ion.conversation import ConversationRPCClient, ConversationRPCServer, RPCRequesterEndpointUnit
from mock import Mock, sentinel, patch, ANY, call, MagicMock
from pyon.util.unit_test import PyonTestCase
from pyon.core.exception import Unauthorized
from nose.plugins.attrib import attr


@attr('UNIT')
class TestRPCRequesterEndpointUnit(PyonTestCase):

    @patch('pyon.ion.endpoint.ProcessEndpointUnitMixin.__init__')
    @patch('pyon.net.endpoint.RPCRequestEndpointUnit.__init__')
    def test_init(self, mockr, mockp):

        ep = RPCRequesterEndpointUnit(process=sentinel.process, other=sentinel.other)
        mockp.assert_called_once_with(ep, process=sentinel.process)
        mockr.assert_called_once_with(ep, other=sentinel.other)


@attr('UNIT')
class TestProcessRPCClient(PyonTestCase):
    def test_create_endpoint_no_process(self):
        prpc = ConversationRPCClient()
        self.assertRaises(StandardError, prpc.create_endpoint)

    @patch('pyon.ion.endpoint.ProcessRPCClient.create_endpoint')
    def test_create_endpoint(self, mockce):
        prpc = ConversationRPCClient(process=sentinel.process)
        prpc.create_endpoint(to_name=sentinel.to_name)

        mockce.assert_called_once_with(prpc, sentinel.to_name, None)

@attr('UNIT')
class TestProcessRPCServer(PyonTestCase):
    def test_init_no_process(self):
        self.assertRaises(AssertionError, ConversationRPCServer)

    @patch('pyon.net.endpoint.RPCServer.create_endpoint')
    def test_create_endpoint(self, mockce):
        prps = ConversationRPCServer(process=sentinel.process)
        prps.routing_call = sentinel.rcall
        prps.create_endpoint(to_name=sentinel.to_name)

        mockce.assert_called_once_with(prps, process=sentinel.process, to_name=sentinel.to_name, routing_call=sentinel.rcall)

