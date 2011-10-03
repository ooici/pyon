#!/usr/bin/env python
from zope.interface import interface
from zope.interface.declarations import implements
from zope.interface.interface import Interface
from pyon.core import exception
from pyon.net.channel import PubSub
from pyon.net.entity import Entity, EntityFactory, BinderListener, RPCServer, Subscriber, Publisher, RequestResponseClient, RequestEntity, RPCRequestEntity, IonEncoder, RPCClient, _Command, RPCResponseEntity
from gevent import event, GreenletExit
from pyon.service.service import BaseService
from pyon.util.async import wait, spawn

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

import unittest

class FakeChannel(object):
    """
    A Channel-like object used for testing.
    """
    def __init__(self):
        self._name = None
        self._sendcount = 0
        self._closecount = 0
        self._sentone = False
    def send(self, _):
        self._sendcount += 1
    def close(self):
        self._closecount += 1
    def connect(self, name):
        self._name = name
    def recv(self):
        if not self._sentone:
            self._sentone = True
            return "a msg"
        else:
            res = event.AsyncResult()
            res.get()

    def bind(self, *args):
        pass
    def listen(self):
        pass
    def accept(self):
        return self

class FakeRPCChannel(FakeChannel):
    """
    Channel-like object used for testing RPC.

    When recv is called for the first time, responds with a dict of headers/payload,
    with the statuscode and error message set to what was initialized in the constructor.
    """
    def __init__(self, code=None, msg=None, **kwargs):
        self._code = code or 200
        self._msg = msg or "OK"
        FakeChannel.__init__(self)

    def recv(self):
        if not self._sentone:
            self._sentone = True
            return IonEncoder().encode({ 'header' : { 'status_code': self._code,
                                                      'error_message': self._msg },
                                         'payload' : 'some payload' })
        else:
            res = event.AsyncResult()
            res.get()

class FakeNode(object):
    """
    A Node-like object used for testing.
    """
    def __init__(self, chan_type=None, **kwargs):
        self._chan_type = chan_type or FakeChannel
        self._chan_kwargs = kwargs
        self._chan = None
    def channel(self, _):
        self._chan = self._chan_type(**self._chan_kwargs)
        return self._chan

class TestEntity(unittest.TestCase):


    def setUp(self):
        self._entity = Entity()

    def test_attach_channel(self):
        ch = FakeChannel()
        self._entity.attach_channel(ch)

        self.assertTrue(self._entity.channel is not None)

    def test_send(self):

        # need a channel to send on
        self.assertRaises(AttributeError, self._entity.send, "fake")

        ch = FakeChannel()
        self._entity.attach_channel(ch)

        self._entity.send("hi")
        self.assertEquals(ch._sendcount, 1)

    def test_close(self):
        ch = FakeChannel()
        self._entity.attach_channel(ch)
        self._entity.close()
        self.assertEquals(ch._closecount, 1)

    def test_spawn_listener(self):
        ch = FakeChannel()
        self._entity.attach_channel(ch)

        self._entity.spawn_listener()

        self._entity.close()
        self.assertTrue(self._entity._recv_greenlet.ready())

class TestEntityFactory(unittest.TestCase):
    def setUp(self):
        self._node = FakeNode()
        self._ef = EntityFactory(node=self._node, name="EFTest")

    def test_create_entity(self):
        e = self._ef.create_entity()

        # check attrs
        self.assertTrue(hasattr(e, 'channel'))
        self.assertTrue(self._ef.name in e.channel._name)

        # make sure we can shut it down
        e.close()

    def test_create_entity_new_name(self):
        e = self._ef.create_entity(to_name="reroute")
        self.assertTrue("reroute" in e.channel._name)
        e.close()

    def test_create_entity_existing_channel(self):
        ch = FakeChannel()
        e = self._ef.create_entity(existing_channel=ch)
        self.assertEquals(e.channel, ch)
        self.assertTrue(e.channel._name is None)

        ch.connect("exist")
        self.assertEquals(e.channel._name, 'exist')
        
        e.close()

    def test_create_entity_kwarg(self):
        """
        Make sure our kwarg gets set.
        """

        class OptEntity(Entity):
            def __init__(self, opt=None, **kwargs):
                self._opt = opt
                Entity.__init__(self, **kwargs)

        self._ef.entity_type = OptEntity

        e = self._ef.create_entity(opt="stringer")
        self.assertTrue(hasattr(e, "_opt"))
        self.assertEquals(e._opt, "stringer")

class TestBinderListener(unittest.TestCase):
    def setUp(self):
        self._node = FakeNode()

    def test_create(self):
        bl1 = BinderListener(self._node, "namey", None, None, None)
        bl2 = BinderListener(self._node, "namey2", Subscriber(node=self._node, callback=lambda: True, name="namey2"), PubSub, None)

    def test_create_with_spawn_and_listen(self):
        """
        Tests both listen() and a custom spawn function being passed.
        """
        def myspawn(cb, *args):
            raise GreenletExit("spawner")

        bl1 = BinderListener(self._node, "namey", None, FakeChannel, myspawn)

        # spawn in greenlet, let myspawn get hit, make sure it got hit
        listen_g = spawn(bl1.listen)
        wait(listen_g)

        self.assertEquals(str(listen_g.value), "spawner")

