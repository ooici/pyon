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

The Channel Protocol doesn't
make a lot of sense for the 'interactive'
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
from pyon.util.log import log
from pika import BasicProperties
from gevent import queue as gqueue
from contextlib import contextmanager
from gevent.event import AsyncResult
from pyon.net.transport import AMQPTransport, NameTrio

class ChannelError(StandardError):
    """
    Exception raised for error using Channel Socket Interface.
    """

class ChannelClosedError(StandardError):
    """
    Denote activity on a closed channel (usually during shutdown).
    """

class ChannelShutdownMessage(object):
    """ Dummy object to unblock queues. """
    pass


class BaseChannel(object):

    _amq_chan                   = None      # underlying transport
    _close_callback             = None      # close callback to use when closing, not always set (used for pooling)
    _closed_error_callback      = None      # callback which triggers when the underlying transport closes with error
    _exchange                   = None      # exchange (too AMQP specific)

    # exchange related settings @TODO: these should likely come from config instead
    _exchange_type              = 'topic'
    _exchange_auto_delete       = True
    _exchange_durable           = False

    def __init__(self, transport=None, close_callback=None):
        """
        Initializes a BaseChannel instance.

        @param  transport       Underlying transport used for broker communication. Can be None, if so, will
                                use the AMQPTransport stateless singleton.
        @type   transport       BaseTransport
        @param  close_callback  The method to invoke when close() is called on this BaseChannel. May be left as None,
                                in which case close_impl() will be called. This expects to be a callable taking one
                                param, this channel instance.
        """
        self.set_close_callback(close_callback)
        self._transport = transport or AMQPTransport.get_instance()

    def set_close_callback(self, close_callback):
        """
        Sets a callback method to be called when this channel's close method is invoked.

        By default, if no callback is set on this channel, close_impl() is called instead.
        The close callback is chiefly used to pool channels in the Node.

        @param  close_callback  The callback method. Should be a callable taking one argument, this channel.
        """
        self._close_callback = close_callback

    def _ensure_amq_chan(self):
        """
        Ensures this Channel has been activated with the Node.
        """
        log.debug("BaseChannel._ensure_amq_chan (current: %s)", self._amq_chan is not None)
        if not self._amq_chan:
            raise ChannelError("No amq_chan attached")

    def _declare_exchange(self, exchange):
        """
        Performs an AMQP exchange declare.

        @param  exchange      The name of the exchange to use.
        @TODO: this really shouldn't exist, messaging layer should not make this declaration.  it will be provided.
               perhaps push into an ion layer derivation to help bootstrapping / getting started fast.
        """
        self._exchange = exchange
        assert self._exchange

        self._ensure_amq_chan()
        assert self._transport

        log.debug("Exchange declare: %s, TYPE %s, DUR %s AD %s", self._exchange, self._exchange_type,
                                                                 self._exchange_durable, self._exchange_auto_delete)

        self._transport.declare_exchange_impl(self._amq_chan,
                                              self._exchange,
                                              exchange_type=self._exchange_type,
                                              durable=self._exchange_durable,
                                              auto_delete=self._exchange_auto_delete)

    def attach_underlying_channel(self, amq_chan):
        """
        Attaches an AMQP channel and indicates this channel is now open.
        """
        self._amq_chan = amq_chan

    def get_channel_id(self):
        """
        Gets the underlying AMQP channel's channel identifier (number).

        @return Channel id, or None.
        """
        if not self._amq_chan:
            return None

        return self._amq_chan.channel_number

    def close(self):
        """
        Default close method.

        If a close callback was specified when creating this instance, it will call that,
        otherwise it calls close_impl.

        If created via a Node (99% likely), the Node will take care of
        calling close_impl for you at the proper time.
        """
        if self._close_callback:
            self._close_callback(self)
        else:
            self.close_impl()

    def close_impl(self):
        """
        Closes the AMQP connection.
        """
        log.debug("BaseChannel.close_impl (%d)", self.get_channel_id())
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
        """
        The node calls here to attach an open Pika channel.
        We attach our on_channel_close handler and then call attach_underlying_channel.
        """
        amq_chan.add_on_close_callback(self.on_channel_close)
        self.attach_underlying_channel(amq_chan)

    def set_closed_error_callback(self, callback):
        """
        Sets the closed error callback.

        This callback is called when the underlying transport closes early with an error.

        This is typically used for internal operations with the broker and will likely not be
        used by others.

        @param callback     The callback to trigger. Should take three parameters, this channel, the error code, and the error text.
        @returns            The former value of the closed error callback.
        """
        oldval = self._closed_error_callback
        self._closed_error_callback = callback
        return oldval

    @contextmanager
    def push_closed_error_callback(self, callback):
        """
        Context manager based approach to set_closed_error_callback.
        """
        cur_cb = self.set_closed_error_callback(callback)
        try:
            yield callback
        finally:
            self.set_closed_error_callback(cur_cb)

    def on_channel_close(self, code, text):
        """
        Callback for when the Pika channel is closed.
        """
        logmeth = log.debug
        if not (code == 0 or code == 200):
            logmeth = log.error
        logmeth("BaseChannel.on_channel_close\n\tchannel number: %d\n\tcode: %d\n\ttext: %s", self._amq_chan.channel_number, code, text)

        # make callback if it exists!
        if not (code == 0 or code == 200) and self._closed_error_callback:
            # run in try block because this can shutter the entire connection
            try:
                self._closed_error_callback(self, code, text)
            except Exception, e:
                log.warn("Closed error callback caught an exception: %s", str(e))

    def _sync_call(self, func, cb_arg, *args, **kwargs):
        """
        Functionally similar to the generic blocking_cb but with error support that's Channel specific.
        """
        ar = AsyncResult()

        def cb(*args, **kwargs):
            ret = list(args)
            if len(kwargs): ret.append(kwargs)
            ar.set(ret)

        def eb(ch, code, text):
            ar.set(ChannelError("_sync_call could not complete due to an error (%d): %s" % (code, text)))

        kwargs[cb_arg] = cb
        with self.push_closed_error_callback(eb):
            func(*args, **kwargs)
            ret_vals = ar.get()

        if isinstance(ret_vals, ChannelError):
            raise ret_vals

        if len(ret_vals) == 0:
            return None
        elif len(ret_vals) == 1:
            return ret_vals[0]
        return tuple(ret_vals)

