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

class BaseChannel(object):
    """
    Channel Protocol: Configuration and operation mechanics for an interaction pattern.

    The channel protocol is a context in which to handle AMQP events.
    Synchronous configuration (Queue, Basic, and Channel class)

    Synchronous:
        Queue.Declare, Queue.Bind, Basic.Consume, Basic.Cancel

    Asynchronous Methods (client to broker):
        Basic.Publish, Basic.Ack, Basic.Reject, Basic.Qos

    Asynchronous Events (broker to client):
        Channel.Close, Basic.Deliver, Basic.Return

    TODO: for synchronous method callbacks, the frame abstraction should
    not show up in this class. The layer below needs to unpack the frames
    and call these methods with a specified signature. 
    """

    amq_chan = None # the amqp transport

    _peer_name = None  # name send uses (exchange, routing_key)
    _chan_name = None  # name recv uses (exchange, binding_key)

    _close_callback = None  # the callback to use when close() is called

    # AMQP Exchange options
    exchange_type = 'topic' # do channels get to create exchanges?
    exchange_auto_delete = True
    exchange_durable = False

    # AMQP Queue options
    queue_auto_delete = True
    queue_durable = False
    queue_exclusive = False

    queue_named = False # use routing_key name for p2p; else, unique
    queue_do_declare = True # toggle actually creating queue; a queue may
                            # be expected to already exist

    # AMQP Consumer options
    consumer_no_ack = True
    consumer_exclusive = False
    prefetch_size = 1
    prefetch_count = 1

    _consuming = False
    _consumer_tag = None
