#!/usr/bin/env python

"""Provides the communication layer above channels."""

from pyon.core import bootstrap, exception
from pyon.core.bootstrap import CFG, IonObject
from pyon.core.exception import ExceptionFactory, IonException, BadRequest
from pyon.net.channel import ChannelClosedError, PublisherChannel, ListenChannel, SubscriberChannel, ServerChannel, BidirClientChannel
from pyon.core.interceptor.interceptor import Invocation, process_interceptors
from pyon.util.containers import get_ion_ts
from pyon.util.log import log
from pyon.net.transport import NameTrio, BaseTransport

from gevent import event, coros
from gevent.timeout import Timeout
from zope import interface
import uuid
import time
import inspect
import traceback
import sys
from pyon.util.sflow import SFlowManager
from types import MethodType
import threading

# create special logging category for RPC message tracking
import logging
rpclog = logging.getLogger('rpc')

class EndpointError(StandardError):
    pass


class EndpointUnit(object):
    """
    A unit of conversation or one-way messaging.

    An EndpointUnit is produced by Endpoints and exist solely for the duration of one
    conversation. It can be thought of as a telephone call.

    In the case of request-response, an EndpointUnit is created on each side of the
    conversation, and exists for the life of that request and response. It is then
    torn down.

    You typically do not need to deal with these objects - they are created for you
    by an BaseEndpoint-derived class and encapsulate the "business-logic" of the communication,
    on top of the Channel layer which is the "transport" aka AMQP or otherwise.
    """

    channel = None
    _endpoint = None
    _interceptors = None

    def __init__(self, endpoint=None, interceptors=None):
        self._endpoint = endpoint
        self.interceptors = interceptors

    @property
    def interceptors(self):
        if self._interceptors is not None:
            return self._interceptors

        assert self._endpoint, "No endpoint attached"
        return self._endpoint.interceptors

    @interceptors.setter
    def interceptors(self, value):
        self._interceptors = value

    def attach_channel(self, channel):
        self.channel = channel

    def _build_invocation(self, **kwargs):
        """
        Builds an Invocation instance to be used by the interceptor stack.
        This method exists so we can override it in derived classes (ex with a process).
        """
        inv = Invocation(**kwargs)
        return inv

    def _message_received(self, msg, headers):
        """
        Entry point for received messages in below channel layer.

        This method should not be overridden unless you are familiar with how the interceptor stack and
        friends work!
        """
        return self.message_received(msg, headers)

    def intercept_in(self, msg, headers):
        """
        Builds an invocation and runs interceptors on it, direction: in.

        This is called manually by the endpoint layer at receiving points (client recv, get_one/listen etc).

        @returns    A 2-tuple of message, headers after going through the interceptors.
        """
        inv = self._build_invocation(path=Invocation.PATH_IN,
                                     message=msg,
                                     headers=headers)
        inv_prime = self._intercept_msg_in(inv)
        new_msg = inv_prime.message
        new_headers = inv_prime.headers

        return new_msg, new_headers

    def _intercept_msg_in(self, inv):
        """
        Performs interceptions of incoming messages.
        Override this to change what interceptor stack to go through and ordering.

        @param inv      An Invocation instance.
        @returns        A processed Invocation instance.
        """
        inv_prime = process_interceptors(self.interceptors["message_incoming"] if "message_incoming" in self.interceptors else [], inv)
        return inv_prime

    def message_received(self, msg, headers):
        """
        """
        pass

    def send(self, msg, headers=None, **kwargs):
        """
        Public send method.
        Calls _build_msg (_build_header and _build_payload), then _send which puts it through the Interceptor stack(s).

        @param  msg         The message to send. Will be passed into _build_payload. You may modify the contents there.
        @param  headers     Optional headers to send. Will override anything produced by _build_header.
        @param  kwargs      Passed through to _send.
        """
        _msg, _header = self._build_msg(msg, headers)
        if headers: _header.update(headers)
        return self._send(_msg, _header, **kwargs)

    def _send(self, msg, headers=None, **kwargs):
        """
        Handles the send interaction with the Channel.

        Override this method to get custom behavior of how you want your endpoint unit to operate.
        Kwargs passed into send will be forwarded here. They are not used in this base method.

        @returns    A 2-tuple of the message body sent and the message headers sent. These are
                    post-interceptor. Derivations will likely override the return value.
        """
        new_msg, new_headers = self.intercept_out(msg, headers)
        self.channel.send(new_msg, new_headers)

        return new_msg, new_headers

    def intercept_out(self, msg, headers):
        """
        Builds an invocation and runs interceptors on it, direction: out.

        This is called manually by the endpoint layer at sending points.

        @returns    A 2-tuple of message, headers after going through the interceptors.
        """
        inv = self._build_invocation(path=Invocation.PATH_OUT,
            message=msg,
            headers=headers)
        inv_prime = self._intercept_msg_out(inv)
        new_msg = inv_prime.message
        new_headers = inv_prime.headers

        return new_msg, new_headers

    def _intercept_msg_out(self, inv):
        """
        Performs interceptions of outgoing messages.
        Override this to change what interceptor stack to go through and ordering.

        @param  inv     An Invocation instance.
        @returns        A processed Invocation instance.
        """
        inv_prime = process_interceptors(self.interceptors["message_outgoing"] if "message_outgoing" in self.interceptors else [], inv)
        return inv_prime

    def close(self):

        if self.channel is not None:
            ev = self.channel.close()
            if not ev.wait(timeout=3):
                log.warn("Channel (%s) close did not respond in time, giving up", self.channel.get_channel_id())

    def _build_header(self, raw_msg, raw_headers):
        """
        Assembles the headers of a message from the raw message's content or raw headers.
        
        Any headers passed in here are strictly for reference. Headers set in there will take
        precedence and override any headers with the same key.
        """
        return {'ts':get_ion_ts()}

    def _build_payload(self, raw_msg, raw_headers):
        """
        Assembles the payload of a message from the raw message's content.

        @TODO will this be used? seems unlikely right now.
        """
        return raw_msg

    def _build_msg(self, raw_msg, raw_headers):
        """
        Builds a message (headers/payload) from the raw message's content.
        You typically do not need to override this method, but override the _build_header
        and _build_payload methods.

        @returns A 2-tuple of payload, headers
        """
        header = self._build_header(raw_msg, raw_headers)
        payload = self._build_payload(raw_msg, raw_headers)

        return payload, header

