#!/usr/bin/env python

"""Provides the communication layer above channels."""

from pyon.core import bootstrap, exception
from pyon.core.bootstrap import CFG, IonObject
from pyon.core.exception import exception_map, IonException, BadRequest, ServerError
from pyon.core.object import IonObjectBase
from pyon.net.channel import ChannelError, ChannelClosedError, BaseChannel, PublisherChannel, ListenChannel, SubscriberChannel, ServerChannel, BidirClientChannel, ChannelShutdownMessage
from pyon.core.interceptor.interceptor import Invocation, process_interceptors
from pyon.util.async import spawn, switch
from pyon.util.log import log
from pyon.net.transport import NameTrio, BaseTransport

from gevent import event, coros
from gevent.timeout import Timeout
from zope import interface
import uuid

import traceback
import sys



interceptors = {"message_incoming": [], "message_outgoing": [], "process_incoming": [], "process_outgoing": []}

# Note: This is now called from pyon.core.bootstrap
def instantiate_interceptors(interceptor_cfg):
    stack = interceptor_cfg["stack"]
    defs = interceptor_cfg["interceptors"]

    by_name_dict = {}
    for type_and_direction in stack:
        interceptor_names = stack[type_and_direction]
        for name in interceptor_names:
            if name in by_name_dict:
                classinst = by_name_dict[name]
            else:
                interceptor_def = defs[name]

                # Instantiate and put in by_name array
                parts = interceptor_def["class"].split('.')
                modpath = ".".join(parts[:-1])
                classname = parts[-1]
                module = __import__(modpath, fromlist=[classname])
                classobj = getattr(module, classname)
                classinst = classobj()

                # Call configure
                classinst.configure(config = interceptor_def["config"] if "config" in interceptor_def else None)

                # Put in by_name_dict for possible re-use
                by_name_dict[name] = classinst

            interceptors[type_and_direction].append(classinst)

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
    _recv_greenlet = None

    def attach_channel(self, channel):
        log.debug("In EndpointUnit.attach_channel")
        log.debug("channel %s" % str(channel))
        self.channel = channel

    # @TODO: is this used?
    def channel_attached(self):
        """
        """
        log.debug("In EndpointUnit.channel_attached")

    def _build_invocation(self, **kwargs):
        """
        Builds an Invocation instance to be used by the interceptor stack.
        This method exists so we can override it in derived classes (ex with a process).
        """
        inv = Invocation(**kwargs)
        return inv

    def _message_received(self, msg, headers):
        """
        Entry point for received messages in below channel layer. This method puts the message through
        the interceptor stack, then funnels the message into the message_received method.

        This method should not be overridden unless you are familiar with how the interceptor stack and
        friends work!
        """
        # interceptor point
        inv = self._build_invocation(path=Invocation.PATH_IN,
                                     message=msg,
                                     headers=headers)
        inv_prime = self._intercept_msg_in(inv)
        new_msg     = inv_prime.message
        new_headers = inv_prime.headers

        return self.message_received(new_msg, new_headers)

    def _intercept_msg_in(self, inv):
        """
        Performs interceptions of incoming messages.
        Override this to change what interceptor stack to go through and ordering.

        @param  inv     An Invocation instance.
        @returns        A processed Invocation instance.
        """
        inv_prime = process_interceptors(interceptors["message_incoming"] if "message_incoming" in interceptors else [], inv)
        return inv_prime

    def message_received(self, msg, headers):
        """
        """
        log.debug("In EndpointUnit.message_received")

    def send(self, msg, headers=None, **kwargs):
        """
        Public send method.
        Calls _build_msg (_build_header and _build_payload), then _send which puts it through the Interceptor stack(s).

        @param  msg         The message to send. Will be passed into _build_payload. You may modify the contents there.
        @param  headers     Optional headers to send. Will override anything produced by _build_header.
        @param  kwargs      Passed through to _send.
        """
        _msg, _header = self._build_msg(msg)
        if headers: _header.update(headers)
        return self._send(_msg, _header, **kwargs)

    def _send(self, msg, headers=None, **kwargs):
        """
        Handles the send interaction with the Channel.

        Override this method to get custom behavior of how you want your endpoint unit to operate.
        Kwargs passed into send will be forwarded here. They are not used in this base method.
        """
        log.debug("In EndpointUnit._send: %s", headers)
        # interceptor point
        inv = self._build_invocation(path=Invocation.PATH_OUT,
                                     message=msg,
                                     headers=headers)
        inv_prime = self._intercept_msg_out(inv)
        new_msg = inv_prime.message
        new_headers = inv_prime.headers

        self.channel.send(new_msg, new_headers)

    def _intercept_msg_out(self, inv):
        """
        Performs interceptions of outgoing messages.
        Override this to change what interceptor stack to go through and ordering.

        @param  inv     An Invocation instance.
        @returns        A processed Invocation instance.
        """
        inv_prime = process_interceptors(interceptors["message_outgoing"] if "message_outgoing" in interceptors else [], inv)
        return inv_prime

    def spawn_listener(self):
        def client_recv():
            while True:
                try:
                    log.debug("client_recv waiting for a message")
                    msg, headers, delivery_tag = self.channel.recv()
                    log.debug("client_recv got a message")
                    log_message(self.channel._send_name , msg, headers, delivery_tag)
                    try:
                        self._message_received(msg, headers)
                    finally:
                        # always ack a listener response
                        self.channel.ack(delivery_tag)
                except ChannelClosedError:
                    log.debug('Channel was closed during client_recv listen loop')
                    break

        # @TODO: spawn should be configurable to maybe the proc_sup in the container?
        self._recv_greenlet = spawn(client_recv)

    def close(self):
        if self._recv_greenlet is not None:
            # This is not entirely correct. We do it here because we want the listener's client_recv to exit gracefully
            # and we may be reusing the channel. This *SEEMS* correct but we're reaching into Channel too far.
            # @TODO: remove spawn_listener altogether.
            self.channel._recv_queue.put(ChannelShutdownMessage())
            self._recv_greenlet.join(timeout=2)
            self._recv_greenlet.kill()      # he's dead, jim

        if self.channel is not None:
            # related to above, the close here would inject the ChannelShutdownMessage if we are NOT reusing.
            # we may end up having a duplicate, but I think logically it would never be a problem.
            # still, need to clean this up.
            self.channel.close()

    def _build_header(self, raw_msg):
        """
        Assembles the headers of a message from the raw message's content.
        """
        log.debug("EndpointUnit _build_header")
        return {}

    def _build_payload(self, raw_msg):
        """
        Assembles the payload of a message from the raw message's content.

        @TODO will this be used? seems unlikely right now.
        """
        log.debug("EndpointUnit _build_payload")
        return raw_msg

    def _build_msg(self, raw_msg):
        """
        Builds a message (headers/payload) from the raw message's content.
        You typically do not need to override this method, but override the _build_header
        and _build_payload methods.

        @returns A 2-tuple of payload, headers
        """
        log.debug("EndpointUnit _build_msg")
        header = self._build_header(raw_msg)
        payload = self._build_payload(raw_msg)

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

    def __init__(self, node=None):

        self.node = node

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
        log.debug("BaseEndpoint._ensure_node (current: %s)", self.node is not None)

        if not self.node:
            container_instance = self._get_container_instance()
            if container_instance:
                log.debug("Pulling node from Container.instance")
                self.node = container_instance.node
            else:
                raise EndpointError("Cannot pull node from Container.instance and no node specified")

    def create_endpoint(self, to_name=None, existing_channel=None, **kwargs):
        """
        @param  to_name     Either a string or a 2-tuple of (exchange, name)
        """
        if existing_channel:
            ch = existing_channel
        else:
            self._ensure_node()
            ch = self._create_channel()

        e = self.endpoint_unit_type(**kwargs)
        e.attach_channel(ch)

        return e

    def _create_channel(self, **kwargs):
        """
        Creates a channel, used by create_endpoint.

        Can pass additional kwargs in to be passed through to the channel provider.
        """
        return self.node.channel(self.channel_type, **kwargs)

    def close(self):
        """
        To be defined by derived classes. Cleanup any resources here, such as channels being open.
        """
        pass

