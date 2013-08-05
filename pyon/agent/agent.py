#!/usr/bin/env python
"""
@package pyon.agent.common_agent
@file pyon/agent/common_agent.py
@author Edward Hunter
@brief Common base class for ION resource agents.
"""

__author__ = 'Edward Hunter'
__license__ = 'Apache 2.0'


# Pyon imports.
from pyon.core import bootstrap
from pyon.core.bootstrap import IonObject
from pyon.event.event import EventPublisher
from pyon.util.log import log
from pyon.util.containers import get_ion_ts
from pyon.ion.resource import RT, PRED, OT, LCS
from pyon.ion.state import StatefulProcessMixin

from pickle import dumps, loads
import json

# Pyon exceptions.
from pyon.core.exception import IonException
from pyon.core.exception import BadRequest
from pyon.core.exception import Conflict
from pyon.core.exception import NotFound
from pyon.core.exception import ServerError

# Interface imports.
from interface.services.iresource_agent import BaseResourceAgent
from interface.services.iresource_agent import ResourceAgentProcessClient
from interface.objects import CapabilityType
from interface.services.coi.iresource_registry_service import ResourceRegistryServiceProcessClient

#Agent imports
from pyon.agent.instrument_fsm import InstrumentFSM, ThreadSafeFSM
from pyon.agent.instrument_fsm import FSMStateError
from pyon.agent.instrument_fsm import FSMCommandUnknownError
from pyon.agent.common import BaseEnum


class UserAgent():
    pass

class ResourceAgentState(BaseEnum):
    """
    Resource agent common states.
    """
    POWERED_DOWN = 'RESOURCE_AGENT_STATE_POWERED_DOWN'
    UNINITIALIZED = 'RESOURCE_AGENT_STATE_UNINITIALIZED'
    INACTIVE = 'RESOURCE_AGENT_STATE_INACTIVE'
    IDLE = 'RESOURCE_AGENT_STATE_IDLE'
    STOPPED = 'RESOURCE_AGENT_STATE_STOPPED'
    COMMAND = 'RESOURCE_AGENT_STATE_COMMAND'
    STREAMING = 'RESOURCE_AGENT_STATE_STREAMING'
    TEST = 'RESOURCE_AGENT_STATE_TEST'
    CALIBRATE = 'RESOURCE_AGENT_STATE_CALIBRATE'
    DIRECT_ACCESS = 'RESOUCE_AGENT_STATE_DIRECT_ACCESS'
    BUSY = 'RESOURCE_AGENT_STATE_BUSY'
    LOST_CONNECTION = 'RESOURCE_AGENT_STATE_LOST_CONNECTION'
    ACTIVE_UNKNOWN = 'RESOURCE_AGENT_STATE_ACTIVE_UNKNOWN'

