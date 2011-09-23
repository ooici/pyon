"""
TODO:
[ ] Plug-able RPC message encoders. Can the Channel try to encode and
decode for the Entity?
[ ] Consuming Entity for subscription/event handler endpoints
[ ] Simple Producing Entity
"""
from gevent import event

import json # generalize

from pyon.core.bootstrap import IonObject
from pyon.core.object import IonObjectBase
from pyon.core import exception
from pyon.net.channel import Bidirectional, BidirectionalClient, PubSub
from pyon.util.async import spawn
from pyon.util.log import log

class Entity(object):

    channel = None
    _recv_greenlet = None

    def attach_channel(self, channel):
        log.debug("In Entity.attach_channel")
        log.debug("channel %s" % str(channel))
        self.channel = channel

    def channel_attached(self):
        """
        """
        log.debug("In Entity.channel_attached")

    def message_received(self, msg):
        """
        """
        log.debug("In Entity.message_received")

    def send(self, msg):
        """
        """
        log.debug("In Entity.send")
        self.channel.send(msg)

    def close(self):
        # @TODO: need a channel close probably!
        #self.channel.close()
        if self._recv_greenlet:
            self._recv_greenlet.kill()

class EntityFactory(object):
    """
    Rename this.

    Creates new channel/entity pairs for communication. This base class only deals with communication
    patterns that send first (and possibly get a response). The derived ListeningEventFactory listens
    first.
    """
    entity_type = Entity
    channel_type = BidirectionalClient
    name = None
    node = None     # connection to the broker, basically

    def __init__(self, node=None, name=None):  #, entity_type=None, channel_type=None):   # took this out, didn't like it - set it class level instead
        """
        name can be a to address or a from address in the derived ListeningEntityFactory.
        """
        self.node = node
        self.name = name
        ##self.entity_type = entity_type or Entity
        ###self.channel_type = channel_type or self.__class__.channel_type or BidirectionalClient

    def create_entity(self, to_name=None, existing_channel=None):
        name = to_name or self.name
        assert name

        if existing_channel:
            ch = existing_channel
        else:
            ch = self.node.channel(self.channel_type)
            ch.connect(('amq.direct', name))

        e = self.entity_type()
        e.attach_channel(ch)

        # @TODO: move this to the entity itself perhaps? or should the Entity know what channel type instead of the factory?
        if self.channel_type in [Bidirectional, BidirectionalClient]:
            log.debug("Setting up bidir listener")
            def client_recv(chan, entity):
                while True:
                    data = chan.recv()
                    log.debug("client_recv got a message")
                    entity.message_received(data)
            e._recv_greenlet = spawn(client_recv, ch, e)

        return e

class ListeningEntityFactory(EntityFactory):
    """
    Rename this.

    Listens for incoming messages, on receipt, forks off a new channel, creates an entity and lets the
    entity do its job.
    """
    channel_type = Bidirectional

    def listen(self):
        """
        Creates a channel to listen on, endlessly loops on message receipts.

        Greenlet?
        """
        def generic_server(chan):
            log.debug("In generic_server. Binding name: %s" % str(self.name))
            chan.bind(('amq.direct', self.name))
            chan.listen()
            while True:
                log.debug("service: %s blocking waiting for message" % str(self.name))
                req_chan = chan.accept()
                msg = req_chan.recv()
                log.debug("service %s received message: %s" % (str(self.name),str(msg)))
                entity = self.create_entity(existing_channel=req_chan)   # @TODO: reply-to here?
                entity.message_received(msg)

        log.debug("bout to call channelelelel %s" % str(self.name))
        ch = self.node.channel(self.channel_type)
        generic_server(ch)
        #return spawn(generic_server, ch)

    def msg_received(self, msg):
        self.dispatch_msg(msg)

    def dispatch_msg(self, msg):
        log.warn("Dispatch message, needs to be overridden")

#
# PUB/SUB
#

class PublisherEntity(Entity):
    pass

class Publisher(EntityFactory):
    """
    Simple publisher sends out broadcast messages.
    """

    entity_type = PublisherEntity
    channel_type = PubSub

    def publish(self, msg):
        e = self.create_entity(self.name)
        e.send(msg)
        e.close()

class SubscriberEntity(Entity):
    """
    @TODO: Should have routing mechanics, possibly shared with other listener entity types
    """
    def message_received(self, msg):
        Entity.message_received(self, msg)
        assert self._callback, "Should have been patched on in Subscriber.create_entity, how did i get created?"  # @TODO: remove obv

        self._callback(msg)
        

class Subscriber(ListeningEntityFactory):

    entity_type = SubscriberEntity
    channel_type = PubSub

    def __init__(self, callback=None, **kwargs):
        """
        @param  callback should be a callable with one arg: msg
        """
        assert callback
        self._callback = callback
        ListeningEntityFactory.__init__(self, **kwargs)

    def create_entity(self, **kwargs):
        log.debug("Subscriber.create_entity override")
        e = ListeningEntityFactory.create_entity(self, **kwargs)

        # @TODO would prefer this to be part of initializer for entity, perhaps kwarg you can pass into create_entity?
        e._callback = self._callback
        return e