class SendingBaseEndpoint(BaseEndpoint):
    def __init__(self, node=None, to_name=None, name=None):
        BaseEndpoint.__init__(self, node=node)

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

    def _create_channel(self, **kwargs):
        """
        Overrides the BaseEndpoint create channel to supply a transport if our send_name is one.
        """
        if isinstance(self._send_name, BaseTransport):
            kwargs.update({'transport':self._send_name})

        return BaseEndpoint._create_channel(self, **kwargs)


def log_message(recv, msg, headers, delivery_tag=None):
    """
    Utility function to print an legible comprehensive summary of a received message.
    """
    if getattr(recv, '__iter__', False):
        recv = ".".join(str(item) for item in recv if item)
    log.info("MESSAGE RECV [S->%s]: len=%s, headers=%s", recv, len(str(msg)), headers)

class ListeningBaseEndpoint(BaseEndpoint):
    """
    Establishes channel type for a host of derived, listen/react endpoint factories.
    """
    channel_type = ListenChannel

    def __init__(self, node=None, name=None, from_name=None, binding=None):
        BaseEndpoint.__init__(self, node=node)

        if name:
            log.warn("ListeningBaseEndpoint: name param is deprecated, please use from_name instead")
        self._recv_name = from_name or name

        # ensure NameTrio
        if not isinstance(self._recv_name, NameTrio):
            self._recv_name = NameTrio(bootstrap.get_sys_name(), self._recv_name, binding)   # if _recv_name is tuple it takes precedence

        self._ready_event = event.Event()
        self._binding = binding

    def _create_channel(self, **kwargs):
        """
        Overrides the BaseEndpoint create channel to supply a transport if our recv name is one.
        """
        if isinstance(self._recv_name, BaseTransport):
            kwargs.update({'transport':self._recv_name})

        return BaseEndpoint._create_channel(self, **kwargs)

    def get_ready_event(self):
        """
        Returns an async event you can .wait() on.
        Used to indicate when listen() is ready to start listening.
        """
        return self._ready_event

    def _setup_listener(self, name, binding=None):
        self._chan.setup_listener(name, binding=binding)

    def listen(self, binding=None):
        log.debug("LEF.listen: binding %s", binding)

        binding = binding or self._binding or self._recv_name.binding

        self._ensure_node()
        kwargs = {}
        if isinstance(self._recv_name, BaseTransport):
            kwargs.update({'transport':self._recv_name})
        self._chan = self.node.channel(self.channel_type, **kwargs)

        # @TODO this does not feel right
        if isinstance(self._recv_name, BaseTransport):
            self._recv_name.setup_listener(binding, self._setup_listener)
            self._chan._recv_name = self._recv_name
        else:
            self._setup_listener(self._recv_name, binding=binding)
        self._chan.start_consume()

        # notify any listeners of our readiness
        self._ready_event.set()

        while True:
            log.debug("LEF: %s blocking, waiting for a message" % str(self._recv_name))
            try:
                newchan = self._chan.accept()
                msg, headers, delivery_tag = newchan.recv()

                log.debug("LEF %s received message %s, headers %s, delivery_tag %s", self._recv_name, msg, headers, delivery_tag)
                log_message(self._recv_name, msg, headers, delivery_tag)

            except ChannelClosedError as ex:
                log.debug('Channel was closed during LEF.listen')
                break

            try:
                e = self.create_endpoint(existing_channel=newchan)
                e._message_received(msg, headers)
            except Exception:
                log.exception("Unhandled error while handling received message")
                raise
            finally:
                # ALWAYS ACK
                newchan.ack(delivery_tag)

    def close(self):
        BaseEndpoint.close(self)
        self._chan.close()

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

    def publish(self, msg, to_name=None):

        ep = None
        if not to_name:
            # @TODO: needs thread safety
            if not self._pub_ep:
                self._pub_ep = self.create_endpoint(self._send_name)
            ep = self._pub_ep
        else:
            ep = self.create_endpoint(to_name)

        ep.send(msg)
        return ep

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
    def __init__(self, callback):
        EndpointUnit.__init__(self)
        self.set_callback(callback)

    def set_callback(self, callback):
        """
        Sets the callback to be used by this SubscriberEndpointUnit when a message is received.
        """
        self._callback = callback

    def message_received(self, msg, headers):
        EndpointUnit.message_received(self, msg, headers)
        assert self._callback, "No callback provided, cannot route subscribed message"

        self._callback(msg, headers)


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
        assert callback, "No callback provided"
        self._callback = callback
        ListeningBaseEndpoint.__init__(self, **kwargs)

    def create_endpoint(self, **kwargs):
        log.debug("Subscriber.create_endpoint override")
        return ListeningBaseEndpoint.create_endpoint(self, callback=self._callback, **kwargs)


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
    def _send(self, msg, headers=None, **kwargs):

        # could have a specified timeout in kwargs
        if 'timeout' in kwargs and kwargs['timeout'] is not None:
            timeout = kwargs['timeout']
        else:
            timeout = CFG.endpoint.receive.timeout or 10

        log.debug("RequestEndpointUnit.send (timeout: %s)", timeout)

        if not self._recv_greenlet:
            self.channel.setup_listener(NameTrio(self.channel._send_name.exchange)) # anon queue
            self.channel.start_consume()
            self.spawn_listener()

        self.response_queue = event.AsyncResult()
        self.message_received = lambda m, h: self.response_queue.set((m, h))

        EndpointUnit._send(self, msg, headers=headers)

        try:
            result_data, result_headers = self.response_queue.get(timeout=timeout)
        except Timeout:
            raise exception.Timeout('Request timed out (%d sec) waiting for response from %s' % (timeout, str(self.channel._send_name)))

        log.debug("Got response to our request: %s, headers: %s", result_data, result_headers)
        return result_data, result_headers

    def _build_header(self, raw_msg):
        """
        Sets headers common to Request-Response patterns, non-ion-specific.
        """
        headers = BidirectionalEndpointUnit._build_header(self, raw_msg)
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
        log.debug("RequestResponseClient.request: %s, headers: %s", msg, headers)
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
    def _build_header(self, raw_msg):
        """
        Sets headers common to Response side of Request-Response patterns, non-ion-specific.
        """
        headers = BidirectionalListeningEndpointUnit._build_header(self, raw_msg)
        headers['performative'] = 'inform-result'                       # overriden by response pattern, feels wrong
        if self.channel and self.channel._send_name and isinstance(self.channel._send_name, NameTrio):
            headers['receiver'] = "%s,%s" % (self.channel._send_name.exchange, self.channel._send_name.queue)       # @TODO: correct?
        headers['language']     = 'ion-r2'
        headers['encoding']     = 'msgpack'
        headers['format']       = raw_msg.__class__.__name__    # hmm
        headers['reply-by']     = 'todo'                        # clock sync is a problem

        return headers

