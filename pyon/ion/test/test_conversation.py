#!/usr/bin/env python
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher

__author__ = 'Stephen Henrie'


from pyon.ion.conversation import ConversationRPCClient, ConversationRPCServer, RPCRequesterEndpointUnit, RPCProviderEndpointUnit
from mock import Mock, sentinel, patch, ANY, call, MagicMock
from pyon.util.unit_test import PyonTestCase
from pyon.util.int_test import IonIntegrationTestCase
from pyon.core.exception import Inconsistent
from nose.plugins.attrib import attr
from pyon.ion.service import BaseService
from pyon.net.endpoint import RPCClient, BidirectionalEndpointUnit
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

    def reverse_string(self, text='', set_convo_id = None):
        string_client = ConversationRPCClient(to_name='string_service', process=self)


        #By specifying a conversation id, a caller that uses the same id will cause the conversation
        #monitor to detect an error in the use of the RPC protocol defined in Scribble.
        if set_convo_id is not None:
            return string_client.request({'text': text}, op='reverse', headers = {'conv-id':set_convo_id})
        else:
            return string_client.request({'text': text}, op='reverse')

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

    def test_interceptor_fails_with_bad_convo_id(self):

        forced_convo_id = '1234'

        #Should throw an exception by intentionally passing in a conversation id already in use within the service
        #This is not allowed.
        with self.assertRaises(Inconsistent) as cm:
            ret = self.provider_client.request({'text': 'hello world', 'set_convo_id': forced_convo_id}, op='reverse_string', headers = {'conv-id': forced_convo_id} )
        self.assertIn( 'Conversation interceptor error for message reverse from provider_service: Transition is undefined: (RESV_reverse_requester, 2)',cm.exception.message)

    def test_interceptor_fails_when_send_multiple_messages(self):


        # save off old send
        old_send = BidirectionalEndpointUnit._send

        class WrongMessageAssertion(Exception):
            pass

        def handle_outgoing_message(*args, **kwargs):
            inv  = args[1]
            if inv.message_annotations.has_key(GovernanceDispatcher.CONVERSATION__STATUS_ANNOTATION) and\
               inv.message_annotations[GovernanceDispatcher.CONVERSATION__STATUS_ANNOTATION] == GovernanceDispatcher.STATUS_REJECT:
                    raise WrongMessageAssertion("Monitor detected an error")

        # make new send to patch on that duplicates send
        def new_send(*args, **kwargs):

            #Only duplicate the message send from the initial client call
            msg_headers = kwargs['headers']
            if msg_headers['conv-id'] == msg_headers['original-conv-id']:
                old_send(*args, **kwargs)

            return old_send(*args, **kwargs)

        # patch it into place with auto-cleanup to send a duplicate message at the channel layer which
        #is below the interceptors
        patcher = patch('pyon.net.endpoint.BidirectionalEndpointUnit._send', new_send)
        patcher.start()
        self.addCleanup(patcher.stop)

        # patch to throw an exception to be caught by the test
        patcher = patch('pyon.core.governance.governance_dispatcher.GovernanceDispatcher.handle_outgoing_message',
                        handle_outgoing_message)
        patcher.start()
        self.addCleanup(patcher.stop)

        #The above patch will intentionally forcing the message to be sent twice which will cause the conversation monitor
        # to detect a duplicate message for the same conversation id and throw an exception.
        #This is not allowed.
        with self.assertRaises(WrongMessageAssertion) as cm:
            ret = self.provider_client.request({'text': 'hello world'}, op='reverse_string' )