class BaseEndpoint(object):
    """
    An Endpoint is an object capable of communication with one or more other Endpoints.

    You should not use this BaseEndpoint base class directly, but one of the derived types such as
    RPCServer, Publisher, Subscriber, etc.

    An BaseEndpoint creates EndpointUnits, which are instances of communication/conversation,
    like a Factory.
    """
    endpoint_unit_type = EndpointUnit
    channel_type = BidirClientChannel
    node = None     # connection to the broker, basically

    # Endpoints
    # TODO: Make weakref or replace entirely
    endpoint_by_name = {}
    _interceptors = None

    def __init__(self, node=None, transport=None):

        self.node = node
        self._transport = transport

#        # @TODO: MOVE THIS
#        if name in self.endpoint_by_name:
#            self.endpoint_by_name[name].append(self)
#        else:
#            self.endpoint_by_name[name] = [self]

    @classmethod
    def _get_container_instance(cls):
        """
        Helper method to return the singleton Container.instance.
        This method helps single responsibility of _ensure_node and makes testing much easier.

        We have to late import Container because Container depends on ProcessRPCServer in this file.

        This is a classmethod so we can use it from other places.
        """
        from pyon.container.cc import Container
        return Container.instance

    def _ensure_node(self):
        """
        Makes sure a node exists in this endpoint, and if it can, pulls from the Container singleton.
        This method is automatically called before accessing the node in both create_endpoint and in
        ListeningBaseEndpoint.listen.
        """

        if not self.node:
            container_instance = self._get_container_instance()
            if container_instance:
                self.node = container_instance.node
            else:
                raise EndpointError("Cannot pull node from Container.instance and no node specified")

    @property
    def interceptors(self):
        if self._interceptors is not None:
            return self._interceptors

        assert self.node, "No node attached"
        return self.node.interceptors

    @interceptors.setter
    def interceptors(self, value):
        self._interceptors = value

    def create_endpoint(self, to_name=None, existing_channel=None, **kwargs):
        """
        @param  to_name     Either a string or a 2-tuple of (exchange, name)
        """
        if existing_channel:
            ch = existing_channel
        else:
            self._ensure_node()
            ch = self._create_channel()

        e = self.endpoint_unit_type(endpoint=self, **kwargs)
        e.attach_channel(ch)

        return e

    def _create_channel(self, transport=None):
        """
        Creates a channel, used by create_endpoint.

        Can pass additional kwargs in to be passed through to the channel provider.
        """
        return self.node.channel(self.channel_type, transport=transport)

    def close(self):
        """
        To be defined by derived classes. Cleanup any resources here, such as channels being open.
        """
        pass

class SendingBaseEndpoint(BaseEndpoint):
    def __init__(self, node=None, to_name=None, name=None, transport=None):
        BaseEndpoint.__init__(self, node=node, transport=transport)

        if name:
            log.warn("SendingBaseEndpoint: name param is deprecated, please use to_name instead")
        self._send_name = to_name or name

        # ensure NameTrio
        if not isinstance(self._send_name, NameTrio):
            self._send_name = NameTrio(bootstrap.get_sys_name(), self._send_name)   # if send_name is a tuple it takes precedence

    def create_endpoint(self, to_name=None, existing_channel=None, **kwargs):
        e = BaseEndpoint.create_endpoint(self, to_name=to_name, existing_channel=existing_channel, **kwargs)

        name = to_name or self._send_name
        assert name

        # ensure NameTrio
        if not isinstance(name, NameTrio):
            name = NameTrio(bootstrap.get_sys_name(), name)     # if name is a tuple it takes precedence

        e.channel.connect(name)
        return e

    def _create_channel(self, transport=None):
        """
        Overrides the BaseEndpoint create channel to supply a transport if our send_name is one.
        """
        if transport is None:
            if isinstance(self._send_name, BaseTransport):
                transport = self._send_name
            elif self._transport is not None:
                transport = self._transport

        return BaseEndpoint._create_channel(self, transport=transport)


