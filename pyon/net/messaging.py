 #!/usr/bin/env python

"""AMQP messaging with Pika."""

import gevent
from gevent import event, coros

from pika.credentials import PlainCredentials
from pika.connection import ConnectionParameters
from pika.adapters import SelectConnection

from pyon.core.bootstrap import CFG
from pyon.net import amqp
from pyon.net import channel
from pyon.util.async import blocking_cb
from pyon.util.log import log
from pyon.util.pool import IDPool

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

    def _new_channel(self, ch_type, **kwargs):
        """
        Creates a pyon Channel based on the passed in type, and activates it for use.
        """
        chan = ch_type(**kwargs)
        amq_chan = blocking_cb(self.client.channel, 'on_open_callback')
        chan.on_channel_open(amq_chan)
        return chan

    def channel(self, ch_type, **kwargs):
        """
        Creates a Channel object with an underlying transport callback and returns it.

        @type ch_type   BaseChannel
        """
        log.debug("NodeB.channel")
        with self._lock:
            # having _queue_auto_delete on is a pre-req to being able to pool.
            if ch_type == channel.BidirClientChannel and not ch_type._queue_auto_delete:
                chid = self._pool.get_id()
                if chid in self._bidir_pool:
                    log.debug("BidirClientChannel requested, pulling from pool (%d)", chid)
                    assert not chid in self._pool_map.values()
                    ch = self._bidir_pool[chid]
                    self._pool_map[ch.get_channel_id()] = chid
                else:
                    log.debug("BidirClientChannel requested, no pool items available, creating new (%d)", chid)
                    ch = self._new_channel(ch_type, **kwargs)
                    ch.set_close_callback(self.on_channel_request_close)
                    self._bidir_pool[chid] = ch
                    self._pool_map[ch.get_channel_id()] = chid
            else:
                ch = self._new_channel(ch_type, **kwargs)
            assert ch

        return ch

    def on_channel_request_close(self, ch):
        """
        Close callback for pooled Channels.

        When a new, pooled Channel is created that this Node manages, it will specify this as the
        close callback in order to prevent that Channel from actually closing.
        """
        log.debug("NodeB: on_channel_request_close\n\tChType %s, Ch#: %d", ch.__class__, ch.get_channel_id())

        assert ch.get_channel_id() in self._pool_map
        with self._lock:
            ch.stop_consume()
            chid = self._pool_map.pop(ch.get_channel_id())
            log.debug("Releasing BiDir pool Pika #%d, our id #%d", ch.get_channel_id(), chid)
            self._pool.release_id(chid)

            # sanity check: if auto delete got turned on, we must remove this channel from the pool
            if ch._queue_auto_delete:
                log.warn("A pooled channel now has _queue_auto_delete set true, we must remove it: check what caused this as it's likely a timing error")

                self._bidir_pool.pop(chid)
                self._pool._ids_free.remove(chid)

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