class TestPublisher(unittest.TestCase):
    def setUp(self):
        self._node = FakeNode()
        self._pub = Publisher(node=self._node, name="testpub")

    def test_publish(self):
        self.assertTrue(self._node._chan is None)

        self._pub.publish("pub")

        self.assertTrue(self._node._chan is not None)
        self.assertEquals(self._node._chan._sendcount, 1)

        self._pub.publish("pub2")
        self.assertEquals(self._node._chan._sendcount, 2)

class TestSubscriber(unittest.TestCase):
    def setUp(self):
        self._node = FakeNode()

    def test_create_sub_without_callback(self):
        self.assertRaises(AssertionError, Subscriber, node=self._node, name="testsub")

    def test_create_entity(self):
        def mycb(msg):
            return "test"

        sub = Subscriber(node=self._node, name="testsub", callback=mycb)
        e = sub.create_entity()

        self.assertEquals(e._callback, mycb)

    def test_subscribe(self):
        def mycb(msg):
            raise GreenletExit(msg)

        sub = Subscriber(node=self._node, name="testsub", callback=mycb)
        bl = BinderListener(node=self._node, name="testsub", entity_factory=sub, listening_channel_type=FakeChannel, spawn_callable=None)

        listen_g = spawn(bl.listen)
        wait(listen_g)

        # from FakeChannel
        self.assertEquals(str(listen_g.value), "a msg")

class TestRequestResponse(unittest.TestCase):
    def setUp(self):
        self._node = FakeNode()

    def test_entity_send(self):
        e = RequestEntity()
        ch = FakeChannel()
        e.attach_channel(ch)

        retval = e.send("msg")
        self.assertEquals(retval, "a msg")

        # cleanup
        e.close()

    def test_rr_client(self):
        """
        """
        rr = RequestResponseClient(node=self._node, name="rr")
        rr.channel_type = FakeChannel

        ret = rr.request("request")
        self.assertEquals(ret, "a msg")

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
    def simple(self, *args):
        self._ar.set(args)
        return True

class FakeRPCServerChannel(FakeChannel):
    def recv(self):
        if not self._sentone:
            self._sentone = True
            info = ISimpleInterface.namesAndDescriptions()[0]
            print "\n\nINFO:", info, "class", info.__class__
            cmd = _Command(None, info[0], info[1].getSignatureInfo(), "")
            pl = cmd._command_dict_from_call('ein', 'zwei')
            print "\n\n\nMY PAYLOAD IS", str(pl), "\n\n\n"
            return IonEncoder().encode({'header':{}, 'payload':pl})
        else:
            res = event.AsyncResult()
            res.get()

class TestRPCRequestEntity(unittest.TestCase):

    def test_entity_send(self):
        e = RPCRequestEntity()
        ch = FakeRPCChannel()
        e.attach_channel(ch)

        ret = e.send("rpc call")
        self.assertEquals(ret, 'some payload')      # we just get payload back due to success RPC code 200

        e.close()

    def test_entity_send_errors(self):
        errlist = [exception.BadRequest, exception.Unauthorized, exception.NotFound, exception.Timeout, exception.Conflict, exception.ServerError, exception.ServiceUnavailable]

        for err in errlist:
            e = RPCRequestEntity()
            ch = FakeRPCChannel(err.status_code, str(err.status_code))
            e.attach_channel(ch)

            self.assertRaises(err, e.send, 'payload')

class TestRPCClient(unittest.TestCase):

    def test_rpc_client(self):
        node = FakeNode(chan_type=FakeRPCChannel, code=200, msg="OK")
        rpcc = RPCClient(node=node, name="simply", iface=ISimpleInterface)

        self.assertTrue(hasattr(rpcc, 'simple'))

        ret = rpcc.simple("zap", "zip")
        self.assertEquals(ret, "some payload")

class TestRPCResponseEntity(unittest.TestCase):

    def simple(self, *args):
        """
        The entity will fire its received message into here.
        """
        self._ar.set(args)

    def test_entity_receive(self):
        self._ar = event.AsyncResult()

        e = RPCResponseEntity(routing_obj=self)
        ch = FakeRPCServerChannel()
        e.attach_channel(ch)

        e.spawn_listener()
        args = self._ar.get()

        self.assertEquals(args, ("ein", "zwei"))

class TestRPCServer(unittest.TestCase):

    def test_rpc_server(self):
        node = FakeNode(chan_type=FakeRPCServerChannel)
        svc = SimpleService()
        rpcs = RPCServer(node=node, name="testrpc", service=svc)

        # uses the chan_type specified in FakeNode constructor for the listener
        bl = BinderListener(node=node, name="testrpc", entity_factory=rpcs, listening_channel_type=None, spawn_callable=None)
        listen_g = spawn(bl.listen)

        # wait for first message to get passed in
        ret = svc._ar.get()
        self.assertTrue(isinstance(ret, tuple))
        self.assertEquals(ret, ("ein", "zwei"))

if __name__ == "__main__":
    unittest.main()
    
