#!/usr/bin/env python

"""ION Resource definitions and functions. Extended resource framework"""

__author__ = 'Michael Meisinger, Stephen Henrie'
__license__ = 'Apache 2.0'

import inspect
import types
import time

from pyon.core.registry import getextends, issubtype
from pyon.core.bootstrap import IonObject, get_service_registry
from pyon.core.exception import BadRequest, NotFound, Inconsistent
from pyon.util.config import Config
from pyon.util.containers import DotDict, named_any, get_ion_ts
from pyon.util.log import log


# Object Types
ObjectTypes = DotDict()
OT = ObjectTypes

# Resource Types
ResourceTypes = DotDict()
RT = ResourceTypes

# Predicate Type4194304
Predicates = DotDict()
PredicateType = DotDict()
PRED = PredicateType

# Association Types, don't confuse with predicate type!
AssociationTypes = ['H2H', 'R2R', 'H2R', 'R2H']
AssociationType = DotDict()
AssociationType.update(zip(AssociationTypes, AssociationTypes))
AT = AssociationType

#Compound Associations
CompoundAssociations = DotDict()

# Life cycle states
LifeCycleStates = DotDict()
LCS = LifeCycleStates
LCS_NONE = "NONE"

# Life cycle events
LCE = DotDict()

lcs_workflow_defs = {}
lcs_workflows = {}


def get_predicate_type_list():
    Predicates.clear()
    assoc_defs = Config(["res/config/associations.yml"]).data['AssociationDefinitions']
    for ad in assoc_defs:
        if ad['predicate'] in Predicates:
            raise Inconsistent('Predicate %s defined multiple times in associations.yml' % ad['predicate'])
        Predicates[ad['predicate']] = ad
    return Predicates.keys()


def get_compound_associations_list():
    CompoundAssociations.clear()
    CompoundAssociations.update(Config(["res/config/associations.yml"]).data['CompoundAssociations'])
    return CompoundAssociations.keys()


def initialize_res_lcsms():
    """
    Initializes default and special resource type state machines
    @todo. Make dynamic later and maybe move out.
    """
    res_lifecycle = (Config(["res/config/resource_lifecycle.yml"])).data

    # Initialize the set of available resource lifecycle workflows
    lcs_workflow_defs.clear()
    lcsm_defs = res_lifecycle["LifecycleWorkflowDefinitions"]
    for wf in lcsm_defs:
        #print "****** FOUND RES WORKFLOW %s" % (wf)
        wfname = wf['name']
        clsname = wf.get('lcsm_class', None)
        if clsname:
            wf_cls = named_any(clsname)
            lcs_workflow_defs[wfname] = wf_cls(**wf)
        else:
            based_on = wf.get('based_on', None)
            wf_base = lcs_workflow_defs[based_on]
            lcs_workflow_defs[wfname] = wf_base._clone_with_restrictions(wf)

    lcs_workflows.clear()

    # Initialize the set of resource types with lifecycle
    for res_type, wf_name in res_lifecycle["LifecycleResourceTypes"].iteritems():
        lcs_workflows[res_type] = lcs_workflow_defs[wf_name]


def load_definitions():
    """Loads constants for resource, association and life cycle states.
    Make sure global module variable objects are updated, not replaced, because other modules had already
    imported them (BAD).
    """
    # Resource Types
    ot_list = getextends('IonObjectBase')
    ot_list.append('IonObjectBase')
    ObjectTypes.clear()
    ObjectTypes.update(zip(ot_list, ot_list))

    # Resource Types
    rt_list = getextends('Resource')
    rt_list.append('Resource')
    ResourceTypes.clear()
    ResourceTypes.update(zip(rt_list, rt_list))

    # Predicate Types
    pt_list = get_predicate_type_list()
    PredicateType.clear()
    PredicateType.update(zip(pt_list, pt_list))

    # Compound Associations
    get_compound_associations_list()

    # Life cycle states
    initialize_res_lcsms()
    LifeCycleStates.clear()
    allstates = list(CommonResourceLifeCycleSM.BASE_STATES) + CommonResourceLifeCycleSM.STATE_ALIASES.keys()
    LifeCycleStates.update(zip(allstates, allstates))

    # Life cycle events
    LCE.clear()
    LCE.update(zip([e.upper() for e in CommonResourceLifeCycleSM.BASE_EVENTS], CommonResourceLifeCycleSM.BASE_EVENTS))


