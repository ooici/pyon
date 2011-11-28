#!/usr/bin/env python

"""Base classes and utils for stream processes"""

__author__ = 'Michael Meisinger'

from pyon.public import CFG, log, BaseService

class StreamProcess(BaseService):

    def process(self, packet):
        """
        Process a message as arriving based on a subscription.
        """
        pass
