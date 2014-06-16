#!/usr/bin/env python

"""Base classes for agents"""


__author__ = 'Michael Meisinger'


import traceback

from pyon.core import bootstrap
from pyon.core.bootstrap import IonObject
from pyon.core import exception as iex
from pyon.ion.event import EventPublisher
from pyon.ion.resource import RT, PRED, LCS
from pyon.util.log import log
from pyon.util.containers import get_ion_ts

from interface.services.isimple_resource_agent import BaseSimpleResourceAgent, SimpleResourceAgentProcessClient
from interface.services.coi.iresource_registry_service import ResourceRegistryServiceProcessClient

class SimpleResourceAgent(BaseSimpleResourceAgent):
    """
    A resource agent is an ION process of type "agent" that exposes the standard
    resource agent service interface.
    """

    process_type = "agent"

    # Override in subclass to publish specific types of events
    COMMAND_EVENT_TYPE = "ResourceCommandEvent"
    # Override in subclass to set specific origin type
    ORIGIN_TYPE = "Resource"

    def __init__(self, *args, **kwargs):
        super(SimpleResourceAgent, self).__init__(*args, **kwargs)

        # The ID of the AgentInstance subtype resource object
        self.agent_id = None
        # The ID of the AgentDefinition subtype resource object
        self.agent_def_id = None
        # The ID of the target resource object, e.g. a device id
        self.resource_id = None
        # The Resource Type of the target resource object - ex. InstrumentDevice or PlatformDevice
        #Must be set by Implementing Class
        self.resource_type = None

    def _on_init(self):
        log.debug("Resource Agent initializing. name=%s, resource_id=%s" % (self._proc_name, self.resource_id))
        self._event_publisher = EventPublisher()

    def _on_quit(self):
        pass


    ##############################################################
    # Governance interfaces and helpers
    ##############################################################

    def _get_process_org_governance_name(self):
        '''
        Look for the org_name associated with this process, default to System root
        '''
        if hasattr(self,'org_governance_name'):
            org_governance_name = self.org_governance_name
            log.debug("Getting org_governance_name from process: " + org_governance_name)
        else:
            org_governance_name = self.container.governance_controller.system_root_org_name
            log.debug("Getting org_governance_name from container: " + org_governance_name)

        return org_governance_name


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
            except iex.IonException as ex:
                # TODO: Distinguish application vs. uncaught exception
                cmd_res.status = getattr(ex, 'status_code', -1)
                cmd_res.result = str(ex)
                log.warn("Agent command %s failed with trace=%s" % (command.command, traceback.format_exc()))
        else:
            log.info("Agent command not supported: %s" % (command.command))
            ex = iex.NotFound("Command not supported: %s" % command.command)
            cmd_res.status = iex.NotFound.status_code
            cmd_res.result = str(ex)

        sub_type = "%s.%s" % (command.command, cmd_res.status)
        event_data = self._post_execute_event_hook(event_type=self.COMMAND_EVENT_TYPE,
            origin=self.resource_id, origin_type=self.ORIGIN_TYPE,
            sub_type=sub_type, command=str(command.command),
            result=str(cmd_res.result))
        post_event = self._event_publisher.publish_event(**event_data)

        return cmd_res

    def _post_execute_event_hook(self, **kwargs):
        """
        Hook to add additional values to the event object to be published
        @param event  A filled out even object of type COMMAND_EVENT_TYPE
        @retval an event object
        """
        return kwargs

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


class UserAgent(SimpleResourceAgent):

    def __init__(self, *args, **kwargs):
        SimpleResourceAgent.__init__(self)
        self.resource_type = RT.ActorIdentity


class SimpleResourceAgentClient(SimpleResourceAgentProcessClient):
    """
    @brief Generic client for resource agents that hides
    @param resource_id The ID this service represents
    @param name Use this kwarg to set the target exchange name (service or process)
    """
    def __init__(self, resource_id, *args, **kwargs):
        assert resource_id, "resource_id must be set for an agent"
        self.resource_id = resource_id

        if not 'name' in kwargs:
            process_id = self._get_agent_process_id(self.resource_id)
            if process_id:
                kwargs['name'] = process_id
                log.debug("Use agent process %s for resource_id=%s" % (process_id, self.resource_id))
            else:
                # TODO: Check if there is a service for this type of resource
                log.debug("No agent process found for resource_id %s" % self.resource_id)
                raise iex.NotFound("No agent process found for resource_id %s" % self.resource_id)

        assert "name" in kwargs, "Name argument for agent target not set"
        SimpleResourceAgentProcessClient.__init__(self, *args, **kwargs)

    def negotiate(self, *args, **kwargs):
        return super(SimpleResourceAgentClient, self).negotiate(self.resource_id, *args, **kwargs)

    def get_capabilities(self, *args, **kwargs):
        return super(SimpleResourceAgentClient, self).get_capabilities(self.resource_id, *args, **kwargs)

    def execute(self, *args, **kwargs):
        return super(SimpleResourceAgentClient, self).execute(self.resource_id, *args, **kwargs)

    def get_param(self, *args, **kwargs):
        return super(SimpleResourceAgentClient, self).get_param(self.resource_id, *args, **kwargs)

    def set_param(self, *args, **kwargs):
        return super(SimpleResourceAgentClient, self).set_param(self.resource_id, *args, **kwargs)

    def emit(self, *args, **kwargs):
        return super(SimpleResourceAgentClient, self).emit(self.resource_id, *args, **kwargs)

    def execute_agent(self, *args, **kwargs):
        return super(SimpleResourceAgentClient, self).execute_agent(self.resource_id, *args, **kwargs)

    def get_agent_param(self, *args, **kwargs):
        return super(SimpleResourceAgentClient, self).get_agent_param(self.resource_id, *args, **kwargs)

    def set_agent_param(self, *args, **kwargs):
        return super(SimpleResourceAgentClient, self).set_agent_param(self.resource_id, *args, **kwargs)

    @classmethod
    def _get_agent_process_id(cls, resource_id):
        agent_procs = bootstrap.container_instance.directory.find_by_value('/Agents', 'resource_id', resource_id)
        if agent_procs:
            if len(agent_procs) > 1:
                log.warn("Inconsistency: More than one agent registered for resource_id=%s: %s" % (
                    resource_id, agent_procs))
            agent_id = agent_procs[0].key
            return str(agent_id)
        return None