def get_restype_lcsm(restype):
    return lcs_workflows.get(restype, None)


def get_maturity_visibility(lcstate):
    if lcstate == 'RETIRED':
        return (None, None)
    return lcstate.split('_')


def is_resource(object):
    return issubtype(object._get_type(), "Resource")


class ResourceLifeCycleSM(object):
    """
    Base class for all resource type life cycle state workflows. Subclasses
    defined states and transitions.
    """
    BASE_STATES = []
    STATE_ALIASES = {}
    BASE_TRANSITIONS = {}

    def __init__(self, **kwargs):
        self.transitions = {}
        self.initial_state = kwargs.get('initial_state', None)
        self._kwargs = kwargs

    @classmethod
    def is_in_state(cls, current_state, query_state):
        return (current_state == query_state) or (current_state in cls.STATE_ALIASES[query_state])

    def _clone_with_restrictions(self, wfargs=None):
        wfargs = wfargs if not None else {}
        clone = self.__class__(**wfargs)
        clone._apply_restrictions(**wfargs)
        return clone

    def _apply_restrictions(self, **kwargs):
        self.illegal_states = kwargs.get('illegal_states', None)
        if self.illegal_states:
            trans_new = self.transitions.copy()
            for (a_state, a_transition), a_newstate in self.transitions.iteritems():
                if a_state in self.illegal_states or a_newstate in self.illegal_states:
                    del trans_new[(a_state, a_transition)]
            self.transitions = trans_new

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