class SendChannel(BaseChannel):
    """
    A channel that can only send.
    """
    _send_name = None           # name that this channel is sending to - tuple (exchange, routing_key)

    def connect(self, name):
        """
        Sets up this channel to send to a name.
        @param  name    The name this channel should send to. Should be a NameTrio.
        """
        log.debug("SendChannel.connect: %s", name)

        self._send_name = name
        self._exchange = name.exchange

    def send(self, data, headers=None):
        log.debug("SendChannel.send")
        self._send(self._send_name, data, headers=headers)

    def _send(self, name, data, headers=None):
        log.debug("SendChannel._send\n\tname: %s\n\tdata: %s\n\theaders: %s", name, data, headers)
        exchange    = name.exchange
        routing_key = name.binding    # uses "_queue" if binding not explictly defined
        headers = headers or {}
        props = BasicProperties(headers=headers)

        self._ensure_amq_chan()

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
    _recv_binding   = None      # binding this queue is listening on (set via _bind)

    # queue defaults
    _queue_auto_delete  = False
    _queue_exclusive    = False
    _queue_durable      = False

    # consumer defaults
    _consumer_exclusive = False
    _consumer_no_ack    = False     # endpoint layers do the acking as they call recv()

    def __init__(self, name=None, binding=None, **kwargs):
        """
        Initializer for a recv channel.

        You may set the receiving name and binding here if you wish, otherwise they will
        be set when you call setup_listener.
        """
        self._recv_queue = gqueue.Queue()

        # set recv name and binding if given
        assert name is None or isinstance(name, tuple)
        self._recv_name = name
        self._recv_binding = binding

        self._setup_listener_called = False

        BaseChannel.__init__(self, **kwargs)

    def setup_listener(self, name=None, binding=None):
        """
        Prepares this receiving channel for listening for messages.

        Calls, in order:
        - _declare_exchange
        - _declare_queue
        - _bind

        Name must be a NameTrio. If queue is None, the broker will generate a name e.g. "amq-RANDOMSTUFF".
        Binding may be left none and will use the queue name by default.

        Sets the _setup_listener_called internal flag, so if this method is called multiple times, such as in the case
        of a pooled channel type, it will not run setup again. Pay attention to this in your override of this method.

        @param  name        A tuple of (exchange, queue). Queue may be left None for the broker to generate one.
        @param  binding     If not set, uses name.
        """
        log.debug('Setup_listener name: %s', name)
        name        = name or self._recv_name
        exchange    = name.exchange
        queue       = name.queue

        log.debug("RecvChannel.setup_listener, exchange %s, queue %s, binding %s", exchange, queue, binding)
        if self._setup_listener_called:
            log.debug("setup_listener already called for this channel")
            return

        # only reset the name if it was passed in
        if name != self._recv_name:
            if isinstance(name, NameTrio):
                self._recv_name = name
            else:
                self._recv_name = NameTrio(exchange, queue, binding)

        self._declare_exchange(exchange)
        queue   = self._declare_queue(queue)
        binding = binding or self._recv_binding or self._recv_name.binding or queue      # last option should only happen in the case of anon-queue

        self._bind(binding)

        self._setup_listener_called = True

    def destroy_listener(self):
        """
        Tears down this channel.

        For performance reasons, only calls destroy queue. Derived implementations that want to tear down the
        binding should override this method.
        """
        #self._destroy_binding()
        self._destroy_queue()

    def _destroy_binding(self):
        """
        Deletes the binding from the listening queue.
        """
        assert self._recv_name# and isinstance(self._recv_name, tuple) and self._recv_name[1] and self._recv_binding

        self._ensure_amq_chan()
        assert self._transport

        self._transport.unbind_impl(self._amq_chan,
                                    exchange=self._recv_name.exchange,
                                    queue=self._recv_name.queue,
                                    binding=self._recv_binding)

    def _destroy_queue(self):
        """
        You should only call this if you want to delete the queue. Even so, you must know you are
        the only one on it - there appears to be no mechanic for determining if anyone else is listening.
        """
        assert self._recv_name# and isinstance(self._recv_name, tuple) and self._recv_name[1]

        self._ensure_amq_chan()
        assert self._transport

        log.info("Destroying listener for queue %s", self._recv_name)
        self._transport.delete_queue_impl(self._amq_chan,
                                          queue=self._recv_name.queue)

    def start_consume(self):
        """
        Starts consuming messages.

        setup_listener must have been called first.
        """
        log.debug("RecvChannel.start_consume")
        if self._consuming:
            raise ChannelError("Already consuming")

        if self._consumer_tag and self._queue_auto_delete:
            log.warn("Attempting to start consuming on a queue that may have been auto-deleted")

        self._ensure_amq_chan()

        self._consumer_tag = self._amq_chan.basic_consume(self._on_deliver,
                                                          queue=self._recv_name.queue,
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
            raise ChannelError("Not consuming")

        if self._queue_auto_delete:
            log.debug("Autodelete is on, this will destroy this queue: %s", self._recv_name.queue)

        self._ensure_amq_chan()

        self._sync_call(self._amq_chan.basic_cancel, 'callback', self._consumer_tag)
        self._consuming = False

    def recv(self):
        """
        Pulls a message off the queue, will block if there are none.
        Typically done by the EndpointUnit layer. Should ack the message there as it is "taking ownership".
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
        log.debug("RecvChannel.close_impl (%d): consuming %s", self.get_channel_id(), self._consuming)

        if self._consuming:
            self.stop_consume()

        self._recv_queue.put(ChannelShutdownMessage())

        BaseChannel.close_impl(self)

    def _declare_queue(self, queue):

        # prepend xp name in the queue for anti-clobbering
        if queue and not self._recv_name.exchange in queue:
            queue = ".".join([self._recv_name.exchange, queue])
            log.debug('Auto-prepending exchange to queue name for anti-clobbering: %s', queue)

        self._ensure_amq_chan()

        log.debug("RecvChannel._declare_queue: %s", queue)
        queue_name = self._transport.declare_queue_impl(self._amq_chan,
                                                        queue=queue or '',
                                                        auto_delete=self._queue_auto_delete,
                                                        durable=self._queue_durable)

        # save the new recv_name if our queue name differs (anon queue via '', or exchange prefixing)
        if queue_name != self._recv_name.queue:
            self._recv_name = NameTrio(self._recv_name.exchange, queue_name, self._recv_name.binding)

        return self._recv_name.queue

    def _bind(self, binding):
        log.debug("RecvChannel._bind: %s", binding)
        assert self._recv_name and self._recv_name.queue

        self._ensure_amq_chan()

        self._transport.bind_impl(self._amq_chan,
                                  exchange=self._recv_name.exchange,
                                  queue=self._recv_name.queue,
                                  binding=binding)

        self._recv_binding = binding

    def _on_deliver(self, chan, method_frame, header_frame, body):
        log.debug("RecvChannel._on_deliver")

        consumer_tag = method_frame.consumer_tag # use to further route?
        delivery_tag = method_frame.delivery_tag # use to ack
        redelivered = method_frame.redelivered
        exchange = method_frame.exchange
        routing_key = method_frame.routing_key

        # put body, headers, delivery tag (for acking) in the recv queue
        self._recv_queue.put((body, header_frame.headers, delivery_tag))

    def ack(self, delivery_tag):
        """
        Acks a message using the delivery tag.
        Should be called by the EP layer.
        """
        log.debug("RecvChannel.ack: %s", delivery_tag)
        self._ensure_amq_chan()
        self._amq_chan.basic_ack(delivery_tag)

    def reject(self, delivery_tag, requeue=False):
        """
        Rejects a message using the delivery tag.
        Should be called by the EP layer.
        """
        log.debug("RecvChannel.reject: %s", delivery_tag)
        self._ensure_amq_chan()
        self._sync_call(self._amq_chan.basic_reject, 'callback', delivery_tag, requeue=requeue)

class PublisherChannel(SendChannel):
    def __init__(self, close_callback=None):
        self._declared = False
        SendChannel.__init__(self, close_callback=close_callback)

    def send(self, data, headers=None):
        if not self._declared:
            assert self._send_name and self._send_name.exchange
            self._declare_exchange(self._send_name.exchange)
            self._declared = True
        SendChannel.send(self, data, headers=headers)

class BidirClientChannel(SendChannel, RecvChannel):
    """
    This should be pooled for the receiving side?

    @TODO: As opposed to current endpoint scheme - no need to spawn a listening greenlet simply to loop on recv(),
    you can use this channel to send first then call recieve linearly, no need for greenletting.
    """
    _consumer_exclusive = True

    def _send(self, name, data, headers=None):
        """
        Override of internal send method.
        Sets reply-to ION level header. (we don't use AMQP if we can avoid it)
        """
        if headers:
            headers = headers.copy()
        else:
            headers = {}

        if not 'reply-to' in headers:
            headers['reply-to'] = "%s,%s" % (self._recv_name.exchange, self._recv_name.queue)

        SendChannel._send(self, name, data, headers=headers)

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
        self._ensure_amq_chan()
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
        send_name = NameTrio(tuple(msg[1].get('reply-to').split(',')))    # @TODO: stringify is not the best
        ch = self.BidirAcceptChannel()
        ch.attach_underlying_channel(amq_chan)
        ch.connect(send_name)
        return ch
