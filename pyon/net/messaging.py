 #!/usr/bin/env python

"""AMQP messaging with Pika."""

import gevent
from gevent import event, coros

from pika.credentials import PlainCredentials
from pika.connection import ConnectionParameters
from pika.adapters import SelectConnection
from pika import BasicProperties

from pyon.core.bootstrap import CFG
from pyon.net import amqp
from pyon.net import channel
from pyon.util.async import blocking_cb
from pyon.util.log import log

class IDPool(object):
    """
    Create a pool of IDs to allow reuse.
    The "new_id" function generates the next valid ID from the previous one. If not given, defaults to
    incrementing an integer.
    """

    def __init__(self, new_id=None):
        log.debug("In IDPool.__init__")
        if new_id is None: new_id = lambda x: x + 1
        log.debug("new_id: %s" % str(new_id))

        self.ids_in_use = set()
        self.ids_free = set()
        self.new_id = new_id
        self.last_id = 0

    def get_id(self):
        log.debug("In IDPool.get_id")
        log.debug("idsfree: %s", self.ids_free)
        log.debug("idsinuse: %s", self.ids_in_use)
        if len(self.ids_free) > 0:
            #log.debug("new_id: %s" % str(new_id))
            id = self.ids_free.pop()
            self.ids_in_use.add(id)
            log.debug("id: %s" % str(id))
            return id

        self.last_id = id_ = self.new_id(self.last_id)
        self.ids_in_use.add(id_)
        log.debug("id: %s" % str(id_))
        return id_

    def release_id(self, the_id):
        log.debug("In IDPool.release_id")
        log.debug("the_id: %s" % str(the_id))
        log.debug("idsfree: %s", self.ids_free)
        log.debug("idsinuse: %s", self.ids_in_use)
        if the_id in self.ids_in_use:
            self.ids_in_use.remove(the_id)
            self.ids_free.add(the_id)

class NodeB(amqp.Node):
    """
    Blocking interface to AMQP messaging primitives.

    Wrap around Node and create blocking interface for getting channel
    objects.
    """

    def __init__(self):
        log.debug("In NodeB.__init__")
        self.ready = event.Event()
        self._lock = coros.RLock()
        self._pool = IDPool()
        self._bidir_pool = {}   # maps inactive/active our numbers (from self._pool) to channels
        self._pool_map = {}     # maps active pika channel numbers to our numbers (from self._pool)

        amqp.Node.__init__(self)

    def start_node(self):
        """
        This should only be called by on_connection_opened.
        so, maybe we don't need a start_node/stop_node interface
        """
        log.debug("In start_node")
        amqp.Node.start_node(self)
        self.running = 1
        self.ready.set()

    def channel(self, chan):
        log.debug("NodeB.channel")
        with self._lock:
            amq_chan = blocking_cb(self.client.channel, 'on_open_callback')
            chan.on_channel_open(amq_chan)
            #chan._close_callback = self.on_channel_request_close       # @TODO

        return chan

    def OLDchannel(self, ch_type):
        log.debug("In NodeB.channel, pool size is %d", len(self._bidir_pool))
        if not self.running:
            log.error("Attempt to open channel on node that is not running")
            raise #?

        log.debug("acquire semaphore")
        with self._lock:
            log.debug("acquired semaphore")

            def new_channel():
                result = event.AsyncResult()
                def on_channel_open_ok(amq_chan):
                    sch = ch_type(close_callback=self.on_channel_request_close)
                    sch.on_channel_open(amq_chan)
                    ch = channel.SocketInterface.Socket(amq_chan, sch)
                    result.set((ch, sch))
                self.client.channel(on_channel_open_ok)
                return result.get()

            if ch_type == channel.BidirectionalClient:
                chid = self._pool.get_id()
                if chid in self._bidir_pool:
                    assert not chid in self._pool_map.values()
                    self._pool_map[self._bidir_pool[chid].amq_chan.channel_number] = chid
                    ch = self._bidir_pool[chid]
                    socket = channel.SocketInterface.Socket(ch.amq_chan, ch)
                else:
                    socket, ch = new_channel()
                    self._bidir_pool[chid] = ch
                    self._pool_map[ch.amq_chan.channel_number] = chid
            else:
                socket, ch = new_channel()

            assert socket and ch
            log.debug("sock channel: %s" % str(socket))

        log.debug("release semaphore")

        return socket

    def on_channel_request_close(self, ch):
        log.debug("NodeB: on_channel_request_close")
        log.debug("ChType %s, Ch#: %d", ch.__class__, ch.amq_chan.channel_number)
        log.debug("MAP: %s", self._pool_map)

        if ch.amq_chan.channel_number in self._pool_map:
            with self._lock:
                chid = self._pool_map.pop(ch.amq_chan.channel_number)
                log.debug("Releasing BiDir pool Pika #%d, our id #%d", ch.amq_chan.channel_number, chid)
                self._pool.release_id(chid)
        else:
            ch.close_impl()

