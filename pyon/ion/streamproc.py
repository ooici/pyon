#!/usr/bin/env python

"""Base classes and utils for stream processes"""

__author__ = 'Michael Meisinger'

from pyon.ion.service import BaseService


class StreamProcess(BaseService):
    """
    """

    process_type = "stream_process"

    def call_process(self, message, stream_route, stream_id):
        '''
        Handles preprocessing of packet and process work
        '''
        self.process(message)

    def process(self, message):
        """
        Process a message as arriving based on a subscription.
        """
        pass
