#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from pyon.util.log import log

from interface.services.istream_process import BaseStreamProcess

class StreamConsumer(BaseStreamProcess):

    def on_start(self):
        log.debug("StreamConsumer start")

    def on_quit(self):
        log.debug("StreamConsumer quit")

    def process(self, packet):
        log.debug("Processing: %s", packet)
