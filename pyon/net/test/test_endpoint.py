#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

import unittest
from zope.interface.declarations import implements
from zope.interface.interface import Interface
from pyon.core import exception
from pyon.net import endpoint
from pyon.net.channel import BaseChannel, SendChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel
from pyon.net.endpoint import EndpointUnit, BaseEndpoint, RPCServer, Subscriber, Publisher, RequestResponseClient, RequestEndpointUnit, RPCRequestEndpointUnit, RPCClient, RPCResponseEndpointUnit
from gevent import event, sleep
from pyon.net.messaging import NodeB
from pyon.service.service import BaseService
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
from mock import Mock, sentinel, patch

# NO INTERCEPTORS - we use these mock-like objects up top here which deliver received messages that don't go through the interceptor stack.
endpoint.interceptors = {'message-in': [],
                         'message-out': [],
                         'process-in': [],
                         'process-out': []}

@attr('UNIT')
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

@attr('UNIT')
class TestBaseEndpoint(PyonTestCase):
    def setUp(self):
        self._node = Mock(spec=NodeB)
        self._ef = BaseEndpoint(node=self._node, name="EFTest")
        self._ch = Mock(spec=SendChannel)
        chtype = Mock()
        chtype.return_value = self._ch
        self._ef.channel_type = chtype

    def test_create_endpoint(self):
        e = self._ef.create_endpoint()

        # check attrs
        self.assertTrue(hasattr(e, 'channel'))
        self.assertEquals(self._ch.connect.call_count, 1)
        self.assertTrue(self._ef.name in self._ch.connect.call_args[0])

        # make sure we can shut it down
        e.close()
        self._ch.close.assert_any_call()

    def test_create_endpoint_new_name(self):
        e = self._ef.create_endpoint(to_name="reroute")
        self.assertEquals(self._ch.connect.call_count, 1)
        self.assertTrue("reroute" in self._ch.connect.call_args[0][0])        # @TODO: this is obtuse
        e.close()

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

class TestPublisher(PyonTestCase):
    def setUp(self):
        self._node = Mock(spec=NodeB)
        self._pub = Publisher(node=self._node, name="testpub")
        self._ch = Mock(spec=SendChannel)
        chtype = Mock()
        chtype.return_value = self._ch
        self._pub.channel_type = chtype

    def test_publish(self):
        self.assertEquals(self._node.channel.call_count, 0)

        self._pub.publish("pub")

        self._node.channel.assert_called_once_with(self._ch)
        self.assertEquals(self._ch.send.call_count, 1)

        self._pub.publish("pub2")
        self._node.channel.assert_called_once_with(self._ch)
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
        ch._send_name = ('', '')

        return ch

@attr('UNIT')
class TestSubscriber(PyonTestCase, RecvMockMixin):

    def setUp(self):
        self._node = Mock(spec=NodeB)

    def test_create_sub_without_callback(self):
        self.assertRaises(AssertionError, Subscriber, node=self._node, name="testsub")

    def test_create_endpoint(self):
        def mycb(msg, headers):
            return "test"

        sub = Subscriber(node=self._node, name="testsub", callback=mycb)
        e = sub.create_endpoint()

        self.assertEquals(e._callback, mycb)

    def test_subscribe(self):
        """
        Test Subscriber.
        The goal of this test is to get messages routed to the callback mock.
        """
        cbmock = Mock()
        sub = Subscriber(node=self._node, name="testsub", callback=cbmock)

        # tell the subscriber to create this as the main listening channel
        listen_channel_mock = self._setup_mock_channel(ch_type=SubscriberChannel, value="subbed", error_message="")
        sub._create_main_channel = lambda: listen_channel_mock

        # tell our channel to return itself when accepted
        listen_channel_mock.accept.return_value = listen_channel_mock

        # we're ready! call listen
        sub.listen()

        # make sure we got our message
        cbmock.assert_called_once_with('subbed', {'status_code':200, 'error_message':'', 'op': None})

@attr('UNIT')
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
        rr = RequestResponseClient(node=self._node, name="rr")
        chtype = Mock()
        chtype.return_value = self._setup_mock_channel()
        rr.channel_type = chtype

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
class TestRPCClient(PyonTestCase, RecvMockMixin):

    @patch('pyon.net.endpoint.IonObject')
    def test_rpc_client(self, iomock):
        node = Mock(spec=NodeB)

        rpcc = RPCClient(node=node, name="simply", iface=ISimpleInterface)
        chtype = Mock()
        chtype.return_value = self._setup_mock_channel()
        rpcc.channel_type = chtype

        self.assertTrue(hasattr(rpcc, 'simple'))

        ret = rpcc.simple("zap", "zip")

        iomock.assert_called_once_with('SimpleInterface_simple_in', one='zap', two='zip')
        self.assertEquals(ret, "bidirmsg")

@attr('UNIT')
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
        ch.send.assert_called_once_with(None, {'status_code':400, 'error_message':'Unknown op name: no_exist'})

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
        ch.send.assert_called_once_with(None, {'status_code':500, 'error_message':'simple() got an unexpected keyword argument \'not_named\''})


@attr('UNIT')
class TestRPCServer(PyonTestCase, RecvMockMixin):

    def test_rpc_server(self):
        node = Mock(spec=NodeB)
        svc = SimpleService()
        rpcs = RPCServer(node=node, name="testrpc", service=svc)

        # build a command object to be returned by the mocked channel
        class FakeMsg(object):
            def __init__(self):
                self.named = ["ein", "zwei"]
        cvalue = FakeMsg()

        listen_channel_mock = self._setup_mock_channel(ch_type=ServerChannel)
        rpcs._create_main_channel = lambda: listen_channel_mock

        # tell our channel to return a mocked handler channel when accepted (listen() implementation detail)
        listen_channel_mock.accept.return_value = self._setup_mock_channel(ch_type=ServerChannel.BidirAcceptChannel, value=cvalue, op="simple")

        rpcs.listen()

        # wait for first message to get passed in
        ret = svc._ar.get()
        self.assertIsInstance(ret, list)
        self.assertEquals(ret, ["ein", "zwei"])

if __name__ == "__main__":
    unittest.main()
    
