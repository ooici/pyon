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
from pyon.agent.instrument_fsm import InstrumentFSM
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
    GET_RESOURCE = 'RESOURCE_AGENT_EVENT_GET_RESOURCE'
    SET_RESOURCE = 'RESOURCE_AGENT_EVENT_SET_RESOURCE'
    EXECUTE_RESOURCE = 'RESOURCE_AGENT_EVENT_EXECUTE_RESOURCE'
    GET_RESOURCE_STATE = 'RESOURCE_AGENT_EVENT_GET_RESOURCE_STATE'
    GET_RESOURCE_CAPABILITIES = 'RESOURCE_AGENT_EVENT_GET_RESOURCE_CAPABILITIES'
    DONE = 'RESOURCE_AGENT_EVENT_DONE'
    PING_RESOURCE = 'RESOURCE_AGENT_PING_RESOURCE'

class ResourceAgentStreamStatus(BaseEnum):
    """
    Status values for stream monitors and alerts.
    """
    ALL_CLEAR = 'RESOURCE_AGENT_STREAM_STATUS_ALL_CLEAR'
    WARNING = 'RESOURCE_AGENT_STREAM_STATUS_WARNING'
    ALARM = 'RESOURCE_AGENT_STREAM_STATUS_ALARM'

class ResourceAgent(BaseResourceAgent):
    """
    A resource agent is an ION process of type "agent" that exposes the standard
    resource agent service interface. This base class captures the mechanisms
    common to all resource agents and is subclassed with implementations
    specific for instrument agents, user agents, etc.
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
        Initialize superclass and id variables.
        """

        # Base class constructor.
        super(ResourceAgent, self).__init__(*args, **kwargs)

        # The ID of the AgentInstance subtype resource object.
        self.agent_id = None

        # The ID of the AgentDefinition subtype resource object.
        self.agent_def_id = None

        # The ID of the target resource object, e.g. a device id.
        self.resource_id = None
        # The Resource Type of the target resource object - ex. InstrumentDevice or PlatformDevice
        #Must be set by Implementing Class
        self.resource_type = None

        # UUID of the current mutex.
        self._mutex_id = None

        # Event publisher.
        self._event_publisher = None

        # An example agent parameter.
        self.aparam_example = None

        # Set intial state.
        if 'initial_state' in kwargs:
            if ResourceAgentState.has(kwargs['initial_state']):
                self._initial_state = kwargs['initial_state']

        else:
            self._initial_state = ResourceAgentState.UNINITIALIZED

        # Construct the default state machine.
        self._construct_fsm()

    def _on_init(self):
        """
        ION on_init initializer called once the process exists.
        """
        log.debug("Resource Agent initializing. name=%s, resource_id=%s"
                  % (self._proc_name, self.resource_id))

        # Create event publisher.
        self._event_publisher = EventPublisher()

        # Start state machine.
        self._fsm.start(self._initial_state)

    def _on_quit(self):
        """
        ION on_quit called prior to terminating the process.
        """
        pass

    ##############################################################
    # Governance interfaces and helpers
    ##############################################################

    def _get_process_org_name(self):
        '''
        Look for the org_name associated with this process, default to System root
        '''
        if hasattr(self,'org_name'):
            org_name = self.org_name
            log.debug("Getting org_name from process: " + org_name)
        else:
            org_name = self.container.governance_controller._system_root_org_name
            log.debug("Getting org_name from container: " + org_name)

        return org_name

    def _is_org_role(self, actor_roles, role):

        org_name = self._get_process_org_name()

        #TODO - may back this out once process org_name relationships are properly created
        if org_name == self.container.governance_controller._system_root_org_name:
            for org in actor_roles:
                if role in actor_roles[org]:
                    return True

        if actor_roles.has_key(org_name):
            return ( role in actor_roles[org_name] )

        return False


    def _get_resource_commitments(self, actor_id):

        if not self.container.governance_controller.enabled:
            return None

        try:
            return self.container.governance_controller.get_resource_commitments(actor_id, self.resource_id)
        except Exception, e:
            log.error(e.message)
            return None


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
        """

        agent_cmds = self._fsm.get_events(current_state)
        agent_cmds = self._filter_capabilities(agent_cmds)
        agent_params = self.get_agent_parameters()

        try:
            [res_cmds, res_params] = self._fsm.on_event(ResourceAgentEvent.GET_RESOURCE_CAPABILITIES, current_state)

        except FSMStateError:
            res_cmds = []
            res_params = []

        res_iface_cmds = self._get_resource_interface(current_state)
        #res_cmds.extend(res_iface_cmds)
        
        caps = []
        for item in agent_cmds:
            cap = IonObject('AgentCapability', name=item,
                            cap_type=CapabilityType.AGT_CMD)
            caps.append(cap)
        for item in agent_params:
            cap = IonObject('AgentCapability', name=item,
                            cap_type=CapabilityType.AGT_PAR)
            caps.append(cap)
        for item in res_cmds:
            cap = IonObject('AgentCapability', name=item,
                            cap_type=CapabilityType.RES_CMD)
            caps.append(cap)
        for item in res_iface_cmds:
            cap = IonObject('AgentCapability', name=item,
                            cap_type=CapabilityType.RES_IFACE)
            caps.append(cap)
        for item in res_params:
            cap = IonObject('AgentCapability', name=item,
                            cap_type=CapabilityType.RES_PAR)
            caps.append(cap)

        return caps

    def get_agent_parameters(self):
        """
        """            
        params = [x[7:] for x in vars(self).keys() if x.startswith('aparam_') \
                  and not x.startswith('aparam_set_')]
        return params
    
    def _filter_capabilities(self, events):
        """
        """
        return events

    def _get_resource_interface(self, current_state=True):
        """
        """
        return []

    ##############################################################
    # Agent interface.
    ##############################################################
    def get_agent(self, resource_id='', params=[]):
        """
        """
        result = {}
        for x in params:
            try:
                key = 'aparam_' + x
                val = getattr(self, key)
                result[x] = val

            except (TypeError, AttributeError):
                raise BadRequest('Bad agent parameter: %s.', str(x))

        return result

    def set_agent(self, resource_id='', params={}):
        """
        """
        retval = {}
        for (x, val) in params.iteritems():
            try:
                
                key = 'aparam_' + x
                getattr(self, key)

            except (TypeError, AttributeError):
                raise BadRequest('Bad agent parameter: %s', str(x))

        for (x, val) in params.iteritems():
                
            key = 'aparam_' + x
            set_key = 'aparam_set_' + x
            try:
                set_func = getattr(self, set_key)
            except AttributeError:
                set_func = None
            
            if set_func and callable(set_func):
                retval[x] = set_func(val)

            elif set_func:
                retval[x] = -1
                    
            else:
                setattr(self, key, val)
                retval[x] = 0
                    
    def get_agent_state(self, resource_id=''):
        """
        Return resource agent current common fsm state.
        """
        return self._fsm.get_current_state()

    def execute_agent(self, resource_id="", command=None):
        """
        """
        if not command:
            iex = BadRequest('Execute argument "command" not set.')
            self._on_command_error('execute_agent', None, None, None, iex)
            raise iex

        # Grab command syntax.
        id = command.command_id
        cmd = command.command
        args = command.args or []
        kwargs = command.kwargs or {}

        if not command.command:
            iex = BadRequest('Command name not set.')
            self._on_command_error('execute_agent', cmd, args, kwargs, iex)
            raise iex

        # Construct a command result object.
        cmd_result = IonObject("AgentCommandResult",
                               command_id=id,
                               command=cmd,
                               ts_execute=get_ion_ts(),
                               status=0)

        try:
            result = self._fsm.on_event(cmd, *args, **kwargs)
            cmd_result.result = result
            self._on_command('execute_agent', cmd, args, kwargs, result)

        except FSMStateError as ex:
            iex = Conflict(*(ex.args))
            self._on_command_error('execute_agent', cmd, args, kwargs, iex)
            raise iex

        except FSMCommandUnknownError as ex:
            iex = BadRequest(*(ex.args))
            self._on_command_error('execute_agent', cmd, args, kwargs, iex)
            raise iex

        except IonException as iex:
            self._on_command_error('execute_agent', cmd, args, kwargs, iex)
            raise

        except Exception as ex:
            iex = ServerError(*(ex.args))
            self._on_command_error('execute_agent', cmd, args, kwargs, iex)
            raise iex

        return cmd_result

    def ping_agent(self, resource_id=""):
        """
        """
        result = 'ping from %s, time: %s' % (str(self), get_ion_ts())
        return result

    def aparam_set_example(self, val):
        """
        """
        if isinstance(val, str):
            self.aparam_example = val

        else:
            raise BadRequest('Invalid type to set agent parameter "example".')

    ##############################################################
    # Resource interface.
    ##############################################################
    def get_resource(self, resource_id='', params=[]):
        """
        """

        try:
            result = self._fsm.on_event(ResourceAgentEvent.GET_RESOURCE, params)
            return result

        except FSMStateError as ex:
            iex = Conflict(*(ex.args))
            self._on_command_error('get_resource', None, [params], None, iex)
            raise iex

        except FSMCommandUnknownError as ex:
            iex = BadRequest(*(ex.args))
            self._on_command_error('get_resource', None, [params], None, iex)
            raise iex

        except IonException as iex:
            self._on_command_error('get_resource', None, [params], None, iex)
            raise

        except Exception as ex:
            iex = ServerError(*(ex.args))
            self._on_command_error('get_resource', None, [params], None, iex)
            raise iex

    def set_resource(self, resource_id='', params={}):
        """
        """

        try:
            result = self._fsm.on_event(ResourceAgentEvent.SET_RESOURCE, params)
            self._on_command('set_resource', None, [params], None, result)
            return result

        except FSMStateError as ex:
            iex = Conflict(*(ex.args))
            self._on_command_error('set_resource', None, [params], None, iex)
            raise iex

        except FSMCommandUnknownError as ex:
            iex = BadRequest(*(ex.args))
            self._on_command_error('set_resource', None, [params], None, iex)
            raise iex

        except IonException as iex:
            self._on_command_error('set_resource', None, [params], None, iex)
            raise iex

        except Exception as ex:
            iex = ServerError(*(ex.args))
            self._on_command_error('set_resource', None, [params], None, iex)
            raise iex

    def get_resource_state(self, resource_id=''):
        """
        """
        try:
            return self._fsm.on_event(ResourceAgentEvent.GET_RESOURCE_STATE)

        except FSMStateError as ex:
            iex = Conflict(*(ex.args))
            self._on_command_error('get_resource_state', None, None, None, iex)
            raise iex

        except FSMCommandUnknownError as ex:
            iex = BadRequest(*(ex.args))
            self._on_command_error('get_resource_state', None, None, None, iex)
            raise iex

        except IonException as iex:
            self._on_command_error('get_resource_state', None, None, None, iex)
            raise iex

        except Exception as ex:
            iex = ServerError(*(ex.args))
            self._on_command_error('get_resource_state', None, None, None, iex)
            raise iex

    def execute_resource(self, resource_id='', command=None):
        """
        """

        if not command:
            iex = BadRequest('Execute argument "command" not set.')
            self._on_command_error('execute_resource', None, None, None, iex)
            raise iex

        # Grab command syntax.
        id = command.command_id
        cmd = command.command
        args = command.args or []
        kwargs = command.kwargs or {}

        if not command.command:
            iex = BadRequest('Command name not set.')
            self._on_command_error('execute_resource', cmd, args, kwargs, iex)
            raise iex

        # Construct a command result object.
        cmd_result = IonObject("AgentCommandResult",
                               command_id=id,
                               command=cmd,
                               ts_execute=get_ion_ts(),
                               status=0)

        try:
            result = self._fsm.on_event(
                ResourceAgentEvent.EXECUTE_RESOURCE, cmd, *args, **kwargs)
            cmd_result.result = result
            self._on_command('execute_resource', cmd, args, kwargs, result)

        except FSMStateError as ex:
            iex = Conflict(*(ex.args))
            self._on_command_error('execute_resource', cmd, args, kwargs, iex)
            raise iex

        except FSMCommandUnknownError as ex:
            iex = BadRequest(*(ex.args))
            self._on_command_error('execute_resource', cmd, args, kwargs, iex)
            raise iex

        except IonException as iex:
            self._on_command_error('execute_resource', cmd, args, kwargs, iex)
            raise iex

        except Exception as ex:
            iex = ServerError(*(ex.args))
            self._on_command_error('execute_resource', cmd, args, kwargs, iex)
            raise iex

        return cmd_result

    def ping_resource(self, resource_id=''):
        """
        """
        try:
            return self._fsm.on_event(ResourceAgentEvent.PING_RESOURCE)

        except FSMStateError as ex:
            iex = Conflict(*(ex.args))
            self._on_command_error('ping_resource', None, None, None, iex)
            raise iex

        except FSMCommandUnknownError as ex:
            iex = BadRequest(*(ex.args))
            self._on_command_error('ping_resource', None, None, None, iex)
            raise iex

        except IonException as iex:
            self._on_command_error('ping_resource', None, None, None, iex)
            raise iex

        except Exception as ex:
            iex = ServerError(*(ex.args))
            self._on_command_error('ping_resource', None, None, None, iex)
            raise iex

    ##############################################################
    # UNINITIALIZED event handlers.
    ##############################################################

    def _handler_uninitialized_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_uninitialized_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

    ##############################################################
    # POWERED_DOWN event handlers.
    ##############################################################

    def _handler_powered_down_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_powered_down_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

    ##############################################################
    # INACTIVE event handlers.
    ##############################################################

    def _handler_inactive_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_inactive_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

    ##############################################################
    # IDLE event handlers.
    ##############################################################

    def _handler_idle_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_idle_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

    ##############################################################
    # STOPPED event handlers.
    ##############################################################

    def _handler_stopped_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_stopped_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

    ##############################################################
    # COMMAND event handlers.
    ##############################################################

    def _handler_command_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_command_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

    ##############################################################
    # STREAMING event handlers.
    ##############################################################

    def _handler_streaming_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_streaming_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

    ##############################################################
    # TEST event handlers.
    ##############################################################

    def _handler_test_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_test_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

    ##############################################################
    # CALIBRATE event handlers.
    ##############################################################

    def _handler_calibrate_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_calibrate_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

    ##############################################################
    # DIRECT_ACCESS event handlers.
    ##############################################################

    def _handler_direct_access_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_direct_access_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

    ##############################################################
    # BUSY event handlers.
    ##############################################################

    def _handler_busy_enter(self, *args, **kwargs):
        """
        """
        self._common_state_enter(*args, **kwargs)

    def _handler_busy_exit(self, *args, **kwargs):
        """
        """
        self._common_state_exit(*args, **kwargs)

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
                              origin=self.resource_id, **event_data)
        log.info('Resource agent %s publsihed state change: %s, time: %s result: %s',
                 self.id, state, get_ion_ts(), str(result))

    def _common_state_exit(self, *args, **kwargs):
        """
        Common work upon every state exit.
        """
        pass

    def _on_command(self, cmd, execute_cmd, args, kwargs, result):
        log.info('Resource agent %s publishing command event: \
                 cmd=%s, execute_cmd=%s, args=%s kwargs=%s time=%s',
                 self.id, str(cmd), str(execute_cmd), str(args), str(kwargs),
                 get_ion_ts())
        event_data = {
            'command': cmd,
            'execute_command': execute_cmd,
            'args': args,
            'kwargs': kwargs,
            'result': result
        }
        self._event_publisher.publish_event(event_type='ResourceAgentCommandEvent',
                                            origin=self.resource_id,
                                            **event_data)

    def _on_command_error(self, cmd, execute_cmd, args, kwargs, ex):
        log.info('Resource agent %s publishing command error event: \
                 cmd=%s, execute_cmd=%s, args=%s, kwargs=%s, \
                 errtype=%s, errmsg=%s, errno=%i, time=%s',
                 self.id, str(cmd), str(execute_cmd), str(args), str(kwargs),
                 str(type(ex)), ex.message, ex.status_code, get_ion_ts())

        if hasattr(ex, 'status_code'):
            status_code = ex.status_code
        else:
            status_code = -1

        event_data = {
            'command': cmd,
            'execute_command': execute_cmd,
            'args': args,
            'kwargs': kwargs,
            'error_type': str(type(ex)),
            'error_msg': ex.message,
            'error_code': status_code
        }

        self._event_publisher.publish_event(event_type='ResourceAgentErrorEvent',
                                            origin=self.resource_id,
                                            **event_data)

    def _construct_fsm(self):
        """
        Construct the state machine and register default handlers.
        Override in subclass to add handlers for resouce-dependent behaviors
        and state transitions.
        """

        # Instrument agent state machine.
        self._fsm = InstrumentFSM(ResourceAgentState, ResourceAgentEvent,
                            ResourceAgentEvent.ENTER, ResourceAgentEvent.EXIT)

        self._fsm.add_handler(ResourceAgentState.UNINITIALIZED, ResourceAgentEvent.ENTER, self._handler_uninitialized_enter)
        self._fsm.add_handler(ResourceAgentState.UNINITIALIZED, ResourceAgentEvent.EXIT, self._handler_uninitialized_exit)

        self._fsm.add_handler(ResourceAgentState.POWERED_DOWN, ResourceAgentEvent.ENTER, self._handler_powered_down_enter)
        self._fsm.add_handler(ResourceAgentState.POWERED_DOWN, ResourceAgentEvent.EXIT, self._handler_powered_down_exit)

        self._fsm.add_handler(ResourceAgentState.INACTIVE, ResourceAgentEvent.ENTER, self._handler_inactive_enter)
        self._fsm.add_handler(ResourceAgentState.INACTIVE, ResourceAgentEvent.EXIT, self._handler_inactive_exit)

        self._fsm.add_handler(ResourceAgentState.IDLE, ResourceAgentEvent.ENTER, self._handler_idle_enter)
        self._fsm.add_handler(ResourceAgentState.IDLE, ResourceAgentEvent.EXIT, self._handler_idle_exit)

        self._fsm.add_handler(ResourceAgentState.STOPPED, ResourceAgentEvent.ENTER, self._handler_stopped_enter)
        self._fsm.add_handler(ResourceAgentState.STOPPED, ResourceAgentEvent.EXIT, self._handler_stopped_exit)

        self._fsm.add_handler(ResourceAgentState.COMMAND, ResourceAgentEvent.ENTER, self._handler_command_enter)
        self._fsm.add_handler(ResourceAgentState.COMMAND, ResourceAgentEvent.EXIT, self._handler_command_exit)

        self._fsm.add_handler(ResourceAgentState.STREAMING, ResourceAgentEvent.ENTER, self._handler_streaming_enter)
        self._fsm.add_handler(ResourceAgentState.STREAMING, ResourceAgentEvent.EXIT, self._handler_streaming_exit)

        self._fsm.add_handler(ResourceAgentState.TEST, ResourceAgentEvent.ENTER, self._handler_test_enter)
        self._fsm.add_handler(ResourceAgentState.TEST, ResourceAgentEvent.EXIT, self._handler_test_exit)

        self._fsm.add_handler(ResourceAgentState.CALIBRATE, ResourceAgentEvent.ENTER, self._handler_calibrate_enter)
        self._fsm.add_handler(ResourceAgentState.CALIBRATE, ResourceAgentEvent.EXIT, self._handler_calibrate_exit)

        self._fsm.add_handler(ResourceAgentState.DIRECT_ACCESS, ResourceAgentEvent.ENTER, self._handler_direct_access_enter)
        self._fsm.add_handler(ResourceAgentState.DIRECT_ACCESS, ResourceAgentEvent.EXIT, self._handler_direct_access_exit)

        self._fsm.add_handler(ResourceAgentState.BUSY, ResourceAgentEvent.ENTER, self._handler_busy_enter)
        self._fsm.add_handler(ResourceAgentState.BUSY, ResourceAgentEvent.EXIT, self._handler_busy_exit)


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
    ###########################################################
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
