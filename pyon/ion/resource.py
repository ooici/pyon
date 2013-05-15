#!/usr/bin/env python

"""ION Resource definitions and functions. Life-cycle FSM. Extended resource framework"""

__author__ = 'Michael Meisinger, Stephen Henrie'
__license__ = 'Apache 2.0'

import inspect
import types
import time

from pyon.core.registry import getextends, issubtype, is_ion_object, isenum
from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest, NotFound, Inconsistent, Unauthorized
from pyon.util.config import Config
from pyon.util.containers import DotDict, named_any, get_ion_ts
from pyon.util.execute import get_method_arguments, get_remote_info, execute_method
from pyon.util.log import log


# Object Types
ObjectTypes = DotDict()
OT = ObjectTypes

# Resource Types
ResourceTypes = DotDict()
RT = ResourceTypes

# Predicate Type
Predicates = DotDict()
PredicateType = DotDict()
PRED = PredicateType

# Compound Associations
CompoundAssociations = DotDict()

# Life cycle states and availability (visibility) states
LifeCycleStates = DotDict()
LCS = LifeCycleStates
LCS_NONE = "NONE"

AvailabilityStates = DotDict()
AS = AvailabilityStates

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
    lcstates = list(CommonResourceLifeCycleSM.MATURITY)
    LifeCycleStates.update(zip(lcstates, lcstates))

    AvailabilityStates.clear()
    avstates = list(CommonResourceLifeCycleSM.AVAILABILITY)
    AvailabilityStates.update(zip(avstates, avstates))


    # Life cycle events
    LCE.clear()
    LCE.update(zip([e.upper() for e in CommonResourceLifeCycleSM.BASE_EVENTS], CommonResourceLifeCycleSM.BASE_EVENTS))


def get_restype_lcsm(restype):
    return lcs_workflows.get(restype, None)


# TODO: Remove references to this from coi-services
# def get_maturity_visibility(lcstate):


def is_resource(object):
    return issubtype(object.type_, "Resource")

def lcstate(maturity, availability):
    if not maturity and maturity not in LCS:
        return BadRequest("lcstate maturity %s unknown" % maturity)
    if not availability and availability not in AS:
        return BadRequest("lcstate availability %s unknown" % availability)
    return "%s_%s" % (maturity, availability)

def lcsplit(lcstate):
    return lcstate.split('_', 1)


