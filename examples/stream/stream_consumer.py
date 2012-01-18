#!/usr/bin/env python

__author__ = 'Michael Meisinger'

"""
# To start the consumer!
id = cc.spawn_process('myconsumer', 'examples.stream.stream_consumer', 'StreamConsumer', {'process':{'type':"stream_process",'listen_name':'a_queue'}})

from examples.stream.stream_consumer import BindingChannel
channel = cc.node.channel(BindingChannel)
channel.setup_listener(('science_data', 'a_queue'), binding='daves_special_sauce')
#channel.start_consume()
"""


from pyon.public import log, StreamProcess
from pyon.net.channel import SubscriberChannel



class BindingChannel(SubscriberChannel):
    """
    Test harness class for creating bindings - without using pubsub service.
    """
    def _declare_queue(self, queue):

        self._recv_name = (self._recv_name[0], '.'.join(self._recv_name))


class StreamConsumer(StreamProcess):

    def on_start(self):
        log.debug("StreamConsumer start")

    def on_quit(self):
        log.debug("StreamConsumer quit")

    def process(self, packet):
        log.debug("Processing: %s", packet)