#    _channel_bind_cb = None

    immediate = False # don't use
    mandatory = False # don't use

    queue = None
    exchange = None

    def __init__(self, close_callback=None):
        """
        Initializes a BaseChannel instance.

        @param  close_callback  The method to invoke when close() is called on this BaseChannel. May be left as None,
                                in which case close_impl() will be called. This expects to be a callable taking one
                                param, this channel instance.
        """
        self._close_callback = close_callback

    def __str__(self):
        res = "\n  _peer_name: "
        res += "None" if self._peer_name is None else str(self._peer_name)
        res += "\n"
        res += "  _chan_name: "
        res += "None" if self._chan_name is None else str(self._chan_name)
        res += "\n"
        res += "  queue: "
        res += "None" if self.queue is None else str(self.queue)
        res += "\n"
        res += "  exchange: "
        res += "None" if self.exchange is None else str(self.exchange)
        return res

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
        if self.amq_chan:
            self.amq_chan.close()

        # PIKA BUG: in v0.9.5, this amq_chan instance will be left around in the callbacks
        # manager, and trips a bug in the handler for on_basic_deliver. We attempt to clean
        # up for Pika here so we don't goof up when reusing a channel number.
        self.amq_chan.callbacks.remove(self.amq_chan.channel_number, 'Basic.GetEmpty')
        self.amq_chan.callbacks.remove(self.amq_chan.channel_number, 'Channel.Close')
        self.amq_chan.callbacks.remove(self.amq_chan.channel_number, '_on_basic_deliver')
        self.amq_chan.callbacks.remove(self.amq_chan.channel_number, '_on_basic_get')

        # uncomment these lines to see the full callback list that Pika maintains
        #stro = pprint.pformat(self.amq_chan.callbacks._callbacks)
        #log.error(str(stro))

    def on_channel_open(self, amq_chan):
        """
        """
        log.debug("In BaseChannel.on_channel_open")
        log.debug("channel_number: %d", amq_chan.channel_number)
        amq_chan.add_on_close_callback(self.on_channel_close)

        self.amq_chan = amq_chan
        self.do_config() # doesn't jive with blocking interface

    def on_channel_close(self, code, text):
        """
        handle possible channel errors

        propagate close where appropriate 

        respond to broker with channel_close_ok

        use instance state (current sync handler) to decide how to report
        channel exceptions 
        """
        logmeth = log.debug
        if code != 0:
            logmeth = log.error
        logmeth("In BaseChannel.on_channel_close")
        logmeth("channel number: %d", self.amq_chan.channel_number)
        logmeth("code: %d" % code)
        logmeth("text: %s" % str(text))

    def do_config(self):
        """
        configure amqp
        implement in subclass 

        XXX only use existing exchange now
        """
        log.debug("In BaseChannel.do_config")

    def config_exchange(self):
        """
        @TODO: too amqp specific, name this something else?  or push it down somewhere else?
        Performs an exchange_declare on the connection.
        """
        assert self.exchange
        # EXCHANGE INTERACTION HERE - use async method to wait for it to finish
        log.debug("Attempting exchange declare: %s, TYPE %s, DUR %s AD %s", self.exchange, self.exchange_type,
                                                                self.exchange_durable, self.exchange_auto_delete)
        blocking_cb(self.amq_chan.exchange_declare, 'callback', exchange=self.exchange,
                                                                type=self.exchange_type,
                                                                durable=self.exchange_durable,
                                                                auto_delete=self.exchange_auto_delete)

    def bind(self, name):
        """
        bind a channel to a name.
        a name [(exchange, routing_key)] is a member of a name space
        (exchange space; where the exchange is an exchange point)
        """
        log.debug("In BaseChannel.bind")
        log.debug("name: %s" % str(name))
        if self._chan_name:
            raise ChannelError('Channel already bound') #?
        self._chan_name = name
        self.exchange = name[0]
        self.queue = ".".join(name)     # prefix sysname so we don't clobber others please

        self.config_exchange()
        self.do_queue()

        self.on_bind()

    def on_bind(self):
        """
        on_transport_bind
        generic procedure that may be overridden in a subclass.
        """
        log.debug("In BaseChannel.on_bind")

    def connect(self, name):
        """
        connect to a channel such that this protocol can send a message to
        it.

        sets the sending context of the channel protocol

        Some Channel Protocols just set the _peer_name statically; others
        may actually require interaction with the broker.
        """
        log.debug("In BaseChannel.connect")
        log.debug("name: %s" % str(name))
        if self._peer_name:
            raise ChannelError('Channel already connected') # this is more "Client" than "Protocol"
        self._peer_name = name

        self.on_connect()

    def on_connect(self):
        """
        on_transport_connect ?
        generic procedure that may be overridden in a subclass.
        """
        log.debug("In BaseChannel.on_connect")

    def listen(self):
        """
        this ultimately starts a consumer.
        for a request-responsive server channel, listen allows connections
            to be made so accept can be called.
        for non-servers/simple receivers, listen starts a consumer so recv
            can be called.
        """
        log.debug("In BaseChannel.listen")
        self.on_listen() # may want to do some config before start_consumer

    def on_listen(self):
        """
        generic procedure that may be overridden in a subclass.
        """
        log.debug("In BaseChannel.on_listen")
        self._start_consumer()

    def do_queue(self):
        log.debug("In BaseChannel.do_queue")
        log.debug("------> queue: %s" % str(self.queue))

        frame = blocking_cb(self.amq_chan.queue_declare, 'callback',
                            queue=self.queue or '',
                            auto_delete=self.queue_auto_delete,
                            durable=self.queue_durable)
        log.debug("Queue declare ok, frame received")

        self.queue = frame.method.queue #XXX who really defines queue!!
        log.debug("queue: %s" % str(self.queue))
        if not self._chan_name[1]:
            self._chan_name = (self._chan_name[0], self.queue) # XXX total HACK!!!
        log.debug("_chan_name: %s" % str(self._chan_name))

        # do a bind
        frame2 = blocking_cb(self.amq_chan.queue_bind, 'callback',
                             queue=self.queue,
                             exchange=self._chan_name[0],
                             routing_key=self._chan_name[1])

        log.debug("Queue bind ok")

    def _start_consumer(self):
        """
        Note:
        in Pika, basic_consume is always treated as a nowait call

        TODO:
        management of consumer_tags?

        In general, any channel can have one consumer (maybe as a rule).
        No matter the variations of how the consumer is configured, it will
        always be started after some configuration interactions have
        happened with the broker.
        """
        log.debug("In BaseChannel._start_consumer")
        if self._consuming:
            raise #?
        self._consumer_tag = self.amq_chan.basic_consume(self._on_basic_deliver,
                                    queue=self.queue,
                                    no_ack=self.consumer_no_ack,
                                    exclusive=self.consumer_exclusive)
        self._consuming = True # XXX ?

    def _on_basic_deliver(self, chan, method_frame, header_frame, body):
        """
        delivery comes with the channel context, so this can easily be
        intercepted before it gets here
        """
        log.debug("In BaseChannel._on_basic_deliver")
        consumer_tag = method_frame.consumer_tag # use to further route?
        delivery_tag = method_frame.delivery_tag # use to ack
        redelivered = method_frame.redelivered
        exchange = method_frame.exchange
        routing_key = method_frame.routing_key

        # amqp specifics are handled here, and a mid-level event can be
        # raised here before the simple message_received. It's all about
        # funneling/organizing context to keep the endpoint handlers simple
        # and functional
        headers = header_frame.__dict__
        headers.update(header_frame.headers)
        self.message_received(body, headers)

    def send(self, data, headers=None):
        """
        use when 'connected' to an endpoint (sending end of a channel)
        """
        log.debug("In BaseChannel.send")
        log.debug("data: %s" % str(data))
        self._send(self._peer_name, data, headers=headers)

    def _send(self, name, data, headers=None,
                                content_type=None,
                                content_encoding=None,
                                message_type=None,
                                reply_to=None,
                                correlation_id=None,
                                message_id=None):
        """
        TODO: redo without intermediate props dict
        how expensive is constructing the BasicProperties for each send?
        """
        log.debug("In BaseChannel._send\n\tname: %s\n\tdata: %s\n\theaders: %s", name, data, headers)
        exchange, routing_key = name
        headers = headers or {}
        props = BasicProperties(headers=headers,
                            content_type=content_type,
                            content_encoding=content_encoding,
                            type=message_type,
                            reply_to=reply_to,
                            correlation_id=correlation_id,
                            message_id=message_id)
        # data is assumed to be properly encoded 
        self.amq_chan.basic_publish(exchange=exchange, #todo  
                                routing_key=routing_key, #todo 
                                body=data,
                                properties=props,
                                immediate=False, #todo 
                                mandatory=False) #todo