def get_object_schema(resource_type):
    """
    This function returns the schema for a given resource_type
    @param resource_type:
    @return:
    """

    schema_info = dict()

    #Prepare the dict entry for schema information including all of the internal object types
    schema_info['schemas'] = dict()

    #ION Objects are not registered as UNICODE names
    ion_object_name = str(resource_type)
    ret_obj = IonObject(ion_object_name, {})

    # If it's an op input param or response message object.
    # Walk param list instantiating any params that were marked None as default.
    if hasattr(ret_obj, "_svc_name"):
        schema = ret_obj._schema
        for field in ret_obj._schema:
            if schema[field]["default"] is None:
                try:
                    value = IonObject(schema[field]["type"], {})
                except NotFound:
                    # TODO
                    # Some other non-IonObject type.  Just use None as default for now.
                    value = None
                setattr(ret_obj, field, value)

    #Add schema information for sub object types
    if hasattr(ret_obj,'_schema'):
        schema_info['schemas'][ion_object_name] = ret_obj._schema
        for field in ret_obj._schema:
            obj_type = ret_obj._schema[field]['type']

            #First look for ION objects
            if is_ion_object(obj_type):

                try:
                    value = IonObject(obj_type, {})
                    schema_info['schemas'][obj_type] = value._schema

                except NotFound:
                    pass

            #Next look for ION Enums
            elif ret_obj._schema[field].has_key('enum_type'):
                if isenum(ret_obj._schema[field]['enum_type']):
                    value = IonObject(ret_obj._schema[field]['enum_type'], {})
                    schema_info['schemas'][ret_obj._schema[field]['enum_type']] = value._str_map


        schema_info['object'] = ret_obj

    elif isenum(resource_type):
        schema_info['schemas'][resource_type] = {}
        schema_info['schemas'][resource_type] = ret_obj._str_map

    else:
        raise ('%s is not an ION Object', resource_type)

    return schema_info

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
        self.initial_availability = kwargs.get('initial_availability', None)
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
                ost_lcs, ost_av = lcsplit(a_state)
                nst_lcs, nst_av = lcsplit(a_newstate)
                if a_state in self.illegal_states or a_newstate in self.illegal_states or \
                                ost_lcs in self.illegal_states or ost_av in self.illegal_states or \
                                nst_lcs in self.illegal_states or nst_av in self.illegal_states:
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

    MATURITY = ['DRAFT', 'PLANNED', 'DEVELOPED', 'INTEGRATED', 'DEPLOYED', 'RETIRED']
    AVAILABILITY = ['PRIVATE', 'DISCOVERABLE', 'AVAILABLE']

    BASE_STATES = ["%s_%s" % (m, v) for m in MATURITY for v in AVAILABILITY]

    # lcstate (maturity) transition events
    PLAN = "plan"
    DEVELOP = "develop"
    INTEGRATE = "integrate"
    DEPLOY = "deploy"
    RETIRE = "retire"

    # Availability transition events
    ANNOUNCE = "announce"
    UNANNOUNCE = "unannounce"
    ENABLE = "enable"
    DISABLE = "disable"

    MAT_EVENTS = [PLAN, DEVELOP, INTEGRATE, DEPLOY, RETIRE]
    AVAIL_EVENTS = [ANNOUNCE, UNANNOUNCE, ENABLE, DISABLE]

    BASE_EVENTS = MAT_EVENTS + AVAIL_EVENTS

    BASE_TRANSITIONS = {}

    # Transitions changing availability
    for m in MATURITY:
        if m != 'RETIRED':
            BASE_TRANSITIONS[("%s_%s" % (m, 'PRIVATE'), ANNOUNCE)] = "%s_%s" % (m, 'DISCOVERABLE')
            BASE_TRANSITIONS[("%s_%s" % (m, 'DISCOVERABLE'), UNANNOUNCE)] = "%s_%s" % (m, 'PRIVATE')

            BASE_TRANSITIONS[("%s_%s" % (m, 'DISCOVERABLE'), ENABLE)] = "%s_%s" % (m, 'AVAILABLE')
            BASE_TRANSITIONS[("%s_%s" % (m, 'AVAILABLE'), DISABLE)] = "%s_%s" % (m, 'DISCOVERABLE')

            BASE_TRANSITIONS[("%s_%s" % (m, 'PRIVATE'), ENABLE)] = "%s_%s" % (m, 'AVAILABLE')
            BASE_TRANSITIONS[("%s_%s" % (m, 'AVAILABLE'), UNANNOUNCE)] = "%s_%s" % (m, 'PRIVATE')

    # Transitions changing maturity
    for v in AVAILABILITY:
        BASE_TRANSITIONS[("%s_%s" % ('DRAFT', v), PLAN)] = "%s_%s" % ('PLANNED', v)

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

        BASE_TRANSITIONS[("%s_%s" % ('DRAFT', v), RETIRE)] = "%s_%s" % ('RETIRED', 'PRIVATE')
        BASE_TRANSITIONS[("%s_%s" % ('PLANNED', v), RETIRE)] = "%s_%s" % ('RETIRED', 'PRIVATE')
        BASE_TRANSITIONS[("%s_%s" % ('DEVELOPED', v), RETIRE)] = "%s_%s" % ('RETIRED', 'PRIVATE')
        BASE_TRANSITIONS[("%s_%s" % ('INTEGRATED', v), RETIRE)] = "%s_%s" % ('RETIRED', 'PRIVATE')
        BASE_TRANSITIONS[("%s_%s" % ('DEPLOYED', v), RETIRE)] = "%s_%s" % ('RETIRED', 'PRIVATE')


    def __init__(self, **kwargs):
        super(CommonResourceLifeCycleSM, self).__init__(**kwargs)
        for (s0, ev), s1 in self.BASE_TRANSITIONS.iteritems():
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

        # Check to make sure the extended resource decorator raise OriginResourceType matches the type of the resource type
        originResourceType = res_container.get_class_decorator_value('OriginResourceType')
        if originResourceType is None:
            log.error('The requested extended resource %s does not contain an OriginResourceType decorator.' , extended_resource_type)

        elif originResourceType != resource_object.type_ and not issubtype(resource_object.type_, originResourceType):
            raise Inconsistent('The OriginResourceType decorator of the requested resource %s(%s) does not match the type of the specified resource id(%s).' % (
                extended_resource_type, originResourceType, resource_object.type_))

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
        restype_workflow = get_restype_lcsm(res_container.resource.type_)
        if restype_workflow:
            successors = restype_workflow.get_successors(lcstate(res_container.resource.lcstate, res_container.resource.availability))
            res_container.lcstate_transitions = {}
            res_container.availability_transitions = {}
            for event, target in successors.iteritems():
                target_lcstate, target_availability = lcsplit(target)
                if not target_lcstate == res_container.resource.lcstate:
                    res_container.lcstate_transitions[event] = target_lcstate
                if not target_availability == res_container.resource.availability:
                    res_container.availability_transitions[event] = target_availability
        else:
            res_container.lcstate_transitions = {"retire": "RETIRED"}
            res_container.availability_transitions = {}

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
        final_target_types = {}  # Keeps track of what resource type filter is desired

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
                    method_name = deco_value if deco_value else 'get_' + field

                    ret_val = self.execute_method_with_resource(resource._id, method_name, **kwargs)
                    if ret_val is not None:
                        setattr(obj, field, ret_val)

                elif decorator == 'ServiceRequest':
                    deco_value = obj.get_decorator_value(field, decorator)
                    if obj._schema[field]['type'] != 'ServiceRequest':
                        log.error('The field %s is an incorrect type for a ServiceRequest decorator.', field)
                        continue

                    method_name = deco_value if deco_value else 'get_' + field

                    if method_name.find('.') == -1:
                        raise Inconsistent('The field %s decorated as a ServiceRequest only supports remote operations.', field)

                    service_client, operation = get_remote_info(self, method_name)
                    rmi_call = method_name.split('.')
                    parms = { 'resource_id': resource._id }
                    parms.update(get_method_arguments(service_client, operation, **kwargs))
                    ret_val = IonObject(OT.ServiceRequest, service_name=rmi_call[0], service_operation=operation, request_parameters=parms )
                    setattr(obj, field, ret_val)

                # Fill field based on compound association chains. Results in nested lists of resource objects
                elif self.is_compound_association(decorator):

                    target_type = obj.get_decorator_value(field, decorator)
                    if target_type.find(',') > 0: #Can specify multiple type filters, only handles two levels for now
                        target_type, final_target_type = target_type.split(',')
                        final_target_types[field] = final_target_type # Keep track for later

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
        # @TODO Can only do 2 level compounds for now. Make recursive someday
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


                #Filter thelist to remove objects that might match the current resource type
                result_obj_list = []
                for ol_nested in obj_list:
                    if ol_nested:
                        #Only get the object types which don't match the current resource type and may match a final type
                        if final_target_types.has_key(field):
                            result_obj_list.extend([target_obj for target_obj in ol_nested if ( target_obj.type_ != resource.type_ and target_obj.type_ == final_target_types[field] ) ])
                        else:
                            result_obj_list.extend([target_obj for target_obj in ol_nested if ( target_obj.type_ != resource.type_  ) ])

                if result_obj_list:
                    if obj._schema[field]['type'] == 'list':
                        setattr(obj, field, result_obj_list)
                    elif obj._schema[field]['type'] == 'int':
                        setattr(obj, field, len(result_obj_list))
                    else:

                        if len(result_obj_list) != 1:
                            # WARNING: Swallow random further objects here!
                            log.warn("Extended object field %s uses only 1 of %d compound associated resources", field, len(result_obj_list))

                        setattr(obj, field, result_obj_list[0]);


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


    def execute_method_with_resource(self, resource_id, method_name, **kwargs):

        try:
            args = [resource_id]
            return execute_method(self, method_name, *args, **kwargs)

        except Unauthorized:
            #No need to do anything if the user was unauthorized. This is NOT an error, just means the user does not have the proper rights.
            pass

        except Exception, e:
            log.error('Error executing method %s for resource id %s: %s' % (method_name, resource_id, str(e)))

        return None



    def create_prepare_resource_support(self, resource_id="", prepare_resource_type=None, origin_resource_type=None):

        if not isinstance(resource_id, types.StringType):
            raise Inconsistent("The parameter resource_id is not a single resource id string")

        if not self.service_provider or not self._rr:
            raise Inconsistent("This class is not initialized properly")

        if prepare_resource_type is not None and prepare_resource_type not in getextends(OT.ResourcePrepareSupport):
            raise BadRequest('The requested resource %s is not extended from %s' % (prepare_resource_type, OT.ResourcePrepareSupport))


        resource_data = IonObject(prepare_resource_type)

        # Check to make sure the extended resource decorator raise OriginResourceType matches the type of the resource type
        origin_resource_decorator =  resource_data.get_class_decorator_value('OriginResourceType')
        if origin_resource_decorator is None and origin_resource_type is None:
            raise NotFound('OriginResourceType decorator not found in object specification %s', prepare_resource_type)

        origin_resource_type = origin_resource_type if origin_resource_type is not None else origin_resource_decorator
        if origin_resource_type is None:
            raise NotFound('OriginResourceType decorator not found in object specification %s', prepare_resource_type)


        resource_object = None
        if resource_id:
            resource_object = self._rr.read(resource_id)

            if origin_resource_type != resource_object.type_ and not issubtype(resource_object.type_, origin_resource_type):
                raise Inconsistent('The OriginResourceType decorator of the requested resource %s(%s) does not match the type of the specified resource id(%s).' % (
                    prepare_resource_type, origin_resource_type, resource_object.type_))

            resource_data._id = resource_object._id
        else:
            resource_object = IonObject(origin_resource_type)

        resource_data.resource = resource_object
        resource_data.resource_schema = get_object_schema(origin_resource_type)

        for field in resource_data._schema:

            deco_value = resource_data.get_decorator_value(field, 'AssociatedResources')
            assoc_dict = {}
            if deco_value is not None:
                if deco_value.find(',') == -1:
                    associated_resources = [deco_value]
                else:
                    associated_resources = deco_value.split(',')

                for res in associated_resources:
                    assoc = self.get_associated_resource_info(origin_resource_type, resource_id, res)
                    assoc_dict[assoc.resource_type] = assoc

                setattr(resource_data, field, assoc_dict)
                continue


        return resource_data


    def get_associated_resource_info(self, origin_resource_type="", resource_id="", assoc_resource_type=None):

        if not origin_resource_type:
            raise Inconsistent("The parameter origin_resource_type is not set")

        if not isinstance(resource_id, types.StringType):
            raise Inconsistent("The parameter resource_id is not a single resource id string")

        if not self.service_provider or not self._rr:
            raise Inconsistent("This class is not initialized properly")

        if assoc_resource_type is not None and assoc_resource_type not in getextends(OT.AssociatedResources):
            raise BadRequest('The requested resource %s is not extended from %s' % (assoc_resource_type, OT.AssociatedResources))


        resource_data = IonObject(assoc_resource_type)

        for field in resource_data._schema:

            deco_value = resource_data.get_decorator_value(field, 'ResourceType')
            if deco_value is not None:

                #Set the type of the associated resource to be used as the key in dict of associations
                setattr(resource_data, 'resource_type', deco_value)

                res_list,_ = self._rr.find_resources(restype=deco_value, id_only=False)

                exclude_lcs_filter_value = resource_data.get_decorator_value(field, 'ExcludeLifecycleStates')
                if exclude_lcs_filter_value is not None and exclude_lcs_filter_value.find(',') > -1:
                    exclude_filter = exclude_lcs_filter_value.split(',')
                    res_list = [res for res in res_list if res.lcstate not in exclude_filter ]

                #Look for ResourceSPOFilter filter and filter above results to exclude other resources already assigned
                #This filter MUST be a comma separated value of Subject, Predicate, Object
                res_filter_value = resource_data.get_decorator_value(field, 'ResourceSPOFilter')
                if res_filter_value is not None and res_filter_value.find(',') > -1:
                    assoc_filter = res_filter_value.split(',')

                    res_associations = self._rr.find_associations(predicate=assoc_filter[1], id_only=False)
                    assoc_list = [a for a in res_associations if a.st==assoc_filter[0] and a.ot==assoc_filter[2]]

                    def resource_available(res):
                        for assoc in assoc_list:
                            if assoc.st == origin_resource_type:
                                if assoc.o == res._id:
                                    if not resource_id:
                                        return False

                                    if assoc.s == resource_id:
                                        return True
                                    else:
                                        return False

                            else:
                                if assoc.s == res._id:
                                    if not resource_id:
                                        return False

                                    if assoc.o == resource_id:
                                        return True
                                    else:
                                        return False

                        return True


                    #Iterate over the list and remove any object which are assigned to other resources and not the target resource
                    final_list = []
                    final_list.extend( [res for res in res_list if resource_available(res)])
                    setattr(resource_data, field, final_list)

                else:
                    setattr(resource_data, field, res_list)

                continue


            deco_value = resource_data.get_decorator_value(field, 'Association')
            if deco_value is not None:

                #If the association is related to an existing resource and this is a create then skip
                if not resource_id and ( resource_data.is_decorator(field, 'ResourceSubject') or
                                         resource_data.is_decorator(field, 'ResourceObject')):
                    continue

                resource_sub = resource_id if resource_data.is_decorator(field, 'ResourceSubject') else None
                resource_obj = resource_id if resource_data.is_decorator(field, 'ResourceObject') else None
                assoc_list = self._rr.find_associations(subject=resource_sub, predicate=deco_value, object=resource_obj, id_only=False)

                subject_type = resource_data.get_decorator_value(field, 'SubjectType')
                if subject_type is not None:
                    assoc_list = [assoc for assoc in assoc_list if ( assoc.st == subject_type )]

                object_type = resource_data.get_decorator_value(field, 'ObjectType')
                if object_type is not None:
                    assoc_list = [assoc for assoc in assoc_list if ( assoc.ot == object_type )]


                setattr(resource_data, field, assoc_list)
                continue



        return resource_data

    def set_service_requests(self, service_request=None, service_name='', service_operation='', request_parameters=None):

        assert(service_request)
        assert(service_name)
        assert(service_operation)
        assert(request_parameters)

        service_request.service_name = service_name
        service_request.service_operation = service_operation
        service_request.request_parameters = request_parameters if request_parameters is not None else {}

        return
