"""
TODO:
[ ] Plug-able RPC message encoders. Can the Channel try to encode and
decode for the Entity?
[ ] Consuming Entity for subscription/event handler endpoints
[ ] Simple Producing Entity
"""
from gevent import event

import json # generalize

from anode.core.bootstrap import AnodeObject
from anode.core.object import AnodeObjectBase
from anode.core import exception
from anode.util.log import log

class Entity(object):

    channel = None

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

class RPCEntityFromService(Entity):
    """
    Going to need a way to enforce the downstream service interface
    """

    def __init__(self, service):
        log.debug("In __init__")
        self.service = service

    def message_received(self, chan, msg):
        log.debug("In RPCEntityFromService.message_received")
        log.debug("chan: %s" % str(chan))
        log.debug("msg: %s" % str(msg))

        wrapped_req = json.loads(msg, object_hook=as_anodeObject)
        cmd_dict = wrapped_req["payload"]

        # Need error handling
        #try:
        try:
            result = self._call_cmd(cmd_dict)
            # Wrap message with response header
            wrapped_result = {"header": {"status_code": 200, "error_message": ""}, "payload": result}
        except exception.IonException as ex:
            log.debug("Got error response")
            wrapped_result = self.create_error_response(ex)

        #self.channel.send(response_msg)
        encoded_response = AnodeEncoder().encode(wrapped_result)
        log.debug("response_msg: %s" % str(encoded_response))
        chan.send(encoded_response)

    def create_error_response(self, ex):
        error_msg = {"header": {"status_code": ex.get_status_code(), "error_message": ex.get_error_message()}}
        return error_msg

    def _call_cmd(self, cmd_dict):
        log.debug("In RPCEntityFromService._call_cmd")
        log.debug("cmd_dict: %s" % str(cmd_dict))
        meth = getattr(self.service, cmd_dict['method'])
        log.debug("meth: %s" % str(meth))
        args = cmd_dict['args']
        log.debug("args: %s" % str(args))
        return meth(*args)


class RPCClientEntityFromInterface(Entity):
    """
    """
    response_queue = None #clean up

    #def __init__(self, service_name, iface):
    def __init__(self, iface):
        log.debug("In RPCClientEntityFromInterface.__init__")
        log.debug("iface: %s" % str(iface))
        #self.service_name = service_name # The name of the service this is a client for
        namesAndDesc = iface.namesAndDescriptions()
        for name, command in namesAndDesc:
            log.debug("name: %s" % str(name))
            log.debug("command: %s" % str(command))
            info = command.getSignatureInfo()
            log.debug("info: %s" % str(info))
            doc = command.getDoc()
            log.debug("doc: %s" % str(doc))
            setattr(self, name, _Command(self, name, info, doc))

    def call_remote(self, cmd_dict):
        """
        Send the command to the remote service.
        Returns a Deferred that fires with the response.
        """
        log.debug("In RPCClientEntityFromInterface.call_remote")
        log.debug("cmd_dict: %s" % str(cmd_dict))
        wrapped_cmd_dict = {"header": {}, "payload": cmd_dict}
        send_data = AnodeEncoder().encode(wrapped_cmd_dict)
        log.debug("wrapped send_data: %s" % str(send_data))
        #result_data = self.channel.send(self.service_name, send_data)
        log.debug("channel: " + str(self.channel))
#        self.channel.send(send_data)
        # Wrap message with request header
        self.channel.send(send_data)
        log.debug("After send")
        self.response_queue = event.AsyncResult()
        log.debug("Before get")
        result_data = self.response_queue.get()
        log.debug("Before loads. result_data: %s" % str(result_data))
        res = json.loads(result_data, object_hook=as_anodeObject)
        log.debug("res: %s" % str(res))
        # Check response header
        header = res["header"]
        if header["status_code"] == 200:
            log.debug("OK status")
            return res["payload"]
        else:
            log.debug("Bad status: %d" % header["status_code"])
            log.debug("Error message: %s" % header["error_message"])
            self.raise_exception(header["status_code"], header["error_message"])

    def raise_exception(self, code, message):
        if code == exception.BAD_REQUEST:
            log.debug("Raising BadRequest");
            raise exception.BadRequest(message)
        elif code == exception.UNAUTHORIZED:
            log.debug("Raising Unauthorized");
            raise exception.Unauthorized(message)
        if code == exception.NOT_FOUND:
            log.debug("Raising NotFound");
            raise exception.NotFound(message)
        if code == exception.TIMEOUT:
            log.debug("Raising Timeout");
            raise exception.Timeout(message)
        if code == exception.CONFLICT:
            log.debug("Raising Conflict");
            raise exception.Conflict(message)
        if code == exception.SERVICE_UNAVAILABLE:
            log.debug("Raising ServiceUnavailable");
            raise exception.ServiceUnavailable(message)
        else:
            log.debug("Raising ServerError");
            raise exception.ServerError(message)

    def _rpc(self, data):
        log.debug("In RPCClientEntityFromInterface._rpc")
        self.channel.send(send_data)

    def message_received(self, msg):
        log.debug("In RPCClientEntityFromInterface.message_received")
        self.response_queue.set(msg) # hmm, channel already queues



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
        log.debug("In _Command.__init__")
        log.debug("client: %s" % str(client))
        log.debug("name: %s" % str(name))
        log.debug("siginfo: %s" % str(siginfo))
        log.debug("doc: %s" % str(doc))
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

class AnodeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, AnodeObjectBase):
            res = obj.__dict__
            res["__isAnAnodeObject"] = True
            return res
        return json.JSONEncoder.default(self, obj)

def as_anodeObject(dct):
    if "__isAnAnodeObject" in dct:
        del dct["__isAnAnodeObject"]
        anodeObj = AnodeObject(dct["type_"].encode('ascii'), dct)
        return anodeObj
    return dct
