#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

import unittest
from zope.interface.declarations import implements
from zope.interface.interface import Interface
from pyon.core import exception
from pyon.net import endpoint
from pyon.net.channel import BaseChannel, SendChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel, RecvChannel, ListenChannel
from pyon.net.endpoint import EndpointUnit, BaseEndpoint, RPCServer, Subscriber, Publisher, RequestResponseClient, RequestEndpointUnit, RPCRequestEndpointUnit, RPCClient, RPCResponseEndpointUnit, EndpointError, SendingBaseEndpoint, ListeningBaseEndpoint, ProcessEndpointUnitMixin, ProcessRPCRequestEndpointUnit, ProcessRPCClient, ProcessRPCResponseEndpointUnit, ProcessRPCServer
from gevent import event, sleep
from pyon.net.messaging import NodeB
from pyon.service.service import BaseService
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
from mock import Mock, sentinel, patch, ANY, call, MagicMock
from pyon.container.cc import Container
from pyon.core.interceptor.interceptor import Invocation
from pyon.net.transport import NameTrio, BaseTransport
from pyon.util.sflow import SFlowManager

# NO INTERCEPTORS - we use these mock-like objects up top here which deliver received messages that don't go through the interceptor stack.
no_interceptors = {'message_incoming': [],
                   'message_outgoing': [],
                   'process_incoming': [],
                   'process_outgoing': []}

class TestError(StandardError):
    """
    Newly defined error, used for side effects in Mock tests.
    """
    pass

@attr('UNIT')
@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
class TestEndpointUnit(PyonTestCase):

    def setUp(self):
        self._endpoint_unit = EndpointUnit()

    def test_attach_channel(self):
        ch = Mock(spec=BaseChannel)
        self._endpoint_unit.attach_channel(ch)

        self.assertTrue(self._endpoint_unit.channel is not None)
        self.assertEquals(self._endpoint_unit.channel, ch)

    @patch('pyon.net.endpoint.get_ion_ts', Mock(return_value=sentinel.ts))
    def test_send(self):

        # need a channel to send on
        self.assertRaises(AttributeError, self._endpoint_unit.send, "fake")

        ch = Mock(spec=SendChannel)
        self._endpoint_unit.attach_channel(ch)

        self._endpoint_unit.send("hi", {'header':'value'})
        ch.send.assert_called_once_with('hi', {'header':'value', 'ts':sentinel.ts})

    def test_close(self):
        ch = Mock(spec=BaseChannel)
        self._endpoint_unit.attach_channel(ch)
        self._endpoint_unit.close()
        ch.close.assert_called_once_with()

    def test_spawn_listener(self):
        def recv():
            ar = event.AsyncResult()
            ar.wait()

        ch = Mock(spec=BidirClientChannel)
        ch.recv.side_effect = recv
        self._endpoint_unit.attach_channel(ch)

        self._endpoint_unit.spawn_listener()

        self._endpoint_unit.close()
        self.assertTrue(self._endpoint_unit._recv_greenlet.ready())

    def test_build_header(self):
        head = self._endpoint_unit._build_header({'fake': 'content'})
        self.assertTrue(isinstance(head, dict))

    def test_build_payload(self):
        fakemsg = {'fake':'content'}
        msg = self._endpoint_unit._build_payload(fakemsg)
        self.assertEquals(msg, fakemsg)

    def test_build_msg(self):
        fakemsg = {'fake':'content'}
        msg = self._endpoint_unit._build_msg(fakemsg)
#        self.assertTrue(isinstance(msg, dict))
#        self.assertTrue(msg.has_key('header'))
#        self.assertTrue(msg.has_key('payload'))
#        self.assertTrue(isinstance(msg['header'], dict))
#        self.assertEquals(fakemsg, msg['payload'])

    def test__message_received(self):
        self._endpoint_unit._build_invocation = Mock()
        self._endpoint_unit._intercept_msg_in = Mock()
        self._endpoint_unit.message_received  = Mock()
        self._endpoint_unit.message_received.return_value = sentinel.msg_return


        retval = self._endpoint_unit._message_received(sentinel.msg, sentinel.headers)

        self.assertEquals(retval, sentinel.msg_return)

        self._endpoint_unit._build_invocation.assert_called_once_with(path=Invocation.PATH_IN,
                                                                      message=sentinel.msg,
                                                                      headers=sentinel.headers)
        self.assertTrue(self._endpoint_unit._intercept_msg_in.called)
        self.assertTrue(self._endpoint_unit.message_received.called)

