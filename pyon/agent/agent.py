#!/usr/bin/env python

"""Base classes for agents"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import CFG, IonObject
from pyon.util.log import log
from pyon.ion.resource import RT, PRED
from pyon.core import exception as iex
from pyon.util.containers import get_ion_ts

from interface.services.iresource_agent import BaseResourceAgent, ResourceAgentProcessClient

class ResourceAgent(BaseResourceAgent):
    """
    A resource agent is an ION process of type "agent" that exposes the standard
    resource agent service interface.
    """

    process_type = "agent"

    def _on_init(self):
        log.debug("Resource Agent initializing. name=%s" % (self._proc_name))
        # The ID of the agent resource object
        self.agent_id = None
        # The ID of the agent definition resource object
        self.agent_def_id = None
        # The ID of the target resource object
        self.resource_id = None

        caps = self.get_capabilities()
        self.container.directory.register("/Agents", self.id,
                                          **dict(name=self._proc_name,
                                             container=self.container.id,
                                             resource_id=self.resource_id,
                                             agent_id=self.agent_id,
                                             def_id=self.agent_def_id,
                                             capabilities=caps))

    def _on_quit(self):
        self.container.directory.unregister("/Agents", self.id)

    def negotiate(self, resource_id="", sap_in=None):
        pass

    def execute(self, resource_id="", command=None):
        return self._execute("rcmd_", command)

    def execute_agent(self, resource_id="", command=None):
        return self._execute("acmd_", command)

    def _execute(self, cprefix, command):
        if not command:
            raise iex.BadRequest("execute argument 'command' not present")
        if not command.command:
            raise iex.BadRequest("command not set")

        cmd_res = IonObject("AgentCommandResult", command_id=command.command_id, command=command.command)
        cmd_func = getattr(self, cprefix + str(command.command), None)
        if cmd_func:
            cmd_res.ts_execute = get_ion_ts()
            try:
                res = cmd_func(*command.args, **command.kwargs)
                cmd_res.status = 0
                cmd_res.result = res
            except Exception as ex:
                # TODO: Distinguish application vs. uncaught exception
                cmd_res.status = getattr(ex, 'status_code', -1)
                cmd_res.result = str(ex)
                log.info("Agent function failed with ex=%s msg=%s" % (type(ex), str(ex)))
        else:
            log.info("Agent command not supported: %s" % (command.command))
            ex = iex.NotFound("Command not supported: %s" % command.command)
            cmd_res.status = iex.NotFound.status_code
            cmd_res.result = str(ex)
        return cmd_res

    def get_capabilities(self, resource_id="", capability_types=[]):
        capability_types = capability_types or ["CONV_TYPE", "AGT_CMD", "AGT_PAR", "RES_CMD", "RES_PAR"]
        cap_list = []
        if "CONV_TYPE" in capability_types:
            cap_list.extend([("CONV_TYPE", cap) for cap in self._get_agent_conv_types()])
        if "AGT_CMD" in capability_types:
            cap_list.extend([("AGT_CMD", cap) for cap in self._get_agent_commands()])
        if "AGT_PAR" in capability_types:
            cap_list.extend([("AGT_PAR", cap) for cap in self._get_agent_params()])
        if "RES_CMD" in capability_types:
            cap_list.extend([("RES_CMD", cap) for cap in self._get_resource_commands()])
        if "RES_PAR" in capability_types:
            cap_list.extend([("RES_PAR", cap) for cap in self._get_resource_params()])
        return cap_list

    def set_param(self, resource_id="", name='', value=''):
        if not hasattr(self, "rpar_%s" % name):
            raise iex.NotFound('Resource parameter not existing: %s' % name)
        pvalue = getattr(self, "rpar_%s" % name)
        setattr(self, "rpar_%s" % name, value)
        return pvalue

    def get_param(self, resource_id="", name=''):
        try:
            return getattr(self, "rpar_%s" % name)
        except AttributeError:
            raise iex.NotFound('Resource parameter not found: %s' % name)

    def set_agent_param(self, resource_id="", name='', value=''):
        if not hasattr(self, "apar_%s" % name):
            raise iex.NotFound('Agent parameter not existing: %s' % name)
        pvalue = getattr(self, "apar_%s" % name)
        setattr(self, "apar_%s" % name, value)
        return pvalue

    def get_agent_param(self, resource_id="", name=''):
        try:
            return getattr(self, "apar_%s" % name)
        except AttributeError:
            raise iex.NotFound('Agent parameter not found: %s' % name)

    def _get_agent_conv_types(self):
        return []

    def _get_agent_params(self):
        return self._get_names(self, "apar_")

    def _get_agent_commands(self):
        return self._get_names(self, "acmd_")

    def _get_resource_params(self):
        return self._get_names(self, "rpar_")

    def _get_resource_commands(self):
        return self._get_names(self, "rcmd_")

    def _get_names(self, obj, prefix):
        return [name[len(prefix):] for name in dir(obj) if name.startswith(prefix)]

class UserAgent(ResourceAgent):
    pass

class ResourceAgentClient(ResourceAgentProcessClient):
    """
    @brief Generic client for resource agents that hides
    @param resource_id The ID this service represents
    @param name Use this kwarg to set the target exchange name (service or process)
    """
    def __init__(self, resource_id, *args, **kwargs):
        assert resource_id, "resource_id must be set for an agent"
        self.resource_id = resource_id
        assert "name" in kwargs, "Name argument for agent target not set"
        ResourceAgentProcessClient.__init__(self, *args, **kwargs)

    def negotiate(self, *args, **kwargs):
        return super(ResourceAgentClient, self).negotiate(self.resource_id, *args, **kwargs)

    def get_capabilities(self, *args, **kwargs):
        return super(ResourceAgentClient, self).get_capabilities(self.resource_id, *args, **kwargs)

    def execute(self, *args, **kwargs):
        return super(ResourceAgentClient, self).execute(self.resource_id, *args, **kwargs)

    def get_param(self, *args, **kwargs):
        return super(ResourceAgentClient, self).get_param(self.resource_id, *args, **kwargs)

    def set_param(self, *args, **kwargs):
        return super(ResourceAgentClient, self).set_param(self.resource_id, *args, **kwargs)

    def emit(self, *args, **kwargs):
        return super(ResourceAgentClient, self).emit(self.resource_id, *args, **kwargs)

    def execute_agent(self, *args, **kwargs):
        return super(ResourceAgentClient, self).execute_agent(self.resource_id, *args, **kwargs)

    def get_agent_param(self, *args, **kwargs):
        return super(ResourceAgentClient, self).get_agent_param(self.resource_id, *args, **kwargs)

    def set_agent_param(self, *args, **kwargs):
        return super(ResourceAgentClient, self).set_agent_param(self.resource_id, *args, **kwargs)
