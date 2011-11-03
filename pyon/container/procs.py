#!/usr/bin/env python

"""Part of the container that manages ION processes etc."""

__author__ = 'Michael Meisinger'

from zope.interface import providedBy
from zope.interface import Interface, implements

from pyon.core.bootstrap import CFG

from pyon.util.log import log
from pyon.util.state_object import  LifecycleStateMixin

class ProcManager(LifecycleStateMixin):
    def on_init(self, container, *args, **kwargs):
        self.container = container

        # Define the callables that can be added to Container public API
        self.container_api = []

        # Add the public callables to Container
        for call in self.container_api:
            setattr(self.container, call.__name__, call)

        self.procs = {}

    def on_start(self, *args, **kwargs):
        log.debug("ProcManager: start")