class _Bidirectional_accepted(BaseChannel):
    """
    services actual requests 

    use the listening channels amqp_chan to start a new consumer and to
    publish messages
    """

#    def __str__(self):
#        res = "_peer_name: "
#        res += "None" if self._peer_name is None else str(self._peer_name)
#        res += "\n"
#        res += "_chan_name: "
#        res += "None" if self._chan_name is None else self._chan_name
#        res += "\n"
#        res += "queue: "
#        res += "None" if self.queue is None else self.queue
#        res += "\n"
#        res += "exchange: "
#        res += "None" if self.exchange is None else self.exchange
#        return res

    def _on_basic_deliver(self, chan, method_frame, header_frame, body):
        """
        Not Implemented yet (can't receive yet) (only send)
        """
        log.debug("In _Bidirectional_accepted._on_basic_deliver")

    def send(self, data, headers=None):
        """
        use reply_to and correlation_id so each endpoint in a pair can
        converse in an arbitrary stream of messages.

        a listening Channel can establish a temp queue for interactions
        specific to this Node/Channel
        """
        log.debug("In _Bidirectional_accepted.send")
        message_type = "rr-data" # request-response data
        #reply_to = "%s,%s" % self._chan_name # encode the tuple 
        #correlation_id = uuid.uuid4().hex # move to lower level
        self._send(self._peer_name,
                   data,
                   message_type=message_type,
                   headers=headers)
                    #reply_to=reply_to)


class Bidirectional(BaseChannel):
    """
    General form of Point to Point with Request Response interaction.

    accept returns the new channel context facilitating point 2 point (for
    a 'request-response' interaction between 2 entities.
    recv does nothing for the listener; the accepted channel receives
    messages from the peer
    send does nothing for the listener; the accepted channel sends messages
    to the peer
    """

#    def __str__(self):
#        res = "_peer_name: "
#        res += "None" if self._peer_name is None else str(self._peer_name)
#        res += "\n"
#        res += "_chan_name: "
#        res += "None" if self._chan_name is None else self._chan_name
#        res += "\n"
#        res += "queue: "
#        res += "None" if self.queue is None else self.queue
#        res += "\n"
#        res += "exchange: "
#        res += "None" if self.exchange is None else self.exchange
#        return res

    def _on_basic_deliver(self, chan, method_frame, header_frame, body):
        message_type = header_frame.type
        # ensure proper type
        #self.message_received(body)
        log.debug("In Bidirectional._on_basic_deliver")
        reply_to = tuple(header_frame.reply_to.split(','))
        headers = header_frame.__dict__
        headers.update(header_frame.headers)
        self._build_accepted_channel(reply_to, body, headers)

    def _build_accepted_channel(self, peer_name, body, headers):
        """Only set send context (can't receive yet)"""
        log.debug("In Bidirectional._build_accepted_channel")
        log.debug("peer_name: %s" % str(peer_name))
        new_chan = _Bidirectional_accepted()
        new_chan.amq_chan = self.amq_chan #hack
        new_chan._peer_name = peer_name
        self.message_received((new_chan, body), headers) # XXX hack  ugh serious bad hack here, totally unfollowable

    def connect(self, name):
        """
        Connect to a channel such that this protocol can send a message to it.

        Sets the sending context of the channel protocol

        Some Channel Protocols just set the _peer_name statically; others
        may actually require interaction with the broker.
        """
        log.debug("In Bidirectional.connect")
        log.debug("name: %s" % str(name))
        if self._peer_name:
            raise ChannelError('Channel already connected') # this is more "Client" than "Protocol"
        self._peer_name = name
        self.queue = ''
        self._chan_name = (self._peer_name[0], '')
        self.exchange = self._peer_name[0]

        self.config_exchange()
        self.do_queue()
        self._chan_name = (self._peer_name[0], self.queue)

    def send(self, data, headers=None):
        """
        use reply_to and correlation_id so each endpoint in a pair can
        converse in an arbitrary stream of messages.

        a listening Channel can establish a temp queue for interactions
        specific to this Node/Channel
        """
        log.debug("In Bidirectional.send")
        message_type = "rr-data" # request-response data
        reply_to = "%s,%s" % self._chan_name # encode the tuple 
        log.debug("_peer_name: %s" % str(self._peer_name))
        log.debug("reply_to: %s" % str(reply_to))
        #correlation_id = uuid.uuid4().hex # move to lower level
        self._send(self._peer_name,
                   data,
                   message_type=message_type,
                   reply_to=reply_to,
                   headers=headers)

