#!/usr/bin/env python

"""
Provides a messaging channel protocol.

Defines the configuration parameter values and execution/command sequence.
(The configuration may require in-band communication with the broker. This
communication can only occur once the Channel transport is technically in a
state that is ready (connectionMade).

Once configured, the Channel Protocol is used to administer the
operational state of the Channel (start or stop consuming; etc.) and to
facilitate communication (delivery/sending of messages) between amqp
messaging and the application.

The Channel Protocol mediates between the application using it and the amqp
protocol underlying it...so the Channel Protocol is a transport protocol in
the language of amqp methods and ooi exchange nomenclature.

The Channel Protocol doesn't make a lot of sense for the 'interactive'
style client methods, like accept, or listen.
Listen kind of does, it says go into listening mode.
If the Channel Protocol is a state machine, then it's states are being
changed by the client interface...and communication events?
When it is first being configured, it is in a pre-ready state, and the amqp
methods drive the state transitions. 
If listen means "put the protocol in the mode where received messages mean
making new connection contexts"...then accept means...
Accept is the synchronous version of getting a message received while in
listen mode


TODO:
[ ] Use nowait on amqp config methods and handle channel exceptions with pika
[ ] PointToPoint Channel (from Bidirectional)
[ ] Channel needs to support reliable delivery (consumer ack; point to
point will ack when the content of a delivery naturally concludes (channel
is closed)
"""

from pyon.util.async import blocking_cb
from pyon.util.log import log
from pika import BasicProperties
from gevent import queue as gqueue

class ChannelError(Exception):
    """
    Exception raised for error using Channel Socket Interface.
    """

class ChannelClosedError(Exception):
    """
    Denote activity on a closed channel (usually during shutdown).
    """

class ChannelShutdownMessage(object):
    """ Dummy object to unblock queues. """
    pass

class BaseChannel(object):

    _amq_chan                   = None      # underlying transport
    _close_callback             = None      # close callback to use when closing, not always set (used for pooling)
    _exchange                   = None      # exchange (too AMQP specific)

    # exchange related settings @TODO: these should likely come from config instead
    _exchange_type              = 'topic'
    _exchange_auto_delete       = True
    _exchange_durable           = False

    def __init__(self, close_callback=None):
        """
        Initializes a BaseChannel instance.

        @param  close_callback  The method to invoke when close() is called on this BaseChannel. May be left as None,
                                in which case close_impl() will be called. This expects to be a callable taking one
                                param, this channel instance.
        """
        self._close_callback = close_callback

    def _declare_exchange_point(self, xp):
        """

        @TODO: this really shouldn't exist, messaging layer should not make this declaration.  it will be provided.
               perhaps push into an ion layer derivation to help bootstrapping / getting started fast.
        """
        self._exchange = xp
        assert self._exchange
        # EXCHANGE INTERACTION HERE - use async method to wait for it to finish
        log.debug("Exchange declare: %s, TYPE %s, DUR %s AD %s", self._exchange, self._exchange_type,
                                                                 self._exchange_durable, self._exchange_auto_delete)
        blocking_cb(self._amq_chan.exchange_declare, 'callback', exchange=self._exchange,
                                                                type=self._exchange_type,
                                                                durable=self._exchange_durable,
                                                                auto_delete=self._exchange_auto_delete)

    def attach_underlying_channel(self, amq_chan):
        """
        Attaches an AMQP channel and indicates this channel is now open.
        @TODO silly name
        """
        self._amq_chan = amq_chan

    def close(self):
        """
        Default close method. If created via a Node (99% likely), the Node will take care of
        calling close_impl for you at the proper time.
        """
        if self._close_callback:
            self._close_callback(self)
        else:
            self.close_impl()

    def close_impl(self):
        """
        Closes the AMQP connection.
        @TODO: belongs here?
        """
        log.debug("BaseChannel.close_impl")
        if self._amq_chan:
            self._amq_chan.close()

        # PIKA BUG: in v0.9.5, this amq_chan instance will be left around in the callbacks
        # manager, and trips a bug in the handler for on_basic_deliver. We attempt to clean
        # up for Pika here so we don't goof up when reusing a channel number.
        self._amq_chan.callbacks.remove(self._amq_chan.channel_number, 'Basic.GetEmpty')
        self._amq_chan.callbacks.remove(self._amq_chan.channel_number, 'Channel.Close')
        self._amq_chan.callbacks.remove(self._amq_chan.channel_number, '_on_basic_deliver')
        self._amq_chan.callbacks.remove(self._amq_chan.channel_number, '_on_basic_get')

        # uncomment these lines to see the full callback list that Pika maintains
        #stro = pprint.pformat(self.amq_chan.callbacks._callbacks)
        #log.error(str(stro))

    def on_channel_open(self, amq_chan):
        amq_chan.add_on_close_callback(self.on_channel_close)
        self.attach_underlying_channel(amq_chan)

    def on_channel_close(self, code, text):
        logmeth = log.debug
        if code != 0:
            logmeth = log.error
        logmeth("BaseChannel.on_channel_close\n\tchannel number: %d\n\tcode: %d\n\ttext: %s", self._amq_chan.channel_number, code, text)