@attr('UNIT')
@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
class TestBaseEndpoint(PyonTestCase):
    def setUp(self):
        self._node = Mock(spec=NodeB)
        self._ef = BaseEndpoint(node=self._node)
        self._ch = Mock(spec=SendChannel)
        self._node.channel.return_value = self._ch

    def test_create_endpoint(self):
        e = self._ef.create_endpoint()

        # check attrs
        self.assertTrue(hasattr(e, 'channel'))

        # make sure we can shut it down
        e.close()
        self._ch.close.assert_any_call()

    def test_create_endpoint_existing_channel(self):
        ch = Mock(spec=SendChannel)
        e = self._ef.create_endpoint(existing_channel=ch)
        self.assertEquals(e.channel, ch)
        self.assertEquals(ch.connect.call_count, 0)

        ch.connect("exist")
        ch.connect.assert_called_once_with('exist')
        
        e.close()

    def test_create_endpoint_kwarg(self):
        """
        Make sure our kwarg gets set.
        """

        class OptEndpointUnit(EndpointUnit):
            def __init__(self, opt=None, **kwargs):
                self._opt = opt
                EndpointUnit.__init__(self, **kwargs)

        self._ef.endpoint_unit_type = OptEndpointUnit

        e = self._ef.create_endpoint(opt="stringer")
        self.assertTrue(hasattr(e, "_opt"))
        self.assertEquals(e._opt, "stringer")

    def test__ensure_node_errors(self):
        bep = BaseEndpoint()
        gcimock = Mock()
        gcimock.return_value = None
        with patch('pyon.net.endpoint.BaseEndpoint._get_container_instance', gcimock):
            self.assertRaises(EndpointError, bep._ensure_node)

    @patch('pyon.net.endpoint.BaseEndpoint._get_container_instance')
    def test__ensure_node_existing_node(self, gcimock):
        self._ef._ensure_node()
        self.assertFalse(gcimock.called)

    @patch('pyon.net.endpoint.BaseEndpoint._get_container_instance')
    def test__ensure_node(self, gcimock):
        bep = BaseEndpoint()
        self.assertIsNone(bep.node)

        bep._ensure_node()

        self.assertEquals(bep.node, gcimock().node)

    def test__get_container_instance(self):
        c = Container() # ensure we've got an instance in Container.instance
        self.assertEquals(BaseEndpoint._get_container_instance(), c)

    def test_close(self):
        bep = BaseEndpoint()
        bep.close()

        # well, it's just a pass, so nothing happens/there for us to test

@attr('UNIT')
@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
class TestSendingBaseEndpoint(PyonTestCase):
    def test_init(self):
        ep = SendingBaseEndpoint(node=sentinel.node)
        self.assertEquals(ep.node, sentinel.node)
        self.assertIsInstance(ep._send_name, NameTrio)

    def test_init_with_to_name(self):
        ep = SendingBaseEndpoint(to_name=(sentinel.xp, sentinel.rkey))
        self.assertEquals(ep._send_name.exchange, sentinel.xp)
        self.assertEquals(ep._send_name.queue, sentinel.rkey)

    @patch('pyon.net.endpoint.log')
    def test_init_with_old_name_gives_warn(self, mocklog):
        ep = SendingBaseEndpoint(name=(sentinel.xp, sentinel.rkey))
        self.assertEquals(ep._send_name.exchange, sentinel.xp)
        self.assertEquals(ep._send_name.queue, sentinel.rkey)
        self.assertTrue(mocklog.warn.called)

    def test_init_with_to_name_namepair(self):
        class MyNameTrio(NameTrio):
            def __init__(self):
                self._exchange = sentinel.my_exchange
                self._queue = sentinel.my_queue

        ep = SendingBaseEndpoint(to_name=MyNameTrio())
        self.assertEquals(ep._send_name.exchange, sentinel.my_exchange)
        self.assertEquals(ep._send_name.queue, sentinel.my_queue)

    def test_create_endpoint_calls_connect(self):
        np = NameTrio(sentinel.xp, sentinel.queue)
        ep = SendingBaseEndpoint(node=Mock(spec=NodeB), to_name=np)
        e = ep.create_endpoint()
        e.channel.connect.assert_called_once_with(np)

    def test_create_endpoint_with_tuple(self):
        ep = SendingBaseEndpoint(node=Mock(spec=NodeB))
        e = ep.create_endpoint(to_name=(sentinel.ex, sentinel.name))
        self.assertIsInstance(e.channel.connect.call_args[0][0], NameTrio)

    def test__create_channel_sets_transport_kwarg(self):
        # if send_name is a transport, it makes sure that kwarg is passed in to node's channel (and therefore the channel)
        class FakeSendName(NameTrio, BaseTransport):
            pass

        fn = FakeSendName()
        ep = SendingBaseEndpoint(node=Mock(spec=NodeB), to_name=fn)

        ch = ep._create_channel()
        self.assertIn('transport', ep.node.channel.call_args[1])
        self.assertIn(fn, ep.node.channel.call_args[1].itervalues())