class BidirectionalClient(BaseChannel):

    consumer_exclusive = True

#    def __str__(self):
#        res = "_peer_name: "
#        res += "None" if self._peer_name is None else str(self._peer_name)
#        res += "\n"
#        res += "_chan_name: "
#        res += "None" if self._chan_name is None else self._chan_name
#        res += "\n"
#        res += "queue: "
#        res += "None" if self.queue is None else self.queue
#        res += "\n"
#        res += "exchange: "
#        res += "None" if self.exchange is None else self.exchange
#        return res

    def connect(self, name):
        """
        connect to a channel such that this protocol can send a message to
        it.

        sets the sending context of the channel protocol

        Some Channel Protocols just set the _peer_name statically; others
        may actually require interaction with the broker.
        """
        log.debug("In BidirectionalClient.connect")
        log.debug("name: %s" % str(name))
        if self._peer_name:
            raise ChannelError('Channel already connected') # this is more "Client" than "Protocol"
        self._peer_name = name
        self._chan_name = (self._peer_name[0], self.queue)

        if self.queue_do_declare:
            self.do_queue()
            self._chan_name = (self._peer_name[0], self.queue)
            self._start_consumer()
            self.queue_do_declare = False

    def send(self, data, headers=None):
        """
        use reply_to and correlation_id so each endpoint in a pair can
        converse in an arbitrary stream of messages.

        a listening Channel can establish a temp queue for interactions
        specific to this Node/Channel
        """
        log.debug("In BidirectionalClient.send")
        log.debug("_peer_name: %s" % str(self._peer_name))
        log.debug("data: %s" % str(data))
        message_type = "rr-data" # request-response data
        reply_to = "%s,%s" % self._chan_name # encode the tuple 
        #correlation_id = uuid.uuid4().hex # move to lower level
        self._send(self._peer_name,
                   data,
                   message_type=message_type,
                   reply_to=reply_to,
                   headers=headers)

    def close(self):
        """
        Close override, cleans up changes made during connect so this can be
        re-used again on the logical level.
        """
        log.debug("In BidirectionalClient.close")
        self._peer_name = None

        BaseChannel.close(self)

class PubSub(BaseChannel):
    """
    Endpoints do not directly interact.

    use a topic amqp exchange
    """

    #exchange_type = 'topic'

#    def __str__(self):
#        res = "_peer_name: "
#        res += "None" if self._peer_name is None else str(self._peer_name)
#        res += "\n"
#        res += "_chan_name: "
#        res += "None" if self._chan_name is None else self._chan_name
#        res += "\n"
#        res += "queue: "
#        res += "None" if self.queue is None else self.queue
#        res += "\n"
#        res += "exchange: "
#        res += "None" if self.exchange is None else self.exchange
#        return res

    def _on_basic_deliver(self, chan, method_frame, header_frame, body):
        message_type = header_frame.type
        # ensure proper type
        #self.message_received(body)
        log.debug("In PubSub._on_basic_deliver")
        log.debug("\nhf: %s\nbody: %s" % (str(header_frame), str(body)))
        #reply_to = tuple(header_frame.reply_to.split(','))
        headers = header_frame.__dict__
        headers.update(header_frame.headers)
        self._build_accepted_channel("", body, headers)

    def _build_accepted_channel(self, peer_name, body, headers):
        """
        only set send context (can't receive yet)
        """
        log.debug("In PubSub._build_accepted_channel")
        log.debug("peer_name: %s" % str(peer_name))
        new_chan = BaseChannel()
        new_chan.amq_chan = self.amq_chan #hack
        new_chan._peer_name = peer_name
        self.message_received((new_chan, body), headers) # XXX hack  ugh serious bad hack here, totally unfollowable

    def on_connect(self):
        self.exchange = self._peer_name[0]
        self.config_exchange()

