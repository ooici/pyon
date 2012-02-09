#!/usr/bin/env python

__author__ = 'Michael Meisinger'

"""
@author Micahel Meisinger
@author David Stuebe
@author Luke Campbell

@brief Run using:
bin/pycc --rel res/deploy/examples/stream.yml

To start the consumer in the pycc shell:
id = cc.spawn_process('myconsumer', 'examples.stream.stream_consumer', 'StreamConsumer', {'process':{'listen_name':'consumer_input_queue'}})
"""


from pyon.public import log, StreamProcess


class StreamConsumer(StreamProcess):

    def on_start(self):
        log.debug("StreamConsumer start")
        self.name = self.CFG.get('process',{}).get('name','consumer')

    def on_quit(self):
        log.debug("StreamConsumer quit")

    def process(self, packet):
        log.debug('(%s): Received Packet' % self.name )
        log.debug('(%s):   - Processing: %s' % (self.name,packet))