class CommonResourceLifeCycleSM(ResourceLifeCycleSM):
    """
    Common resource type life cycle state workflow. Specialized
    clones may remove states and transitions.
    Supports hierarchical states.
    """

    MATURITY = ['DRAFT', 'PLANNED', 'DEVELOPED', 'INTEGRATED', 'DEPLOYED']
    VISIBILITY = ['PRIVATE', 'DISCOVERABLE', 'AVAILABLE']

    BASE_STATES = ["%s_%s" % (m, v) for m in MATURITY for v in VISIBILITY]
    BASE_STATES.append('RETIRED')

    STATE_ALIASES = {}

    for i in list(MATURITY) + VISIBILITY:
        matchstates = [s for s in BASE_STATES if i in s]
        if matchstates:
            STATE_ALIASES[i] = tuple(matchstates)

    STATE_ALIASES['REGISTERED'] = tuple(["%s_%s" % (m, v) for m in MATURITY if m != 'DRAFT' for v in VISIBILITY])

    # Names of transition events
    PLAN = "plan"
    DEVELOP = "develop"
    INTEGRATE = "integrate"
    DEPLOY = "deploy"
    RETIRE = "retire"

    ANNOUNCE = "announce"
    UNANNOUNCE = "unannounce"
    ENABLE = "enable"
    DISABLE = "disable"

    MAT_EVENTS = [PLAN, DEVELOP, INTEGRATE, DEPLOY, RETIRE]
    VIS_EVENTS = [ANNOUNCE, UNANNOUNCE, ENABLE, DISABLE]

    BASE_EVENTS = [
        PLAN, DEVELOP, INTEGRATE, DEPLOY,
        ENABLE, DISABLE, ANNOUNCE, UNANNOUNCE,
        RETIRE
    ]

    BASE_TRANSITIONS = {}

    for m in MATURITY:
        BASE_TRANSITIONS[("%s_%s" % (m, 'PRIVATE'), ANNOUNCE)] = "%s_%s" % (m, 'DISCOVERABLE')
        BASE_TRANSITIONS[("%s_%s" % (m, 'DISCOVERABLE'), UNANNOUNCE)] = "%s_%s" % (m, 'PRIVATE')

        BASE_TRANSITIONS[("%s_%s" % (m, 'DISCOVERABLE'), ENABLE)] = "%s_%s" % (m, 'AVAILABLE')
        BASE_TRANSITIONS[("%s_%s" % (m, 'AVAILABLE'), DISABLE)] = "%s_%s" % (m, 'DISCOVERABLE')

        BASE_TRANSITIONS[("%s_%s" % (m, 'PRIVATE'), ENABLE)] = "%s_%s" % (m, 'AVAILABLE')
        BASE_TRANSITIONS[("%s_%s" % (m, 'AVAILABLE'), UNANNOUNCE)] = "%s_%s" % (m, 'PRIVATE')

    for v in VISIBILITY:
        BASE_TRANSITIONS[("%s_%s" % ('DRAFT', v), PLAN)] = "%s_%s" % ('PLANNED', v)
        BASE_TRANSITIONS[("%s_%s" % ('DRAFT', v), RETIRE)] = 'RETIRED'

        BASE_TRANSITIONS[("%s_%s" % ('DRAFT', v), DEVELOP)] = "%s_%s" % ('DEVELOPED', v)
        BASE_TRANSITIONS[("%s_%s" % ('PLANNED', v), DEVELOP)] = "%s_%s" % ('DEVELOPED', v)
        BASE_TRANSITIONS[("%s_%s" % ('INTEGRATED', v), DEVELOP)] = "%s_%s" % ('DEVELOPED', v)
        BASE_TRANSITIONS[("%s_%s" % ('DEPLOYED', v), DEVELOP)] = "%s_%s" % ('DEVELOPED', v)

        BASE_TRANSITIONS[("%s_%s" % ('DRAFT', v), INTEGRATE)] = "%s_%s" % ('INTEGRATED', v)
        BASE_TRANSITIONS[("%s_%s" % ('PLANNED', v), INTEGRATE)] = "%s_%s" % ('INTEGRATED', v)
        BASE_TRANSITIONS[("%s_%s" % ('DEVELOPED', v), INTEGRATE)] = "%s_%s" % ('INTEGRATED', v)
        BASE_TRANSITIONS[("%s_%s" % ('DEPLOYED', v), INTEGRATE)] = "%s_%s" % ('INTEGRATED', v)

        BASE_TRANSITIONS[("%s_%s" % ('DRAFT', v), DEPLOY)] = "%s_%s" % ('DEPLOYED', v)
        BASE_TRANSITIONS[("%s_%s" % ('PLANNED', v), DEPLOY)] = "%s_%s" % ('DEPLOYED', v)
        BASE_TRANSITIONS[("%s_%s" % ('DEVELOPED', v), DEPLOY)] = "%s_%s" % ('DEPLOYED', v)
        BASE_TRANSITIONS[("%s_%s" % ('INTEGRATED', v), DEPLOY)] = "%s_%s" % ('DEPLOYED', v)

    BASE_TRANSITIONS[('REGISTERED', RETIRE)] = 'RETIRED'

    def __init__(self, **kwargs):
        super(CommonResourceLifeCycleSM, self).__init__(**kwargs)
        # Flatten transitions originating from hierarchical states
        for (s0, ev), s1 in self.BASE_TRANSITIONS.iteritems():
            assert s1 not in self.STATE_ALIASES, "Transition target state cannot be hierarchical"
            if s0 in self.STATE_ALIASES:
                for state in self.STATE_ALIASES[s0]:
                    self.transitions[(state, ev)] = s1
            else:
                self.transitions[(s0, ev)] = s1
                #import pprint; pprint.pprint(self.transitions)

    def _create_basic_transitions(self):
        pass

    def _add_constraints(self):
        pass