@attr('UNIT')
class TestListeningBaseEndpoint(PyonTestCase):

    def test__create_channel_sets_transport_kwarg(self):
        # if send_name is a transport, it makes sure that kwarg is passed in to node's channel (and therefore the channel)
        class FakeSendName(NameTrio, BaseTransport):
            pass

        fn = FakeSendName()
        ep = ListeningBaseEndpoint(node=Mock(spec=NodeB), from_name=fn)

        ch = ep._create_channel()
        self.assertIn('transport', ep.node.channel.call_args[1])
        self.assertIn(fn, ep.node.channel.call_args[1].itervalues())

    @patch('pyon.net.endpoint.log')
    def test_init_with_name_instead_of_from_name(self, mocklog):
        ep = ListeningBaseEndpoint(node=Mock(spec=NodeB), name=sentinel.name)
        self.assertEquals(mocklog.warn.call_count, 1)
        self.assertIn("deprecated", mocklog.warn.call_args[0][0])

    def test_get_ready_event(self):
        ep = ListeningBaseEndpoint(node=Mock(spec=NodeB))
        self.assertEquals(ep.get_ready_event(), ep._ready_event)

    def test_close(self):
        ep = ListeningBaseEndpoint(node=Mock(soec=NodeB))
        ep._chan = Mock()
        ep.close()

        ep._chan.close.assert_called_once_with()

    def test_listen_with_base_transport_for_name(self):

        # make a listen loop that will exit right away
        chmock = Mock(spec=ListenChannel)
        chmock.accept.side_effect = ChannelClosedError

        nodemock = Mock(spec=NodeB)
        nodemock.channel.return_value = chmock

        class FakeRecvName(BaseTransport, NameTrio):
            pass
        recv_name = FakeRecvName()
        recv_name.setup_listener = Mock()

        ep = ListeningBaseEndpoint(node=nodemock, from_name=recv_name)
        ep.listen(binding=sentinel.binding)

        self.assertTrue(ep.get_ready_event().is_set())
        self.assertIn('transport', nodemock.channel.call_args[1])
        self.assertIn(recv_name, nodemock.channel.call_args[1].itervalues())

    def test_listen(self):
        # make a listen loop that will exit right away
        chmock = Mock(spec=ListenChannel)
        chmock.accept.side_effect = ChannelClosedError

        nodemock = Mock(spec=NodeB)
        nodemock.channel.return_value = chmock

        ep = ListeningBaseEndpoint(node=nodemock, from_name=NameTrio(sentinel.ex, sentinel.queue))
        ep.listen()

        chmock.setup_listener.assert_called_once_with(ep._recv_name, binding=sentinel.queue)

    @patch('pyon.net.endpoint.log')
    def test_listen_exception_in_handling(self, mocklog):

        # make a listen loop that will return one message (to blow up in processing)
        chmock = MagicMock(spec=ListenChannel)
        chmock.accept.return_value.__enter__.return_value = Mock()
        chmock.accept.return_value.__enter__.return_value.recv = Mock(return_value=(sentinel.msg, sentinel.headers, sentinel.delivery_tag))

        nodemock = Mock(spec=NodeB)
        nodemock.channel.return_value = chmock

        recv_name = NameTrio(sentinel.ex, sentinel.queue)

        ep = ListeningBaseEndpoint(node=nodemock, from_name=recv_name)

        # make msg received error out!
        ep.create_endpoint = Mock(return_value=Mock(spec=EndpointUnit))
        ep.create_endpoint.return_value._message_received.side_effect = TestError

        self.assertRaises(TestError, ep.listen)
        chmock.setup_listener.assert_called_once_with(recv_name, binding=sentinel.queue)
        chmock.start_consume.assert_called_once_with()

        chmock.accept.assert_called_once_with()
        chmock.accept.return_value.__enter__.return_value.recv.assert_called_once_with()
        ep.create_endpoint.assert_called_once_with(existing_channel=chmock.accept.return_value.__enter__.return_value)
        self.assertEquals(mocklog.exception.call_count, 1)

