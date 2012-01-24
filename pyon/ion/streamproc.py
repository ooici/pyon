#!/usr/bin/env python

"""Base classes and utils for stream processes"""

__author__ = 'Michael Meisinger'

from pyon.util.log import log
from pyon.core.bootstrap import CFG
from pyon.service.service import BaseService

class StreamProcess(BaseService):
    """
        call spawn_proc with
        'type':"stream_process"
        'configuration': {'process':{'listen_name':<exchange_name>,'publish_streams':{<name>:<stream_id>}}}

        This will create a process which is calling the 'process' method on any message which arrives in the queue
        <exchange_name>. The instance will have publisher objects as attributes with <name>. To publish a message to
        their stream from the process method it would look like:

        self.<name>.publish(msg)
    """

    process_type = "stream_process"



    def process(self, packet):
        """
        Process a message as arriving based on a subscription.
        """
        pass
