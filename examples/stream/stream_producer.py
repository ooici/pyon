#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import time
import threading

from pyon.public import log, BaseService, endpoint

class StreamProducer(BaseService):

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
        pub = endpoint.Publisher(node=self.container.node, name=stream_route)
        num = 1
        while True:
            msg = dict(num=str(num))
            pub.publish(msg)
            log.debug("Message %s published", num)
            num += 1
            time.sleep(interval/1000.0)
