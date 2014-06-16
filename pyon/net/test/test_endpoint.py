#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'


from nose.plugins.attrib import attr
from mock import Mock, sentinel, patch, ANY, call, MagicMock
from gevent import event, spawn
import unittest
from zope.interface.declarations import implements
from zope.interface.interface import Interface
from gevent import sleep

from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from pyon.core import exception
from pyon.core.bootstrap import get_sys_name, CFG
from pyon.container.cc import Container
from pyon.core.interceptor.interceptor import Invocation
from pyon.net.channel import BaseChannel, SendChannel, BidirClientChannel, SubscriberChannel, ChannelClosedError, ServerChannel, RecvChannel, ListenChannel
from pyon.net.endpoint import EndpointUnit, BaseEndpoint, RPCServer, Subscriber, Publisher, RequestResponseClient, RequestEndpointUnit, RPCRequestEndpointUnit, RPCClient, RPCResponseEndpointUnit, EndpointError, SendingBaseEndpoint, ListeningBaseEndpoint
from pyon.net.messaging import NodeB
from pyon.ion.service import BaseService
from pyon.net.transport import NameTrio, BaseTransport
from pyon.util.sflow import SFlowManager

# NO INTERCEPTORS - we use these mock-like objects up top here which deliver received messages that don't go through the interceptor stack.
no_interceptors = {'message_incoming': [],
                   'message_outgoing': [],
                   'process_incoming': [],
                   'process_outgoing': []}

# simplify send assertions -- can only validate header contents;
# response may have stacks, the simple mock.assert_called_once_with will fail
def assert_called_once_with_header(test, mock, expected):
    test.assertEqual(1, mock.call_count)
    actual = mock.call_args[0][1]
    test.assertEqual(expected, actual)

class TestError(StandardError):
    """
Newly defined error, used for side effects in Mock tests.
"""
    pass

@attr('UNIT')
class TestEndpointUnit(PyonTestCase):

    def setUp(self):
        self._endpoint_unit = EndpointUnit(interceptors={})

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

    def test_build_header(self):
        head = self._endpoint_unit._build_header({'fake': 'content'}, {})
        self.assertTrue(isinstance(head, dict))

    def test_build_payload(self):
        fakemsg = {'fake':'content'}
        msg = self._endpoint_unit._build_payload(fakemsg, {'fake':'header'})
        self.assertEquals(msg, fakemsg)

    def test_build_msg(self):
        fakemsg = {'fake':'content'}
        msg, headers = self._endpoint_unit._build_msg(fakemsg, {})

        self.assertEquals(msg, fakemsg)
        self.assertEquals(headers, {'ts':ANY})

    def test_intercept_in(self):
        self._endpoint_unit._build_invocation = Mock()
        self._endpoint_unit._intercept_msg_in = Mock()

        self._endpoint_unit.intercept_in(sentinel.msg, sentinel.headers)

        self._endpoint_unit._build_invocation.assert_called_once_with(path=Invocation.PATH_IN,
                                                                      message=sentinel.msg,
                                                                      headers=sentinel.headers)
        self.assertTrue(self._endpoint_unit._intercept_msg_in.called)

    def test__message_received(self):
        self._endpoint_unit.message_received  = Mock()
        self._endpoint_unit.message_received.return_value = sentinel.msg_return

        retval = self._endpoint_unit._message_received(sentinel.msg, sentinel.headers)

        self.assertEquals(retval, sentinel.msg_return)

        self.assertTrue(self._endpoint_unit.message_received.called)

@attr('UNIT')
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

    def test_listen_exception_in_handling(self):

        # make a listen loop that will return one message (to blow up in processing)
        chmock = MagicMock(spec=ListenChannel)
        chmock.accept.return_value = Mock()
        chmock.accept.return_value.recv = Mock(return_value=(sentinel.msg, sentinel.headers, sentinel.delivery_tag))
        chmock.accept.return_value._recv_queue.qsize.return_value = 1

        nodemock = Mock(spec=NodeB)
        nodemock.channel.return_value = chmock

        recv_name = NameTrio(sentinel.ex, sentinel.queue)

        ep = ListeningBaseEndpoint(node=nodemock, from_name=recv_name)

        # make msg received error out!
        ep.create_endpoint = Mock(return_value=Mock(spec=EndpointUnit))
        ep.create_endpoint.return_value._message_received.side_effect = TestError
        ep.create_endpoint.return_value.intercept_in.return_value = (sentinel.msg, sentinel.headers)

        self.assertRaises(TestError, ep.listen)
        chmock.setup_listener.assert_called_once_with(recv_name, binding=sentinel.queue)
        chmock.start_consume.assert_called_once_with()

        chmock.accept.assert_called_once_with(n=1, timeout=None)
        chmock.accept.return_value.recv.assert_called_once_with()
        ep.create_endpoint.assert_called_once_with(existing_channel=chmock.accept.return_value)

    def test_get_stats_no_channel(self):
        ep = ListeningBaseEndpoint()
        self.assertRaises(EndpointError, ep.get_stats)

    def test_get_stats(self):
        ep = ListeningBaseEndpoint()
        ep._chan = Mock(spec=ListenChannel)

        ep.get_stats()

        ep._chan.get_stats.assert_called_once_with()