class ChannelShutdownMessage(object):
    """ Dummy object to unblock queues. """
    pass

class SocketInterface(object):
    """
    Adapts an AMQP channel.
    Adds a blocking layer using gevent Async Events to achieve a socket/0mq like behavior.
    """

    ch_proto = None

    def __init__(self, amq_chan, ch_proto):
        """
        @param amq_chan instance of amqp channel from amqp client
        @param ch_proto instance of a ChannelProtocol
        """
        log.debug("In SocketInterface.__init__")
        log.debug("amq_chan: %s" % str(amq_chan))
        log.debug("ch_proto: %s" % str(ch_proto))
        #self.ch_proto_type = ch_proto_type
        self.amq_chan = amq_chan
        #ch_proto = ch_proto_type()
        #ch_proto.on_channel_open(amq_chan)
        self.ch_proto = ch_proto

        self._bound = 0
        self._connected = 0
        self._listening = 0

        self._receive_queue = gqueue.Queue()
        ch_proto.message_received = self.message_received

    def _next_in_queue(self):
        msg = self._receive_queue.get()
        if isinstance(msg, ChannelShutdownMessage):
            raise ChannelClosedError('Attempt to recv on a channel that is being closed.')
        return msg

    @classmethod
    def Socket(cls, amq_chan, ch_proto):
        """Main way to instantiate a Channel wrapping SocketInterface
        """
        log.debug("In SocketInterface.Socket")
        log.debug("amq_chan: %s" % str(amq_chan))
        log.debug("ch_proto: %s" % str(ch_proto))
        inst = cls(amq_chan, ch_proto)
        return inst

    def message_received(self, msg, headers):
        log.debug("In SocketInterface.message_received")
        self._receive_queue.put((msg, headers))

    def accept(self):
        """
        use in server mode to get the next connection made to this
        listening channel

        for a listener, this still reads from the message received queue.

        create new channel proto with provided proto type and use same
        amq_chan to create a new consumer.
        """
        log.debug("In SocketInterface.accept")
        #self.ch_proto.accept()

        if not self._listening:
            raise ChannelError('Channel not listening')#?
        #new_serv_ch_proto, body = self._receive_queue.get()
        fullon, headers = self._next_in_queue()
        log.debug("we got %d items: %s" % (len(fullon), str(fullon)))

        new_serv_ch_proto, body = fullon[0:2]

        new_chan = SocketInterface(self.amq_chan, new_serv_ch_proto)
        #new_chan.ch_proto.connect() # need
        new_chan._connected = 1 # hack
        new_chan.message_received(body, headers) # hack
        return new_chan

    def bind(self, name):
        """
        Bind Channel to a name.

        Sets context for receiving peer/server.
        """
        log.debug("In SocketInterface.bind")
        log.debug("name: %s" % str(name))

        self.ch_proto.bind(name)
        self._bound = 1 
        return


    def close(self):
        """
        shutdown everything 
        cancel consumers, if any are active 
        close underlying amqp channel
        """
        log.debug("In SocketInterface.close")
        self._receive_queue.put(ChannelShutdownMessage())
        self.ch_proto.close()

    def connect(self, name):
        """
        Connect to a Channel of name.

        Sets context for a sending peer/client.
        """
        log.debug("In SocketInterface.connect")
        log.debug("name: %s" % str(name))

        self.ch_proto.connect(name)
        self._connected = 1 # hmm, used for blocking interface only; redundant with chan proto tho
        return


    def listen(self, n=1):
        """
        Channel must be bound to a name to start listening

        The n parameter will map to a qos setting where appropriate

        If the channel is in a good state, then a consumer is started.
        Depending on the interaction protocol, different things can happen
        when a message is received.
        """
        log.debug("In SocketInterface.listen")
        if not self._bound or self._connected:
            raise ChannelError('Not in a state to listen')
        self.ch_proto.listen() # this should wait for the ok event
        self._connected = 1 # for servers too?
        self._listening = 1 # XXX need? listening state dictates accept/recv behavior

    def recv(self, *args):
        """
        """
        log.debug("In SocketInterface.recv")
        if not self._connected:
            raise ChannelError('Channel not connected')#?
        return self._next_in_queue()

    def send(self, data, headers=None):
        """
        """
        log.debug("In SocketInterface.send")
        self.ch_proto.send(data, headers=headers)
