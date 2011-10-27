from gevent import event

from pyon.core.bootstrap import CFG, sys_name
from pyon.core import exception
from pyon.net.channel import Bidirectional, BidirectionalClient, PubSub, ChannelError, ChannelClosedError
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

    def _message_received(self, msg):
        """
        Entry point for received messages in below channel layer. This method puts the message through
        the interceptor stack, then funnels the message into the message_received method.

        This method should not be overridden unless you are familiar with how the interceptor stack and
        friends work!
        """
        # interceptor point
        inv = self._build_invocation(path=Invocation.PATH_IN,
                                     message=msg)
        inv_prime = process_interceptors(interceptors["message_incoming"] if "message_incoming" in interceptors else [], inv)
        new_msg = inv_prime.message

        self.message_received(new_msg)

    def message_received(self, msg):
        """
        """
        log.debug("In Endpoint.message_received")

    def send(self, raw_msg):
        """
        """
        log.debug("In Endpoint.send")
        msg = self._build_msg(raw_msg)

        # interceptor point

        # @TODO dict check is a hax
        if isinstance(msg, dict):
            inv = self._build_invocation(path=Invocation.PATH_OUT,
                                         message=msg)
            inv_prime = process_interceptors(interceptors["message_outgoing"] if "message_outgoing" in interceptors else [], inv)
            new_msg = inv_prime.message
        else:
            new_msg = msg

        self.channel.send(new_msg)

    def spawn_listener(self):
        def client_recv():
            while True:
                log.debug("client_recv waiting for a message")
                data = self.channel.recv()
                log.debug("client_recv got a message")
                self._message_received(data)

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
        """
        log.debug("Endpoint _build_payload")
        return raw_msg

    def _build_msg(self, raw_msg):
        """
        Builds a message (headers/payload) from the raw message's content.
        You typically do not need to override this method, but override the _build_header
        and _build_payload methods.

        @returns A dict containing two keys: header and payload.
        """
        log.debug("Endpoint _build_msg")
        header = self._build_header(raw_msg)
        payload = self._build_payload(raw_msg)

        msg = {"header": header, "payload": payload}
        return msg

class EndpointFactory(object):
    """
    Creates new channel/endpoint pairs for communication.
    This base class only deals with communication
    patterns that send first (and possibly get a response). The derived ListeningEventFactory listens
    first.

    TODO Rename this.
    """
    endpoint_type = Endpoint
    channel_type = BidirectionalClient
    name = None
    node = None     # connection to the broker, basically

    # Endpoints
    # TODO: Make weakref or repace entirely
    endpoint_by_name = {}

    def __init__(self, node=None, name=None):
        """
        name can be a to address or a from address in the derived ListeningEndpointFactory. Either a string
        or a 2-tuple of (exchange, name).
        """
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
                name = (sys_name, name)
            ch = self.node.channel(self.channel_type)
            ch.connect(name)

        e = self.endpoint_type(**kwargs)
        e.attach_channel(ch)

        return e

    def close(self):
        """
        To be defined by derived classes. Cleanup any resources here, such as channels being open.
        """
        pass

class BinderListener(object):
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
        self._chan.bind((sys_name, self._name))
        self._chan.listen()

        self._ready_event.set(True)

        while True:
            log.debug("BinderListener: %s blocking waiting for message" % str(self._name))
            try:
                req_chan = self._chan.accept()
                msg = req_chan.recv()
                log.debug("BinderListener %s received message: %s" % (str(self._name),str(msg)))
                e = self._ent_fact.create_endpoint(existing_channel=req_chan)   # @TODO: reply-to here?

                self._spawn(e._message_received, msg)

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
    Designed to be used inside of a BinderListener.
    """
    channel_type = Bidirectional

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
    channel_type = PubSub

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

    def message_received(self, msg):
        Endpoint.message_received(self, msg)
        assert self._callback, "No callback provided, cannot route subscribed message"

        self._callback(msg)


class Subscriber(ListeningEndpointFactory):

    endpoint_type = SubscriberEndpoint
    channel_type = PubSub

    def __init__(self, callback=None, **kwargs):
        """
        @param  callback should be a callable with one arg: msg
        """
        assert callback
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
    def send(self, msg):
        log.debug("RequestEndpoint.send")

        if not self._recv_greenlet:
            self.spawn_listener()

        self.response_queue = event.AsyncResult()
        self.message_received = lambda m: self.response_queue.set(m)

        Endpoint.send(self, msg)

        result_data = self.response_queue.get(timeout=10)
        log.debug("got response to our request: %s" % str(result_data))
        return result_data

class RequestResponseClient(EndpointFactory):
    """
    Sends a request, waits for a response.
    """
    endpoint_type = RequestEndpoint

    def request(self, msg):
        log.debug("RequestResponseClient.request: %s" % str(msg))
        e = self.create_endpoint(self.name)
        try:
            retval = e.send(msg)
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

    pass


class RPCRequestEndpoint(RequestEndpoint):

    def send(self, msg):
        log.debug("RPCRequestEndpoint.send (call_remote): %s" % str(msg))

        res = RequestEndpoint.send(self, msg)
        log.debug("RPCRequestEndpoint got this response: %s" % str(res))

        # Check response header
        header = res["header"]
        if header["status_code"] == 200:
            log.debug("OK status")
            return res["payload"]
        else:
            log.debug("Bad status: %d" % header["status_code"])
            log.debug("Error message: %s" % header["error_message"])
            self._raise_exception(header["status_code"], header["error_message"])

        return res

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
        self._define_interface(iface)
        RequestResponseClient.__init__(self, **kwargs)

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
        self._response_headers = None