class ListeningBaseEndpoint(BaseEndpoint):
    """
    Establishes channel type for a host of derived, listen/react endpoint factories.
    """
    channel_type = ListenChannel

    class MessageObject(object):
        """
        Received message wrapper.

        Contains a body, headers, and a delivery_tag. Internally used by listen, the
        standard method used by ListeningBaseEndpoint, but will be returned to you
        if you use get_one_msg or get_n_msgs. If using the latter, you are responsible
        for calling ack or reject.

        make_body calls the endpoint's interceptor incoming stack - this may potentially
        raise an IonException in normal program flow. If this happens, the body/headers
        attributes will remain None and the error attribute will be set. Calling route()
        will be a no-op, but ack/reject work.
        """
        def __init__(self, msgtuple, ackmethod, rejectmethod, e):
            """
            Creates a MessageObject.

            @param  msgtuple        A 3-tuple of (body, headers, delivery_tag)
            @param  ackmethod       A callable to call to ack a message.
            @param  rejectmethod    A callable to call to reject a message.
            @param  e               An EndpointUnit.
            """
            self.ackmethod      = ackmethod
            self.rejectmethod   = rejectmethod
            self.endpoint       = e

            self.raw_body, self.raw_headers, self.delivery_tag = msgtuple
            self.body           = None
            self.headers        = None
            self.error          = None

        def make_body(self):
            """
            Runs received raw message through the endpoint's interceptors.
            """
            try:
                self.body, self.headers = self.endpoint.intercept_in(self.raw_body, self.raw_headers)
            except IonException as ex:
                log.info("MessageObject.make_body raised an error: \n%s", traceback.format_exc(ex))
                self.error = ex

        def ack(self):
            """
            Passthrough to underlying channel's ack.

            Must call this if using get_one_msg/get_n_msgs.
            """
            self.ackmethod(self.delivery_tag)

        def reject(self, requeue=False):
            """
            Passthrough to underlying channel's reject.

            Must call this if using get_one_msg/get_n_msgs.
            """
            self.rejectmethod(self.delivery_tag, requeue=requeue)

        def route(self):
            """
            Call default endpoint's _message_received, where business logic takes place.

            For instance, a Subscriber would call the registered callback, or an RPCServer would
            call the Service's operation.

            You are likely not to use this if using get_one_msg/get_n_msgs.
            """
            if self.error is not None:
                log.info("Refusing to route a MessageObject with an error")
                return

            self.endpoint._message_received(self.body, self.headers)

    def __init__(self, node=None, name=None, from_name=None, binding=None, transport=None):
        BaseEndpoint.__init__(self, node=node, transport=transport)

        if name:
            log.warn("ListeningBaseEndpoint: name param is deprecated, please use from_name instead")
        self._recv_name = from_name or name

        # ensure NameTrio
        if not isinstance(self._recv_name, NameTrio):
            self._recv_name = NameTrio(bootstrap.get_sys_name(), self._recv_name, binding)   # if _recv_name is tuple it takes precedence

        self._ready_event = event.Event()
        self._binding = binding
        self._chan = None

    def _create_channel(self, **kwargs):
        """
        Overrides the BaseEndpoint create channel to supply a transport if our recv name is one.
        """
        if isinstance(self._recv_name, BaseTransport):
            kwargs.update({'transport': self._recv_name})
        elif self._transport is not None:
            kwargs.update({'transport': self._transport})

        return BaseEndpoint._create_channel(self, **kwargs)

    def get_ready_event(self):
        """
        Returns an async event you can .wait() on.
        Used to indicate when listen() is ready to start listening.
        """
        return self._ready_event

    def _setup_listener(self, name, binding=None):
        self._chan.setup_listener(name, binding=binding)

    def listen(self, binding=None, thread_name=None):
        """
        Main driving method for ListeningBaseEndpoint.

        Meant to be spawned in a greenlet. This method creates/sets up a channel to listen,
        starts listening, and consumes messages in a loop until the Endpoint is closed.
        """

        if thread_name:
            threading.current_thread().name = thread_name   # monkeypatched to greenlet name

        self.prepare_listener(binding=binding)

        # notify any listeners of our readiness
        self._ready_event.set()

        while True:
            m = None
            try:
                m = self.get_one_msg()
                m.route()       # call default handler

            except ChannelClosedError as ex:
                break
            finally:
                # ChannelClosedError will go into here too, so make sure we have a message object to ack with
                if m is not None:
                    m.ack()

    def prepare_listener(self, binding=None):
        """
        Creates a channel, prepares it, and begins consuming on it.

        Used by listen.
        """
        self.initialize(binding=binding)
        self.activate()

    def initialize(self, binding=None):
        """
        Creates a channel and prepares it for use.

        After this, the endpoint is in the ready state.
        """
        binding = binding or self._binding or self._recv_name.binding

        self._ensure_node()
        self._chan = self._create_channel()

        # @TODO this does not feel right
        if isinstance(self._recv_name, BaseTransport):
            self._recv_name.setup_listener(binding, self._setup_listener)
            self._chan._recv_name = self._recv_name
        else:
            self._setup_listener(self._recv_name, binding=binding)

    def activate(self):
        """
        Begins consuming.

        You must have called initialize first.
        """
        assert self._chan
        self._chan.start_consume()

    def deactivate(self):
        """
        Stops consuming.

        You must have called initialize and activate first.
        """
        assert self._chan
        self._chan.stop_consume()       # channel will yell at you if this is invalid

    def _get_n_msgs(self, num=1, timeout=None):
        """
        Internal method to accept n messages, create MessageObject wrappers, return them.

        INBOUND INTERCEPTORS ARE PROCESSED HERE. If the Interceptor stack throws an IonException,
        the response will be sent immediatly and the MessageObject returned to you will not have
        body/headers set and will have error set. You should expect to check body/headers or error.
        """
        assert self._chan, "_get_n_msgs: needs the endpoint to have been initialized"

        mos = []
        newch = self._chan.accept(n=num, timeout=timeout)
        qsize = newch._recv_queue.qsize()
        if qsize == 0:
            self._chan.exit_accept()
            return []

        for x in xrange(newch._recv_queue.qsize()):
            mo = self.MessageObject(newch.recv(), newch.ack, newch.reject, self.create_endpoint(existing_channel=newch))
            mo.make_body()      # puts through EP interceptors
            mos.append(mo)
            log_message("MESSAGE RECV >>> RPC-request", mo.raw_body, mo.raw_headers, self._recv_name, mo.delivery_tag, is_send=False)

        return mos

    def get_one_msg(self, timeout=None):
        """
        Receives one message.

        Blocks until one message is received, or the optional timeout is reached.

        INBOUND INTERCEPTORS ARE PROCESSED HERE. If the Interceptor stack throws an IonException,
        the response will be sent immediatly and the MessageObject returned to you will not have
        body/headers set and will have error set. You should expect to check body/headers or error.

        @raises ChannelClosedError  If the channel has been closed.
        @raises Timeout             If no messages available when timeout is reached.
        @returns                    A MessageObject.
        """
        mos = self._get_n_msgs(num=1, timeout=timeout)
        return mos[0]

    def get_n_msgs(self, num, timeout=None):
        """
        Receives num messages.

        INBOUND INTERCEPTORS ARE PROCESSED HERE. If the Interceptor stack throws an IonException,
        the response will be sent immediatly and the MessageObject returned to you will not have
        body/headers set and will have error set. You should expect to check body/headers or error.

        Blocks until all messages received, or the optional timeout is reached.
        @raises ChannelClosedError  If the channel has been closed.
        @raises Timeout             If no messages available when timeout is reached.
        @returns                    A list of MessageObjects.
        """
        return self._get_n_msgs(num, timeout=timeout)

    def get_all_msgs(self, timeout=None):
        """
        Receives all available messages on the queue.

        WARNING: If the queue is not exclusive, there is a possibility this method behaves incorrectly.
        You should always pass a timeout to this method.

        Blocks until all messages received, or the optional timeout is reached.
        @raises ChannelClosedError  If the channel has been closed.
        @raises Timeout             If no messages available when timeout is reached.
        @returns                    A list of MessageObjects.
        """
        n, _ = self.get_stats()
        return self._get_n_msgs(n, timeout=timeout)

    def close(self):
        BaseEndpoint.close(self)
        ev = self._chan.close()

        if not ev.wait(timeout=3):
            log.warn("Listen channel (%s) close did not respond in time, giving up", self._chan.get_channel_id())

    def get_stats(self):
        """
        Returns a tuple of the form (# ready messages, # of consumers).

        This endpoint must have been initialized in order to have a valid queue
        to work on.

        Passes down to the channel layer to get this info.
        """
        if not self._chan:
            raise EndpointError("No channel attached")

        return self._chan.get_stats()


