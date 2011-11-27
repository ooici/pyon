#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import time
import threading

from pyon.util.log import log
from pyon.net.endpoint import Publisher

from interface.services.inoop_service import BaseNoopService

class StreamProducer(BaseNoopService):

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
        interval = self.CFG.stream_producer.interval
        stream_route = self.CFG.stream_producer.stream_route
        pub = Publisher(name=stream_route, node=self.container.node)
        num = 1
        while True:
            msg = dict(num=str(num))
            pub.publish(msg)
            log.debug("Message %s published", num)
            num += 1
            time.sleep(interval/1000.0)