@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
@attr('UNIT')
class TestPublisher(PyonTestCase):
    def setUp(self):
        self._node = Mock(spec=NodeB)
        self._pub = Publisher(node=self._node, to_name="testpub")
        self._ch = Mock(spec=SendChannel)
        self._node.channel.return_value = self._ch

    def test_publish(self):
        self.assertEquals(self._node.channel.call_count, 0)

        self._pub.publish("pub")

        self._node.channel.assert_called_once_with(self._pub.channel_type)
        self.assertEquals(self._ch.send.call_count, 1)

        self._pub.publish("pub2")
        self._node.channel.assert_called_once_with(self._pub.channel_type)
        self.assertEquals(self._ch.send.call_count, 2)

    def test_publish_with_new_name(self):

        self.assertEquals(self._node.channel.call_count, 0)

        self._pub.publish(sentinel.msg, to_name=sentinel.to_name)
        self.assertEquals(self._ch.send.call_count, 1)

        self._pub.publish(sentinel.msg, to_name=sentinel.to_name)
        self.assertEquals(self._ch.send.call_count, 2)

    def test_close(self):
        self._pub.publish(sentinel.msg)
        self._pub._pub_ep.close = Mock()

        self._pub.close()
        self._pub._pub_ep.close.assert_called_once_with()


class RecvMockMixin(object):
    """
    Helper mixin to get a properly mocked receiving channel into several tests.
    """
    def _setup_mock_channel(self, ch_type=BidirClientChannel, status_code=200, error_message="no problem", value="bidirmsg", op=None):
        """
        Sets up a mocked channel, ready for fake bidir communication.

        @param  ch_type         Channel type the mock should spec to.
        @param  status_code     The status code of the operation, relevant only for RR comms.
        @param  error_message   The error message of the operation, relevant only for RR comms.
        @param  op              The op name, relevant only for RR comms.
        @param  value           The msg body to be returned.
        """
        ch = MagicMock(spec=ch_type())
        # set a return value for recv so we get an immediate response
        vals = [(value, {'status_code':status_code, 'error_message':error_message, 'op': op}, sentinel.delivery_tag)]
        def _ret(*args, **kwargs):
            if len(vals):
                return vals.pop()
            raise ChannelClosedError()

        ch.recv.side_effect = _ret

        # need to set a send_name for now
        ch._send_name = NameTrio('', '')

        return ch

@attr('UNIT')
@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
class TestSubscriber(PyonTestCase, RecvMockMixin):

    def setUp(self):
        self._node = Mock(spec=NodeB)

    def test_create_sub_without_callback(self):
        self.assertRaises(AssertionError, Subscriber, node=self._node, from_name="testsub")

    def test_create_endpoint(self):
        def mycb(msg, headers):
            return "test"

        sub = Subscriber(node=self._node, from_name="testsub", callback=mycb)
        e = sub.create_endpoint()

        self.assertEquals(e._callback, mycb)

    def test_subscribe(self):
        """
        Test Subscriber.
        The goal of this test is to get messages routed to the callback mock.
        """
        cbmock = Mock()
        sub = Subscriber(node=self._node, from_name="testsub", callback=cbmock)

        # tell the subscriber to create this as the main listening channel
        listen_channel_mock = self._setup_mock_channel(ch_type=SubscriberChannel, value="subbed", error_message="")
        sub.node.channel.return_value = listen_channel_mock

        # tell our channel to return itself when accepted
        listen_channel_mock.accept.return_value.__enter__.return_value = listen_channel_mock

        # we're ready! call listen
        sub.listen()

        # make sure we got our message
        cbmock.assert_called_once_with('subbed', {'status_code':200, 'error_message':'', 'op': None})

