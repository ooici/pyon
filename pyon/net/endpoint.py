#!/usr/bin/env python

"""Provides the communication layer above channels."""

from gevent import event
from zope import interface

from pyon.core import bootstrap
from pyon.core.bootstrap import CFG
from pyon.core import exception
from pyon.core.object import IonServiceDefinition
from pyon.net.channel import Bidirectional, BidirectionalClient, PubSub, ChannelError, ChannelClosedError, BaseChannel, PubChannel, ListenChannel, SubscriberChannel, ServerChannel, BidirClientChannel
from pyon.core.interceptor.interceptor import Invocation, process_interceptors
from pyon.util.async import spawn, switch
from pyon.util.log import log

interceptors = {"message_incoming": [], "message_outgoing": [], "process_incoming": [], "process_outgoing": []}

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

instantiate_interceptors(CFG.interceptor)

class Endpoint(object):

    channel = None
    _recv_greenlet = None

    def attach_channel(self, channel):
        log.debug("In Endpoint.attach_channel")
        log.debug("channel %s" % str(channel))
        self.channel = channel

    # @TODO: is this used?
    def channel_attached(self):
        """
        """
        log.debug("In Endpoint.channel_attached")

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

        self.message_received(new_msg, new_headers)

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
        log.debug("In Endpoint.message_received")

    def send(self, msg, headers=None):
        """
        Public send method.
        Calls _build_msg (_build_header and _build_payload), then _send which puts it through the Interceptor stack(s).

        @param  msg         The message to send. Will be passed into _build_payload. You may modify the contents there.
        @param  headers     Optional headers to send. Will override anything produced by _build_header.
        """
        _msg, _header = self._build_msg(msg)
        if headers: _header.update(headers)
        return self._send(_msg, _header)

    def _send(self, msg, headers=None):
        """
        """
        log.debug("In Endpoint._send: %s", headers)
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
                log.debug("client_recv waiting for a message")
                msg, headers, delivery_tag = self.channel.recv()
                log.debug("client_recv got a message")
                try:
                    self._message_received(msg, headers)
                finally:
                    # always ack a listener response
                    self.channel.ack(delivery_tag)

        # @TODO: spawn should be configurable to maybe the proc_sup in the container?
        self._recv_greenlet = spawn(client_recv)

    def close(self):
        if self._recv_greenlet is not None:
            self._recv_greenlet.kill()
        if self.channel is not None:
            self.channel.close()

    def _build_header(self, raw_msg):
        """
        Assembles the headers of a message from the raw message's content.
        """
        log.debug("Endpoint _build_header")
        return {}

    def _build_payload(self, raw_msg):
        """
        Assembles the payload of a message from the raw message's content.

        @TODO will this be used? seems unlikely right now.
        """
        log.debug("Endpoint _build_payload")
        return raw_msg

    def _build_msg(self, raw_msg):
        """
        Builds a message (headers/payload) from the raw message's content.
        You typically do not need to override this method, but override the _build_header
        and _build_payload methods.

        @returns A 2-tuple of payload, headers
        """
        log.debug("Endpoint _build_msg")
        header = self._build_header(raw_msg)
        payload = self._build_payload(raw_msg)

        return payload, header

class EndpointFactory(object):
    """
    Creates new channel/endpoint pairs for communication.
    This base class only deals with communication
    patterns that send first (and possibly get a response). The derived ListeningEventFactory listens
    first.

    TODO Rename this.
    """
    endpoint_type = Endpoint
    channel_type = BidirClientChannel
    name = None
    node = None     # connection to the broker, basically

    # Endpoints
    # TODO: Make weakref or replace entirely
    endpoint_by_name = {}

    def __init__(self, node=None, name=None):
        """
        name can be a to address or a from address in the derived ListeningEndpointFactory. Either a string
        or a 2-tuple of (exchange, name).
        """

        if not isinstance(name, tuple):
            name = (bootstrap.sys_name, name)

        self.node = node
        self.name = name

        if name in self.endpoint_by_name:
            self.endpoint_by_name[name].append(self)
        else:
            self.endpoint_by_name[name] = [self]

    def create_endpoint(self, to_name=None, existing_channel=None, **kwargs):
        """
        @param  to_name     Either a string or a 2-tuple of (exchange, name)
        """
        if existing_channel:
            ch = existing_channel
        else:
            name = to_name or self.name
            assert name
            if not isinstance(name, tuple):
                name = (bootstrap.sys_name, name)
            #ch = self.node.channel(self.channel_type)
            ch = self.channel_type()
            self.node.channel(ch)

            # @TODO: bla
            if hasattr(ch, 'connect'):
                ch.connect(name)

        e = self.endpoint_type(**kwargs)
        e.attach_channel(ch)

        return e

    def close(self):
        """
        To be defined by derived classes. Cleanup any resources here, such as channels being open.
        """
        pass

