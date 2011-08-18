#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from anode.base import CFG, messaging, channel, GreenProcessSupervisor

class Container(object):
    """
    The Capability Container. Its purpose is to spawn/monitor processes and services
    that do the bulk of the work in the ION system.
    """
    def __init__(self, *args, **kwargs):
        self.proc_sup = GreenProcessSupervisor()

    def start(self):
        self.proc_sup.start()

    def stop(self):
        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)

    def serve_forever(self):
        if not self.proc_sup.running:
            self.start()
        self.proc_sup.join_children()