@attr('UNIT')
@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
class TestRequestResponse(PyonTestCase, RecvMockMixin):
    def setUp(self):
        self._node = Mock(spec=NodeB)

    def test_endpoint_send(self):
        e = RequestEndpointUnit()
        ch = self._setup_mock_channel()
        e.attach_channel(ch)

        retval, heads = e.send("msg")
        self.assertEquals(retval, "bidirmsg")

        # cleanup
        e.close()

    @patch('pyon.net.endpoint.BidirectionalEndpointUnit._send', Mock())
    def test_endpoint_send_with_timeout(self):
        e = RequestEndpointUnit()
        e._recv_greenlet = sentinel.recv_greenlet
        e.channel = Mock()

        self.assertRaises(exception.Timeout, e._send, sentinel.msg, sentinel.headers, timeout=1)

    def test_rr_client(self):
        """
        """
        rr = RequestResponseClient(node=self._node, to_name="rr")
        rr.node.channel.return_value = self._setup_mock_channel()

        ret = rr.request("request")
        self.assertEquals(ret, "bidirmsg")

    def test_rr_server(self):
        # Err, not defined at the moment.
        pass


class ISimpleInterface(Interface):
    """
    Defines a simple interface for testing rpc client/servers.
    """
    def simple(one='', two=''):
        pass

class SimpleService(BaseService):
    implements(ISimpleInterface)
    name = "simple"
    dependencies = []
    def __init__(self):
        self._ar = event.AsyncResult()
    def simple(self, named=None):
        self._ar.set(named)
        return True

