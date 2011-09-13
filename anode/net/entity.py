"""
TODO:
[ ] Plug-able RPC message encoders. Can the Channel try to encode and
decode for the Entity?
[ ] Consuming Entity for subscription/event handler endpoints
[ ] Simple Producing Entity
"""
from gevent import event

import json # generalize

class Entity(object):

    channel = None

    def attach_channel(self, channel):
        self.channel = channel

    def channel_attached(self):
        """
        """

    def message_received(self, msg):
        """
        """

class RPCEntityFromService(Entity):
    """
    Going to need a way to enforce the downstream service interface
    """

    def __init__(self, service):
        self.service = service

    def message_received(self, chan, msg):
        cmd_dict = json.loads(msg)

        # Need error handling
        #try:
        result = self._call_cmd(cmd_dict)
        response_msg = json.dumps(result)

        #self.channel.send(response_msg)
        chan.send(response_msg)

    def _call_cmd(self, cmd_dict):
        meth = getattr(self.service, cmd_dict['method'])
        kwargs = cmd_dict['params']
        return meth(**kwargs)


class RPCClientEntityFromInterface(Entity):
    """
    """
    response_queue = None #clean up

    #def __init__(self, service_name, iface):
    def __init__(self, iface):
        #self.service_name = service_name # The name of the service this is a client for
        namesAndDesc = iface.namesAndDescriptions()
        for name, command in namesAndDesc:
            info = command.getSignatureInfo()
            doc = command.getDoc()
            setattr(self, name, _Command(self, name, info, doc))

    def call_remote(self, cmd_dict):
        """
        Send the command to the remote service.
        Returns a Deferred that fires with the response.
        """
        send_data = json.dumps(cmd_dict) #XXX handle encoding errors
        #result_data = self.channel.send(self.service_name, send_data)
        self.channel.send(send_data)
        self.response_queue = event.AsyncResult()
        result_data = self.response_queue.get()
        return json.loads(result_data)

    def _rpc(self, data):
        self.channel.send(send_data)

    def message_received(self, msg):
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
        self.client = client
        self.name = name
        self.positional = siginfo['positional']
        self.required = siginfo['required']
        self.optional = siginfo['optional']
        self.__doc__ = doc

    def __call__(self, **kwargs):
        command_dict = self._command_dict_from_call(**kwargs)
        return self.client.call_remote(command_dict)

    def _command_dict_from_call(self, **kwargs):
        """parameters specified by name
        """
        cmd_dict = {}
        cmd_dict['method'] = self.name
        cmd_dict['params'] = kwargs
        return cmd_dict