class ResourceAgentEvent(BaseEnum):
    """
    Resource agent common events.
    """
    ENTER = 'RESOURCE_AGENT_EVENT_ENTER'
    EXIT = 'RESOURCE_AGENT_EVENT_EXIT'
    POWER_UP = 'RESOURCE_AGENT_EVENT_POWER_UP'
    POWER_DOWN = 'RESOURCE_AGENT_EVENT_POWER_DOWN'
    INITIALIZE = 'RESOURCE_AGENT_EVENT_INITIALIZE'
    RESET = 'RESOURCE_AGENT_EVENT_RESET'
    GO_ACTIVE = 'RESOURCE_AGENT_EVENT_GO_ACTIVE'
    GO_INACTIVE = 'RESOURCE_AGENT_EVENT_GO_INACTIVE'
    RUN = 'RESOURCE_AGENT_EVENT_RUN'
    CLEAR = 'RESOURCE_AGENT_EVENT_CLEAR'
    PAUSE = 'RESOURCE_AGENT_EVENT_PAUSE'
    RESUME = 'RESOURCE_AGENT_EVENT_RESUME'
    GO_COMMAND = 'RESOURCE_AGENT_EVENT_GO_COMMAND'
    GO_DIRECT_ACCESS = 'RESOURCE_AGENT_EVENT_GO_DIRECT_ACCESS'
    EXECUTE_DIRECT_ACCESS = 'RESOURCE_AGENT_EXECUTE_DIRECT_ACCESS'
    GET_RESOURCE = 'RESOURCE_AGENT_EVENT_GET_RESOURCE'
    SET_RESOURCE = 'RESOURCE_AGENT_EVENT_SET_RESOURCE'
    EXECUTE_RESOURCE = 'RESOURCE_AGENT_EVENT_EXECUTE_RESOURCE'
    GET_RESOURCE_STATE = 'RESOURCE_AGENT_EVENT_GET_RESOURCE_STATE'
    GET_RESOURCE_CAPABILITIES = 'RESOURCE_AGENT_EVENT_GET_RESOURCE_CAPABILITIES'
    DONE = 'RESOURCE_AGENT_EVENT_DONE'
    PING_RESOURCE = 'RESOURCE_AGENT_PING_RESOURCE'
    LOST_CONNECTION = 'RESOURCE_AGENT_EVENT_LOST_CONNECTION'
    AUTORECONNECT = 'RESOURCE_AGENT_EVENT_AUTORECONNECT'
    GET_RESOURCE_SCHEMA = 'RESOURCE_AGENT_EVENT_GET_RESOURCE_SCHEMA'
    CHANGE_STATE_ASYNC = 'RESOURCE_AGENT_EVENT_CHANGE_STATE_ASYNC'

class ResourceAgentStreamStatus(BaseEnum):
    """
    Status values for stream monitors and alerts.
    """
    ALL_CLEAR = 'RESOURCE_AGENT_STREAM_STATUS_ALL_CLEAR'
    WARNING = 'RESOURCE_AGENT_STREAM_STATUS_WARNING'
    ALARM = 'RESOURCE_AGENT_STREAM_STATUS_ALARM'