class SendChannel(BaseChannel):
    """
    A channel that can only send.
    """
    _send_name = None           # name that this channel is sending to - tuple (exchange, routing_key)

    def connect(self, name):
        log.debug("SendChannel.connect: %s", name)

        self._send_name = name
        self._exchange = name[0]

    def send(self, data, headers=None):
        log.debug("SendChannel.send")
        self._send(self._send_name, data, headers=headers)

    def _send(self, name, data, headers=None,
                                content_type=None,
                                content_encoding=None,
                                message_type=None,
                                reply_to=None,
                                correlation_id=None,
                                message_id=None):

        log.debug("SendChannel._send\n\tname: %s\n\tdata: %s\n\theaders: %s", name, data, headers)
        exchange, routing_key = name
        headers = headers or {}
        props = BasicProperties(headers=headers,
                            content_type=content_type,
                            content_encoding=content_encoding,
                            type=message_type,
                            reply_to=reply_to,
                            correlation_id=correlation_id,
                            message_id=message_id)

        self._amq_chan.basic_publish(exchange=exchange, #todo
                                routing_key=routing_key, #todo
                                body=data,
                                properties=props,
                                immediate=False, #todo
                                mandatory=False) #todo

class RecvChannel(BaseChannel):
    """
    A channel that can only receive.
    """
    # data for this receive channel
    _recv_queue     = None
    _consuming      = False
    _consumer_tag   = None
    _recv_name      = None      # name this receiving channel is receiving on - tuple (exchange, queue)

    # queue defaults
    _queue_auto_delete  = False
    _queue_exclusive    = False
    _queue_durable      = False

    # consumer defaults
    _consumer_exclusive = False
    _consumer_no_ack    = False     # endpoint layers do the acking as they call recv()

    def __init__(self, **kwargs):
        self._recv_queue = gqueue.Queue()
        BaseChannel.__init__(self, **kwargs)

    def setup_listener(self, name, binding=None):
        """
        @param  name        A tuple of (exchange, queue)
        @param  binding     If not set, uses name.
        """
        xp, queue = name

        self._recv_name = (xp, queue)

        log.debug("RecvChannel.setup_listener, xp %s, queue %s, binding %s" % (xp, queue, binding))

        self._declare_exchange_point(xp)
        queue   = self._declare_queue(queue)
        binding = binding or queue      # should only happen in the case of anon-queue

        self._bind(binding)

    def start_consume(self):
        log.debug("RecvChannel.start_consume")
        if self._consuming:
            raise StandardError("Already consuming")

        if self._consumer_tag and self._queue_auto_delete:
            log.warn("Attempting to start consuming on a queue that may have been auto-deleted")

        self._consumer_tag = self._amq_chan.basic_consume(self._on_deliver,
                                                          queue=self._recv_name[1],
                                                          no_ack=self._consumer_no_ack,
                                                          exclusive=self._consumer_exclusive)
        self._consuming = True

    def stop_consume(self):
        """
        Stops consuming messages.

        If the queue has auto_delete, this will delete it.
        """
        log.debug("RecvChannel.stop_consume")
        if not self._consuming:
            raise StandardError("Not consuming")

        if self._queue_auto_delete:
            log.info("Autodelete is on, this will destroy this queue")

        blocking_cb(self._amq_chan.basic_cancel, 'callback', self._consumer_tag)
        self._consuming = False

    def recv(self):
        """
        Pulls a message off the queue, will block if there are none.
        Typically done by the Endpoint layer. Should ack the message there as it is "taking ownership".
        """
        msg = self._recv_queue.get()

        # how we handle closed/closing calls, not the best @TODO
        if isinstance(msg, ChannelShutdownMessage):
            raise ChannelClosedError('Attempt to recv on a channel that is being closed.')

        return msg

    def close_impl(self):
        """
        Close implementation override.

        If we've declared and we're not auto_delete, must delete here.
        Also put a ChannelShutdownMessage in the recv queue so anything blocking on reading it will get notified via ChannelClosedError.
        """
        # stop consuming if we are consuming
        log.debug("BaseChannel.close_impl: consuming %s", self._consuming)
        if self._consuming:
            self.stop_consume()

        if not self._queue_auto_delete and self._recv_name and self._recv_name[1]:
            log.debug("Deleting queue %s", self._recv_name)
            blocking_cb(self._amq_chan.queue_delete, 'callback', queue=self._recv_name[1])

        self._recv_queue.put(ChannelShutdownMessage())

        BaseChannel.close_impl(self)

    def _declare_queue(self, queue):

        # prepend xp name in the queue for anti-clobbering
        if queue:
            queue = ".".join([self._recv_name[0], queue])

        log.debug("RecvChannel._declare_queue: %s", queue)
        frame = blocking_cb(self._amq_chan.queue_declare, 'callback',
                            queue=queue or '',
                            auto_delete=self._queue_auto_delete,
                            durable=self._queue_durable)

        # if the queue was anon, save it
        #if queue is None:
        # always save the new recv_name - we may have created a new one
        self._recv_name = (self._recv_name[0], frame.method.queue)

        return self._recv_name[1]

    def _bind(self, binding):
        log.debug("RecvChannel._bind: %s" % binding)
        assert self._recv_name and self._recv_name[1]
        
        queue = self._recv_name[1]
        blocking_cb(self._amq_chan.queue_bind, 'callback',
                    queue=queue,
                    exchange=self._recv_name[0],
                    routing_key=binding)

    def _on_deliver(self, chan, method_frame, header_frame, body):
        log.debug("RecvChannel._on_deliver")

        consumer_tag = method_frame.consumer_tag # use to further route?
        delivery_tag = method_frame.delivery_tag # use to ack
        redelivered = method_frame.redelivered
        exchange = method_frame.exchange
        routing_key = method_frame.routing_key

        # merge down "user" headers with amqp headers
        headers = header_frame.__dict__
        headers.update(header_frame.headers)

        # put body, headers, delivery tag (for acking) in the recv queue
        self._recv_queue.put((body, headers, delivery_tag))  # and more

    def ack(self, delivery_tag):
        """
        Acks a message using the delivery tag.
        Should be called by the EP layer.
        """
        log.debug("RecvChannel.ack: %s" % delivery_tag)
        self._amq_chan.basic_ack(delivery_tag)