#
# PUB/SUB
#

class PublisherEndpointUnit(EndpointUnit):
    pass

class Publisher(SendingBaseEndpoint):
    """
    Simple publisher sends out broadcast messages.
    """

    endpoint_unit_type = PublisherEndpointUnit
    channel_type = PublisherChannel

    def __init__(self, **kwargs):
        self._pub_ep = None
        SendingBaseEndpoint.__init__(self, **kwargs)

    def publish(self, msg, to_name=None, headers=None):
        if to_name is not None:
            if not isinstance(to_name, NameTrio):
                to_name = NameTrio(bootstrap.get_sys_name(), to_name)   # ensure NT before

        # only use the cached pub_ep if to_name is None
        ep = None
        if to_name is None:

            # we may have to create the cached ep
            if self._pub_ep is None:

                # send_name better have been specified in the constructor then
                if self._send_name is None:
                    raise EndpointError("Publisher has no address to send to, specify to_name on publish or send_name in initializer")

                self._pub_ep = self.create_endpoint(self._send_name)
                self._pub_ep.channel.connect(self._send_name)

            ep = self._pub_ep
        else:
            ep = self.create_endpoint(to_name)
            ep.channel.connect(to_name)

        ep.send(msg, headers)
        if ep != self._pub_ep:
            ep.close()

    def close(self):
        """
        Closes the opened publishing channel, if we've opened it previously.
        """
        if self._pub_ep:
            self._pub_ep.close()


class SubscriberEndpointUnit(EndpointUnit):
    """
    @TODO: Should have routing mechanics, possibly shared with other listener endpoint types
    """
    def __init__(self, callback, **kwargs):
        EndpointUnit.__init__(self, **kwargs)
        self.set_callback(callback)

    def set_callback(self, callback):
        """
        Sets the callback to be used by this SubscriberEndpointUnit when a message is received.
        """
        self._callback = callback

    def message_received(self, msg, headers):
        EndpointUnit.message_received(self, msg, headers)
        assert self._callback, "No callback provided, cannot route subscribed message"

        self._make_routing_call(self._callback, None, msg, headers)

    def _make_routing_call(self, call, timeout, *op_args, **op_kwargs):
        """
        Calls into the routing object.

        May be overridden at a lower level.
        """
        # @TODO respect timeout
        return call(*op_args, **op_kwargs)


class Subscriber(ListeningBaseEndpoint):
    """
    Subscribes to messages.

    The Subscriber is flexible in that it lets you subscribe to a known queue, or an anonymous
    queue with a binding, but you must make sure to use the correct calls to set that up.

    Known queue:  name=(xp, thename), binding=None
    New queue:    name=None or (xp, None), binding=your binding
    """

    endpoint_unit_type = SubscriberEndpointUnit
    channel_type = SubscriberChannel

    def __init__(self, callback=None, **kwargs):
        """
        @param  callback should be a callable with two args: msg, headers
        """
        self._callback = callback
        ListeningBaseEndpoint.__init__(self, **kwargs)

    def create_endpoint(self, **kwargs):
        return ListeningBaseEndpoint.create_endpoint(self, callback=self._callback, **kwargs)

    def __str__(self):
        return "Subscriber: recv_name: %s, cb: %s" % (str(self._recv_name), str(self._callback))

