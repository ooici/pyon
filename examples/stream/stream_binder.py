#!/usr/bin/env python

"""
@author David Stuebe

@brief This process exists to take the place of the pubsub service which implements the subscription and create the
rabbitmq binding because the pubsub service is not running in the simple stream example.

This is functionality is not to be touched, modified or (re)implemented as part of creating a stream process.


# To do the bind by starting an agent process
id = cc.spawn_process('binder', 'examples.stream.stream_binder', 'StreamBinder', {'process':{'type':"agent"}, 'args':{'queue_name':'consumer_input_queue', 'binding':'glider_data'}})


# To do the bind using the pycc shell
from examples.stream.stream_binder import BindingChannel
channel = cc.node.channel(BindingChannel)
channel.setup_listener(('science_data', 'consumer_input'), binding='glider_data')
"""


from pyon.public import log, BaseService
from pyon.net.channel import SubscriberChannel



class BindingChannel(SubscriberChannel):
    """
    Test harness class for creating bindings - without using pubsub service.
    Only for use in the stream example...
    """
    def _declare_queue(self, queue):

        self._recv_name = (self._recv_name[0], '.'.join(self._recv_name))


class StreamBinder(BaseService):
    """
    This is a special process designed to take the place of the pubsub service for the stream example
    """

    def on_start(self):
        log.debug("StreamBinder start")
        queue_name = self.CFG.get('args',{}).get('queue_name',None)
        binding = self.CFG.get('args',{}).get('binding',None)

        self.channel = self.container.node.channel(BindingChannel)
        self.channel.setup_listener(('science_data',queue_name),binding=binding)

        # How do we make this process end now?