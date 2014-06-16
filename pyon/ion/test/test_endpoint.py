#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'

from pyon.net import endpoint
from pyon.ion.endpoint import ProcessEndpointUnitMixin, ProcessRPCRequestEndpointUnit, ProcessRPCClient, ProcessRPCResponseEndpointUnit, ProcessRPCServer, ProcessPublisherEndpointUnit, ProcessPublisher, ProcessSubscriberEndpointUnit, ProcessSubscriber
from mock import Mock, sentinel, patch, ANY, call, MagicMock
from pyon.net.channel import SendChannel
from pyon.util.unit_test import PyonTestCase
from pyon.core.exception import Unauthorized
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
        header = ep._build_header(sentinel.raw_msg, {})

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
        header = ep._build_header(sentinel.raw_msg, {})

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
        header = ep._build_header(sentinel.raw_msg, {})

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
        header = ep._build_header(sentinel.raw_msg, {})

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
        header = ep._build_header(sentinel.raw_msg, {})

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

    @patch('pyon.net.endpoint.RPCResponseEndpointUnit._message_received')
    def test_message_received(self, mockmr):
        procmock = Mock()
        procmock.push_context = MagicMock()


        ep = ProcessRPCResponseEndpointUnit(process=procmock, interceptors={})
        ep._routing_obj = procmock

        msg_dict = {'iam':'adict'}
        header_dict =   {'op':'anyop'}
        ep.message_received(msg_dict, header_dict)

        ep._routing_obj.anyop.assert_called_once_with(iam='adict')

        def deny_anyop(self, operation, id=None):
            raise Unauthorized('The anyop operation has been denied')

        msg_dict2 = {'iam':'adict2'}
        ep._routing_obj._service_op_preconditions = {'anyop': 'deny_anyop'}
        ep._routing_obj.container.governance_controller.check_process_operation_preconditions = deny_anyop
        with self.assertRaises(Unauthorized) as cm:
            ep.message_received(msg_dict2, header_dict)
        self.assertIn('The anyop operation has been denied',cm.exception.message)

        #Using the internal mock counter to see if it was still only called once.
        ep._routing_obj.anyop.assert_called_once_with(iam='adict')



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


@attr('UNIT')
class TestProcessPublisherEndpointUnit(PyonTestCase):

    @patch('pyon.ion.endpoint.ProcessEndpointUnitMixin._build_header')
    @patch('pyon.net.endpoint.PublisherEndpointUnit._build_header')
    def test_build_header(self, mockr, mockp):
        mockr.return_value = {'one':1, 'two':2}
        mockp.return_value = {'two':-2, 'three':3}

        ep = ProcessPublisherEndpointUnit()
        header = ep._build_header(sentinel.raw_msg, {})

        self.assertEquals(header, {'one':1, 'two':-2, 'three':3})

@attr('UNIT')
class TestProcessPublisher(PyonTestCase):

    @patch('pyon.ion.endpoint.Publisher.__init__')
    def test_init(self, mockp):
        p = ProcessPublisher(sentinel.process, kw1=sentinel.kw1, kw2=sentinel.kw2)

        self.assertEquals(p._process, sentinel.process)
        mockp.assert_called_once_with(p, kw1=sentinel.kw1, kw2=sentinel.kw2)

    @patch('pyon.ion.endpoint.Publisher.create_endpoint')
    def test_create_endpoint(self, mockpce):
        p = ProcessPublisher(sentinel.process)

        ep = p.create_endpoint(sentinel.arg, kw=sentinel.kwarg)
        mockpce.assert_called_once_with(ANY, sentinel.arg, process=sentinel.process, kw=sentinel.kwarg)