#
# BIDIRECTIONAL ENDPOINTS
#
class BidirectionalEndpointUnit(EndpointUnit):
    pass


class BidirectionalListeningEndpointUnit(EndpointUnit):
    pass

#
#  REQ / RESP (and RPC)
#


class RequestEndpointUnit(BidirectionalEndpointUnit):
    def _get_response(self, conv_id, timeout):
        """
        Gets a response message to the conv_id within the given timeout.

        @raises Timeout
        @return A 2-tuple of the received message body and received message headers.
        """
        with Timeout(seconds=timeout):

            # start consuming
            self.channel.start_consume()

            # consume in a loop: if we get a message not intended for us, we discard
            # it and consume again
            while True:
                rmsg, rheaders, rdtag = self.channel.recv()
                try:
                    nm, nh = self.intercept_in(rmsg, rheaders)
                finally:
                    self.channel.ack(rdtag)

                # is this the message we are looking for?
                if 'conv-id' in nh and nh['conv-id'] == conv_id:
                    return nm, nh   # breaks loop
                else:
                    log.warn("Discarding unknown message, likely from a previous timed out request (conv-id: %s, seq: %s, perf: %s)", nh.get('conv-id', "no conv id"), nh.get('conv-seq', 'no conv seq'), nh.get('performative', 'None'))

    def _send(self, msg, headers=None, **kwargs):

        # could have a specified timeout in kwargs
        if 'timeout' in kwargs and kwargs['timeout'] is not None:
            timeout = kwargs['timeout']
        else:
            timeout = CFG.get_safe('endpoint.receive.timeout', 10)

        # we have a timeout, update reply-by header
        headers['reply-by'] = str(int(headers['ts']) + timeout * 1000)
        self.channel.setup_listener(NameTrio(self.channel._send_name.exchange)) # anon queue
        # call base send, and get back the headers it ended up building and sending
        # we extract the conv-id so we can tell the listener what is valid.
        _, sent_headers = BidirectionalEndpointUnit._send(self, msg, headers=headers)

        try:
            result_data, result_headers = self._get_response(sent_headers['conv-id'], timeout)
        except Timeout:
            raise exception.Timeout('Request timed out (%d sec) waiting for response from %s, conv %s' % (timeout, str(self.channel._send_name), sent_headers['conv-id']))
        return result_data, result_headers

    def _build_header(self, raw_msg, raw_headers):
        """
        Sets headers common to Request-Response patterns, non-ion-specific.
        """
        headers = BidirectionalEndpointUnit._build_header(self, raw_msg, raw_headers)
        headers['performative'] = 'request'
        if self.channel and self.channel._send_name and isinstance(self.channel._send_name, NameTrio):
            headers['receiver'] = "%s,%s" % (self.channel._send_name.exchange, self.channel._send_name.queue)   # @TODO correct?

        return headers


class RequestResponseClient(SendingBaseEndpoint):
    """
    Sends a request, waits for a response.
    """
    endpoint_unit_type = RequestEndpointUnit

    def request(self, msg, headers=None, timeout=None):
        e = self.create_endpoint(self._send_name)
        try:
            retval, headers = e.send(msg, headers=headers, timeout=timeout)
        finally:
            # always close, even if endpoint raised a logical exception
            e.close()
        return retval


class ResponseEndpointUnit(BidirectionalListeningEndpointUnit):
    """
    The listener side makes one of these.
    """
    def _build_header(self, raw_msg, raw_headers):
        """
        Sets headers common to Response side of Request-Response patterns, non-ion-specific.
        """
        headers = BidirectionalListeningEndpointUnit._build_header(self, raw_msg, raw_headers)
        headers['performative'] = 'inform-result'                       # overriden by response pattern, feels wrong
        #TODO - figure out why _send_name would not be there
        if self.channel and hasattr(self.channel, '_send_name') and self.channel._send_name and isinstance(self.channel._send_name, NameTrio):
            headers['receiver'] = "%s,%s" % (self.channel._send_name.exchange, self.channel._send_name.queue)       # @TODO: correct?
        headers['language']     = 'ion-r2'
        headers['encoding']     = 'msgpack'
        headers['format']       = raw_msg.__class__.__name__

        return headers


class RequestResponseServer(ListeningBaseEndpoint):
    endpoint_unit_type = ResponseEndpointUnit
    channel_type = ServerChannel
    pass


