#!/usr/bin/env python
from pyon.core.interceptor.interceptor import Invocation
from pyon.net.transport import NameTrio

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

import unittest
from zope.interface.declarations import implements
from zope.interface.interface import Interface
from pyon.core import exception
from pyon.net import endpoint
from pyon.net.channel import BaseChannel, SendChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel
from pyon.net.endpoint import EndpointUnit, BaseEndpoint, RPCServer, Subscriber, Publisher, RequestResponseClient, RequestEndpointUnit, RPCRequestEndpointUnit, RPCClient, RPCResponseEndpointUnit, EndpointError, SendingBaseEndpoint
from gevent import event, sleep
from pyon.net.messaging import NodeB
from pyon.service.service import BaseService
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
from mock import Mock, sentinel, patch

# NO INTERCEPTORS - we use these mock-like objects up top here which deliver received messages that don't go through the interceptor stack.
no_interceptors = {'message-in': [],
                   'message-out': [],
                   'process-in': [],
                   'process-out': []}

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

    def test_send(self):

        # need a channel to send on
        self.assertRaises(AttributeError, self._endpoint_unit.send, "fake")

        ch = Mock(spec=SendChannel)
        self._endpoint_unit.attach_channel(ch)

        self._endpoint_unit.send("hi", {'header':'value'})
        ch.send.assert_called_once_with('hi', {'header':'value'})

    def test_close(self):
        ch = Mock(spec=BaseChannel)
        self._endpoint_unit.attach_channel(ch)
        self._endpoint_unit.close()
        ch.close.assert_called_once_with()

    def test_spawn_listener(self):
        ch = Mock(spec=BidirClientChannel)
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

@patch.dict(endpoint.interceptors, no_interceptors, clear=True)
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
        ch = Mock(spec=ch_type())
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
        listen_channel_mock.accept.return_value = listen_channel_mock

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

    def test_rr_client(self):
        """
        """
        rr = RequestResponseClient(node=self._node, to_name="rr")
        rr.node.channel.return_value = self._setup_mock_channel()

        ret = rr.request("request")
        self.assertEquals(ret, "bidirmsg")

    def test_rr_server(self):
        """
        Err, not defined at the moment.
        """
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
                                               'reply-by': 'todo'})

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
        listen_channel_mock.accept.return_value = self._setup_mock_channel(ch_type=ServerChannel.BidirAcceptChannel, value=cvalue, op="simple")

        rpcs.listen()

        # wait for first message to get passed in
        ret = svc._ar.get()
        self.assertIsInstance(ret, list)
        self.assertEquals(ret, ["ein", "zwei"])

if __name__ == "__main__":
    unittest.main()
    