@attr('UNIT')
@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
class TestRPCRequestEndpoint(PyonTestCase, RecvMockMixin):

    def test_build_msg(self):
        e = RPCRequestEndpointUnit()
        fakemsg = {'fake':'content'}
        msg = e._build_msg(fakemsg)

        # er in json now, how to really check
        self.assertNotEquals(str(msg), str(fakemsg))

    def test_endpoint_send(self):
        e = RPCRequestEndpointUnit()
        ch = self._setup_mock_channel()
        e.attach_channel(ch)

        ret, heads = e.send("rpc call")
        self.assertEquals(ret, 'bidirmsg')      # we just get payload back due to success RPC code 200

        e.close()

    def test_endpoint_send_errors(self):
        errlist = [exception.BadRequest, exception.Unauthorized, exception.NotFound, exception.Timeout, exception.Conflict, exception.ServerError, exception.ServiceUnavailable]

        for err in errlist:
            e = RPCRequestEndpointUnit()
            ch = self._setup_mock_channel(status_code=err.status_code, error_message=str(err.status_code))
            e.attach_channel(ch)

            self.assertRaises(err, e.send, 'payload')

    def test__raise_exception_known(self):
        e = RPCRequestEndpointUnit()
        self.assertRaises(exception.NotFound, e._raise_exception, 404, "no")

    def test__raise_exception_unknown(self):
        e = RPCRequestEndpointUnit()
        self.assertRaises(exception.ServerError, e._raise_exception, 999, "no")

    @patch('pyon.net.endpoint.RequestEndpointUnit._send', Mock(side_effect=exception.Timeout))
    def test_timeout_makes_sflow_sample(self):
        e = RPCRequestEndpointUnit()
        e._sample_request = Mock()

        self.assertRaises(exception.Timeout, e._send, sentinel.msg, sentinel.headers, timeout=1)
        e._sample_request.assert_called_once_with(-1, 'Timeout', sentinel.msg, sentinel.headers, '', {})

    def test__get_sample_name(self):
        e = RPCRequestEndpointUnit()
        self.assertEquals(e._get_sample_name(), "unknown-rpc-client")

    def test__get_sflow_manager(self):
        Container.instance = None
        e = RPCRequestEndpointUnit()
        self.assertIsNone(e._get_sflow_manager())

    def test__get_sflow_manager_with_container(self):
        Container.instance = None
        c = Container()     # ensure an instance
        e = RPCRequestEndpointUnit()
        self.assertEquals(e._get_sflow_manager(), c.sflow_manager)

        Container.instance = None

    @patch('pyon.net.endpoint.time.time', Mock(return_value=1))
    def test__build_sample(self):
        e = RPCRequestEndpointUnit()

        heads = {'conv-id': sentinel.conv_id,
                 'ts': '1',
                 'op': 'remove_femur',
                 'sender': sentinel.sender,
                 'receiver': sentinel.receiver}
        resp_heads = {'sender-service': 'theservice'}

        samp = e._build_sample(sentinel.name, 200, "Ok", "msg", heads, "response", resp_heads)

        self.assertEquals(samp, {
                                    'app_name'  :   sentinel.name,
                                    'op'        :   'theservice.remove_femur',
                                    'attrs'     :   {'conv-id': sentinel.conv_id, 'service': 'theservice'},
                                    'status_descr' : "Ok",
                                    'status'    :   '0',
                                    'req_bytes' :   len('msg'),
                                    'resp_bytes':   len('response'),
                                    'uS'        :   999000,     # it's in microseconds!
                                    'initiator' :   sentinel.sender,
                                    'target'    :   sentinel.receiver
                                })

    def test__build_sample_uses_last_name_for_op(self):
        e = RPCRequestEndpointUnit()

        heads = {'conv-id': sentinel.conv_id,
                 'ts': '1',
                 'op': 'remove_femur',
                 'sender': sentinel.sender,
                 'receiver': sentinel.receiver}
        resp_heads = {'sender-service': 'service1,service2,service3'}

        samp = e._build_sample(sentinel.name, 200, "Ok", "msg", heads, "response", resp_heads)

        self.assertIn('op', samp)
        self.assertEquals(samp['op'], 'service3.remove_femur')

    @patch.dict('pyon.net.endpoint.CFG', {'container':{'sflow':{'enabled':True}}})
    def test__sample_request(self):
        e = RPCRequestEndpointUnit()

        e._get_sflow_manager = Mock(return_value=Mock(spec=SFlowManager))
        e._get_sflow_manager.return_value.should_sample = True
        e._build_sample = Mock(return_value={'test':sentinel.test})

        e._sample_request(sentinel.status, sentinel.status_descr, sentinel.msg, sentinel.headers, sentinel.response, sentinel.response_headers)

        e._get_sflow_manager.assert_called_once_with()
        e._build_sample.assert_called_once_with(ANY, sentinel.status, sentinel.status_descr, sentinel.msg, sentinel.headers, sentinel.response, sentinel.response_headers)

        e._get_sflow_manager.return_value.transaction.assert_called_once_with(test=sentinel.test)

    @patch.dict('pyon.net.endpoint.CFG', {'container':{'sflow':{'enabled':True}}})
    @patch('pyon.net.endpoint.log')
    def test__sample_request_no_sample(self, mocklog):
        e = RPCRequestEndpointUnit()

        e._get_sflow_manager = Mock(return_value=Mock(spec=SFlowManager))
        e._get_sflow_manager.return_value.should_sample = False
        e._get_sample_name = Mock()

        e._sample_request(sentinel.status, sentinel.status_descr, sentinel.msg, sentinel.headers, sentinel.response, sentinel.response_headers)

        self.assertEquals(mocklog.debug.call_count, 1)
        self.assertIn("not to sample", mocklog.debug.call_args[0][0])

    @patch.dict('pyon.net.endpoint.CFG', {'container':{'sflow':{'enabled':True}}})
    @patch('pyon.net.endpoint.log')
    def test__sample_request_exception(self, mocklog):

        e = RPCRequestEndpointUnit()

        e._get_sflow_manager = Mock(return_value=Mock(spec=SFlowManager))
        e._get_sflow_manager.return_value.should_sample = True
        e._build_sample = Mock(side_effect=TestError)

        e._sample_request(sentinel.status, sentinel.status_descr, sentinel.msg, sentinel.headers, sentinel.response, sentinel.response_headers)

        mocklog.exception.assert_called_once_with("Could not sample, ignoring")

@attr('UNIT')
@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
class TestRPCClient(PyonTestCase, RecvMockMixin):

    @patch('pyon.net.endpoint.IonObject')
    def test_rpc_client(self, iomock):
        node = Mock(spec=NodeB)

        rpcc = RPCClient(node=node, to_name="simply", iface=ISimpleInterface)
        rpcc.node.channel.return_value = self._setup_mock_channel()

        self.assertTrue(hasattr(rpcc, 'simple'))

        ret = rpcc.simple(one="zap", two="zip")

        iomock.assert_called_once_with('SimpleInterface_simple_in', one='zap', two='zip')
        self.assertEquals(ret, "bidirmsg")

    def test_rpc_client_with_unnamed_args(self):
        rpcc = RPCClient(to_name="simply", iface=ISimpleInterface)
        self.assertRaises(AssertionError, rpcc.simple, "zap", "zip")