class ExchangeManagementEndpoint(Endpoint):
    def create_xs(self, name):
        pass

class ExchangeManagement(EndpointFactory):
    endpoint_type = ExchangeManagementEndpoint
    channel_type = BaseChannel

    def __init__(self, **kwargs):
        self._pub_ep = None
        EndpointFactory.__init__(self, **kwargs)

    def create_xs(self, name):
        if not self._exchange_ep:
            self._exchange_ep = self.create_endpoint(self.name)

        self._exchange_ep.create_xs(name)

    def close(self):
        if self._exchange_ep:
            self._exchange_ep.close()

class OLDBinderListener(object):
    def __init__(self, node, name, endpoint_factory, listening_channel_type, spawn_callable):
        """
        @param spawn_callable   A callable to spawn a new received message worker thread. Calls with
                                the callable to be spawned and args. If None specified, does not create
                                a new thread: all processing is done synchronously.
        """
        self._node = node
        self._name = name
        self._ent_fact = endpoint_factory or ListeningEndpointFactory(node, name)
        self._ch_type = listening_channel_type or Bidirectional
        self._spawn = spawn_callable or (lambda cb, *args: cb(*args))
        self._chan = None
        self._ready_event = event.AsyncResult()

    def get_ready_event(self):
        """
        Returns an AsyncResult you can use to wait on to determine if this BinderListener has been setup
        and is ready to accept messages.

        @TODO: this sounds a lot like lifecycle
        """
        return self._ready_event

    def listen(self):
        log.debug("BinderListener.listen")
        self._chan = self._node.channel(self._ch_type)
        self._chan.bind((bootstrap.sys_name, self._name))
        self._chan.listen()

        self._ready_event.set(True)

        while True:
            log.debug("BinderListener: %s blocking waiting for message" % str(self._name))
            try:
                req_chan = self._chan.accept()
                msg, headers = req_chan.recv()
                log.debug("BinderListener %s received message: %s, headers: %s", self._name, msg, headers)
                e = self._ent_fact.create_endpoint(existing_channel=req_chan)   # @TODO: reply-to here?

                self._spawn(e._message_received, msg, headers)

            except ChannelError as ex:
                log.exception('Channel error during BinderListener.listen')
                switch()
            except ChannelClosedError as ex:
                log.debug('Channel was closed during BinderListener.listen')
                break

    def close(self):
        if self._chan: self._chan.close()