class RequestResponseServer(ListeningBaseEndpoint):
    endpoint_unit_type = ResponseEndpointUnit
    channel_type = ServerChannel
    pass

class RPCRequestEndpointUnit(RequestEndpointUnit):

    def _send(self, msg, headers=None, **kwargs):
        log.info("MESSAGE SEND [S->D] RPC: %s" % str(msg))

        res, res_headers = RequestEndpointUnit._send(self, msg, headers=headers, **kwargs)

        #log_message('?WHO AM I?', res, res_headers)
        log.debug("RPCRequestEndpointUnit got this response: %s, headers: %s" % (str(res), str(res_headers)))

        # Check response header
        if res_headers["status_code"] == 200:
            log.debug("OK status")
            return res, res_headers
        else:
            log.debug("Bad status: %d" % res_headers["status_code"])
            log.debug("Error message: %s" % res_headers["error_message"])
            self._raise_exception(res_headers["status_code"], res_headers["error_message"])

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

    def _build_header(self, raw_msg):
        """
        Build header override.

        This should set header values that are invariant or have nothing to do with the specific
        call being made (such as op).
        """
        headers = RequestEndpointUnit._build_header(self, raw_msg)
        headers['protocol'] = 'rpc'
        headers['conv-seq'] = 1     # @TODO will not work well with agree/status etc
        headers['conv-id']  = self._build_conv_id()
        headers['language'] = 'ion-r2'
        headers['encoding'] = 'msgpack'
        headers['format']   = raw_msg.__class__.__name__    # hmm
        headers['reply-by'] = 'todo'                        # clock sync is a problem

        return headers

    def _raise_exception(self, code, message):
        if str(code) in exception_map:
            raise exception_map[str(code)](message)
        else:
            log.debug("Raising ServerError")
            raise ServerError(message)

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
            assert len(args)==0, "You MUST used named keyword args when calling a dynamically generated remote method"      # we have no way of getting correct order
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
        headers = headers or {}
        headers['op'] = op

        return RequestResponseClient.request(self, msg, headers=headers, timeout=timeout)