@attr('INT', group='COI')
class TestListeningBaseEndpointInt(IonIntegrationTestCase):
    def setUp(self):
        self.patch_cfg('pyon.ion.exchange.CFG', {'container':{'messaging':{'server':{'primary':'amqp', 'priviledged':None}},
                                                              'datastore':CFG['container']['datastore']},
                                                 'server':CFG['server']})
        self._start_container()

    def test_get_stats(self):
        ep = ListeningBaseEndpoint(node=self.container.node)
        gl = spawn(ep.listen, binding="test_get_stats")

        ep.get_ready_event().wait(timeout=5)

        gs_res = ep.get_stats()
        self.assertEquals(gs_res, (0, 1)) # num of messages, num listeners

        ep.close()
        gl.join(timeout=5)

    def test_get_stats_multiple_on_named_queue(self):
        ep1 = ListeningBaseEndpoint(node=self.container.node, from_name="test_get_stats_multi")
        gl1 = spawn(ep1.listen)

        ep2 = ListeningBaseEndpoint(node=self.container.node, from_name="test_get_stats_multi")
        gl2 = spawn(ep2.listen)

        ep1.get_ready_event().wait(timeout=5)
        ep2.get_ready_event().wait(timeout=5)

        gs_res1 = ep1.get_stats()
        self.assertEquals(gs_res1, (0, 2)) # num of messages, num listeners

        gs_res2 = ep2.get_stats()
        self.assertEquals(gs_res2, (0, 2)) # num of messages, num listeners

        ep1.close()
        ep2.close()
        gl1.join(timeout=5)
        gl2.join(timeout=5)

@attr('INT', group='COI')
class TestListeningBaseEndpointIntWithLocal(TestListeningBaseEndpointInt):
    def setUp(self):
        self.patch_cfg('pyon.ion.exchange.CFG', {'container':{'messaging':{'server':{'primary':'localrouter', 'priviledged':None}},
                                                              'datastore':CFG['container']['datastore']},
                                                 'server':CFG['server']})
        self._start_container()

@attr('UNIT')
class TestPublisher(PyonTestCase):
    def setUp(self):
        self._node = Mock(spec=NodeB)
        self._pub = Publisher(node=self._node, to_name="testpub")
        self._ch = Mock(spec=SendChannel)
        self._node.channel.return_value = self._ch
        self._node.interceptors = {}

    def test_publish(self):
        self.assertEquals(self._node.channel.call_count, 0)

        self._pub.publish("pub")

        self._node.channel.assert_called_once_with(self._pub.channel_type, transport=None)
        self.assertEquals(self._ch.send.call_count, 1)

        self._pub.publish("pub2")
        self._node.channel.assert_called_once_with(self._pub.channel_type, transport=None)
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