class ListeningEndpointFactory(EndpointFactory):
    """
    Establishes channel type for a host of derived, listen/react endpoint factories.
    """
    #channel_type = Bidirectional
    #channel_type = ListenChannel        # channel type is perverted here - we don't produce this, we just make one to listen on

    def __init__(self, node=None, name=None):
        EndpointFactory.__init__(self, node=node, name=name)
        self._ready_event = event.Event()

    def get_ready_event(self):
        """
        Returns an async event you can .wait() on.
        Used to indicate when listen() is ready to start listening.
        """
        return self._ready_event

    def _create_main_channel(self):
        return ListenChannel()

    def listen(self):
        log.debug("LEF.listen")

        self._chan = self._create_main_channel()
        self.node.channel(self._chan)
        self._chan.setup_listener(self.name, binding=self.name[1])
        self._chan.start_consume()

        # notify any listeners of our readiness
        self._ready_event.set()

        while True:
            log.debug("LEF: %s blocking, waiting for a message" % str(self.name))
            try:
                newchan = self._chan.accept()
                msg, headers, delivery_tag = newchan.recv()
                log.debug("LEF %s received message %s, headers %s, delivery_tag %s", self.name, msg, headers, delivery_tag)

                e = self.create_endpoint(existing_channel=newchan)

                e._message_received(msg, headers)

                # ack will only take place if message_received went ok
                newchan.ack(delivery_tag)

            except ChannelError as ex:
                log.exception('Channel error during LEF.listen')
                switch()

            except ChannelClosedError as ex:
                log.debug('Channel was closed during LEF.listen')
                break

    def close(self):
        EndpointFactory.close(self)
        self._chan.close()

#
# PUB/SUB
#

class PublisherEndpoint(Endpoint):
    pass

class Publisher(EndpointFactory):
    """
    Simple publisher sends out broadcast messages.
    """

    endpoint_type = PublisherEndpoint
    #channel_type = PubSub
    channel_type = PubChannel

    def __init__(self, **kwargs):
        self._pub_ep = None
        EndpointFactory.__init__(self, **kwargs)

    def publish(self, msg):
        # @TODO: needs thread safety
        if not self._pub_ep:
            self._pub_ep = self.create_endpoint(self.name)

        self._pub_ep.send(msg)

    def close(self):
        """
        Closes the opened publishing channel, if we've opened it previously.
        """
        if self._pub_ep:
            self._pub_ep.close()



class SubscriberEndpoint(Endpoint):
    """
    @TODO: Should have routing mechanics, possibly shared with other listener endpoint types
    """
    def __init__(self, callback):
        Endpoint.__init__(self)
        self.set_callback(callback)

    def set_callback(self, callback):
        """
        Sets the callback to be used by this SubscriberEndpoint when a message is received.
        """
        self._callback = callback

    def message_received(self, msg, headers):
        Endpoint.message_received(self, msg, headers)
        assert self._callback, "No callback provided, cannot route subscribed message"

        self._callback(msg, headers)


class Subscriber(ListeningEndpointFactory):

    endpoint_type = SubscriberEndpoint
    #channel_type = PubSub

    def _create_main_channel(self):
        return SubscriberChannel()

    def __init__(self, callback=None, **kwargs):
        """
        @param  callback should be a callable with one arg: msg
        """
        assert callback, "No callback provided"
        self._callback = callback
        ListeningEndpointFactory.__init__(self, **kwargs)

    def create_endpoint(self, **kwargs):
        log.debug("Subscriber.create_endpoint override")
        return ListeningEndpointFactory.create_endpoint(self, callback=self._callback, **kwargs)


#
# BIDIRECTIONAL ENDPOINTS
#
class BidirectionalEndpoint(Endpoint):
    pass

class BidirectionalListeningEndpoint(Endpoint):
    pass

#
#  REQ / RESP (and RPC)
#

class RequestEndpoint(BidirectionalEndpoint):
    def _send(self, msg, headers=None):
        log.debug("RequestEndpoint.send")

        if not self._recv_greenlet:
            self.channel.setup_listener((self.channel._send_name[0], None)) # @TODO: not quite right..
            self.channel.start_consume()
            self.spawn_listener()

        self.response_queue = event.AsyncResult()
        self.message_received = lambda m, h: self.response_queue.set((m, h))

        Endpoint._send(self, msg, headers=headers)

        result_data, result_headers = self.response_queue.get()#timeout=CFG.endpoint.receive.timeout)
        log.debug("Got response to our request: %s, headers: %s", result_data, result_headers)
        return result_data, result_headers

class RequestResponseClient(EndpointFactory):
    """
    Sends a request, waits for a response.
    """
    endpoint_type = RequestEndpoint

    def request(self, msg):
        log.debug("RequestResponseClient.request: %s" % str(msg))
        e = self.create_endpoint(self.name)
        try:
            retval, headers = e.send(msg)
        finally:
            # always close, even if endpoint raised a logical exception
            e.close()
        return retval

