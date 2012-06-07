#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.net import endpoint
from pyon.ion.endpoint import ProcessEndpointUnitMixin, ProcessRPCRequestEndpointUnit, ProcessRPCClient, ProcessRPCResponseEndpointUnit, ProcessRPCServer
from mock import Mock, sentinel, patch, ANY, call, MagicMock
from pyon.net.channel import SendChannel
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr

sentinel_interceptors = {'message_incoming': sentinel.msg_incoming,
                         'message_outgoing': sentinel.msg_outgoing,
                         'process_incoming': sentinel.proc_incoming,
                         'process_outgoing': sentinel.proc_outgoing}

@attr('UNIT')
class TestProcessEndpointUnitMixin(PyonTestCase):

    @patch('pyon.net.endpoint.EndpointUnit.__init__')
    def test_init(self, mockep):
        ep = ProcessEndpointUnitMixin(process=sentinel.proc, other=sentinel.other)
        self.assertEquals(ep._process, sentinel.proc)
        mockep.assert_called_once_with(ep, other=sentinel.other)

    @patch('pyon.net.endpoint.EndpointUnit._build_invocation')
    def test__build_invocation(self, mockbi):
        ep = ProcessEndpointUnitMixin(process=sentinel.proc)
        ep._build_invocation(invother=sentinel.anything)

        mockbi.assert_called_once_with(ep, process=sentinel.proc, invother=sentinel.anything)

    @patch('pyon.ion.endpoint.process_interceptors')
    @patch('pyon.net.endpoint.process_interceptors')
    def test__intercept_msg_in(self, mocknpi, mockipi):
        mockipi.return_value = sentinel.inv2
        mocknpi.return_value = sentinel.inv2
        ep = ProcessEndpointUnitMixin(process=sentinel.proc, interceptors=sentinel_interceptors)

        ep._intercept_msg_in(sentinel.inv)

        mocknpi.assert_has_calls([call(sentinel.msg_incoming, sentinel.inv)])
        mockipi.assert_has_calls([call(sentinel.proc_incoming, sentinel.inv2)])

    @patch('pyon.ion.endpoint.process_interceptors')
    @patch('pyon.net.endpoint.process_interceptors')
    def test__intercept_msg_out(self, mocknpi, mockipi):
        mockipi.return_value = sentinel.inv2
        mocknpi.return_value = sentinel.inv2
        ep = ProcessEndpointUnitMixin(process=sentinel.proc, interceptors=sentinel_interceptors)

        ep._intercept_msg_out(sentinel.inv)

        mockipi.assert_has_calls([call(sentinel.proc_outgoing, sentinel.inv)])
        mocknpi.assert_has_calls([call(sentinel.msg_outgoing, sentinel.inv2)])

    def test__get_sample_name(self):
        ep = ProcessEndpointUnitMixin(process=Mock())
        self.assertEquals(ep._get_sample_name(), str(ep._process.id))

    def test__get_sflow_manager(self):
        ep = ProcessEndpointUnitMixin(process=Mock())
        self.assertEquals(ep._get_sflow_manager(), ep._process.container.sflow_manager)

    @patch('pyon.net.endpoint.BaseEndpoint._get_container_instance')
    def test__build_header_no_context(self, mockgci):
        ep = ProcessEndpointUnitMixin(process=Mock())
        header = ep._build_header(sentinel.raw_msg)

        self.assertIn('sender-name', header)
        self.assertIn('sender', header)
        self.assertIn('sender-type', header)
        self.assertNotIn('sender-service', header)
        self.assertIn('origin-container-id', header)

        self.assertEquals(header['sender-name'], ep._process.name)
        self.assertEquals(header['sender'], ep._process.id)
        self.assertEquals(header['sender-type'], ep._process.process_type)
        self.assertEquals(header['origin-container-id'], mockgci().id)


    @patch('pyon.net.endpoint.BaseEndpoint._get_container_instance')
    def test__build_header_service(self, mockgci):
        procmock = Mock()
        procmock.process_type = 'service'

        ep = ProcessEndpointUnitMixin(process=procmock)
        ep.channel = Mock(spec=SendChannel)
        header = ep._build_header(sentinel.raw_msg)

        self.assertIn('sender-name', header)
        self.assertIn('sender', header)
        self.assertIn('sender-type', header)
        self.assertIn('sender-service', header)
        self.assertIn('origin-container-id', header)

        self.assertEquals(header['sender-name'], ep._process.name)
        self.assertEquals(header['sender'], ep._process.id)
        self.assertEquals(header['sender-type'], ep._process.process_type)
        self.assertEquals(header['sender-service'], "%s,%s" % (ep.channel._send_name.exchange, procmock.name))
        self.assertEquals(header['origin-container-id'], mockgci().id)

    @patch('pyon.net.endpoint.BaseEndpoint._get_container_instance')
    def test__build_header_with_context(self, mockgci):
        procmock = Mock()
        procmock.get_context.return_value={'ion-actor-id': sentinel.ion_actor_id,
                                           'ion-actor-roles': sentinel.ion_actor_roles,
                                           'ion-actor-tokens': sentinel.ion_actor_tokens,
                                           'expiry': sentinel.expiry,
                                           'origin-container-id': sentinel.container_id}

        ep = ProcessEndpointUnitMixin(process=procmock)
        ep.channel = Mock(spec=SendChannel)
        header = ep._build_header(sentinel.raw_msg)

        self.assertIn('ion-actor-id', header)
        self.assertIn('ion-actor-roles', header)
        self.assertIn('ion-actor-tokens', header)
        self.assertIn('expiry', header)
        self.assertIn('origin-container-id', header)

        self.assertEquals(header['ion-actor-id'], sentinel.ion_actor_id)
        self.assertEquals(header['ion-actor-roles'], sentinel.ion_actor_roles)
        self.assertEquals(header['ion-actor-tokens'], sentinel.ion_actor_tokens)
        self.assertEquals(header['expiry'], sentinel.expiry)
        self.assertEquals(header['origin-container-id'], sentinel.container_id)

