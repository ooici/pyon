#!/usr/bin/env python

"""Base classes for agents"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.public import CFG, IonObject, log, RT, AT

from interface.services.iresource_agent import BaseResourceAgent

class ResourceAgent(BaseResourceAgent):

    def _on_init(self):
        log.debug("Resource Agent initializing. name=%s" % (self._proc_name))
        self.clients.directory.register("/Agents", self.id)

        self.agent_id = None
        self.agent_def_id = None
        self.resource_id = None

    def _on_quit(self):
        self.clients.directory.unregister("/Agents", self.id)

    def execute(self, command={}):
        pass
    

class UserAgent(BaseResourceAgent):
    pass