@attr('UNIT')
@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
class TestRPCResponseEndpoint(PyonTestCase, RecvMockMixin):

    def simple(self, named=None):
        """
        The endpoint will fire its received message into here.
        """
        self._ar.set(named)

    def test_endpoint_receive(self):
        self._ar = event.AsyncResult()

        # build a command object to be returned by the mocked channel
        class FakeMsg(object):
            def __init__(self):
                self.named = ["ein", "zwei"]
        cvalue = FakeMsg()

        e = RPCResponseEndpointUnit(routing_obj=self)
        ch = self._setup_mock_channel(value=cvalue, op="simple")
        e.attach_channel(ch)

        e.spawn_listener()
        args = self._ar.get()

        self.assertEquals(args, ["ein", "zwei"])

    @patch('pyon.net.endpoint.get_ion_ts', Mock(return_value=sentinel.ts))
    def test_receive_bad_op(self):

        class FakeMsg(object):
            def __init__(self):
                self.named = ["ein", "zwei"]
        cvalue = FakeMsg()

        e = RPCResponseEndpointUnit(routing_obj=self)
        ch = self._setup_mock_channel(value=cvalue, op="no_exist")
        e.attach_channel(ch)

        e.spawn_listener()
        e._recv_greenlet.join()

        # test to make sure send got called with our error
        ch.send.assert_called_once_with(None, {'status_code':400,
                                               'error_message':'Unknown op name: no_exist',
                                               'conv-id': '',
                                               'conv-seq': 2,
                                               'protocol':'',
                                               'performative': 'failure',
                                               'language':'ion-r2',
                                               'encoding':'msgpack',
                                               'format':'NoneType',
                                               'receiver': ',',
                                               'ts': sentinel.ts,
                                               'reply-by': 'todo'})

    @patch('pyon.net.endpoint.get_ion_ts', Mock(return_value=sentinel.ts))
    def test_recv_bad_kwarg(self):
        # we try to call simple with the kwarg "not_named" instead of the correct one
        class FakeMsg(object):
            def __init__(self):
                self.not_named = ["ein", "zwei"]
        cvalue = FakeMsg()

        e = RPCResponseEndpointUnit(routing_obj=self)
        ch = self._setup_mock_channel(value=cvalue, op="simple")
        e.attach_channel(ch)

        e.spawn_listener()
        e._recv_greenlet.join()

        # test to make sure send got called with our error
        ch.send.assert_called_once_with(None, {'status_code':500,
                                               'error_message':'simple() got an unexpected keyword argument \'not_named\'',
                                               'conv-id': '',
                                               'conv-seq': 2,
                                               'protocol':'',
                                               'performative': 'failure',
                                               'language':'ion-r2',
                                               'encoding':'msgpack',
                                               'format':'NoneType',
                                               'receiver': ',',
                                               'ts': sentinel.ts,
                                               'reply-by': 'todo'})

    def test__message_received_interceptor_exception(self):
        e = RPCResponseEndpointUnit(routing_obj=self)
        e.send = Mock()
        e.send.return_value = sentinel.sent
        with patch('pyon.net.endpoint.ResponseEndpointUnit._message_received', new=Mock(side_effect=exception.IonException)):
            retval = e._message_received(sentinel.msg, {})

            self.assertEquals(retval, sentinel.sent)
            e.send.assert_called_once_with(None, {'status_code': -1,
                                                  'error_message':'',
                                                  'conv-id': '',
                                                  'conv-seq': 2,
                                                  'protocol':'',
                                                  'performative': 'failure'})

    def error_op(self):
        """
        Routing method for next test, raises an IonException.
        """
        raise exception.Unauthorized(sentinel.unauth)

    def test__message_received_error_in_op(self):
        # we want to make sure IonExceptions raised in business logic get a response, now that
        # _message_received sends the responses

        class FakeMsg(object):
            pass
        cvalue = FakeMsg()

        e = RPCResponseEndpointUnit(routing_obj=self)
        ch = self._setup_mock_channel(value=cvalue, op="error_op")
        e.attach_channel(ch)

        e.send = Mock()

        e.spawn_listener()
        e._recv_greenlet.join()

        e.send.assert_called_once_with(None, {'status_code': 401,
                                              'error_message': str(sentinel.unauth),
                                              'conv-id': '',
                                              'conv-seq': 2,
                                              'protocol':'',
                                              'performative':'failure'})

    def test_message_received_dict(self):
        rout_obj = Mock()
        e = RPCResponseEndpointUnit(routing_obj=rout_obj)

        msg_dict = {'iam':'adict'}
        e.message_received(msg_dict, {'op':'anyop'})

        rout_obj.anyop.assert_called_once_with(iam='adict')

    def test_message_received_unknown_msg_type(self):
        rout_obj = Mock()
        e = RPCResponseEndpointUnit(routing_obj=rout_obj)

        self.assertRaises(exception.BadRequest, e.message_received, 3, {})

