#!/usr/bin/env python

__author__ = 'Stephen Henrie'
__license__ = 'Apache 2.0'


from pyon.ion.conversation import ConversationRPCClient, ConversationRPCServer, RPCRequesterEndpointUnit
from mock import Mock, sentinel, patch, ANY, call, MagicMock
from pyon.util.unit_test import PyonTestCase
from pyon.util.int_test import IonIntegrationTestCase
from pyon.core.exception import Inconsistent
from nose.plugins.attrib import attr
from pyon.service.service import BaseService
from pyon.net.endpoint import RPCClient
from pyon.util.context import LocalContextMixin

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


class ConversationTestProcess(LocalContextMixin):
    name = 'conv_test'
    id='conv_test'
    process_type = 'simple'


class StringService(BaseService):
    """
    Class to use for testing below.
    """
    name = 'string_service'
    id = 'string_service'
    dependencies = []

    def reverse(self, text=''):
        return text[::-1]


class ProviderService(BaseService):
    """
    Class to use for testing below.
    """
    name = 'provider_service'
    id = 'provider_service'
    dependencies = []

    def reverse_string(self, text=''):
        string_client = ConversationRPCClient(to_name='string_service', process=self)

        #By specifying a conversation id, a caller that uses the same id will cause the conversation
        #monitor to detect an error in the use of the RPC protocol defined in Scribble.
        return string_client.request({'text': text}, op='reverse', headers = {'conv-id':1234})

@attr('INT', group='coi')

class TestConversationInterceptor(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()

        #Instantiate a process to represent the test
        process = ConversationTestProcess()

        self.pid = self.container.spawn_process('string', 'pyon.ion.test.test_conversation', 'StringService')
        self.pid = self.container.spawn_process('provider', 'pyon.ion.test.test_conversation', 'ProviderService')
        self.provider_client = ConversationRPCClient(to_name='provider_service', process=process)

    def test_interceptor_passes(self):

        ret = self.provider_client.request({'text': 'hello world'}, op='reverse_string' )

        #Check to see if the text has been reversed.
        self.assertEqual(ret,'dlrow olleh')

    def test_interceptor_fails(self):

        #Should throw an exception by intentionally passing in a conversation id already in use within the service
        #This is not allowed.
        with self.assertRaises(Inconsistent) as cm:
            ret = self.provider_client.request({'text': 'hello world'}, op='reverse_string', headers = {'conv-id':1234} )
        self.assertIn( 'Conversation interceptor error for message reverse from provider_service: Transition is undefined: (RESV_reverse_requester, 2)',cm.exception.message)