#        self._response_payload = None

    def _build_header(self, raw_msg):
        hdrs = ResponseEndpoint._build_header(self, raw_msg)
        hdrs.update(self._response_headers)
        return hdrs

    def message_received(self, msg):
        assert self._routing_obj, "How did I get created without a routing object?"

        log.debug("In RPCResponseEndpoint.message_received")
        log.debug("chan: %s" % str(self.channel))
        log.debug("msg: %s" % str(msg))

        #wrapped_req = json.loads(msg, object_hook=as_ionObject)
        #wrapped_req = msgpack.loads(msg)
        #wrapped_req = as_ionObject(wrapped_req)
        #cmd_dict = wrapped_req["payload"]
        cmd_dict = msg["payload"]

        result = None
        try:
            result = self._call_cmd(cmd_dict)
            self._response_headers = { 'status_code': 200, 'error_message': '' }
        except exception.IonException as ex:
            log.debug("Got error response")
            wrapped_result = self._create_error_response(ex)

        #self.channel.send(response_msg)
        self.send(result)

    def _call_cmd(self, cmd_dict):
        log.debug("In RPCResponseEndpoint._call_cmd")
        log.debug("cmd_dict: %s" % str(cmd_dict))
        meth = getattr(self._routing_obj, cmd_dict['method'])
        log.debug("meth: %s" % str(meth))
        args = cmd_dict['args']
        log.debug("args: %s" % str(args))
        return meth(*args)

    def _create_error_response(self, ex):
        self._response_headers = {'status_code': ex.get_status_code(), 'error_message': ex.get_error_message()}

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

    def __init__(self, process):
        RPCRequestEndpoint.__init__(self)
        self._process = process

    def _build_invocation(self, **kwargs):
        newkwargs = kwargs.copy()
        newkwargs.update({'process':self._process})

        inv = RPCRequestEndpoint._build_invocation(**newkwargs)
        return inv

    def _message_received(self, msg):
        """
        Override to send incoming messages through the process_incoming interceptor stack
        """
        # @TODO dict check is a hax
        if isinstance(msg, dict):
            inv = self._build_invocation(path=Invocation.PATH_IN,
                                         message=msg)
            inv_prime = process_interceptors(interceptors["process_incoming"] if "process_incoming" in interceptors else [], inv)
            new_msg = inv_prime.message
        else:
            new_msg = msg

        RPCRequestEndpoint._message_received(self, new_msg)

    def send(self, msg):
        """
        Override to send outgoing messages through the process_outgoing interceptor stack
        """
        # @TODO dict check is a hax
        if isinstance(msg, dict):
            inv = self._build_invocation(path=Invocation.PATH_OUT,
                                         message=msg)
            inv_prime = process_interceptors(interceptors["process_outgoing"] if "process_outgoing" in interceptors else [], inv)
            new_msg = inv_prime.message
        else:
            new_msg = msg

        RPCRequestEndpoint.send(self, new_msg)

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

        # must set here: sender-name, conv-id, conv-seq, performative
        header = RPCRequestEndpoint._build_header(self, raw_msg)

        header.update({'sender-name'  : self._process.name,     # @TODO
                       'sender'       : self.channel._chan_name,
                       'conv-id'      : None,                   # @TODO
                       'conv-seq'     : 1,
                       'performative' : 'request'})

        return header

class ProcessRPCResponseEndpoint(RPCResponseEndpoint):

    def __init__(self, process):
        RPCResponseEndpoint.__init__(self)
        self._process = process

    def _build_invocation(self, **kwargs):
        newkwargs = kwargs.copy()
        newkwargs.update({'process':self._process})

        inv = RPCRequestEndpoint._build_invocation(**newkwargs)
        return inv

    def _message_received(self, msg):
        """
        Override to send incoming messages through the process_incoming interceptor stack
        """
        # @TODO dict check is a hax
        if isinstance(msg, dict):
            inv = self._build_invocation(path=Invocation.PATH_IN,
                                         message=msg)
            inv_prime = process_interceptors(interceptors["process_incoming"] if "process_incoming" in interceptors else [], inv)
            new_msg = inv_prime.message
        else:
            new_msg = msg

        RPCResponseEndpoint._message_received(self, new_msg)

    def send(self, msg):
        """
        Override to send outgoing messages through the process_outgoing interceptor stack
        """
        # @TODO dict check is a hax
        if isinstance(msg, dict):
            inv = self._build_invocation(path=Invocation.PATH_OUT,
                                         message=msg)
            inv_prime = process_interceptors(interceptors["process_outgoing"] if "process_outgoing" in interceptors else [], inv)
            new_msg = inv_prime.message
        else:
            new_msg = msg

        RPCResponseEndpoint.send(self, new_msg)

class _Command(object):
    """
    RPC Message Format
    Command method generated from interface.
    
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
        self.positional = siginfo['positional']
        self.required = siginfo['required']
        self.optional = siginfo['optional']
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