@attr('UNIT')
@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
class TestRPCServer(PyonTestCase, RecvMockMixin):

    def test_rpc_server(self):
        node = Mock(spec=NodeB)
        svc = SimpleService()
        rpcs = RPCServer(node=node, from_name="testrpc", service=svc)

        # build a command object to be returned by the mocked channel
        class FakeMsg(object):
            def __init__(self):
                self.named = ["ein", "zwei"]
        cvalue = FakeMsg()

        listen_channel_mock = self._setup_mock_channel(ch_type=ServerChannel)
        rpcs.node.channel.return_value = listen_channel_mock

        # tell our channel to return a mocked handler channel when accepted (listen() implementation detail)
        listen_channel_mock.accept.return_value.__enter__.return_value = self._setup_mock_channel(ch_type=ServerChannel.BidirAcceptChannel, value=cvalue, op="simple")

        rpcs.listen()

        # wait for first message to get passed in
        ret = svc._ar.get()
        self.assertIsInstance(ret, list)
        self.assertEquals(ret, ["ein", "zwei"])

sentinel_interceptors = {'message_incoming': sentinel.msg_incoming,
                         'message_outgoing': sentinel.msg_outgoing,
                         'process_incoming': sentinel.proc_incoming,
                         'process_outgoing': sentinel.proc_outgoing}

@attr('UNIT')
@patch.dict(endpoint.interceptors, sentinel_interceptors, clear=True)
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

    @patch('pyon.net.endpoint.process_interceptors')
    def test__intercept_msg_in(self, mockpi):
        mockpi.return_value = sentinel.inv2
        ep = ProcessEndpointUnitMixin(process=sentinel.proc)

        ep._intercept_msg_in(sentinel.inv)

        # order is important here! msg first, then proc
        mockpi.assert_has_calls([call(sentinel.msg_incoming, sentinel.inv), call(sentinel.proc_incoming, sentinel.inv2)])

    @patch('pyon.net.endpoint.process_interceptors')
    def test__intercept_msg_out(self, mockpi):
        mockpi.return_value = sentinel.inv2
        ep = ProcessEndpointUnitMixin(process=sentinel.proc)

        ep._intercept_msg_out(sentinel.inv)

        # order is important here! proc first, then msg
        mockpi.assert_has_calls([call(sentinel.proc_outgoing, sentinel.inv), call(sentinel.msg_outgoing, sentinel.inv2)])

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

    @patch('pyon.net.endpoint.ProcessEndpointUnitMixin.__init__')
    @patch('pyon.net.endpoint.RPCRequestEndpointUnit.__init__')
    def test_init(self, mockr, mockp):

        ep = ProcessRPCRequestEndpointUnit(process=sentinel.process, other=sentinel.other)
        mockp.assert_called_once_with(ep, process=sentinel.process)
        mockr.assert_called_once_with(ep, other=sentinel.other)

    @patch('pyon.net.endpoint.ProcessEndpointUnitMixin._build_header')
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

    @patch('pyon.net.endpoint.ProcessEndpointUnitMixin.__init__')
    @patch('pyon.net.endpoint.RPCResponseEndpointUnit.__init__')
    def test_init(self, mockr, mockp):

        ep = ProcessRPCResponseEndpointUnit(process=sentinel.process, other=sentinel.other)
        mockp.assert_called_once_with(ep, process=sentinel.process)
        mockr.assert_called_once_with(ep, other=sentinel.other)

    @patch('pyon.net.endpoint.ProcessEndpointUnitMixin._build_header')
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

        ep = ProcessRPCResponseEndpointUnit(process=procmock)
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




if __name__ == "__main__":
    unittest.main()
    
