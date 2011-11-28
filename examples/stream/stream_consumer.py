#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from pyon.public import log, StreamProcess

class StreamConsumer(StreamProcess):

    def on_start(self):
        log.debug("StreamConsumer start")

    def on_quit(self):
        log.debug("StreamConsumer quit")

    def process(self, packet):
        log.debug("Processing: %s", packet)