class RPCResponseEndpointUnit(ResponseEndpointUnit):
    def __init__(self, routing_obj=None, **kwargs):
        ResponseEndpointUnit.__init__(self)
        self._routing_obj = routing_obj
        
    def _message_received(self, msg, headers):
        """
        Internal _message_received override.

        We need to be able to detect IonExceptions raised in the Interceptor stacks as well as in the actual
        call to the op we're routing into. This override will handle the return value being sent to the caller.
        """
        result = None
        try:
            result, response_headers = ResponseEndpointUnit._message_received(self, msg, headers)       # execute interceptor stack, calls into our message_received
        except IonException as ex:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            tb_list = traceback.extract_tb(sys.exc_info()[2])
            tb_list = traceback.format_list(tb_list)
            tb_output = ""
            for elt in tb_list:
                tb_output += elt
            log.debug("Got error response")
            log.debug("Exception message: %s" % ex)
            log.debug("Traceback:\n%s" % tb_output)
            response_headers = self._create_error_response(ex)

        # REPLIES: propogate protocol, conv-id, conv-seq
        response_headers['protocol']    = headers.get('protocol', '')
        response_headers['conv-id']     = headers.get('conv-id', '')
        response_headers['conv-seq']    = headers.get('conv-seq', 1) + 1

        log.info("MESSAGE SEND [S->D] RPC: %s, headers: %s", result, response_headers)

        return self.send(result, response_headers)

    def message_received(self, msg, headers):
        assert self._routing_obj, "How did I get created without a routing object?"

        log.debug("RPCResponseEndpointUnit.message_received\n\tmsg: %s\n\theaders: %s", msg, headers)

        cmd_arg_obj = msg
        cmd_op      = headers.get('op', None)

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

        result = None
        response_headers = {}
        try:
            result = ro_meth(**cmd_arg_obj)

            response_headers = { 'status_code': 200, 'error_message': '' }
        except TypeError as ex:
            log.exception("TypeError while attempting to call routing object's method")
            response_headers = self._create_error_response(ServerError(ex.message))

        return result, response_headers

    def _create_error_response(self, ex):
        # have seen exceptions where the "message" is really a tuple, and pika is not a fan: make sure it is str()'d
        return {'status_code': ex.get_status_code(),
                'error_message': str(ex.get_error_message()),
                'performative':'failure'}

