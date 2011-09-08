"""
Tentatively named prototype


"""
import anode

import gevent
from gevent import event

from pika.credentials import PlainCredentials
from pika.connection import ConnectionParameters
from pika.adapters import SelectConnection
from pika import BasicProperties

from anode.net import channel
from anode.net import amqp

from anode.core.bootstrap import CFG

class IDPool(object):
    """
    Create a pool of IDs to allow reuse. The "new_id" function generates the next
    valid ID from the previous one. If not given, defaults to incrementing an integer.
    """

    def __init__(self, new_id=None):
        if new_id is None: new_id = lambda x: x + 1

        self.ids_in_use = set()
        self.ids_free = set()
        self.new_id = new_id
        self.last_id = 0

    def get_id(self):
        if len(self.ids_free) > 0:
            return self.ids_free.pop()

        self.last_id = id_ = self.new_id(self.last_id)
        self.ids_in_use.add(id_)
        return id_

    def release_id(self, the_id):
        if the_id in self.ids_in_use:
            self.ids_in_use.remove(the_id)
            self.ids_free.add(the_id)

class NodeB(amqp.Node):
    """
    prototype blocking interface to messaging primitives 

    wrap around Node and create blocking interface for getting channel
    objects
    """

    def __init__(self):
        self.ready = event.Event()

    def start_node(self):
        """
        This should only be called by on_connection_opened..
        so, maybe we don't need a start_node/stop_node interface
        """
        amqp.Node.start_node(self)
        self.running = 1
        print 'start_node'
        self.ready.set()
        print 'ready set'

    def channel(self, ch_type):
        if not self.running:
            print 'not running'
            raise #?
        result = event.AsyncResult()
        def on_channel_open_ok(amq_chan):
            ch = channel.SocketInterface.Socket(amq_chan, ch_type)
            result.set(ch)
        self.client.channel(on_channel_open_ok)
        ch = result.get()
        #ch = channel.SocketInterface(client)
        return ch

def ioloop(connection):
    # Loop until CTRL-C
    try:
        # Start our blocking loop
        connection.ioloop.start()

    except KeyboardInterrupt:

        # Close the connection
        connection.close()

        # Loop until the connection is closed
        connection.ioloop.start()

def makeNode():
    """
    blocking construction and connection of node
    """
    node = NodeB()
    messagingParams = CFG.server.amqp
    print "XXXXX messagingParams: " + str(messagingParams)
    credentials = PlainCredentials(messagingParams["username"], messagingParams["password"])
    conn_parameters = ConnectionParameters(host=messagingParams["host"], virtual_host=messagingParams["vhost"], port=messagingParams["port"], credentials=credentials)
    connection = SelectConnection(conn_parameters , node.on_connection_open)
    ioloop_process = gevent.spawn(ioloop, connection)
    #ioloop_process = gevent.spawn(connection.ioloop.start)
    print 'waiting for node'
    node.ready.wait()
    print 'node ready'
    return node, ioloop_process
    #return node, ioloop, connection

def testb():
    node, ioloop_process = makeNode()
    ch = node.channel(channel.BaseChannel)
    print ch
    ch.bind(('amq.direct', 'foo'))
    print 'bound'
    ch.listen(1)
    print 'listening'
    msg = ch.recv()
    print 'message: ', msg
    ioloop_process.join()

def testbclient():
    node, ioloop_process = makeNode()
    ch = node.channel(channel.BidirectionalClient)
    print ch
    ch.connect(('amq.direct', 'foo'))
    print 'sending'
    ch.send('hey, whats up?')
    print 'sent'
    print 'receiving'
    msg = ch.recv()
    print 'message: ', msg

def test_accept():
    node, ioloop_process = makeNode()
    ch = node.channel(channel.Bidirectional)
    print ch
    ch.bind(('amq.direct', 'foo'))
    print 'bound'
    ch.listen(1)
    ch_serv = ch.accept() # do we need the name of the connected peer?
    print 'accepted'
    msg = ch_serv.recv()
    print 'message: ', msg
    ch_serv.send('not much, dude')

    ioloop_process.join()

class NodeNB(amqp.Node):
    """
    Main messaging interface that goes active when amqp client connects.
    Integrates messaging and processing

    The life cycle of this depends on the underlying amqp connection.

    This thing (or a subordinate but coupled/controlled object) mediates
    Messaging Channels that are used to send messages or that dispatch
    received messages to receiver/consumer protocol things.
    """

    def __init__(self):
        self.channels = {}
        self.id_pool = IDPool()

    def start_node(self):
        """
        This should only be called by on_connection_opened..
        so, maybe we don't need a start_node/stop_node interface
        """
        amqp.Node.start_node(self)
        for ch_id in self.channels:
            self.start_channel(ch_id)

    def stop_node(self):
        """
        """

    def channel(self, ch_type):
        """
        ch_type is one of PointToPoint, etc.
        return Channel instance that will be activated with amqp_channel
        and configured

        name (exchange, key)
        name shouldn't need to be specified here, but it is for now
        """
        ch = ch_type()
        ch_id = self.id_pool.get_id()
        self.channels[ch_id] = ch
        if self.running:
            self.start_channel(ch_id)
        return ch

    def start_channel(self, ch_id):
        ch = self.channels[ch_id]
        self.client.channel(ch.on_channel_open)

    def spawnServer(self, f):
        """
        """

class TestServer(channel.BaseChannel):

    def do_config(self):
        self._chan_name = ('amq.direct', 'foo')
        self.queue = 'foo'
        self.do_queue()

class TestClient(channel.BaseChannel):

    def do_config(self):
        self._peer_name = ('amq.direct', 'foo')
        self.send('test message')


def testnb():
    node = NodeNB()
    #ch = node.channel(('amq.direct', 'foo'), TestServer)
    ch = node.channel(TestServer)
    #ch = node.channel(TestClient)
    conn_parameters = ConnectionParameters()
    connection = SelectConnection(conn_parameters , node.on_connection_open)
    # Loop until CTRL-C
    try:
        # Start our blocking loop
        connection.ioloop.start()

    except KeyboardInterrupt:

        # Close the connection
        connection.close()

        # Loop until the connection is closed
        connection.ioloop.start()


if __name__ == '__main__':
    #testnb()
    #testb()
    testbclient()
    #test_accept()