@attr('UNIT')
class TestProcessSubscriberEndpointUnit(PyonTestCase):

    @patch('pyon.ion.endpoint.ProcessEndpointUnitMixin.__init__')
    @patch('pyon.net.endpoint.SubscriberEndpointUnit.__init__')
    def test_init(self, mockr, mockp):

        ep = ProcessSubscriberEndpointUnit(process=sentinel.process, callback=sentinel.callback, other=sentinel.other)
        mockp.assert_called_once_with(ep, process=sentinel.process)
        mockr.assert_called_once_with(ep, callback=sentinel.callback, other=sentinel.other)

    @patch('pyon.ion.endpoint.ProcessEndpointUnitMixin._build_header')
    @patch('pyon.net.endpoint.SubscriberEndpointUnit._build_header')
    def test__build_header(self, mockr, mockp):

        mockr.return_value = {'one':1, 'two':2}
        mockp.return_value = {'two':-2, 'three':3}

        ep = ProcessSubscriberEndpointUnit()
        header = ep._build_header(sentinel.raw_msg, {})

        self.assertEquals(header, {'one':1, 'two':-2, 'three':3})

    @patch('pyon.net.endpoint.SubscriberEndpointUnit._message_received')
    def test__message_received(self, mockmr):
        procmock = Mock()
        procmock.push_context = MagicMock()

        ep = ProcessSubscriberEndpointUnit(process=procmock, interceptors={})
        ep._message_received(sentinel.msg, sentinel.headers)

        procmock.push_context.assert_called_once_with(sentinel.headers)
        procmock.push_context().__enter__.assert_called_once_with()
        mockmr.assert_called_once_with(ep, sentinel.msg, sentinel.headers)

    @patch('pyon.ion.endpoint.SubscriberEndpointUnit._make_routing_call')
    def test__make_routing_call(self, mockmrc):
        ep = ProcessSubscriberEndpointUnit()

        ep._make_routing_call(sentinel.call, sentinel.timeout, sentinel.arg, kw=sentinel.kwarg)
        mockmrc.assert_called_once_with(ep, sentinel.call, sentinel.timeout, sentinel.arg, kw=sentinel.kwarg)

    def test__make_routing_call_with_routing_call_set(self):
        mrc = Mock()
        proc = Mock()
        proc.get_context.return_value = sentinel.context

        ep = ProcessSubscriberEndpointUnit(process=proc, routing_call=mrc)

        ep._make_routing_call(sentinel.call, sentinel.timeout, sentinel.arg, kw=sentinel.kwarg)
        mrc.assert_called_once_with(sentinel.call, sentinel.context, sentinel.arg, kw=sentinel.kwarg)

        mrcar = mrc()
        #mrcar.get.assert_called_once_with(timeout=sentinel.timeout)
        mrcar.get.assert_called_once_with()


@attr('UNIT')
class TestProcessSubscriber(PyonTestCase):
    @patch('pyon.ion.endpoint.Subscriber.__init__')
    def test_init(self, mocks):
        s = ProcessSubscriber(process=sentinel.process, routing_call=sentinel.routing_call, kw1=sentinel.kw1, kw2=sentinel.kw2)

        self.assertEquals(s._process, sentinel.process)
        self.assertEquals(s._routing_call, sentinel.routing_call)
        mocks.assert_called_once_with(s, kw1=sentinel.kw1, kw2=sentinel.kw2)

    def test_routing_call_property(self):
        s = ProcessSubscriber(process=sentinel.process, routing_call=sentinel.routing_call)

        self.assertEquals(s.routing_call, sentinel.routing_call)

        s.routing_call = sentinel.something_else
        self.assertEquals(s.routing_call, sentinel.something_else)

    @patch('pyon.ion.endpoint.Subscriber.create_endpoint')
    def test_create_endpoint(self, mockce):

        s = ProcessSubscriber(process=sentinel.process, routing_call=sentinel.routing_call)
        ep = s.create_endpoint(kw=sentinel.kwarg)

        mockce.assert_called_once_with(ANY, process=sentinel.process, routing_call=sentinel.routing_call, kw=sentinel.kwarg)