class RPCServer(RequestResponseServer):
    endpoint_unit_type = RPCResponseEndpointUnit

    def __init__(self, service=None, **kwargs):
        log.debug("In RPCServer.__init__")
        self._service = service
        RequestResponseServer.__init__(self, **kwargs)

    def create_endpoint(self, **kwargs):
        """
        @TODO: push this into RequestResponseServer
        """
        log.debug("RPCServer.create_endpoint override")
        return RequestResponseServer.create_endpoint(self, routing_obj=self._service, **kwargs)


class ProcessRPCRequestEndpointUnit(RPCRequestEndpointUnit):

    def __init__(self, process=None, **kwargs):
        RPCRequestEndpointUnit.__init__(self, **kwargs)
        self._process = process

    def _build_invocation(self, **kwargs):
        newkwargs = kwargs.copy()
        newkwargs.update({'process':self._process})

        inv = RPCRequestEndpointUnit._build_invocation(self, **newkwargs)
        return inv

    def _intercept_msg_in(self, inv):
        """
        Override for incoming message interception.

        This is a request, so the order should be Message, Process
        """
        inv_one = RPCRequestEndpointUnit._intercept_msg_in(self, inv)
        inv_two = process_interceptors(interceptors["process_incoming"] if "process_incoming" in interceptors else [], inv_one)
        return inv_two

    def _intercept_msg_out(self, inv):
        """
        Override for outgoing message interception.

        This is request, so the order should be Process, Message
        """
        inv_one = process_interceptors(interceptors["process_outgoing"] if "process_outgoing" in interceptors else [], inv)
        inv_two = RPCRequestEndpointUnit._intercept_msg_out(self, inv_one)

        return inv_two

    def _build_header(self, raw_msg):
        """
        Builds the header for this Process-level RPC conversation.
        https://confluence.oceanobservatories.org/display/syseng/CIAD+COI+OV+Common+Message+Format
        """

        context = self._process.get_context()
        log.debug('ProcessRPCRequestEndpointUnit._build_header has context of: %s', context)

        # conv-id/seq/protocol are set in the base class
        header = RPCRequestEndpointUnit._build_header(self, raw_msg)

        # add our process identity to the headers
        header.update({'sender-name'  : self._process.name or 'unnamed-process',     # @TODO
                       'sender'       : self._process.id })

        if hasattr(self._process,'process_type' ):
            header.update({'sender-type'  : self._process.process_type or 'unknown-process-type' })
            if self._process.process_type == 'service':
                header.update({ 'sender-service' : "%s,%s" % ( self.channel._send_name.exchange,self._process.name) })

        # use context to set security attributes forward
        if isinstance(context, dict):
            # fwd on actor specific information, according to common message format spec
            actor_id            = context.get('ion-actor-id', None)
            actor_roles         = context.get('ion-actor-roles', None)
            actor_tokens        = context.get('ion-actor-tokens', None)
            expiry              = context.get('expiry', None)
            container_id        = context.get('origin-container-id', None)

            #If an actor-id is specified then there may be other associated data that needs to be passed on
            if actor_id:
                header['ion-actor-id']  = actor_id
                if actor_roles:     header['ion-actor-roles']   = actor_roles
                if actor_tokens:    header['ion-actor-tokens']  = actor_tokens

            if expiry:          header['expiry']                = expiry
            if container_id:    header['origin-container-id']   = container_id
        else:
            # no context? we're the originator of the message then
            container_id                    = BaseEndpoint._get_container_instance().id
            header['origin-container-id']   = container_id

        return header

