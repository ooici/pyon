#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import time
from gevent.greenlet import Greenlet
from pyon.public import log, ProcessPublisher, SimpleProcess

from pyon.core import bootstrap

"""
@author Michael Meisinger
@author David Stuebe
@author Luke Campbell


@brief Run using:
bin/pycc --rel res/deploy/examples/stream.yml

To start the producer in the pycc shell:
id_p = cc.spawn_process('myproducer', 'examples.stream.stream_producer', 'StreamProducer', {'stream_producer':{'interval':4000,'routing_key':'glider_data'}})
"""

class StreamProducer(SimpleProcess):
    """
    StreamProducer is not a stream process. A stream process is defined by a having an input stream which is processed.
    The Stream Producer takes the part of an agent pushing data into the system.

    """


    def on_init(self):
        log.debug("StreamProducer init. Self.id=%s" % self.id)

    def on_start(self):
        log.debug("StreamProducer start")
        self.producer_proc = Greenlet(self._trigger_func)
        self.producer_proc.start()


    def on_quit(self):
        log.debug("StreamProducer quit")
        self.process_proc.kill()
        super(StreamProducer,self).on_quit()

    def _trigger_func(self):
        interval = self.CFG.get('stream_producer').get('interval')
        routing_key = self.CFG.get('stream_producer').get('routing_key')

        # Create scoped exchange name
        XP = '.'.join([bootstrap.get_sys_name(),'science_data'])

        pub = ProcessPublisher(node=self.container.node, name=(XP,routing_key), process=self)
        num = 1
        while True:
            msg = dict(num=str(num))
            pub.publish(msg)
            log.debug("Message %s published", num)
            num += 1
            time.sleep(interval/1000.0)
