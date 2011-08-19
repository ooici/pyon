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

    #def message_received(self, msg): #hack. Fix!
    def message_received(self, chan, msg):
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
        meth = getattr(self.service, cmd_dict['name'])
        args = cmd_dict['required']
        kwargs = dict([(str(k), v) for k, v in cmd_dict['optional'].items()])
        return meth(*args, **kwargs)



class RPCClientEntityFromInterface(Entity):
    """
    Provides IRabbitMQControlService interface.

    In this version of the client, the methods are automatically generated
    from the interface. It's harder to see how the client works (you have
    to refer to the interface), but you gain robustness by directly using
    the interface.
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
    Serialize using json
    """

    def __init__(self, client, name, siginfo, doc):
        self.client = client
        self.name = name
        self.positional = siginfo['positional']
        self.required = siginfo['required']
        self.optional = siginfo['optional']
        self.__doc__ = doc

    def __call__(self, *args, **kwargs):
        command_dict = self._commad_dict_from_call(*args, **kwargs)
        return self.client.call_remote(command_dict)

    def _commad_dict_from_call(self, *args, **kwargs):
        if not len(args) == len(self.required):
            raise TypeError('%s() takes at least %d arguments (%d given)' %
                    (self.name, len(self.required), len(args)))
        cmd_dict = {}
        cmd_dict['name'] = self.name
        cmd_dict['required'] = args
        cmd_dict['optional'] = {}
        for k, v in self.optional.iteritems():
            cmd_dict['optional'][k] = kwargs.get(k, v)
        if not (len(cmd_dict['required']) + len(cmd_dict['optional'])) == len(self.positional):
            raise TypeError('%s() takes %d arguments (%d given)' %
                    (self.name, len(self.positional), len(cmd_dict)))
        return cmd_dict