@param ch_type Channel type the mock should spec to.
@param status_code The status code of the operation, relevant only for RR comms.
@param error_message The error message of the operation, relevant only for RR comms.
@param op The op name, relevant only for RR comms.
@param value The msg body to be returned.
"""
        ch = MagicMock(spec=ch_type())
        # set a return value for recv so we get an immediate response
        vals = [(value, {'status_code':status_code, 'error_message':error_message, 'op': op, 'conv-id':sentinel.conv_id}, sentinel.delivery_tag)]
        def _ret(*args, **kwargs):
            if len(vals):
                return vals.pop()
            raise ChannelClosedError()

        ch.recv.side_effect = _ret

        # need to set a send_name for now
        ch._send_name = NameTrio('', '')

        return ch

@attr('UNIT')
class TestSubscriber(PyonTestCase, RecvMockMixin):

    def setUp(self):
        self._node = Mock(spec=NodeB)
        self._node.interceptors = {}

    def test_create_endpoint(self):
        def mycb(msg, headers):
            return "test"

        sub = Subscriber(node=self._node, from_name="testsub", callback=mycb)
        e = sub.create_endpoint()

        self.assertEquals(e._callback, mycb)

    def test_subscribe(self):
        #Test Subscriber.
        #The goal of this test is to get messages routed to the callback mock.
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
        cbmock.assert_called_once_with('subbed', {'conv-id': sentinel.conv_id, 'status_code':200, 'error_message':'', 'op': None})

@attr('UNIT')
@patch('pyon.net.endpoint.BidirectionalEndpointUnit._send', Mock(return_value=(sentinel.body, {'conv-id':sentinel.conv_id})))
class TestRequestResponse(PyonTestCase, RecvMockMixin):
    def setUp(self):
        self._node = Mock(spec=NodeB)

    def test_endpoint_send(self):
        e = RequestEndpointUnit(interceptors={})
        ch = self._setup_mock_channel()
        e.attach_channel(ch)

        retval, heads = e.send("msg")
        self.assertEquals(retval, "bidirmsg")

        # cleanup
        e.close()

    def test_endpoint_send_with_timeout(self):
        e = RequestEndpointUnit()
        e.channel = Mock()
        e.channel.recv = lambda: sleep(5)   # simulate blocking when recv is called

        self.assertRaises(exception.Timeout, e._send, sentinel.msg, MagicMock(), timeout=1)

    def test_rr_client(self):
        rr = RequestResponseClient(node=self._node, to_name="rr")
        rr.node.channel.return_value = self._setup_mock_channel()
        rr.node.interceptors = {}

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
class TestRPCRequestEndpoint(PyonTestCase, RecvMockMixin):

    def test_build_msg(self):
        e = RPCRequestEndpointUnit()
        fakemsg = {'fake':'content'}
        msg = e._build_msg(fakemsg, {})

        # er in json now, how to really check
        self.assertNotEquals(str(msg), str(fakemsg))

    @patch('pyon.net.endpoint.RPCRequestEndpointUnit._build_conv_id', Mock(return_value=sentinel.conv_id))
    def test_endpoint_send(self):
        e = RPCRequestEndpointUnit(interceptors={})
        ch = self._setup_mock_channel()
        e.attach_channel(ch)

        ret, heads = e.send("rpc call")
        self.assertEquals(ret, 'bidirmsg') # we just get payload back due to success RPC code 200

        e.close()

    @patch('pyon.net.endpoint.RPCRequestEndpointUnit._build_conv_id', Mock(return_value=sentinel.conv_id))
    def test_endpoint_send_errors(self):
        errlist = [exception.BadRequest, exception.Unauthorized, exception.NotFound, exception.Timeout, exception.Conflict, exception.ServerError, exception.ServiceUnavailable]

        for err in errlist:
            e = RPCRequestEndpointUnit(interceptors={})
            ch = self._setup_mock_channel(status_code=err.status_code, error_message=str(err.status_code))
            e.attach_channel(ch)
            self.assertRaises(err, e.send, {})

@attr('UNIT')
class TestRPCClient(PyonTestCase, RecvMockMixin):

    @patch('pyon.net.endpoint.IonObject')
    @patch('pyon.net.endpoint.RPCRequestEndpointUnit._build_conv_id', Mock(return_value=sentinel.conv_id))
    def test_rpc_client(self, iomock):
        node = Mock(spec=NodeB)

        rpcc = RPCClient(node=node, to_name="simply", iface=ISimpleInterface)
        rpcc.node.channel.return_value = self._setup_mock_channel()
        rpcc.node.interceptors = {}

        self.assertTrue(hasattr(rpcc, 'simple'))

        ret = rpcc.simple(one="zap", two="zip")

        iomock.assert_called_once_with('SimpleInterface_simple_in', one='zap', two='zip')
        self.assertEquals(ret, "bidirmsg")

    def test_rpc_client_with_unnamed_args(self):
        rpcc = RPCClient(to_name="simply", iface=ISimpleInterface)
        self.assertRaises(AssertionError, rpcc.simple, "zap", "zip")

@attr('UNIT')
class TestRPCResponseEndpoint(PyonTestCase, RecvMockMixin):

    def simple(self, named=None):
        """
        The endpoint will fire its received message into here.
        """
        self._ar.set(named)

    def _do_listen(self, e):
        while True:
            try:
                msg, headers, _ = e.channel.recv()

                nm, nh = e.intercept_in(msg, headers)
                e._message_received(nm, nh)

            except ChannelClosedError:
                break

    def test_endpoint_receive(self):
        self._ar = event.AsyncResult()

        # build a command object to be returned by the mocked channel
        class FakeMsg(object):
            def __init__(self):
                self.named = ["ein", "zwei"]
        cvalue = FakeMsg()

        e = RPCResponseEndpointUnit(routing_obj=self, interceptors={})
        ch = self._setup_mock_channel(value=cvalue, op="simple")
        e.attach_channel(ch)

        self._do_listen(e)
        args = self._ar.get(timeout=10)

        self.assertEquals(args, ["ein", "zwei"])

    @patch('pyon.net.endpoint.get_ion_ts', Mock(return_value=sentinel.ts))
    def test_receive_bad_op(self):

        class FakeMsg(object):
            def __init__(self):
                self.named = ["ein", "zwei"]
        cvalue = FakeMsg()

        e = RPCResponseEndpointUnit(routing_obj=self, interceptors={})
        ch = self._setup_mock_channel(value=cvalue, op="no_exist")
        e.attach_channel(ch)

        self._do_listen(e)

        assert_called_once_with_header(self, ch.send, {'status_code':400,
                                                       'error_message':'Unknown op name: no_exist',
                                                       'conv-id': sentinel.conv_id,
                                                       'conv-seq': 2,
                                                       'protocol':'',
                                                       'performative': 'failure',
                                                       'language':'ion-r2',
                                                       'encoding':'msgpack',
                                                       'format':'list',
                                                       'receiver': ',',
                                                       'ts': sentinel.ts})

    @patch('pyon.net.endpoint.get_ion_ts', Mock(return_value=sentinel.ts))
    def test_recv_bad_kwarg(self):
        # we try to call simple with the kwarg "not_named" instead of the correct one
        class FakeMsg(object):
            def __init__(self):
                self.not_named = ["ein", "zwei"]
        cvalue = FakeMsg()

        e = RPCResponseEndpointUnit(routing_obj=self, interceptors={})
        ch = self._setup_mock_channel(value=cvalue, op="simple")
        e.attach_channel(ch)

        self._do_listen(e)

        # test to make sure send got called with our error
        assert_called_once_with_header(self, ch.send, {'status_code':400,
                                                       'error_message':'Argument not_named not present in op signature',
                                                       'conv-id': sentinel.conv_id,
                                                       'conv-seq': 2,
                                                       'protocol':'',
                                                       'performative': 'failure',
                                                       'language':'ion-r2',
                                                       'encoding':'msgpack',
                                                       'format':'NoneType',
                                                       'receiver': ',',
                                                       'msg-rcvd':ANY,
                                                       'ts': sentinel.ts})

    def test__message_received_interceptor_exception(self):
        e = RPCResponseEndpointUnit(routing_obj=self)
        e.send = Mock()
        e.send.return_value = sentinel.sent
        e.channel = Mock()
        with patch('pyon.net.endpoint.ResponseEndpointUnit._message_received', new=Mock(side_effect=exception.IonException)):
            retval = e._message_received(sentinel.msg, {})

            self.assertEquals(retval, sentinel.sent)
            assert_called_once_with_header(self, e.send, {'status_code': -1,
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

        e = RPCResponseEndpointUnit(routing_obj=self, interceptors={})
        ch = self._setup_mock_channel(value=cvalue, op="error_op")
        e.attach_channel(ch)

        e.send = Mock()

        self._do_listen(e)

        assert_called_once_with_header(self, e.send, {'status_code': 401,
                                                      'error_message': str(sentinel.unauth),
                                                      'conv-id': sentinel.conv_id,
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

    @patch('pyon.net.endpoint.ResponseEndpointUnit._send', Mock(side_effect=exception.Timeout))
    @unittest.skip('timeouts no longer captured by sFlow')
    def test_timeout_makes_sflow_sample(self):
        e = RPCResponseEndpointUnit(interceptors={})
        e._sample_request = Mock()

        self.assertRaises(exception.Timeout, e._send, sentinel.msg, sentinel.headers, timeout=1)
        e._sample_request.assert_called_once_with(-1, 'Timeout', sentinel.msg, sentinel.headers, '', {})

    def test__get_sample_name(self):
        e = RPCResponseEndpointUnit(interceptors={})
        self.assertEquals(e._get_sample_name(), "unknown-rpc-server")

    def test__get_sflow_manager(self):
        Container.instance = None
        e = RPCResponseEndpointUnit(interceptors={})
        self.assertIsNone(e._get_sflow_manager())

    def test__get_sflow_manager_with_container(self):
        Container.instance = None
        c = Container() # ensure an instance
        e = RPCResponseEndpointUnit(interceptors={})
        self.assertEquals(e._get_sflow_manager(), c.sflow_manager)

        Container.instance = None

    @patch('pyon.net.endpoint.time.time', Mock(return_value=1))
    def test__build_sample(self):
        e = RPCResponseEndpointUnit(interceptors={})

        heads = {'conv-id': sentinel.conv_id,
                 'ts': '1',
                 'op': 'remove_femur',
                 'sender': 'sender',
                 'receiver': 'getter'}
        resp_heads = {'sender-service': 'theservice'}

        samp = e._build_sample(sentinel.name, 200, "Ok", "msg", heads, "response", resp_heads, sentinel.qlen)

        self.assertEquals(samp, {
            'app_name' : get_sys_name(),
            'op' : 'remove_femur',
            'attrs' : {'ql':sentinel.qlen, 'pid':sentinel.name},
            'status_descr' : "Ok",
            'status' : '0',
            'req_bytes' : len('msg'),
            'resp_bytes': len('response'),
            'uS' : 999000, # it's in microseconds!
            'initiator' : 'sender',
            'target' : 'theservice'
        })

    @patch.dict('pyon.net.endpoint.CFG', {'container':{'sflow':{'enabled':True}}})
    def test__sample_request(self):
        e = RPCResponseEndpointUnit(interceptors={})

        e._get_sflow_manager = Mock(return_value=Mock(spec=SFlowManager))
        e._get_sflow_manager.return_value.should_sample = True
        e._build_sample = Mock(return_value={'test':sentinel.test})
        e.channel = Mock()
        e.channel.get_stats = Mock(return_value=(3, 0))
        e.channel._recv_queue.qsize = Mock(return_value=3)

        e._sample_request(sentinel.status, sentinel.status_descr, sentinel.msg, sentinel.headers, sentinel.response, sentinel.response_headers)

        e._get_sflow_manager.assert_called_once_with()
        e._build_sample.assert_called_once_with(ANY, sentinel.status, sentinel.status_descr, sentinel.msg, sentinel.headers, sentinel.response, sentinel.response_headers, 6)

        e._get_sflow_manager.return_value.transaction.assert_called_once_with(test=sentinel.test)

    @patch.dict('pyon.net.endpoint.CFG', {'container':{'sflow':{'enabled':True}}})
    @patch('pyon.net.endpoint.log')
    def test__sample_request_no_sample(self, mocklog):
        e = RPCResponseEndpointUnit(interceptors={})

        e._get_sflow_manager = Mock(return_value=Mock(spec=SFlowManager))
        e._get_sflow_manager.return_value.should_sample = False
        e._get_sample_name = Mock()

        e._sample_request(sentinel.status, sentinel.status_descr, sentinel.msg, sentinel.headers, sentinel.response, sentinel.response_headers)

        self.assertEquals(mocklog.debug.call_count, 1)
        self.assertIn("not to sample", mocklog.debug.call_args[0][0])

    @patch.dict('pyon.net.endpoint.CFG', {'container':{'sflow':{'enabled':True}}})
    @patch('pyon.net.endpoint.log')
    def test__sample_request_exception(self, mocklog):

        e = RPCResponseEndpointUnit(interceptors={})

        e._get_sflow_manager = Mock(return_value=Mock(spec=SFlowManager))
        e._get_sflow_manager.return_value.should_sample = True
        e._build_sample = Mock(side_effect=TestError)

        e._sample_request(sentinel.status, sentinel.status_descr, sentinel.msg, sentinel.headers, sentinel.response, sentinel.response_headers)

        mocklog.exception.assert_called_once_with("Could not sample, ignoring")

@attr('UNIT')
class TestRPCServer(PyonTestCase, RecvMockMixin):

    def test_rpc_server(self):
        node = Mock(spec=NodeB)
        svc = SimpleService()
        rpcs = RPCServer(node=node, from_name="testrpc", service=svc)
        node.interceptors = {}

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