class PubChannel(SendChannel):
    pass

class BidirClientChannel(SendChannel, RecvChannel):
    """
    This should be pooled for the receiving side?

    As opposed to current endpoint scheme - no need to spawn a listening greenlet simply to loop on recv(),
    you can use this channel to send first then call recieve linearly, no need for greenletting.
    """
    _queue_auto_delete  = True
    _consumer_exclusive = True

    def _send(self, name, data, headers=None,
                                content_type=None,
                                content_encoding=None,
                                message_type=None,
                                reply_to=None,
                                correlation_id=None,
                                message_id=None):
        """
        Override of internal send method.
        Sets reply_to/message_type if not set as a kwarg.
        """
        reply_to        = reply_to or "%s,%s" % self._recv_name
        message_type    = message_type or "rr-data"

        SendChannel._send(self, name, data, headers=headers,
                                            content_type=content_type,
                                            content_encoding=content_encoding,
                                            message_type=message_type,
                                            reply_to=reply_to,
                                            correlation_id=correlation_id,
                                            message_id=message_id)

class ListenChannel(RecvChannel):
    """
    Used for listening patterns (RR server, Subscriber).
    Main use is accept() - listens continously on one queue, pulls messages off, creates a new channel
                           to interact and returns it
    """

    class AcceptedListenChannel(RecvChannel):
        """
        The type of channel returned by accept.
        """
        def close_impl(self):
            """
            Do not close underlying amqp channel
            """
            pass

    def _create_accepted_channel(self, amq_chan, msg):
        ch = self.AcceptedListenChannel()
        ch.attach_underlying_channel(amq_chan)
        return ch

    def accept(self):
        """
        @returns A new channel that can:
                    - takes a copy of the underlying transport channel
                    - send() aka reply
                    - close without closing underlying transport channel
                    - FUTURE: receive (use a preexisting listening pool), for more complicated patterns
                              aka AGREE/STATUS/CANCEL
                    - has the initial received message here put onto its recv gqueue
                    - recv() returns messages in its gqueue, endpoint should ack
        """
        m = self.recv()
        ch = self._create_accepted_channel(self._amq_chan, m)
        ch._recv_queue.put(m)       # prime our recieved message here, should be acked by EP layer

        return ch

class SubscriberChannel(ListenChannel):
    pass

class ServerChannel(ListenChannel):

    class BidirAcceptChannel(ListenChannel.AcceptedListenChannel, SendChannel):
        pass

    def _create_accepted_channel(self, amq_chan, msg):
        send_name = tuple(msg[1].get('reply_to').split(','))        # @TODO: this seems very wrong
        ch = self.BidirAcceptChannel()
        ch.attach_underlying_channel(amq_chan)
        ch._send_name = send_name
        return ch