class RPCRequestEndpointUnit(RequestEndpointUnit):

    exception_factory = ExceptionFactory()

    def _send(self, msg, headers=None, **kwargs):
        log_message("MESSAGE SEND >>> RPC-request", msg, headers, is_send=True)

        res, res_headers = RequestEndpointUnit._send(self, msg, headers=headers, **kwargs)

        log_message("MESSAGE RECV >>> RPC-reply", res, res_headers, is_send=False)

        # Check response header
        if res_headers["status_code"] != 200:
            stacks = None
            if isinstance(res, list):
                stacks = res
                # stack information is passed as a list of tuples (label, stack)
                # default label for new IonException is '__init__',
                # but change the label of the first remote exception to show RPC invocation.
                # other stacks would have already had labels updated.
                new_label = 'remote call to %s' % (res_headers['receiver'])
                top_stack = stacks[0][1]
                stacks[0] = (new_label, top_stack)
            log.info("RPCRequestEndpointUnit received an error (%d): %s", res_headers['status_code'], res_headers['error_message'])
            ex = self.exception_factory.create_exception(res_headers["status_code"], res_headers["error_message"], stacks=stacks)
            raise ex

        return res, res_headers

    conv_id_counter = 0
    _lock = coros.RLock()       # @TODO: is this safe?
    _conv_id_root = None

    def _build_conv_id(self):
        """
        Builds a unique conversation id based on the container name.
        """
        with RPCRequestEndpointUnit._lock:
            RPCRequestEndpointUnit.conv_id_counter += 1

            if not RPCRequestEndpointUnit._conv_id_root:
                # set default to use uuid-4, similar to what we'd get out of the container id anyway
                RPCRequestEndpointUnit._conv_id_root = str(uuid.uuid4())[0:6]

                # try to get the real one from the container, but do it safely
                try:
                    from pyon.container.cc import Container
                    if Container.instance and Container.instance.id:
                        RPCRequestEndpointUnit._conv_id_root = Container.instance.id
                except:
                    pass

        return "%s-%d" % (RPCRequestEndpointUnit._conv_id_root, RPCRequestEndpointUnit.conv_id_counter)

    def _build_header(self, raw_msg, raw_headers):
        """
        Build header override.

        This should set header values that are invariant or have nothing to do with the specific
        call being made (such as op).
        """
        headers = RequestEndpointUnit._build_header(self, raw_msg, raw_headers)
        headers['protocol'] = 'rpc'
        headers['language'] = 'ion-r2'
        headers['encoding'] = 'msgpack'
        headers['format']   = raw_msg.__class__.__name__
        headers['reply-by'] = 'todo'                        # set by _send override @TODO should be set here

        #Use the headers for conv-id and conv-seq if passed in from higher level API
        headers['conv-id'] = raw_headers['conv-id'] if raw_headers and 'conv-id' in raw_headers else self._build_conv_id()
        headers['conv-seq'] = raw_headers['conv-seq'] if raw_headers and 'conv-seq' in raw_headers else 1 #@TODO will not work well with agree/status etc

        return headers


class RPCClient(RequestResponseClient):
    """
    Base RPCClient class.

    RPC Clients are defined via generate_interfaces for each service, but also may be defined
    on the fly by instantiating one and passing a service Interface class (from the same files
    as the predefined clients) or an IonServiceDefinition, typically obtained from the pycc shell.
    This way, a developer debugging a live system has access to a service he/she may not know about
    at compile time.
    """
    endpoint_unit_type = RPCRequestEndpointUnit

    def __init__(self, iface=None, **kwargs):
        if isinstance(iface, interface.interface.InterfaceClass):
            self._define_interface(iface)
#        elif isinstance(iface, IonServiceDefinition):
#            self._define_svcdef(iface)

        RequestResponseClient.__init__(self, **kwargs)

#    def _define_svcdef(self, svc_def):
#        """
#        Defines an RPCClient's attributes from an IonServiceDefinition.
#        """
#        for meth in svc_def.operations:
#            name        = meth.op_name
#            in_obj      = meth.def_in
#            callargs    = meth.def_in.schema.keys()     # requires ordering to be correct via OrderedDict yaml patching of pyon/core/object.py
#            doc         = meth.__doc__
#
#            self._set_svc_method(name, in_obj, meth.def_in.schema.keys(), doc)

    def _define_interface(self, iface):
        """
        from dorian's RPCClientEntityFromInterface: sets attrs on this client instance from an interface definition.
        """
        methods = iface.namesAndDescriptions()

        # @TODO: hack to get the name of the svc for object name building
        svc_name = iface.getName()[1:]

        for name, command in methods:
            in_obj_name = "%s_%s_in" % (svc_name, name)
            doc         = command.getDoc()

            self._set_svc_method(name, in_obj_name, command.getSignatureInfo()['positional'], doc)

    def _set_svc_method(self, name, in_obj, callargs, doc):
        """
        Common method to properly set a friendly-named remote call method on this RPCClient.

        Since it is not possible to dynamically generate a method signature at run-time (without exec/eval),
        the method has to do translations between *args and **kwargs. Therefore, it needs to know what the
        kwargs are meant to be, either via the interface's method signature, or the IonServiceDefinition's method
        schema.
        """
        def svcmethod(self, *args, **kwargs):
            assert len(args) == 0, "You MUST used named keyword args when calling a dynamically generated remote method"      # we have no way of getting correct order
            headers = kwargs.pop('headers', None)           # pull headers off, cannot put this in the signature due to *args for ordering
            ionobj = IonObject(in_obj, **kwargs)
            return self.request(ionobj, op=name, headers=headers)

        newmethod           = svcmethod
        newmethod.__doc__   = doc
        setattr(self.__class__, name, newmethod)

    def request(self, msg, headers=None, op=None, timeout=None):
        """
        Request override for RPCClients.

        Puts the op into the headers and calls the base class version.
        """
        assert op
        assert headers is None or isinstance(headers, dict)

        if headers is not None:
            headers = headers.copy()
        else:
            headers = {}

        headers['op'] = op

        return RequestResponseClient.request(self, msg, headers=headers, timeout=timeout)