class ExtendedResourceContainer(object):
    """
    Class to support creating and filling extended resource containers.
    @todo rename to ExtendedResourceUtil
    """
    def __init__(self, serv_prov, res_registry=None):
        self.service_provider = serv_prov
        if res_registry is not None:
            self._rr = res_registry
        else:
            if hasattr(serv_prov.container, 'has_capability') and serv_prov.container.has_capability('RESOURCE_REGISTRY'):
                self._rr = serv_prov.container.resource_registry
            else:
                self._rr = self.service_provider.clients.resource_registry

        # Keeps a context used during evaluation of the resource container fields
        self.ctx = None

    def create_extended_resource_container_list(self, extended_resource_type, resource_id_list,
                                                computed_resource_type=None,
                                                ext_associations=None, ext_exclude=None, **kwargs):
        """
        Returns a list of extended resource containers for given list of resource_ids.
        """
        if not isinstance(resource_id_list, types.ListType):
            raise Inconsistent("The parameter resource_id_list is not a list of resource_ids")

        ret = list()
        for res_id in resource_id_list:
            ext_res = self.create_extended_resource_container(extended_resource_type, res_id, computed_resource_type,
                ext_associations, ext_exclude )
            ret.append(ext_res)

        return ret

    def create_extended_resource_container(self, extended_resource_type, resource_id, computed_resource_type=None,
                                           ext_associations=None, ext_exclude=None, **kwargs):
        """
        Returns an extended resource container for a given resource_id.
        """
        overall_start_time = time.time()
        self.ctx = None  # Clear the context in case this instance gets reused

        if not isinstance(resource_id, types.StringType):
            raise Inconsistent("The parameter resource_id is not a single resource id string")

        if not self.service_provider or not self._rr:
            raise Inconsistent("This class is not initialized properly")

        if extended_resource_type not in getextends(OT.ResourceContainer):
            raise BadRequest('The requested resource %s is not extended from %s' % (extended_resource_type, OT.ResourceContainer))

        if computed_resource_type and computed_resource_type not in getextends(OT.ComputedAttributes):
            raise BadRequest('The requested resource %s is not extended from %s' % (computed_resource_type, OT.ComputedAttributes))

        resource_object = self._rr.read(resource_id)

        if not resource_object:
            raise NotFound("The Resource %s does not exist" % resource_id)

        res_container = IonObject(extended_resource_type)

        # @TODO - replace with object level decorators and raise exceptions
        if not hasattr(res_container, 'origin_resource_type'):
            log.error('The requested resource %s does not contain a properly set origin_resource_type field.' , extended_resource_type)
            #raise Inconsistent('The requested resource %s does not contain a properly set origin_resource_type field.' % extended_resource_type)

        if hasattr(res_container, 'origin_resource_type') and res_container.origin_resource_type != resource_object.type_\
        and not issubtype(resource_object.type_, res_container.origin_resource_type):
            log.error('The origin_resource_type of the requested resource %s(%s) does not match the type of the specified resource id(%s).' % (
                extended_resource_type, res_container.origin_resource_type, resource_object.type_))
            #raise Inconsistent('The origin_resource_type of the requested resource %s(%s) does not match the type of the specified resource id(%s).' % (extended_resource_type, res_container.origin_resource_type, resource_object.type_))

        res_container._id = resource_object._id
        res_container.resource = resource_object

        # Initialize context object field and load resource associations
        self._prepare_context(resource_object._id)

        # Fill lcstate related resource container fields
        self.set_container_lcstate_info(res_container)

        # Fill resource container fields
        self.set_container_field_values(res_container, ext_exclude, **kwargs)

        # Fill computed attributes
        self.set_computed_attributes(res_container, computed_resource_type, ext_exclude, **kwargs)

        # Fill additional associations
        self.set_extended_associations(res_container, ext_associations, ext_exclude)

        res_container.ts_created = get_ion_ts()

        overall_stop_time = time.time()

        log.debug("Time to process extended resource container %s %f secs", extended_resource_type, overall_stop_time - overall_start_time )

        #log.info("ResourceContainer: %s" % res_container)

        return res_container

    def set_container_lcstate_info(self, res_container):
        """
        Set lcstate related fields in resource container, such as available lcstate transitions.
        This is true for all resources, independent of the type.
        """
        restype_workflow = get_restype_lcsm(res_container.resource._get_type())
        if restype_workflow:
            res_container.lcstate_transitions = restype_workflow.get_successors(res_container.resource.lcstate)
        else:
            res_container.lcstate_transitions = {"retire": "RETIRED"}

    def set_container_field_values(self, res_container, ext_exclude, **kwargs):
        """
        Sets resource container fields that are not extended or computed.
        """
        self.set_object_field_values(res_container, res_container.resource, ext_exclude, **kwargs)

    def set_computed_attributes(self, res_container, computed_resource_type, ext_exclude, **kwargs):
        """
        Creates the specified ComputedAttributes object if given and iterate over the fields
        to set the computed values.
        """
        if not computed_resource_type or computed_resource_type is None:
            return

        res_container.computed = IonObject(computed_resource_type)

        self.set_object_field_values(res_container.computed, res_container.resource, ext_exclude, **kwargs)

    def set_object_field_values(self, obj, resource, ext_exclude, **kwargs):
        """
        Iterate through all fields of the given object and set values according
        to the field type and decorator definition in the object type schema.
        """

        # Step 1: Determine needs to fill fields with resource objects.
        field_needs = []         # Fields that need to be set in a subsequent step
        resource_needs = set()   # Resources to read by id based on needs
        assoc_needs = set()      # Compound associations to follow

        for field in obj._schema:

            # Skip any fields that were specifically to be excluded
            if ext_exclude is not None and field in ext_exclude:
                continue

            # Iterate over all of the decorators for the field
            for decorator in obj._schema[field]['decorators']:

                field_start_time = time.time()

                # Field gets value from method or service call (local to current executing process)
                if decorator == 'Method':
                    deco_value = obj.get_decorator_value(field, decorator)
                    if deco_value:
                        method_name = deco_value
                    else:
                        method_name = 'get_' + field
                    ret_val = self.execute_method(resource._id, method_name, **kwargs)
                    if ret_val is not None:
                        setattr(obj, field, ret_val)

                # Fill field based on compound association chains. Results in nested lists of resource objects
                elif self.is_compound_association(decorator):
                    target_type = obj.get_decorator_value(field, decorator)
                    predicates = self.get_compound_association_predicates(decorator)
                    assoc_list = self._find_associated_resources(resource, predicates[0], target_type)
                    field_needs.append((field, "A", (assoc_list, predicates)))
                    for target_id, assoc in assoc_list:
                        assoc_needs.add((target_id, predicates[1]))

                # Fill field based on association with list of resource objects
                elif self.is_association_predicate(decorator):
                    target_type = obj.get_decorator_value(field, decorator)
                    assoc_list = self._find_associated_resources(resource, decorator, target_type)
                    if assoc_list:
                        if obj._schema[field]['type'] == 'list':
                            field_needs.append((field, "L", assoc_list))
                            [resource_needs.add(target_id) for target_id, assoc in assoc_list]
                        elif obj._schema[field]['type'] == 'int':
                            setattr(obj, field, len(assoc_list))
                        else:
                            first_assoc = assoc_list[0]
                            if len(assoc_list) != 1:
                                # WARNING: Swallow random further objects here!
                                log.warn("Extended object field %s uses only 1 of %d associated resources", field, len(assoc_list))
                            field_needs.append((field, "O", first_assoc))
                            resource_needs.add(first_assoc[0])

                field_stop_time = time.time()

                log.debug("Time to process field %s(%s) %f secs", field, decorator, field_stop_time - field_start_time)

        # field_needs contains a list of what's needed to load in next step (different cases)
        if not field_needs:
            return

        # Step 2: Read second level of compound associations as needed
        # @TODO Can only do 2 level compounds for now. Make recursive
        if assoc_needs:
            assocs = self._rr.find_associations(anyside=list(assoc_needs), id_only=False)
            self._add_associations(assocs)

            # Determine resource ids to read for compound associations
            for field, need_type, needs in field_needs:
                if need_type == 'A':
                    assoc_list, predicates = needs
                    for target_id, assoc in assoc_list:
                        res_type = assoc.ot if target_id == assoc.o else assoc.st
                        assoc_list1 = self._find_associated_resources(target_id, predicates[1], None, res_type)
                        for target_id1, assoc1 in assoc_list1:
                            resource_needs.add(target_id1)

        # Step 3: Read resource objects based on needs
        res_list = self._rr.read_mult(list(resource_needs))
        res_objs = dict(zip(resource_needs, res_list))

        # Step 4: Set fields to loaded resource objects based on type
        for field, need_type, needs in field_needs:
            if need_type == 'L':
                obj_list = [res_objs[target_id] for target_id, assoc in needs]
                setattr(obj, field, obj_list)
            elif need_type == 'O':
                target_id, assoc = needs
                setattr(obj, field, res_objs[target_id])
            elif need_type == 'A':
                assoc_list, predicates = needs
                obj_list = []
                for target_id, assoc in assoc_list:
                    res_type = assoc.ot if target_id == assoc.o else assoc.st
                    assoc_list1 = self._find_associated_resources(target_id, predicates[1], None, res_type)
                    obj_list.append([res_objs[target_id1] for target_id1, assoc1 in assoc_list1])

                if obj_list:
                    if obj._schema[field]['type'] == 'list':
                        setattr(obj, field, obj_list)
                    elif obj._schema[field]['type'] == 'int':
                        setattr(obj, field, len(obj_list))
                    else:
                        if len(obj_list) != 1:
                            # WARNING: Swallow random further objects here!
                            log.warn("Extended object field %s uses only 1 of %d compound associated resources", field, len(obj_list))
                        setattr(obj, field, obj_list[0])

    def set_extended_associations(self, res_container, ext_associations, ext_exclude):
        """
        Iterates over the dict of extended field names and associations dynamically passed in.
        """
        if ext_associations is not None:
            for ext_field in ext_associations:

                if ext_exclude is not None and ext_field in ext_exclude:
                    continue

                objs = self._find_associated_resources(res_container.resource, ext_associations[ext_field])
                if objs:
                    res_container.ext_associations[ext_field] = objs
                else:
                    res_container.ext_associations[ext_field] = list()

    def _prepare_context(self, resource_id):
        """
        Initializes the context object and loads associations for resource id.
        """
        self.ctx = dict(by_subject={}, by_object={})
        assocs = self._rr.find_associations(anyside=resource_id, id_only=False)
        self._add_associations(assocs)

    def _add_associations(self, assocs):
        """
        Adds a list of Association objects to the context memory structure, indexed by
        (resource_id, predicate).
        """
        by_subject = self.ctx['by_subject']
        by_object = self.ctx['by_object']
        for assoc in assocs:
            sub_key = (assoc.s, assoc.p)
            if sub_key not in by_subject:
                by_subject[sub_key] = []
            by_subject[sub_key].append(assoc)
            obj_key = (assoc.o, assoc.p)
            if obj_key not in by_object:
                by_object[obj_key] = []
            by_object[obj_key].append(assoc)

    def is_predicate_association(self, predicate,  predicate_type, res):
        for predt in predicate[predicate_type]:
            if res == predt:
                return True
        return False

    def is_predicate_association_extension(self, predicate,  predicate_type, res):
        for predt in predicate[predicate_type]:
            if res in getextends(predt):
                return True
        return False

    def is_association_predicate(self, association):
        return Predicates.has_key(association)

    def is_compound_association(self, association):
        return CompoundAssociations.has_key(association)

    def get_compound_association_predicates(self, association):
        if CompoundAssociations.has_key(association):
            return CompoundAssociations[association]['predicates']

        return list()  # If not found then return empty list

    def _find_associated_resources(self, resource, association_predicate, target_type=None, res_type=None):
        """
        Returns a list of tuples (target_id, Association) based on associations for the given
        resource (object), predicate and optional target object type.
        This method figures out appropriate association lookup based on the predicate definitions
        @param resource Either a resource object or a resource id (then res_type is needed)
        """
        assoc_list = []
        res_type = res_type or resource.type_
        resource_id = resource if type(resource) is str else resource._id

        # First validate the association predicate
        pred = Predicates[association_predicate]
        if not pred:
            return assoc_list  # Unknown association type so return empty list

        # Need to check through all of these in this order to account for specific vs base class inclusions
        if self.is_predicate_association(pred, 'domain', res_type):
            assoc_list.extend(self._find_associations(resource_id, association_predicate, target_type, backward=False))

            # If no objects were found, try finding as subjects just in case.
            if not assoc_list:
                assoc_list.extend(self._find_associations(resource_id, association_predicate, target_type, backward=True))

        elif self.is_predicate_association(pred, 'range', res_type):
            assoc_list.extend(self._find_associations(resource_id, association_predicate, target_type, backward=True))

        elif self.is_predicate_association_extension(pred, 'domain', res_type):
            assoc_list.extend(self._find_associations(resource_id, association_predicate, target_type, backward=False))

            # If no objects were found, try finding as subjects just in case.
            if not assoc_list:
                assoc_list.extend(self._find_associations(resource_id, association_predicate, target_type, backward=True))

        elif self.is_predicate_association_extension(pred, 'range', res_type):
            assoc_list.extend(self._find_associations(resource_id, association_predicate, target_type, backward=True))

        return assoc_list

    def _find_associations(self, resource_id, predicate, target_type=None, backward=False):
        """
        Searches through associations in context either objects (from as subject) or subjects (from an object).
        Filters by target type if given.
        @retval a list of tuples (target resource id, Association object)
        """
        assoc_list = []
        if backward:
            by_object = self.ctx['by_object'].get((resource_id,predicate), [])
            assoc_list.extend([(assoc.s, assoc) for assoc in by_object if not target_type or assoc.st == target_type])
        else:
            by_subject = self.ctx['by_subject'].get((resource_id,predicate), [])
            assoc_list.extend([(assoc.o, assoc) for assoc in by_subject if not target_type or assoc.ot == target_type])
        return assoc_list

    # This method will dynamically call the specified method. It will look for the method in the current class
    # and also in the class specified by the service_provider
    def execute_method(self, resource_id, method_name, **kwargs):

        try:

            #First look to see if this is a remote method
            if method_name.find('.') > 0:

                #This is a remote method.
                rmi_call = method_name.split('.')
                #Retrieve service definition
                service_name = rmi_call[0]
                operation = rmi_call[1]
                if service_name == 'resource_registry':
                    service_client = self._rr
                else:
                    target_service = get_service_registry().get_service_by_name(service_name)
                    service_client = target_service.client(node=self.service_provider.container.instance.node, process=self.service_provider)

                methodToCall = getattr(service_client, operation)
                param_list = [resource_id]
                param_dict = self._get_method_arguments(service_client, operation, **kwargs)
                ret = methodToCall(*param_list, **param_dict )
                return ret

            else:
                #For local methods, first look for the method in the current class
                func = getattr(self, method_name, None)
                if func:
                    param_dict = self._get_method_arguments(self,method_name, **kwargs)
                    return func(resource_id, **param_dict)
                else:
                    #Next look to see if the method exists in the service provider process
                    func = getattr(self.service_provider, method_name, None)
                    if func:
                        param_dict = self._get_method_arguments(self.service_provider,method_name, **kwargs)
                        return func(resource_id, **param_dict)

                return None

        except Exception, e:
            log.error('Error executing method %s for resource id %s: %s' % (method_name, resource_id, str(e)))
            return None

    def _get_method_arguments(self, module, method_name, **kwargs):

        param_dict = {}

        try:
            method_args = inspect.getargspec(getattr(module,method_name))
            for arg in method_args[0]:
                if kwargs.has_key(arg):
                    param_dict[arg] = kwargs[arg]

        except Exception, e:
            #Log a warning and simply return an empty dict
            log.warn('Cannot determine the arguments for method: %s in module: %s: %s',module, method_name, e.message )

        return param_dict