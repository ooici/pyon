"""

Channel Protocol

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
point will ack when the contet of a delivery naturally concludes (channel
is closed)
"""

import uuid
import time

from pika import BasicProperties

from gevent import queue as gqueue
from gevent import event

class ChannelError(Exception):
    """
    Exception raised for error using Channel Socket Interface.
    """

class Admin(object):
    """
    service thing to look up what exchanges should be available to the
    Node.
    thing could also be used to register exchanges (ex points).
    Defaults could be in local file (e.g. /etc/hosts)

    an actual network service could give more accurate/dynamic info.
    """

class _AMQPHandlerMixin(object):

    def on_channel_open(self, amq_chan):
        amq_chan.add_on_close_callback(self.on_channel_close)
        self.amq_chan = amq_chan

    def on_channel_close(self, code, text):
        """
        handle possible channel errors

        propagate close where appropriate 

        respond to broker with channel_close_ok

        use instance state (current sync handler) to decide how to report
        channel exceptions 
        """
        print 'channel close'


class ChannelProtocol(object):
    """
    """

    def message_received(self, msg):
        """
        msg is a unit of data, some kind of object depending on what kind
        of Channel it is
        """

class BaseChannel(object):
    """
    Channel Protocol
    Configuration and operation mechanics for an interaction pattern

    The channel protocol is a context in which to handle amqp events.
    Synchronous configuration (Queue, Basic, and Channel class)

    Synchronous:
        Queue.Declare
        Queue.Bind
        Basic.Consume
        Basic.Cancel

    Asynchronous Methods (client to broker):
        Basic.Publish
        Basic.Ack
        Basic.Reject
        Basic.Qos

    Asynchronous Events (broker to client):
        Channel.Close
        Basic.Deliver
        Basic.Return


    TODO: for synchronous method callbacks, the frame abstraction should
    not show up in this class. The layer below needs to unpack the frames
    and call these methods with a specified signature. 
    """

    amq_chan = None # the amqp transport

    _peer_name = None # name send uses (exchange, routing_key)
    _chan_name = None # name recv uses (exchange, binding_key)

    # AMQP options
    exchange_type = 'direct' # do channels get to create exchanges?
    exchange_auto_delete = False
    exchange_durable = False
    queue_auto_delete = True
    queue_durable = False
    queue_exclusive = False

    queue_named = False # use routing_key name for p2p; else, unique
    queue_do_declare = True # toggle actually creating queue; a queue may
                            # be expected to already exist

    consumer_no_ack = True
    consumer_exclusive = False
    prefetch_size = 1
    prefetch_count = 1

    _consuming = False
    _channel_bind_cb = None

    immediate = False # don't use
    mandatory = False # don't use

    queue = None
    exchange = None


    def on_channel_open(self, amq_chan):
        """
        """
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
        print 'channel close'
        print code, text

    def do_config(self):
        """
        configure amqp
        implement in subclass 

        XXX only use existing exchange now
        """

    def bind(self, callback, name, shared_queue=False):
        """
        bind a channel to a name.
        a name [(exchange, routing_key)] is a member of a name space
        (exchange space; where the exchange is an exchange point)

        shared_queue option is injected here until the best place for it is
        clear.
        shared_queue means, use a common (probably already created) queue,
        or a unique/exclusive (auto_delete True) queue
        """
        if self._chan_name:
            raise ChannelError('Channel already bound') #?
        self._chan_name = name
        if shared_queue:
            self.queue = name[1]
        else:
            self.queue = ''
        #self._bind_callback = callback
        self.do_queue(callback)
        
    def on_bind(self):
        """
        on_transport_bind
        generic procedure that may be overridden in a subclass.
        """

    def connect(self, name, callback=None):
        """
        connect to a channel such that this protocol can send a message to
        it.

        sets the sending context of the channel protocol

        Some Channel Protocols just set the _peer_name statically; others
        may actually require interaction with the broker.
        """
        if self._peer_name:
            raise ChannelError('Channel already connected') # this is more "Client" than "Protocol"
        self._peer_name = name
        if callback:
            self._connect_callback = callback
            callback()

    def on_connect(self):
        """
        on_transport_connect ?
        generic procedure that may be overridden in a subclass.
        """

    def listen(self):
        """
        this ultimately starts a consumer.
        for a request-responsive server channel, listen allows connections
            to be made so accept can be called.
        for non-servers/simple receivers, listen starts a consumer so recv
            can be called.
        """
        self.on_listen() # may want to do some config before start_consumer

    def on_listen(self):
        """
        generic procedure that may be overridden in a subclass.
        """
        self._start_consumer()

    def do_queue(self, callback=None):
        if callback:
            self._channel_bind_cb = callback
        self.amq_chan.queue_declare(callback=self._on_queue_declare_ok,
                                    queue=self.queue,
                                    auto_delete=self.queue_auto_delete,
                                    durable=self.queue_durable)

    def _on_queue_declare_ok(self, frame):
        """
        reply contains queue name, number of messages and number of
        consumers

        when binding unique queues, get the name from here.
        """
        self.queue = frame.method.queue #XXX who really defines queue!!
        if not self._chan_name[1]:
            self._chan_name = (self._chan_name[0], self.queue) # XXX total HACK!!!
        self.amq_chan.queue_bind(callback=self._on_queue_bind_ok,
                                queue=self.queue,
                                exchange=self._chan_name[0],
                                routing_key=self._chan_name[1])

    def _on_queue_bind_ok(self, frame):
        """
        or queue_bind can be called with no wait, and we handle a channel
        exception in the case of an error

        nowait with consumer raises channel exception on error
        """
        if self._channel_bind_cb:
            self._channel_bind_cb()
        else:
            self._start_consumer()

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
        if self._consuming:
            raise #?
        consumer_tag = self.amq_chan.basic_consume(self._on_basic_deliver,
                                    queue=self.queue,
                                    no_ack=self.consumer_no_ack,
                                    exclusive=self.consumer_exclusive)
        self._consuming = True # XXX ?

    def _on_basic_deliver(self, chan, method_frame, header_frame, body):
        """
        delivery comes with the channel context, so this can easily be
        intercepted before it gets here
        """
        consumer_tag = method_frame.consumer_tag # use to further route?
        delivery_tag = method_frame.delivery_tag # use to ack
        redelivered = method_frame.redelivered
        exchange = method_frame.exchange
        routing_key = method_frame.routing_key
        
        # amqp specifics are handled here, and a mid-level event can be
        # raised here before the simple message_received. It's all about
        # funneling/organizing context to keep the endpoint handlers simple
        # and functional

        self.message_received(body)

    def send(self, data):
        """
        use when 'connected' to an endpoint (sending end of a channel)
        """
        self._send(self._peer_name, data)

    def sendto(self, name, data):
        """
        """

    def _send(self, name, data, headers={},
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
        exchange, routing_key = name
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

class _Bidirectional_Listener(BaseChannel):
    """
    the client methods of a listening channel that an application would
    invoke.

    the event handlers a listening channel need to handle for configuration
    and context/connection listening/acception/closing.
    """

    def _accept(self):
        """
        would the non-blocking interface actually return a new protocol? or
        just context for creating a new protocol?

        Any message received received by the chan in listening mode is 
        retrieved through this method (recv wouldn't not be used by the 
        listener)

        the bind step creates (or identifies an existing) queue and binds
        that queue to an exchange of specified name with a specified key.

        listen puts the protocol into a state where connections can be
        made.
        the consumer is started, and each received message is a new
        connection.
        when a connection is made (in the form a receiving a message) a new
        Channel Protocol instance is made that:
         - can receive the first message (and extract the peer address 
           to use as a send context)
         - can send a contextualized message (amqp headers)
        """

class _Bidirectional_accepted(BaseChannel):
    """
    services actual requests 

    use the listening channels amqp_chan to start a new consumer and to
    publish messages
    """

    def _on_basic_deliver(self, chan, method_frame, header_frame, body):
        """
        Not Implemented yet (can't receive yet) (only send)
        """

    def send(self, data):
        """
        use reply_to and correlation_id so each endpoint in a pair can
        converse in an arbitrary stream of messages.

        a listening Channel can establish a temp queue for interactions
        specific to this Node/Channel
        """
        message_type = "rr-data" # request-response data
        #reply_to = "%s,%s" % self._chan_name # encode the tuple 
        #correlation_id = uuid.uuid4().hex # move to lower level
        self._send(self._peer_name, data, 
                                message_type=message_type)
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

    consumer_exclusive = True

    def _on_basic_deliver(self, chan, method_frame, header_frame, body):
        message_type = header_frame.type
        # ensure proper type
        #self.message_received(body)
        reply_to = tuple(header_frame.reply_to.split(','))
        self._build_accepted_channel(reply_to, body)

    def _build_accepted_channel(self, peer_name, body):
        """
        only set send context (can't receive yet)
        """
        new_chan = _Bidirectional_accepted()
        new_chan.amq_chan = self.amq_chan #hack
        new_chan._peer_name = peer_name
        self.message_received((new_chan, body)) # XXX hack

    def connect(self, name, callback):
        """
        connect to a channel such that this protocol can send a message to
        it.

        sets the sending context of the channel protocol

        Some Channel Protocols just set the _peer_name statically; others
        may actually require interaction with the broker.
        """
        if self._peer_name:
            raise ChannelError('Channel already connected') # this is more "Client" than "Protocol"
        self._peer_name = name
        self.queue = ''
        self._chan_name = (self._peer_name[0], '')
        # bind to temp reply queue
        def set_reply_name():
            self._chan_name = (self._peer_name[0], self.queue)
            callback()
        self.do_queue(set_reply_name)
        #self._connect_callback = callback


    def send(self, data):
        """
        use reply_to and correlation_id so each endpoint in a pair can
        converse in an arbitrary stream of messages.

        a listening Channel can establish a temp queue for interactions
        specific to this Node/Channel
        """
        message_type = "rr-data" # request-response data
        reply_to = "%s,%s" % self._chan_name # encode the tuple 
        #correlation_id = uuid.uuid4().hex # move to lower level
        self._send(self._peer_name, data, 
                                message_type=message_type,
                                reply_to=reply_to)

class BidirectionalClient(BaseChannel):
    consumer_exclusive = True
    def connect(self, name, callback):
        """
        connect to a channel such that this protocol can send a message to
        it.

        sets the sending context of the channel protocol

        Some Channel Protocols just set the _peer_name statically; others
        may actually require interaction with the broker.
        """
        if self._peer_name:
            raise ChannelError('Channel already connected') # this is more "Client" than "Protocol"
        self._peer_name = name
        self.queue = ''
        self._chan_name = (self._peer_name[0], '')
        # bind to temp reply queue
        def set_reply_name():
            self._chan_name = (self._peer_name[0], self.queue)
            self._start_consumer()
            callback()
        self.do_queue(set_reply_name)
        #self._connect_callback = callback


    def send(self, data):
        """
        use reply_to and correlation_id so each endpoint in a pair can
        converse in an arbitrary stream of messages.

        a listening Channel can establish a temp queue for interactions
        specific to this Node/Channel
        """
        message_type = "rr-data" # request-response data
        reply_to = "%s,%s" % self._chan_name # encode the tuple 
        #correlation_id = uuid.uuid4().hex # move to lower level
        self._send(self._peer_name, data, 
                                message_type=message_type,
                                reply_to=reply_to)



class PointToPoint(BaseChannel):
    """
    recv receives the point 2 point message.
    accept does nothing.
    """


class PubSub(BaseChannel):
    """
    Endpoints do not directly interact.

    use a topic amqp exchange
    """

    #exchange_type = 'topic'


class SocketInterface(object):
    """
    Adapts an amqp channel.
    Adds a blocking layer using gevent Async Events to achieve a socket/0mq like behavior.
    """

    ch_proto = None

    def __init__(self, amq_chan, ch_proto):
        """
        amq_chan - instance of amqp channel from amqp client
        ch_proto instance of a ChannelProtocol
        """
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


    @classmethod
    def Socket(cls, amq_chan, ch_proto_type):
        """Main way to instantiate a Channel wrapping SocketInterface
        """
        ch_proto = ch_proto_type()
        ch_proto.on_channel_open(amq_chan)
        inst = cls(amq_chan, ch_proto)
        return inst

    def message_received(self, msg):
        self._receive_queue.put(msg)

    def accept(self):
        """
        use in server mode to get the next connection made to this
        listening channel

        for a listener, this still reads from the message received queue.

        create new channel proto with provided proto type and use same
        amq_chan to create a new consumer.
        """
        #self.ch_proto.accept()

        if not self._listening:
            raise ChannelError('Channel not listening')#?
        new_serv_ch_proto, body = self._receive_queue.get()

        new_chan = SocketInterface(self.amq_chan, new_serv_ch_proto)
        #new_chan.ch_proto.connect() # need
        new_chan._connected = 1 # hack
        new_chan.message_received(body) # hack
        return new_chan

    def bind(self, name):
        """
        Bind Channel to a name.

        Sets context for receiving peer/server.
        """
        result = event.AsyncResult()
        def bind_callback():
            result.set()

        self.ch_proto.bind(bind_callback, name, shared_queue=True)
        result.wait()
        self._bound = 1 
        return


    def close(self):
        """
        shutdown everything 
        cancel consumers, if any are active 
        close underlying amqp channel
        """

    def connect(self, name):
        """
        Connect to a Channel of name.

        Sets context for a sending peer/client.
        """
        result = event.AsyncResult()
        def connect_callback():
            result.set()

        self.ch_proto.connect(name, connect_callback)
        result.wait()
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
        if not self._bound or self._connected:
            raise ChannelError('Not in a state to listen')
        self.ch_proto.listen() # this should wait for the ok event
        self._connected = 1 # for servers too?
        self._listening = 1 # XXX need? listening state dictates accept/recv behavior

    def recv(self, *args):
        """
        """
        if not self._connected:
            raise ChannelError('Channel not connected')#?
        return self._receive_queue.get()

    def recv_into(self, callback):
        """
        """

    def send(self, data):
        """
        """
        self.ch_proto.send(data)

    def sendto(self, data, name):
        """
        """