class RPCResponseEndpointUnit(ResponseEndpointUnit):
    def __init__(self, routing_obj=None, **kwargs):
        ResponseEndpointUnit.__init__(self, **kwargs)
        self._routing_obj = routing_obj

    def intercept_in(self, msg, headers):
        """
        ERR This is wrong
        """

        try:
            new_msg, new_headers = ResponseEndpointUnit.intercept_in(self, msg, headers)
            return new_msg, new_headers
        except IonException as ex:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            tb_list = traceback.extract_tb(sys.exc_info()[2])
            tb_list = traceback.format_list(tb_list)
            tb_output = ""
            for elt in tb_list:
                tb_output += elt
            log.debug("server exception being passed to client", exc_info=True)
            result = ex.get_stacks()
            response_headers = self._create_error_response(ex)

            response_headers['protocol']    = headers.get('protocol', '')
            response_headers['conv-id']     = headers.get('conv-id', '')
            response_headers['conv-seq']    = headers.get('conv-seq', 1) + 1

            self.send(result, response_headers)

            # reraise for someone else to catch
            raise

    def _message_received(self, msg, headers):
        """
        Internal _message_received override.

        We need to be able to detect IonExceptions raised in the Interceptor stacks as well as in the actual
        call to the op we're routing into. This override will handle the return value being sent to the caller.
        """
        result = None
        response_headers = {}

        ts = get_ion_ts()
        response_headers['msg-rcvd'] = ts

        try:
            result, new_response_headers = ResponseEndpointUnit._message_received(self, msg, headers)       # execute interceptor stack, calls into our message_received
            response_headers.update(new_response_headers)       # don't clobber our msg-rcvd header

        except IonException as ex:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            tb_list = traceback.extract_tb(sys.exc_info()[2])
            tb_list = traceback.format_list(tb_list)
            tb_output = ""
            for elt in tb_list:
                tb_output += elt
            log.debug("server exception being passed to client", exc_info=True)
            result = ex.get_stacks()

            response_headers.update(self._create_error_response(ex))

        finally:
            # REPLIES: propogate protocol, conv-id, conv-seq
            response_headers['protocol']    = headers.get('protocol', '')
            response_headers['conv-id']     = headers.get('conv-id', '')
            response_headers['conv-seq']    = headers.get('conv-seq', 1) + 1
        # sample (possibly) before we do any sending
        self._sample_request(response_headers['status_code'], response_headers['error_message'], msg, headers, result, response_headers)

        return self.send(result, response_headers)

    def _send(self, msg, headers=None, **kwargs):
        """
        Override for more accurate reply log message.
        """
        log_message("MESSAGE SEND <<< RPC-reply", msg, headers, is_send=True)
        return ResponseEndpointUnit._send(self, msg, headers=headers, **kwargs)

    def message_received(self, msg, headers):
        assert self._routing_obj, "How did I get created without a routing object?"

        cmd_arg_obj = msg
        cmd_op      = headers.get('op', None)

        # get timeout
        timeout = self._calculate_timeout(headers)

        # transform cmd_arg_obj into a dict
        if hasattr(cmd_arg_obj, '__dict__'):
            cmd_arg_obj = cmd_arg_obj.__dict__
        elif isinstance(cmd_arg_obj, dict):
            pass
        else:
            raise BadRequest("Unknown message type, cannot convert into kwarg dict: %s" % str(type(cmd_arg_obj)))

        # op name must exist!
        if not hasattr(self._routing_obj, cmd_op):
            raise BadRequest("Unknown op name: %s" % cmd_op)

        ro_meth     = getattr(self._routing_obj, cmd_op)

        # check arguments (as long as it is a function. might be a mock in testing.)
        # @TODO doesn't really feel correct.
        if isinstance(ro_meth, MethodType):
            ro_meth_args = inspect.getargspec(ro_meth)

            # if the keyword one is not none, we can support anything
            if ro_meth_args[2] is None:
                for arg_name in cmd_arg_obj:
                    if not arg_name in ro_meth_args[0]:
                        return None, self._create_error_response(BadRequest("Argument %s not present in op signature" % arg_name))

        result = None
        response_headers = {}

        ######
        ###### THIS IS WHERE THE SERVICE OPERATION IS CALLED ######
        ######
        result              = self._make_routing_call(ro_meth, timeout, **cmd_arg_obj)
        response_headers    = { 'status_code': 200, 'error_message': '' }
        ######

        return result, response_headers

    def _calculate_timeout(self, headers):
        """
        Takes incoming message headers and calculates an integer value in seconds to be used for timeouts.

        @return None or an integer value in seconds.
        """
        if not ('ts' in headers and 'reply-by' in headers):
            return None

        ts = int(headers['ts'])
        reply_by = int(headers['reply-by'])
        latency = int(get_ion_ts()) - ts         # we don't have access to response headers here, so calc again, not too big of a deal

        # reply-by minus timestamp gives us max allowable, subtract 2x observed latency, give 10% margin, and convert to integers
        to_val = int((reply_by - ts - 2 * latency) / 1000 * 0.9)

        log.debug("calculated timeout val of %s for conv-id %s", to_val, headers.get('conv-id', 'NONE'))

        return to_val

    def _create_error_response(self, ex):
        # have seen exceptions where the "message" is really a tuple, and pika is not a fan: make sure it is str()'d
        return {'status_code': ex.get_status_code(),
                'error_message': str(ex.get_error_message()),
                'performative': 'failure'}

    def _make_routing_call(self, call, timeout, *op_args, **op_kwargs):
        """
        Calls into the routing object.

        May be overridden at a lower level.
        """
        return call(*op_args, **op_kwargs)       # REMOVED TIMEOUT
        #try:
        #    with Timeout(timeout):
        #        return call(*op_args, **op_kwargs)
        #except Timeout:
        #    # cleanup shouldn't be needed, executes in same greenlet as current
        #    raise exception.Timeout("Timed out making call to service (non-ION process)")

    def _sample_request(self, status, status_descr, msg, headers, response, response_headers):
        """
        Performs sFlow sampling of a completed/errored RPC request (if configured to).

        Makes two calls:
        1) get_sflow_manager (overridden at process level)
        2) make sample dict (the kwargs to sflow_manager.transaction, may be overridden where appropriate)

        Then performs the transact call if the manager says to do so.
        """
        if CFG.get_safe('container.sflow.enabled', False):
            sm = self._get_sflow_manager()
            if sm and sm.should_sample:
                sample_name = self._get_sample_name()
                try:
                    # get queue length
                    qlen, _ = self.channel.get_stats()
                    qlen += self.channel._recv_queue.qsize()      # add delivered but unproc'd msgs, @TODO correct?

                    trans_kwargs = self._build_sample(sample_name, status, status_descr, msg, headers, response, response_headers, qlen)
                    sm.transaction(**trans_kwargs)
                except Exception:
                    log.exception("Could not sample, ignoring")

            else:
                log.debug("No SFlowManager or it told us not to sample this transaction")

    def _get_sample_name(self):
        """
        Gets the app_name that should be used for the sample.

        Typically this would be a process id.
        """
        # at the rpc level we really don't know, we're not a process.
        return "unknown-rpc-server"

    def _get_sflow_manager(self):
        """
        Finds the sFlow manager that should be used.
        """
        # at this level, we don't have any ref back to the container other than the singleton
        from pyon.container.cc import Container
        if Container.instance:
            return Container.instance.sflow_manager

        return None

    def _build_sample(self, name, status, status_descr, msg, headers, response, response_headers, qlen):
        """
        Builds a transaction sample.

        Should return a dict in the form of kwargs to be passed to SFlowManager.transaction.
        @see sFlow application spec: http://sflow.org/sflow_application.txt
        """
        # build args to pass to transaction
        #extra_attrs = {'conv-id': headers.get('conv-id', ''),
        #               'service': response_headers.get('sender-service', '')}
        extra_attrs = {'ql': qlen}      # queue length (both on server + delivered to this process)

        # Message Latency
        # Defined as difference between message sent timestamp and message received timestamp.
        if 'msg-rcvd' in response_headers and 'ts' in headers:
            rsts = int(headers['ts'])
            mrts = int(response_headers['msg-rcvd'])

            extra_attrs['ml'] = str(mrts - rsts)

        # Process Saturation
        # processing time / total time running, as an integer percentage
        if 'process-saturation' in response_headers:
            extra_attrs['ps'] = response_headers['process-saturation']

        # Process ID
        # for mapping extra attrs to a pid -> passed in as name here
        extra_attrs['pid'] = name

        # uS: process latency
        # 1-way message latency (req to svc ONLY) + processing time
        cur_time_ms = int(get_ion_ts())
        time_taken = (cur_time_ms - int(headers.get('ts', cur_time_ms))) * 1000      # sflow wants microseconds!

        # build op name: typically sender-service.op, or falling back to sender.op
        svc_name = response_headers.get('sender-service', response_headers.get('sender', headers.get('receiver', '')))
        if "," in svc_name:
            svc_name = svc_name.rsplit(',', 1)[-1]

        op = headers.get('op', 'unknown')

        # status code map => ours to sFlow (defaults to 3 aka INTERNAL_ERROR)
        status = SFlowManager.status_map.get(status, 3)

        sample = {'app_name':     bootstrap.get_sys_name()[0:64],
                  'op':           op[0:32],
                  'attrs':        extra_attrs,
                  'status_descr': status_descr[0:64],
                  'status':       str(status),
                  'req_bytes':    len(str(msg)),
                  'resp_bytes':   len(str(response)),
                  'uS':           time_taken,
                  'initiator':    headers.get('sender', '')[0:64],
                  'target':       svc_name[0:64] }

        return sample