class ProcessRPCClient(RPCClient):
    endpoint_unit_type = ProcessRPCRequestEndpointUnit

    def __init__(self, process=None, **kwargs):
        self._process = process
        RPCClient.__init__(self, **kwargs)

    def create_endpoint(self, to_name=None, existing_channel=None, **kwargs):
        if not self._process:
            raise StandardError("No Process specified")

        newkwargs = kwargs.copy()
        newkwargs['process'] = self._process
        return RPCClient.create_endpoint(self, to_name, existing_channel, **newkwargs)

class ProcessRPCResponseEndpointUnit(RPCResponseEndpointUnit):

    def __init__(self, process=None, **kwargs):
        RPCResponseEndpointUnit.__init__(self, **kwargs)
        self._process = process
        assert process

    def _message_received(self, msg, headers):
        """
        Message received override.

        Sets the process' context here to be picked up by subsequent calls out by this service to other services, or replies.
        """
        with self._process.push_context(headers):
            return RPCResponseEndpointUnit._message_received(self, msg, headers)

    def _build_invocation(self, **kwargs):
        newkwargs = kwargs.copy()
        newkwargs.update({'process':self._process})

        inv = RPCResponseEndpointUnit._build_invocation(self, **newkwargs)
        return inv

    def _intercept_msg_in(self, inv):
        """
        Override for incoming message interception.

        This is response incoming, so the order should be Message, Process
        """
        inv_one = RPCResponseEndpointUnit._intercept_msg_in(self, inv)
        inv_two = process_interceptors(interceptors["process_incoming"] if "process_incoming" in interceptors else [], inv_one)
        return inv_two

    def _intercept_msg_out(self, inv):
        """
        Override for outgoing message interception.

        This is response outgoing, so the order should be Process, Message
        """
        inv_one = process_interceptors(interceptors["process_outgoing"] if "process_outgoing" in interceptors else [], inv)
        inv_two = RPCResponseEndpointUnit._intercept_msg_out(self, inv_one)
        return inv_two

    def _build_header(self, raw_msg):
        """
        Builds the header for this Process-level RPC conversation.
        https://confluence.oceanobservatories.org/display/syseng/CIAD+COI+OV+Common+Message+Format
        """

        context = self._process.get_context()
        log.debug('ProcessRPCResponseEndpointUnit._build_header has context of: %s', context)

        # conv-id/seq/protocol are set in the base class
        header = RPCResponseEndpointUnit._build_header(self, raw_msg)

        # add our process identity to the headers
        header.update({'sender-name'  : self._process.name or 'unnamed-process',     # @TODO
                       'sender'       : self._process.id })

        if hasattr(self._process,'process_type' ):
            header.update({'sender-type'  : self._process.process_type or 'unknown-process-type' })
            if self._process.process_type == 'service':
                header.update({ 'sender-service' : "%s,%s" % ( self.channel._send_name.exchange,self._process.name) })

        # use context to set security attributes forward
        if isinstance(context, dict):
            # fwd on actor specific information, according to common message format spec
            actor_id            = context.get('ion-actor-id', None)
            actor_roles         = context.get('ion-actor-roles', None)
            actor_tokens        = context.get('ion-actor-tokens', None)
            expiry              = context.get('expiry', None)
            container_id        = context.get('origin-container-id', None)

            #If an actor-id is specified then there may be other associated data that needs to be passed on
            if actor_id:
                header['ion-actor-id']  = actor_id
                if actor_roles:     header['ion-actor-roles']   = actor_roles
                if actor_tokens:    header['ion-actor-tokens']  = actor_tokens

            if expiry:          header['expiry']                = expiry
            if container_id:    header['origin-container-id']   = container_id
        else:
            # no context? we're the originator of the message then (in a response??)
            container_id                    = BaseEndpoint._get_container_instance().id
            header['origin-container-id']   = container_id

        return header

class ProcessRPCServer(RPCServer):
    endpoint_unit_type = ProcessRPCResponseEndpointUnit

    def __init__(self, process=None, **kwargs):
        assert process
        self._process = process
        RPCServer.__init__(self, **kwargs)

    def create_endpoint(self, **kwargs):
        newkwargs = kwargs.copy()
        newkwargs['process'] = self._process
        return RPCServer.create_endpoint(self, **newkwargs)