class ResourceAgent(BaseResourceAgent, StatefulProcessMixin):
    """
    A resource agent is an ION process of type "agent" that exposes the standard
    resource agent service interface. This base class captures the mechanisms
    common to all resource agents and is subclassed with implementations
    specific for instrument agents, user agents, etc.
    Pointless comment.
    """

    ##############################################################
    # Class variables.
    ##############################################################

    # ION process type.
    process_type = "agent"

    # Override in subclass to publish specific types of events.
    COMMAND_EVENT_TYPE = "ResourceCommandEvent"

    # Override in subclass to set specific origin type.
    ORIGIN_TYPE = "Resource"

    # Override in subclass to expose agent capabilities.
    CAPABILITIES = []

    ##############################################################
    # Constructor and ION init/deinit.
    ##############################################################

    def __init__(self, *args, **kwargs):
        """
        Initialize superclass and base class variables.
        """

        # Base class constructor.
        super(ResourceAgent, self).__init__(*args, **kwargs)

        # The ID of the AgentInstance subtype resource object.
        self.agent_id = None

        # The ID of the AgentDefinition subtype resource object.
        self.agent_def_id = None

        # The ID of the target resource object, e.g. a device id.
        self.resource_id = None
        
        # The Resource Type of the target resource object -
        # ex. InstrumentDevice or PlatformDevice
        # Must be set by Implementing Class        
        self.resource_type = None

        # Event publisher.
        self._event_publisher = None

        # An example agent parameter.
        self.aparam_example = None

        # Override in derived class to set initial state of set in
        # config.
        self._initial_state = None
        
        # Construct the default state machine.
        # This is overridden in derived classes and calls base class with
        # state and event parameters.
        self._construct_fsm()
        
        self._proc_state = {}
        self._proc_state_changed = False
        
        # Resource schema.
        self._resource_schema = {}
        
        # Agent schema.
        self._agent_schema = {}
        
    def on_init(self):
        """
        ION on_init initializer called once the process exists.
        """
        
        # The registrar to create publishers.
        agent_info = self.CFG.get('agent', None)
        if not agent_info:
            log.error('No agent config found.')
        else:
            self.resource_id = agent_info.get('resource_id', '')
        
        log.info("Resource Agent on_init. name=%s, resource_id=%s",
                 self._proc_name, self.resource_id)

        # Create event publisher.
        self._event_publisher = EventPublisher()

        # Retrieve stored states.
        try:
            state = self._get_state('agent_state') or ResourceAgentState.UNINITIALIZED
            prev_state = self._get_state('agent_state') or ResourceAgentState.UNINITIALIZED

        except Exception as ex:
            log.error('Exception retrieving agent state in on_init: %s.', str(ex))
            log.exception('Exception retrieving agent state in on_init.')
            state = ResourceAgentState.UNINITIALIZED
            prev_state = ResourceAgentState.UNINITIALIZED
        else:
            log.info('Got agent state: %s', state)
            log.info('Got agent prior state: %s', prev_state)

        # Load state.
        try:
            self._load_state()
        except Exception as ex:
            log.error('Error loading state in on_init: %s', str(ex))
            log.exception('Error loading state in on_init.')

        # Start state machine.
        self._initial_state = self.CFG.get('initial_state', None) or self._initial_state
        self._fsm.start(self._initial_state)

        # If configured, wipe out the prior agent memory.
        restored_aparams = []
        unrestored_aparams = []
        bootmode = self.CFG.get_safe('bootmode')
        log.info('Restoring aparams: bootmode=%s', str(bootmode))
        if bootmode == 'restart':
            (restored_aparams, unrestored_aparams) = self._restore_aparams()
            self._restore_resource(state, prev_state)
        else:
            unrestored_aparams = self.get_agent_parameters()
            try:
                self._get_state_vector().clear()
            except Exception as ex:
                log.error('Error clearing state in on_init: %s', str(ex))
                log.exception('Error clearing state in on_init.')

        self._configure_aparams(unrestored_aparams)

    def on_quit(self):
        """
        ION on_quit called prior to terminating the process.
        """
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
        """
        TBD.
        """
        pass

    ##############################################################
    # Capabilities interface.
    ##############################################################

    def get_capabilities(self, resource_id="", current_state=True):
        """
        Dynamically calculate the accessible agent and resource
        interface.
        """

        agent_cmds = self._fsm.get_events(current_state)
        agent_cmds = self._filter_capabilities(agent_cmds)
        agent_params = self.get_agent_parameters()

        try:
            [res_cmds, res_params] = self._fsm.on_event(ResourceAgentEvent.GET_RESOURCE_CAPABILITIES, current_state)

        except FSMStateError, FSMCommandUnknownError:
            res_cmds = []
            res_params = []

        except Exception as ex:            
            self._on_command_error('get_capabilities', None, None, None, ex)
  
        res_iface_cmds = self._get_resource_interface(current_state)

        caps = []
        for item in agent_cmds:
            schema = self._agent_schema.get('commands',{}).get(item,{})
            cap = IonObject('AgentCapability', name=item,
                            cap_type=CapabilityType.AGT_CMD,
                            schema=schema)
            caps.append(cap)

        for item in agent_params:
            schema = self._agent_schema.get('parameters',{}).get(item,{})
            cap = IonObject('AgentCapability', name=item,
                            cap_type=CapabilityType.AGT_PAR,
                            schema=schema)
            caps.append(cap)

        for item in res_cmds:
            try:
                schema = self._resource_schema.get('commands',{}).get(item,{})
            except:
                log.error('Bad resource schema.')
                schema = {}
            cap = IonObject('AgentCapability', name=item,
                            cap_type=CapabilityType.RES_CMD,
                            schema=schema)
            caps.append(cap)

        for item in res_iface_cmds:
            cap = IonObject('AgentCapability', name=item,
                            cap_type=CapabilityType.RES_IFACE)
            caps.append(cap)

        for item in res_params:
            try:
                schema = self._resource_schema.get('parameters',{}).get(item,{})
            except:
                log.error('Bad resource schema.')
                schema = {}
            cap = IonObject('AgentCapability', name=item,
                            cap_type=CapabilityType.RES_PAR,
                            schema=schema)
            caps.append(cap)

        schema = self._agent_schema.get('states',{})
        cap = IonObject('AgentCapability', name='agent_states',
                            cap_type=CapabilityType.AGT_STATES,
                            schema=schema)
        caps.append(cap)
        
        schema = self._agent_schema.get('alert_defs',{})
        cap = IonObject('AgentCapability', name='alert_defs',
                            cap_type=CapabilityType.ALERT_DEFS,
                            schema=schema)
        caps.append(cap)
        
        schema = self._agent_schema.get('command_args',{})
        cap = IonObject('AgentCapability', name='command_args',
                            cap_type=CapabilityType.AGT_CMD_ARGS,
                            schema=schema)
        caps.append(cap)

        schema = self._agent_schema.get('streams',{})
        cap = IonObject('AgentCapability', name='streams',
                            cap_type=CapabilityType.AGT_STREAMS,
                            schema=schema)
        caps.append(cap)

        return caps

    def get_agent_parameters(self):
        """
        Return the set of agent parameter keys.
        """            
        params = [x[7:] for x in vars(self).keys() if x.startswith('aparam_') 
                  and not x.startswith('aparam_set_')
                  and not x.startswith('aparam_get_')]
        return params
    
    def _filter_capabilities(self, events):
        """
        Filter the events to give only those intended to be exposed
        as external commands. Override in derived classes.
        """
        return events

    def _get_resource_interface(self, current_state=True):
        """
        Return the resource interface capabilities.
        Override in derived classes.
        """
        return []

    def _get_agent_schema(self):
        """
        """
        return 'I am an agent schema!'

    ##############################################################
    # Agent interface.
    ##############################################################
    
    def get_agent(self, resource_id='', params=[]):
        """
        Get agent parameter values.
        """
        result = {}
        for x in params:
            try:
                key = 'aparam_' + x
                getattr(self, key)
            except (TypeError, AttributeError):
                ex = BadRequest('Bad agent parameter: %s', str(x))
                self._on_command_error('get_agent', None, [params], None, ex)

        for x in params:
            key = 'aparam_' + x
            get_key = 'aparam_get_' + x
            
            try:
                get_func = getattr(self, get_key)
            except (TypeError, AttributeError):
                get_func = None
                
            if get_func and callable(get_func):
                result[x] = get_func()
            
            else:
                result[x] = getattr(self, key)

        return result

    def set_agent(self, resource_id='', params={}):
        """
        Set agent parameter values.
        """
        for (x, val) in params.iteritems():
            try:
                key = 'aparam_' + x
                getattr(self, key)

            except (TypeError, AttributeError):
                ex = BadRequest('Bad agent parameter: %s', str(x))
                self._on_command_error('set_agent', None, [params], None, ex)

        for (x, val) in params.iteritems():
                
            key = 'aparam_' + x
            set_key = 'aparam_set_' + x
            try:
                set_func = getattr(self, set_key)
                
            except AttributeError:
                set_func = None
            
            if set_func and callable(set_func):
                set_func(val)                        

            else:
                setattr(self, key, val)                

            get_key = 'aparam_get_' + x
            get_func = getattr(self, get_key, None)
            val = None
            if get_func and callable(get_func):
                val = get_func()
            else:
                val = getattr(self, key)

            try:
                self._set_state(key, val)
            except Exception as ex:
                log.error('Exception setting state: %s', str(ex))
                log.exception('Could not set state in set_agent.')

    def get_agent_state(self, resource_id=''):
        """
        Return resource agent current common fsm state.
        """
        return self._fsm.get_current_state()

    def execute_agent(self, resource_id="", command=None):
        """
        Execute an agent function.
        """
        if not command or not command.command:
            ex = BadRequest('Execute argument "command" not set.')
            self._on_command_error('execute_agent', None, None, None, ex)

        # Grab command syntax.
        id = command.command_id
        cmd = command.command
        args = command.args or []
        kwargs = command.kwargs or {}

        # Construct a command result object.
        cmd_result = IonObject("AgentCommandResult",
                               command_id=id,
                               command=cmd,
                               ts_execute=get_ion_ts(),
                               status=0)

        try:
            result = self._fsm.on_event(cmd, *args, **kwargs)
            #if not isinstance(result, dict):
            #    result = {'result' : result}
            cmd_result.result = result
            self._on_command('execute_agent', cmd, args, kwargs, result)

        except Exception as ex:
            self._on_command_error('execute_agent', cmd, args, kwargs, ex)

        return cmd_result

    def ping_agent(self, resource_id=""):
        """
        Ping the agent itself.
        """
        result = 'ping from %s, time: %s' % (str(self), get_ion_ts())
        return result

    def aparam_set_example(self, val):
        """
        Example set function.
        """
        if isinstance(val, str):
            self.aparam_example = val

        else:
            iex = BadRequest('Invalid type to set agent parameter "example".')
            self._on_command_error('aparam_set_example', None, val, None, iex)
            
    ##############################################################
    # Resource interface.
    ##############################################################
    
    def get_resource(self, resource_id='', params=[]):
        """
        Get resource parameters.
        """

        try:
            result = self._fsm.on_event(ResourceAgentEvent.GET_RESOURCE, params)
            return result

        except Exception as ex:
            
            self._on_command_error('get_resource', None, [params], None, ex)

    def set_resource(self, resource_id='', params={}):
        """
        Set resource parameters.
        """

        try:
            result = self._fsm.on_event(ResourceAgentEvent.SET_RESOURCE, params)
            self._on_command('set_resource', None, [params], None, result)
            return result

        except Exception as ex:
            self._on_command_error('set_resource', None, [params], None, ex)

    def get_resource_state(self, resource_id=''):
        """
        Get the state of the resource.
        """
        try:
            return self._fsm.on_event(ResourceAgentEvent.GET_RESOURCE_STATE)

        except Exception as ex:
            self._on_command_error('get_resource_state', None, None, None, ex)

    def execute_resource(self, resource_id='', command=None):
        """
        Execute a resource function.
        """

        if not command or not command.command:
            iex = BadRequest('Execute argument "command" not set.')
            self._on_command_error('execute_resource', None, None, None, iex)

        # Grab command syntax.
        id = command.command_id
        cmd = command.command
        args = command.args or []
        kwargs = command.kwargs or {}

        # Construct a command result object.
        cmd_result = IonObject("AgentCommandResult",
                               command_id=id,
                               command=cmd,
                               ts_execute=get_ion_ts(),
                               status=0)

        try:
            result = self._fsm.on_event(
                ResourceAgentEvent.EXECUTE_RESOURCE, cmd, *args, **kwargs)
            #if not isinstance(result, dict):
            #    result = {'result' : result}
            cmd_result.result = result
            self._on_command('execute_resource', cmd, args, kwargs, result)

        except Exception as ex:
            self._on_command_error('execute_resource', cmd, args, kwargs, ex)

        return cmd_result

    def ping_resource(self, resource_id=''):
        """
        Ping the resource.
        """
        try:
            return self._fsm.on_event(ResourceAgentEvent.PING_RESOURCE)

        except Exception as ex:
            self._on_command_error('ping_resource', None, None, None, ex)

    ##############################################################
    # Helpers.
    ##############################################################
    
    def _common_state_enter(self, *args, **kwargs):
        """
        Common work upon every state entry.
        """
        state = self._fsm.get_current_state()

        event_data = {
            'state': state
        }
        result = self._event_publisher.publish_event(event_type='ResourceAgentStateEvent',
                                                origin_type=self.ORIGIN_TYPE,
                                                origin=self.resource_id,
                                                **event_data)
        log.info('Resource agent %s publsihed state change: %s, time: %s result: %s',
                 self.id, state, get_ion_ts(), str(result))

        try:
            self._set_state('agent_state', state)
            self._flush_state()
        except Exception as ex:
            log.error('Exception setting state: %s', str(ex))
            log.exception('Could not set state in _common_state_enter.')

        new_state = self._get_state('agent_state')

        self._on_state_enter(state)

    def _on_state_enter(self, state):
        """
        Used by derived classes to extend common state enter. Xx.
        """
        pass
    
    def _common_state_exit(self, *args, **kwargs):
        """
        Common work upon every state exit.
        """
        state = self._fsm.get_current_state()
        log.info('Resource agent %s leaving state: %s, time: %s',
                 self.id, state, get_ion_ts())

        try:
            self._set_state('prev_agent_state', state)
            self._on_state_exit(state)
        except Exception as ex:
            log.error('Error persisting agent state in _common_state_exit: %s',
                      str(ex))
            log.exception('Could not set state in _common_state_exit.')

    def _on_state_exit(self, state):
        """
        Used by derived classes to extend common state exit.
        """
        pass

    def _on_command(self, cmd, execute_cmd, args, kwargs, result):
        """
        Common action after a successful agent command.
        """

        cmd = cmd or ''
        execute_cmd = execute_cmd or ''
        args = args or []
        kwargs = kwargs or {}                
        result = result or {}
        
        if not isinstance(result, dict):
            log.error('Agent command result not a dict: cmd=%s, execute_cmd=%s, result=%s',
                      cmd, execute_cmd, str(result))
        
        event_data = {
            'command': cmd,
            'execute_command': execute_cmd,
            'args': args,
            'kwargs': kwargs,
            'result': result
        }
        msg = 'Resource agent %s publishing command event %s:' % \
            (self.id, event_data)
        log.info(msg)
        self._event_publisher.publish_event(event_type='ResourceAgentCommandEvent',
                                            origin_type=self.ORIGIN_TYPE,
                                            origin=self.resource_id,
                                            **event_data)

    def _on_command_error(self, cmd, execute_cmd, args, kwargs, ex):
        """
        Common action after an unsuccessful agent command.
        """        
        if isinstance(ex, FSMStateError):
            iex = Conflict(*(ex.args))
        
        elif isinstance(ex, FSMCommandUnknownError):
            iex = BadRequest(*(ex.args))
        
        elif isinstance(ex, IonException):
            iex = ex

        else:
            iex = ServerError(*(ex.args))
        
        errstr = 'Resource agent %s publishing command error event: ' % self.id
        errstr += 'cmd=%s, execute_cmd=%s, args=%s, kwargs=%s, ' % \
            (str(cmd), str(execute_cmd), str(args), str(kwargs))
        errstr += 'error=%s' % str(iex)
        log.error(errstr)

        cmd = cmd or ''
        execute_cmd = execute_cmd or ''
        args = args or []
        kwargs = kwargs or {}        

        event_data = {
            'command': cmd,
            'execute_command': execute_cmd,
            'args': args,
            'kwargs': kwargs,
            'error_type': str(type(ex)),
            'error_msg': ex.message,
            'error_code': iex.status_code or -1
        }

        self._event_publisher.publish_event(event_type='ResourceAgentErrorEvent',
                                            origin_type=self.ORIGIN_TYPE,
                                            origin=self.resource_id,
                                            **event_data)

        raise iex

    def _restore_aparams(self):
        """
        Restore agent aparams.
        """
        aparams = self.get_agent_parameters()
        restored = []
        unrestored = []
        for key in aparams:
            try:
                val = self._get_state('aparam_' + key)
            except Exception as ex:
                val = None
                log.error('Error getting state in _restore_aparams: %s', str(ex))
                log.exception('Error getting state in _restore_aparam.')

            if val:
                set_key = 'aparam_set_' + key
                set_func = getattr(self, set_key, None)
                if set_func and callable(set_func):
                    set_func(val)
                else:
                    setattr(self, 'aparam_' + key, val)
                restored.append(key)
                log.info('Restored aparam: %s, %s', key, val)
            else:
                unrestored.append(key)
        log.info('Restored aparams: %s', str(restored))
        log.info('Unrestored aparams: %s', str(unrestored))
        return (restored, unrestored)
        
    def _configure_aparams(self, aparams=[]):
        """
        Override in derived class to configure aparams from
        from agent configuration.
        """
        pass

    def _restore_resource(self, state, prev_state):
        """
        Override in derived class to restore agent state and
        resource parameters.
        """
        pass

    def _construct_fsm(self, states=ResourceAgentState, events=ResourceAgentEvent):
        """
        Construct the state machine and register default handlers.
        Override in subclass to add handlers for resouce-dependent behaviors
        and state transitions.
        """

        # Instrument agent state machine.
        self._fsm = ThreadSafeFSM(states, events, ResourceAgentEvent.ENTER,
                                  ResourceAgentEvent.EXIT)

        for state in states.list():
            self._fsm.add_handler(state, ResourceAgentEvent.ENTER, self._common_state_enter)
            self._fsm.add_handler(state, ResourceAgentEvent.EXIT, self._common_state_exit)