class ResponseEndpoint(BidirectionalListeningEndpoint):
    """
    The listener side makes one of these.
    """
    pass

class RequestResponseServer(ListeningEndpointFactory):
    endpoint_type = ResponseEndpoint

    def _create_main_channel(self):
        return ServerChannel()

class RPCRequestEndpoint(RequestEndpoint):

    def _send(self, msg, headers=None):
        log.debug("RPCRequestEndpoint.send (call_remote): %s" % str(msg))

        res, res_headers = RequestEndpoint._send(self, msg, headers=headers)
        log.debug("RPCRequestEndpoint got this response: %s, headers: %s" % (str(res), str(res_headers)))

        # Check response header
        if res_headers["status_code"] == 200:
            log.debug("OK status")
            return res, res_headers
        else:
            log.debug("Bad status: %d" % res_headers["status_code"])
            log.debug("Error message: %s" % res_headers["error_message"])
            self._raise_exception(res_headers["status_code"], res_headers["error_message"])

        return res, res_headers

    def _raise_exception(self, code, message):
        if code == exception.BAD_REQUEST:
            log.debug("Raising BadRequest")
            raise exception.BadRequest(message)
        elif code == exception.UNAUTHORIZED:
            log.debug("Raising Unauthorized")
            raise exception.Unauthorized(message)
        if code == exception.NOT_FOUND:
            log.debug("Raising NotFound: %s" % str(message))
            raise exception.NotFound(message)
        if code == exception.TIMEOUT:
            log.debug("Raising Timeout")
            raise exception.Timeout(message)
        if code == exception.CONFLICT:
            log.debug("Raising Conflict")
            raise exception.Conflict(message)
        if code == exception.SERVICE_UNAVAILABLE:
            log.debug("Raising ServiceUnavailable")
            raise exception.ServiceUnavailable(message)
        else:
            log.debug("Raising ServerError")
            raise exception.ServerError(message)

class RPCClient(RequestResponseClient):
    endpoint_type = RPCRequestEndpoint

    def __init__(self, iface=None, **kwargs):
        if isinstance(iface, interface.interface.InterfaceClass):
            self._define_interface(iface)
        elif isinstance(iface, IonServiceDefinition):
            self._define_svcdef(iface)

        RequestResponseClient.__init__(self, **kwargs)

    def _define_svcdef(self, svc_def):
        """
        Defines an RPCClient's attributes from an IonServiceDefinition.
        """
        for meth in svc_def.methods:
            name = meth.op_name
            info = meth.def_in
            doc = meth.__doc__

            setattr(self, name, _Command(self.request, name, info, doc))

    def _define_interface(self, iface):
        """
        from dorian's RPCClientEntityFromInterface: sets attrs on this client instance from an interface definition.
        """
        namesAndDesc = iface.namesAndDescriptions()
        for name, command in namesAndDesc:
            #log.debug("name: %s" % str(name))
            #log.debug("command: %s" % str(command))
            info = command.getSignatureInfo()
            #log.debug("info: %s" % str(info))
            doc = command.getDoc()
            #log.debug("doc: %s" % str(doc))
            setattr(self, name, _Command(self.request, name, info, doc))        # @TODO: _Command is a callable is non-obvious, make callback to call_remote here explicit

class RPCResponseEndpoint(ResponseEndpoint):
    def __init__(self, routing_obj=None, **kwargs):
        ResponseEndpoint.__init__(self)
        self._routing_obj = routing_obj

    def message_received(self, msg, headers):
        assert self._routing_obj, "How did I get created without a routing object?"

        log.debug("In RPCResponseEndpoint.message_received")
        log.debug("chan: %s" % str(self.channel))
        log.debug("msg: %s" % str(msg))
        log.debug("headers: %s" % str(headers))

        cmd_dict = msg

        result = None
        response_headers = {}
        try:
            result = self._call_cmd(cmd_dict)
            response_headers = { 'status_code': 200, 'error_message': '' }
        except exception.IonException as ex:
            log.debug("Got error response")
            response_headers = self._create_error_response(ex)

        self.send(result, response_headers)

    def _call_cmd(self, cmd_dict):
        log.debug("In RPCResponseEndpoint._call_cmd")
        log.debug("cmd_dict: %s" % str(cmd_dict))
        meth = getattr(self._routing_obj, cmd_dict['method'])
        log.debug("meth: %s" % str(meth))
        args = cmd_dict['args']
        log.debug("args: %s" % str(args))
        return meth(*args)

    def _create_error_response(self, ex):
        return {'status_code': ex.get_status_code(), 'error_message': ex.get_error_message()}

