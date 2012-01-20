#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import time
import threading

from pyon.public import log, BaseService, ProcessPublisher

"""
@author Micahel Meisinger
@author David Stuebe
@author Luke Campbell


@brief Run using:
bin/pycc --rel res/deploy/examples/stream.yml

To start the producer in the pycc shell:
id_p = cc.spawn_process('myproducer', 'examples.stream.stream_producer', 'StreamProducer', {'process':{'type':"agent"},'stream_producer':{'interval':4000,'routing_key':'glider_data'}})
"""

class StreamProducer(BaseService):
    """
    StreamProducer is not a stream process. A stream process is defined by a having an input stream which is processed.
    The Stream Producer takes the part of an agent pushing data into the system.

    """


    def on_init(self):
        log.debug("StreamProducer init. Self.id=%s" % self.id)

    def on_start(self):

        log.debug("StreamProducer start")
        # Threads become efficent Greenlets with gevent
        self.producer_proc = threading.Thread(target=self._trigger_func)
        self.producer_proc.start()

    def on_quit(self):
        log.debug("StreamProducer quit")

    def _trigger_func(self):
        interval = self.CFG.get('stream_producer').get('interval')
        routing_key = self.CFG.get('stream_producer').get('routing_key')

        pub = ProcessPublisher(node=self.container.node, name=('science_data',routing_key), process=self)
        num = 1
        while True:
            msg = dict(num=str(num))
            pub.publish(msg)
            log.debug("Message %s published", num)
            num += 1
            time.sleep(interval/1000.0)