#
#  REQ / RESP (and RPC)
#

class RequestEntity(Entity):
    pass

class RequestResponseClient(EntityFactory):
    """
    Sends a request, waits for a response.
    """
    entity_type = RequestEntity

    def request(self, msg):
        log.debug("RequestResponseClient.request: %s" % str(msg))
        e = self.create_entity(self.name)
        self.response_queue = event.AsyncResult()
        e.message_received = lambda m: self.response_queue.set(m)

        e.send(msg)

        result_data = self.response_queue.get()
        log.debug("got response to our request: %s" % str(result_data))
        return result_data

class ResponseEntity(Entity):
    """
    The listener side makes one of these.
    """
    pass

class RequestResponseServer(ListeningEntityFactory):
    entity_type = ResponseEntity

    pass


class RPCRequestEntity(RequestEntity):
    pass

class RPCClient(RequestResponseClient):
    entity_type = RPCRequestEntity

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
            setattr(self, name, _Command(self, name, info, doc))        # @TODO: _Command is a callable is non-obvious, make callback to call_remote here explicit

    def call_remote(self, cmd_dict):
        log.debug("RPCClient call_remote: %s" % str(cmd_dict))

        wrapped_cmd_dict = {"header": {}, "payload": cmd_dict}
        send_data = IonEncoder().encode(wrapped_cmd_dict)

        result_data = self.request(send_data)
        res = json.loads(result_data, object_hook=as_ionObject)

        log.debug("Call_remote got this response: %s" % str(res))

        # @TODO: handle exceptions here? or in entity?

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

class RPCResponseEntity(ResponseEntity):
    def __init__(self, **kwargs):
        self._routing_obj = None

    def message_received(self, msg):
        assert self._routing_obj, "How did I get created without a routing object?"

        log.debug("In RPCResponseEntity.message_received")
        log.debug("chan: %s" % str(self.channel))
        log.debug("msg: %s" % str(msg))

        wrapped_req = json.loads(msg, object_hook=as_ionObject)
        cmd_dict = wrapped_req["payload"]

        try:
            result = self._call_cmd(cmd_dict)
            # Wrap message with response header
            wrapped_result = {"header": {"status_code": 200, "error_message": ""}, "payload": result}
        except exception.IonException as ex:
            log.debug("Got error response")
            wrapped_result = self._create_error_response(ex)

        #self.channel.send(response_msg)
        encoded_response = IonEncoder().encode(wrapped_result)
        log.debug("response_msg: %s" % str(encoded_response))
        self.send(encoded_response)

    def _call_cmd(self, cmd_dict):
        log.debug("In RPCResponseEntity._call_cmd")
        log.debug("cmd_dict: %s" % str(cmd_dict))
        meth = getattr(self._routing_obj, cmd_dict['method'])
        log.debug("meth: %s" % str(meth))
        args = cmd_dict['args']
        log.debug("args: %s" % str(args))
        return meth(*args)

    def _create_error_response(self, ex):
        error_msg = {"header": {"status_code": ex.get_status_code(), "error_message": ex.get_error_message()}}
        return error_msg


class RPCServer(RequestResponseServer):
    entity_type = RPCResponseEntity

    def __init__(self, service=None, **kwargs):
        log.debug("In RPCServer.__init__")
        self._service = service
        RequestResponseServer.__init__(self, **kwargs)

    def create_entity(self, **kwargs):
        """
        @TODO: push this into RequestResponseServer
        """
        log.debug("RPCServer.create_entity override")
        e = RequestResponseServer.create_entity(self, **kwargs)

        # @TODO would prefer this to be part of initializer for entity, perhaps kwarg you can pass into create_entity?
        e._routing_obj = self._service
        return e


class _Command(object):
    """
    RPC Message Format
    Command method generated from interface.
    
    Note: the required siginfo could be used by the client to catch bad
    calls before it makes them. 
    If calls are only made using named arguments, then the optional siginfo
    can validate that the correct named arguments are used.
    """

    def __init__(self, client, name, siginfo, doc):
        #log.debug("In _Command.__init__")
        #log.debug("client: %s" % str(client))
        #log.debug("name: %s" % str(name))
        #log.debug("siginfo: %s" % str(siginfo))
        #log.debug("doc: %s" % str(doc))
        self.client = client
        self.name = name
        self.positional = siginfo['positional']
        self.required = siginfo['required']
        self.optional = siginfo['optional']
        self.__doc__ = doc

    def __call__(self, *args):
        log.debug("In _Command.__call__")
        command_dict = self._command_dict_from_call(*args)
        return self.client.call_remote(command_dict)

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

class IonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, IonObjectBase):
            res = obj.__dict__
            res["__isAnIonObject"] = True
            return res
        return json.JSONEncoder.default(self, obj)

def as_ionObject(dct):
    if "__isAnIonObject" in dct:
        del dct["__isAnIonObject"]
        ionObj = IonObject(dct["type_"].encode('ascii'), dct)
        return ionObj
    return dct