@attr('UNIT')
class TestProcessRPCRequestEndpointUnit(PyonTestCase):

    @patch('pyon.ion.endpoint.ProcessEndpointUnitMixin.__init__')
    @patch('pyon.net.endpoint.RPCRequestEndpointUnit.__init__')
    def test_init(self, mockr, mockp):

        ep = ProcessRPCRequestEndpointUnit(process=sentinel.process, other=sentinel.other)
        mockp.assert_called_once_with(ep, process=sentinel.process)
        mockr.assert_called_once_with(ep, other=sentinel.other)

    @patch('pyon.ion.endpoint.ProcessEndpointUnitMixin._build_header')
    @patch('pyon.net.endpoint.RPCRequestEndpointUnit._build_header')
    def test__build_header(self, mockr, mockp):

        mockr.return_value = {'one':1, 'two':2}
        mockp.return_value = {'two':-2, 'three':3}

        ep = ProcessRPCRequestEndpointUnit()
        header = ep._build_header(sentinel.raw_msg)

        self.assertEquals(header, {'one':1, 'two':-2, 'three':3})

@attr('UNIT')
class TestProcessRPCClient(PyonTestCase):
    def test_create_endpoint_no_process(self):
        prpc = ProcessRPCClient()
        self.assertRaises(StandardError, prpc.create_endpoint)

    @patch('pyon.net.endpoint.RPCClient.create_endpoint')
    def test_create_endpoint(self, mockce):
        prpc = ProcessRPCClient(process=sentinel.process)
        prpc.create_endpoint(to_name=sentinel.to_name)

        mockce.assert_called_once_with(prpc, sentinel.to_name, None, process=sentinel.process)

@attr('UNIT')
class TestProcessRPCResponseEndpointUnit(PyonTestCase):

    @patch('pyon.ion.endpoint.ProcessEndpointUnitMixin.__init__')
    @patch('pyon.net.endpoint.RPCResponseEndpointUnit.__init__')
    def test_init(self, mockr, mockp):

        ep = ProcessRPCResponseEndpointUnit(process=sentinel.process, other=sentinel.other)
        mockp.assert_called_once_with(ep, process=sentinel.process)
        mockr.assert_called_once_with(ep, other=sentinel.other)

    @patch('pyon.ion.endpoint.ProcessEndpointUnitMixin._build_header')
    @patch('pyon.net.endpoint.RPCResponseEndpointUnit._build_header')
    def test__build_header(self, mockr, mockp):

        mockr.return_value = {'one':1, 'two':2}
        mockp.return_value = {'two':-2, 'three':3}

        ep = ProcessRPCResponseEndpointUnit()
        header = ep._build_header(sentinel.raw_msg)

        self.assertEquals(header, {'one':1, 'two':-2, 'three':3})

    @patch('pyon.net.endpoint.RPCResponseEndpointUnit._message_received')
    def test__message_received(self, mockmr):
        procmock = Mock()
        procmock.push_context = MagicMock()

        ep = ProcessRPCResponseEndpointUnit(process=procmock, interceptors={})
        ep._message_received(sentinel.msg, sentinel.headers)

        procmock.push_context.assert_called_once_with(sentinel.headers)
        procmock.push_context().__enter__.assert_called_once_with()
        mockmr.assert_called_once_with(ep, sentinel.msg, sentinel.headers)

@attr('UNIT')
class TestProcessRPCServer(PyonTestCase):
    def test_init_no_process(self):
        self.assertRaises(AssertionError, ProcessRPCServer)

    @patch('pyon.net.endpoint.RPCServer.create_endpoint')
    def test_create_endpoint(self, mockce):
        prps = ProcessRPCServer(process=sentinel.process)
        prps.routing_call = sentinel.rcall
        prps.create_endpoint(to_name=sentinel.to_name)

        mockce.assert_called_once_with(prps, process=sentinel.process, to_name=sentinel.to_name, routing_call=sentinel.rcall)