class RPCServer(RequestResponseServer):
    endpoint_type = RPCResponseEndpoint

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


class ProcessRPCRequestEndpoint(RPCRequestEndpoint):

    def __init__(self, process=None, **kwargs):
        RPCRequestEndpoint.__init__(self, **kwargs)
        self._process = process

    def _build_invocation(self, **kwargs):
        newkwargs = kwargs.copy()
        newkwargs.update({'process':self._process})

        inv = RPCRequestEndpoint._build_invocation(self, **newkwargs)
        return inv

    def _intercept_msg_in(self, inv):
        """
        Override for incoming message interception.

        This is a request, so the order should be Message, Process
        """
        inv_one = RPCRequestEndpoint._intercept_msg_in(self, inv)
        inv_two = process_interceptors(interceptors["process_incoming"] if "process_incoming" in interceptors else [], inv_one)
        return inv_two

    def _intercept_msg_out(self, inv):
        """
        Override for outgoing message interception.

        This is request, so the order should be Process, Message
        """
        inv_one = process_interceptors(interceptors["process_outgoing"] if "process_outgoing" in interceptors else [], inv)
        inv_two = RPCRequestEndpoint._intercept_msg_out(self, inv_one)

        return inv_two

    def _build_header(self, raw_msg):
        """
        See: https://confluence.oceanobservatories.org/display/CIDev/Process+Model

        From R1 Conversations:
            headers: (many get copied to message instance via R1 interceptor)
                sender              - set by envelope interceptor (headers.get('sender', message.get('sender'))
                sender-name         - set in Process.send
                conv-id             - set by envelope interceptor (passed in or ''), set by Process.send (from conv.conv_id, or created new if no conv)
                conv-seq            - set by envelope interceptor (passed in or '1'), or set by Process.reply
                performative        - set by envelope interceptor (passed in or ''), set by Process.send supercalls, possible values: request, inform_result, failure, [agree, refuse]
                protocol            - set by envelope interceptor (passed in or ''), set by Process.send (from conv.protocol or CONV_TYPE_NONE), possible values: rpc...
                reply-to            - set by envelope interceptor (reply-to, sender)
                user-id             - set by envelope interceptor (passed in or "ANONYMOUS")
                expiry              - set by envelope interceptor (passed in or "0")
                quiet               - (unused)
                encoding            - set by envelope interceptor (passed in or "json"), set by codec interceptor (ION_R1_GPB)
                language            - set by envelope interceptor (passed in or "ion1")
                format              - set by envelope interceptor (passed in or "raw")
                ontology            - set by envelope interceptor (passed in or '')
                status              - set by envelope interceptor (passed in or 'OK')
                ts                  - set by envelope interceptor (always current time in ms)
                op                  - set by envelope interceptor (copies 'operation' passed in)
            conversation?
            process
            content

        """

        context = self._process.get_context()
        log.debug('TODO: PROCESS RPC REQUEST ENDPOINT HAS CONTEXT OF %s', context)

        # must set here: sender-name, conv-id, conv-seq, performative
        header = RPCRequestEndpoint._build_header(self, raw_msg)

        header.update({'sender-name'  : self._process.name,     # @TODO
                       'sender'       : 'todo',#self.channel._chan_name,
                       'conv-id'      : 'none',                   # @TODO
                       'conv-seq'     : 1,
                       'performative' : 'request'})
        
        # use context to set security attributes forward
        if isinstance(context, dict):
            # @TODO: these names, get them right
            user_id             = context.get('user-id', None)
            container_signature = context.get('signature', None)
            role_id             = context.get('role-id', None)

            if user_id:             header['user-id'] = user_id
            if container_signature: header['signature'] = signature
            if role_id:             header['role-id'] = role_id

        return header
    
