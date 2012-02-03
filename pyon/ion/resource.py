#!/usr/bin/env python

"""Resource specific definitions"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.containers import DotDict
from pyon.core.registry import IonObjectRegistry, getextends
from pyon.util.config import Config

# Resource Types
ResourceTypes = DotDict()
RT = ResourceTypes

# Predicate Types
Predicates = DotDict()
PredicateType = DotDict()
PRED = PredicateType

# Life cycle states
LifeCycleStates = DotDict()
LCS = LifeCycleStates

# Life cycle events
LCE = DotDict()

lcs_workflows = {}

def get_predicate_type_list():
    Predicates.clear()
    Predicates.update(Config(["res/config/predicates.yml"]).data['PredicateTypes'])
    return Predicates.keys()

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
    rt_list = getextends('Resource')
    rt_list.append('Resource')
    ResourceTypes.clear()
    ResourceTypes.update(zip(rt_list, rt_list))

    # Association Types
    at_list = get_predicate_type_list()
    PredicateType.clear()
    PredicateType.update(zip(at_list, at_list))

    # Life cycle states
    initialize_res_lcsms()
    LifeCycleStates.clear()
    allstates = list(ResourceLifeCycleSM.BASE_STATES) + ResourceLifeCycleSM.STATE_ALIASES.keys()
    LifeCycleStates.update(zip(allstates, allstates))

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
    INTEGRATED =    'INTEGRATED'     # The actual resource is integrated into composite and tested
    DEPLOYED =     'DEPLOYED'        # Aggregate state: Not Deployed in target environment
    PRIVATE =       'PRIVATE'        # Not discoverable
    PUBLIC =        'PUBLIC'         # Aggregate state: discoverable
    DISCOVERABLE =   'DISCOVERABLE'  # discoverable, not acquirable
    AVAILABLE =      'AVAILABLE'     # discoverable, acquirable
    RETIRED =     'RETIRED'          # Resource for historic reference only

    BASE_STATES = [
        DRAFT,
        PLANNED, DEVELOPED, INTEGRATED,
        PRIVATE, DISCOVERABLE, AVAILABLE,
        RETIRED
    ]

    STATE_ALIASES = {
        REGISTERED: (PLANNED, DEVELOPED, INTEGRATED,
                     PRIVATE, DISCOVERABLE, AVAILABLE),
        UNDEPLOYED: (PLANNED, DEVELOPED, INTEGRATED),
        DEPLOYED: (PRIVATE, DISCOVERABLE, AVAILABLE),
        PUBLIC: (DISCOVERABLE, AVAILABLE),
    }

    # Names of transition events
    REGISTER = "register"
    DEVELOP = "develop"
    INTEGRATE = "integrate"
    DEPLOY = "deploy"
    RECOVER = "recover"
    PUBLISH = "publish"
    ENABLE = "enable"
    DISABLE = "disable"
    HIDE = "hide"
    RETIRE = "retire"

    BASE_EVENTS = [
        REGISTER,DEVELOP,INTEGRATE, DEPLOY,RECOVER,
        PUBLISH,ENABLE,DISABLE,HIDE,RETIRE
    ]

    BASE_TRANSITIONS = {
        (DRAFT, REGISTER) : PLANNED,
        (DRAFT, DEPLOY): PRIVATE,
        (DRAFT, ENABLE) : AVAILABLE,
        (PLANNED, DEVELOP): DEVELOPED,
        (DEVELOPED, INTEGRATE): INTEGRATED,
        (UNDEPLOYED, DEPLOY): PRIVATE,
        (PRIVATE, PUBLISH): DISCOVERABLE,
        (PRIVATE, ENABLE): AVAILABLE,
        (DISCOVERABLE, ENABLE): AVAILABLE,
        (AVAILABLE, DISABLE): DISCOVERABLE,
        (PUBLIC, HIDE): PRIVATE,
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

    def get_successors(self, some_state):
        """ 
        For a given state, return a dict of possible transition events => successor states
        """
        ret = {}
        for (a_state, a_transition), a_newstate in self.transitions.iteritems():
            if a_state == some_state:
                #keyed on transition because they are unique with respect to origin state
                ret[a_transition] = a_newstate

        return ret

    def get_predecessors(self, some_state):
        """
        For a given state, return a dict of possible predecessor states => the transition to move
        """
        ret = {}
        for (a_state, a_transition), a_newstate in self.transitions.iteritems():
            if a_newstate == some_state:
                #keyed on state because they are unique with respect to destination state
                ret[a_state] = a_transition

        return ret

class InformationResourceLCSM(ResourceLifeCycleSM):
    ILLEGAL_STATES = []
    ADD_TRANSITIONS = {
    }