class ResourceAgentClient(ResourceAgentProcessClient):
    """
    Generic client for resource agents.
    """
    def __init__(self, resource_id, *args, **kwargs):
        """
        Client constructor.
        @param resource_id The ID this service represents.
        @param name Use this kwarg to set the target exchange name
        (service or process).
        """

        # Assert and set the resource ID.
        assert resource_id, "resource_id must be set for an agent"
        self.resource_id = resource_id

        # Set the name, retrieve as proc ID if not set by user.
        if not 'name' in kwargs:
            process_id = self._get_agent_process_id(self.resource_id)
            if process_id:
                kwargs = kwargs.copy()
                kwargs['name'] = process_id
                log.debug("Use agent process %s for resource_id=%s" % (process_id, self.resource_id))
            else:
                # TODO: Check if there is a service for this type of resource
                log.debug("No agent process found for resource_id %s" % self.resource_id)
                raise NotFound("No agent process found for resource_id %s" % self.resource_id)

        assert "name" in kwargs, "Name argument for agent target not set"

        # transpose name -> to_name to make underlying layer happy
        kwargs["to_name"] = kwargs.pop("name")

        # Superclass constructor.
        ResourceAgentProcessClient.__init__(self, *args, **kwargs)

    ##############################################################
    # Client interface.
    ##############################################################

    def negotiate(self, *args, **kwargs):
        return super(ResourceAgentClient, self).negotiate(self.resource_id, *args, **kwargs)

    def get_capabilities(self, *args, **kwargs):
        return super(ResourceAgentClient, self).get_capabilities(self.resource_id, *args, **kwargs)

    def execute_agent(self, *args, **kwargs):
        return super(ResourceAgentClient, self).execute_agent(self.resource_id, *args, **kwargs)

    def get_agent(self, *args, **kwargs):
        return super(ResourceAgentClient, self).get_agent(self.resource_id, *args, **kwargs)

    def set_agent(self, *args, **kwargs):
        return super(ResourceAgentClient, self).set_agent(self.resource_id, *args, **kwargs)

    def get_agent_state(self, *args, **kwargs):
        return super(ResourceAgentClient, self).get_agent_state(self.resource_id, *args, **kwargs)

    def ping_agent(self, *args, **kwargs):
        return super(ResourceAgentClient, self).ping_agent(self.resource_id, *args, **kwargs)

    def execute_resource(self, *args, **kwargs):
        return super(ResourceAgentClient, self).execute_resource(self.resource_id, *args, **kwargs)

    def get_resource(self, *args, **kwargs):
        return super(ResourceAgentClient, self).get_resource(self.resource_id, *args, **kwargs)

    def set_resource(self, *args, **kwargs):
        return super(ResourceAgentClient, self).set_resource(self.resource_id, *args, **kwargs)

    def get_resource_state(self, *args, **kwargs):
        return super(ResourceAgentClient, self).get_resource_state(self.resource_id, *args, **kwargs)

    def ping_resource(self, *args, **kwargs):
        return super(ResourceAgentClient, self).ping_resource(self.resource_id, *args, **kwargs)

    def emit(self, *args, **kwargs):
        return super(ResourceAgentClient, self).emit(self.resource_id, *args, **kwargs)

    ##############################################################
    # Helpers.
    ##############################################################
    
    @classmethod
    def _get_agent_process_id(cls, resource_id):
        """
        Retrun the agent container proc id given the resource_id.
        """
        agent_procs = bootstrap.container_instance.directory.find_by_value('/Agents', 'resource_id', resource_id)
        if agent_procs:
            if len(agent_procs) > 1:
                log.warn("Inconsistency: More than one agent registered for resource_id=%s: %s" % (
                    resource_id, agent_procs))
            agent_id = agent_procs[0].key
            return str(agent_id)
        return None