class ProcessRPCClient(RPCClient):
    endpoint_type = ProcessRPCRequestEndpoint

    def __init__(self, process=None, **kwargs):
        self._process = process
        RPCClient.__init__(self, **kwargs)

    def create_endpoint(self, to_name=None, existing_channel=None, **kwargs):
        if not self._process:
            raise StandardError("No Process specified")

        newkwargs = kwargs.copy()
        newkwargs['process'] = self._process
        return RPCClient.create_endpoint(self, to_name, existing_channel, **newkwargs)

class ProcessRPCResponseEndpoint(RPCResponseEndpoint):

    def __init__(self, process=None, **kwargs):
        RPCResponseEndpoint.__init__(self, **kwargs)
        self._process = process
        assert process

    def message_received(self, msg, headers):
        """
        Message received override.

        Sets the process' context here to be picked up by subsequent calls out by this service to other services.
        """
        with self._process.push_context(headers):
            return RPCResponseEndpoint.message_received(self, msg, headers)

    def _build_invocation(self, **kwargs):
        newkwargs = kwargs.copy()
        newkwargs.update({'process':self._process})

        inv = RPCResponseEndpoint._build_invocation(self, **newkwargs)
        return inv

    def _intercept_msg_in(self, inv):
        """
        Override for incoming message interception.

        This is response incoming, so the order should be Message, Process
        """
        inv_one = RPCResponseEndpoint._intercept_msg_in(self, inv)
        inv_two = process_interceptors(interceptors["process_incoming"] if "process_incoming" in interceptors else [], inv_one)
        return inv_two

    def _intercept_msg_out(self, inv):
        """
        Override for outgoing message interception.

        This is response outgoing, so the order should be Process, Message
        """
        inv_one = process_interceptors(interceptors["process_outgoing"] if "process_outgoing" in interceptors else [], inv)
        inv_two = RPCResponseEndpoint._intercept_msg_out(self, inv_one)
        return inv_two

class ProcessRPCServer(RPCServer):
    endpoint_type = ProcessRPCResponseEndpoint

    def __init__(self, process=None, **kwargs):
        assert process
        self._process = process
        RPCServer.__init__(self, **kwargs)

    def create_endpoint(self, **kwargs):
        newkwargs = kwargs.copy()
        newkwargs['process'] = self._process
        return RPCServer.create_endpoint(self, **newkwargs)

class _Command(object):
    """
    RPC Message Format
    Command method generated from interface.

    @TODO: CURRENTLY UNUSED SIGINFO FOR VALIDATION
    Note: the required siginfo could be used by the client to catch bad
    calls before it makes them. 
    If calls are only made using named arguments, then the optional siginfo
    can validate that the correct named arguments are used.
    """

    def __init__(self, callback, name, siginfo, doc):
        #log.debug("In _Command.__init__")
        #log.debug("client: %s" % str(client))
        #log.debug("name: %s" % str(name))
        #log.debug("siginfo: %s" % str(siginfo))
        #log.debug("doc: %s" % str(doc))
        self.callback = callback
        self.name = name
#        self.positional = siginfo['positional']
#        self.required = siginfo['required']
#        self.optional = siginfo['optional']
        self.__doc__ = doc

    def __call__(self, *args):
        log.debug("In _Command.__call__")
        command_dict = self._command_dict_from_call(*args)
        return self.callback(command_dict)

    def _command_dict_from_call(self, *args):
        """
        parameters specified by name
        """
        log.debug("In _Command._command_dict_from_call")
        cmd_dict = {}
        cmd_dict['method'] = self.name
        cmd_dict['args'] = args
        log.debug("cmd_dict: %s" % str(cmd_dict))
        return cmd_dict