class RPCServer(RequestResponseServer):
    endpoint_unit_type = RPCResponseEndpointUnit

    def __init__(self, service=None, **kwargs):
        #log.debug("In RPCServer.__init__")
        self._service = service
        RequestResponseServer.__init__(self, **kwargs)

    def create_endpoint(self, **kwargs):
        """
        @TODO: push this into RequestResponseServer
        """
        #log.debug("RPCServer.create_endpoint override")
        return RequestResponseServer.create_endpoint(self, routing_obj=self._service, **kwargs)

    def __str__(self):
        return "RPCServer: recv_name: %s" % (str(self._recv_name))

def log_message(prefix="MESSAGE", msg=None, headers=None, recv=None, delivery_tag=None, is_send=True):
    """
    Utility function to print an legible comprehensive summary of a received message.
    @NOTE: This is an expensive operation
    """
    if rpclog.isEnabledFor(logging.DEBUG):
        try:
            headers = headers or {}
            _sender = headers.get('sender', '?') + "(" + headers.get('sender-name', '') + ")"
            _send_hl, _recv_hl = ("###", "") if is_send else ("", "###")

            if recv and getattr(recv, '__iter__', False):
                recv = ".".join(str(item) for item in recv if item)
            _recv = headers.get('receiver', '?')
            _opstat = "op=%s"%headers.get('op', '') if 'op' in headers else "status=%s"%headers.get('status_code', '')
            try:
                import msgpack
                _msg = msgpack.unpackb(msg)
                _msg = str(_msg)
            except Exception:
                _msg = str(msg)
            _msg = _msg[0:400]+"..." if len(_msg) > 400 else _msg
            _delivery = "\nDELIVERY: tag=%s"%delivery_tag if delivery_tag else ""
            rpclog.debug("%s: %s%s%s -> %s%s%s %s:\nHEADERS: %s\nCONTENT: %s%s",
                prefix, _send_hl, _sender, _send_hl, _recv_hl, _recv, _recv_hl, _opstat, str(headers), _msg, _delivery)
        except Exception as ex:
            log.warning("%s log error: %s", prefix, str(ex))
