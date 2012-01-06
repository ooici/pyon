#!/usr/bin/env python

"""Resource specific definitions"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.containers import DotDict
from pyon.core.object import IonObjectRegistry
from pyon.util.config import Config

# Resource Types
ResourceTypes = DotDict()
RT = ResourceTypes

# Association Types
AssociationTypes = DotDict()
AssocTypes = DotDict()
AT = AssocTypes

# Life cycle states
LifeCycleStates = DotDict()
LCS = LifeCycleStates

# Life cycle events
LCE = DotDict()

lcs_workflows = {}

def get_association_type_list():
    AssociationTypes.clear()
    AssociationTypes.update(Config(["res/config/associations.yml"]).data['AssociationTypes'])
    return AssociationTypes.keys()

def initialize_res_lcsms():
    """
    Initializes default and special resource type state machines
    @todo. Make dynamic later and maybe move out.
    """
    lcs_workflows.clear()
    default_lcsm = ResourceLifeCycleSM()
    lcs_workflows['Resource'] = default_lcsm

def load_definitions():
    """Loads constants for resource, association and life cycle states.
    Make sure global module variable objects are updated, not replaced, because other modules had already
    imported them (BAD).
    """
    # Resource Types
    rt_list = list(IonObjectRegistry.allextends.get('Resource', []))
    rt_list.append('Resource')
    ResourceTypes.clear()
    ResourceTypes.update(zip(rt_list, rt_list))

    # Association Types
    at_list = get_association_type_list()
    AssocTypes.clear()
    AssocTypes.update(zip(at_list, at_list))

    # Life cycle states
    initialize_res_lcsms()
    LifeCycleStates.clear()
    LifeCycleStates.update(zip(ResourceLifeCycleSM.BASE_STATES, ResourceLifeCycleSM.BASE_STATES))

    LCE.clear()
    LCE.update(zip(ResourceLifeCycleSM.BASE_EVENTS, ResourceLifeCycleSM.BASE_EVENTS))

def get_restype_lcsm(restype):
    return lcs_workflows['Resource']

class ResourceLifeCycleSM(object):
    """
    Base class for all resource type life cycle state workflows. Specific subtypes of resources can
    add/remove transitions.
    Supports hierarchical states
    """

    # Names of states and aggregate states
    DRAFT =       'DRAFT'            # Newly created, potentially inconsistent
    REGISTERED =  'REGISTERED'       # Aggregate state: Consistent, ready for cross-referencing, not retired
    UNDEPLOYED =   'UNDEPLOYED'      # Aggregate state: Not deployed in target environment
    PLANNED =       'PLANNED'        # Consistent, with actual resource not yet present
    DEVELOPED =     'DEVELOPED'      # The actual resource exists
    TESTED =        'TESTED'         # The actual resource is tested by provider
    INTEGRATED =    'INTEGRATED'     # The actual resource is integrated into composite and tested
    COMMISSIONED =  'COMMISSIONED'   # The actual resource is certified commissioned
    DEPLOYED =     'DEPLOYED'        # Aggregate state: Not Deployed in target environment
    OFF =           'OFF'            # Aggregate state: Off
    ON =            'ON'             # Aggregate state: On
    PUBLIC =        'PUBLIC'         # Aggregate state: Announced, discoverable
    PRIVATE =       'PRIVATE'        # Aggregate state: Unannounced, not discoverable
    OFFLINE =        'OFFLINE'       # Inactive, unannounced
    ONLINE =         'ONLINE'        # Active, unannounced
    INACTIVE =       'INACTIVE'      # Inactive, announced (public)
    ACTIVE =         'ACTIVE'        # Active, announced (public)
    RETIRED =     'RETIRED'          # Resource for historic reference only

    BASE_STATES = [
        DRAFT,
        PLANNED, DEVELOPED, TESTED, INTEGRATED, COMMISSIONED,
        OFFLINE, ONLINE, INACTIVE, ACTIVE,
        RETIRED
    ]

    STATE_ALIASES = {
        REGISTERED: (PLANNED, DEVELOPED, TESTED, INTEGRATED, COMMISSIONED,
                     OFFLINE, ONLINE, INACTIVE, ACTIVE),
        UNDEPLOYED: (PLANNED, DEVELOPED, TESTED, INTEGRATED, COMMISSIONED),
        DEPLOYED: (OFFLINE, ONLINE, INACTIVE, ACTIVE),
        OFF: (OFFLINE, INACTIVE),
        ON: (ONLINE, ACTIVE),
        PUBLIC: (INACTIVE, ACTIVE),
        PRIVATE: (OFFLINE, ONLINE),
    }

    # Names of transition events
    REGISTER = "register"
    DEVELOP = "develop"
    TEST = "test"
    INTEGRATE = "integrate"
    COMMISSION = "commission"
    DECOMMISSION = "decommission"
    DEPLOY = "deploy"
    RECOVER = "recover"
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    PUBLISH = "publish"
    UNPUBLISH = "unpublish"
    RETIRE = "retire"

    BASE_EVENTS = [
        REGISTER,DEVELOP,TEST,INTEGRATE,COMMISSION,DECOMMISSION,
        DEPLOY,RECOVER,
        ACTIVATE,DEACTIVATE,PUBLISH,UNPUBLISH,RETIRE
    ]

    BASE_TRANSITIONS = {
        (DRAFT, REGISTER) : PLANNED,
        (PLANNED, DEVELOP): DEVELOPED,
        (DEVELOPED, TEST): TESTED,
        (TESTED, INTEGRATE): INTEGRATED,
        (INTEGRATED, COMMISSION): COMMISSIONED,
        (COMMISSIONED, DECOMMISSION): TESTED,
        (COMMISSIONED, DEPLOY): OFFLINE,
        (OFFLINE, ACTIVATE): ONLINE,
        (OFFLINE, PUBLISH): INACTIVE,
        (INACTIVE, ACTIVATE): ACTIVE,
        (INACTIVE, UNPUBLISH): OFFLINE,
        (ONLINE, PUBLISH): ACTIVE,
        (ONLINE, DEACTIVATE): OFFLINE,
        (ACTIVE, UNPUBLISH): ONLINE,
        (ACTIVE, DEACTIVATE): INACTIVE,
        (REGISTERED, RETIRE): RETIRED,
    }

    def __init__(self):
        self.transitions = {}
        # Flatten transitions originating from hierarchical states
        for (s0,ev),s1 in self.BASE_TRANSITIONS.iteritems():
            assert s1 not in self.STATE_ALIASES, "Transition target state cannot be hierarchical"
            if s0 in self.STATE_ALIASES:
                for state in self.STATE_ALIASES[s0]:
                    self.transitions[(state,ev)] = s1
            else:
                self.transitions[(s0,ev)] = s1
        #import pprint
        #pprint.pprint(self.transitions)

    def _create_basic_transitions(self):
        pass

    def _add_constraints(self):
        pass

    @classmethod
    def is_in_state(cls, current_state, query_state):
        return (current_state == query_state) or (current_state in cls.STATE_ALIASES[query_state])

    def get_successor(self, current_state, transition_event):
        """
        For given current_state and transition_event, return the successor state if
        defined in the FSM transitions or None
        """
        return self.transitions.get((current_state, transition_event), None)


class InformationResourceLCSM(ResourceLifeCycleSM):
    ILLEGAL_STATES = []
    ADD_TRANSITIONS = {
    }
