#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from anode.base import CFG, messaging, channel, GreenProcessSupervisor

class Container(object):
    """
    The Capability Container. Its purpose is to spawn/monitor processes and services
    that do the bulk of the work in the ION system.
    """
    def __init__(self):
        self.proc_sup = GreenProcessSupervisor()
        self.proc_sup.start()

    def stop(self):
        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.container.timeout.shutdown)