def ioloop(connection):
    # Loop until CTRL-C
    log.debug("In ioloop")
    import threading
    threading.current_thread().name = "NODE"
    try:
        # Start our blocking loop
        log.debug("Before start")
        connection.ioloop.start()
        log.debug("After start")

    except KeyboardInterrupt:

        log.debug("Got keyboard interrupt")

        # Close the connection
        connection.close()

        # Loop until the connection is closed
        connection.ioloop.start()

def make_node(connection_params=None):
    """
    Blocking construction and connection of node.

    @param connection_params  AMQP connection parameters. By default, uses CFG.server.amqp (most common use).
    """
    log.debug("In make_node")
    node = NodeB()
    connection_params = connection_params or CFG.server.amqp
    credentials = PlainCredentials(connection_params["username"], connection_params["password"])
    conn_parameters = ConnectionParameters(host=connection_params["host"], virtual_host=connection_params["vhost"], port=connection_params["port"], credentials=credentials)
    connection = SelectConnection(conn_parameters , node.on_connection_open)
    ioloop_process = gevent.spawn(ioloop, connection)
    #ioloop_process = gevent.spawn(connection.ioloop.start)
    node.ready.wait()
    return node, ioloop_process
    #return node, ioloop, connection

def testb():
    log.debug("In testb")
    node, ioloop_process = make_node()
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
    log.debug("In testbclient")
    node, ioloop_process = make_node()
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
    log.debug("In test_accept")
    node, ioloop_process = make_node()
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
    Main non blocking messaging interface that goes active when amqp client connects.
    Integrates messaging and processing

    The life cycle of this depends on the underlying amqp connection.

    This thing (or a subordinate but coupled/controlled object) mediates
    Messaging Channels that are used to send messages or that dispatch
    received messages to receiver/consumer protocol things.
    """

    def __init__(self):
        log.debug("In NodeNB.__init__")
        self.channels = {}
        self.id_pool = IDPool()

    def start_node(self):
        """
        This should only be called by on_connection_opened..
        so, maybe we don't need a start_node/stop_node interface
        """
        log.debug("In NodeNB.start_node")
        amqp.Node.start_node(self)
        for ch_id in self.channels:
            self.start_channel(ch_id)

    def stop_node(self):
        """
        """
        log.debug("In NodeNB.stop_node")

    def channel(self, ch_type):
        """
        ch_type is one of PointToPoint, etc.
        return Channel instance that will be activated with amqp_channel
        and configured

        name (exchange, key)
        name shouldn't need to be specified here, but it is for now
        """
        log.debug("In NodeNB.channel")
        ch = ch_type()
        ch_id = self.id_pool.get_id()
        log.debug("channel id: %s" % str(ch_id))
        self.channels[ch_id] = ch
        if self.running:
            self.start_channel(ch_id)
        log.debug("channel: %s" % str(ch))
        return ch

    def start_channel(self, ch_id):
        log.debug("In NodeNB.start_channel")
        log.debug("ch_id: %s" % str(ch_id))
        ch = self.channels[ch_id]
        log.debug("ch: %s" % str(ch))
        self.client.channel(ch.on_channel_open)

    def spawnServer(self, f):
        """
        """
        log.debug("In spawnServer")

class TestServer(channel.BaseChannel):

    def do_config(self):
        log.debug("In TestServer.do_config")
        self._chan_name = ('amq.direct', 'foo')
        self.queue = 'foo'
        self.do_queue()

class TestClient(channel.BaseChannel):

    def do_config(self):
        log.debug("In TestClient.do_config")
        self._peer_name = ('amq.direct', 'foo')
        self.send('test message')


def testnb():
    log.debug("In testnb")
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
