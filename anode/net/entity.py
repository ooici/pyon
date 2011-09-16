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

        cmd_dict = json.loads(msg, object_hook=as_anodeObject)

        # Need error handling
        #try:
        result = self._call_cmd(cmd_dict)
        response_msg = AnodeEncoder().encode(result)
        log.debug("response_msg: %s" % str(response_msg))

        #self.channel.send(response_msg)
        chan.send(response_msg)

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
        send_data = AnodeEncoder().encode(cmd_dict)
        log.debug("send_data: %s" % str(send_data))
        #result_data = self.channel.send(self.service_name, send_data)
        log.debug("channel: " + str(self.channel))
        self.channel.send(send_data)
        log.debug("After send")
        self.response_queue = event.AsyncResult()
        log.debug("Before get")
        result_data = self.response_queue.get()
        log.debug("Before loads")
        res = json.loads(result_data, object_hook=as_anodeObject)
        log.debug("res: %s" % str(res))
        return res

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
