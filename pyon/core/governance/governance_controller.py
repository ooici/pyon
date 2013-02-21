    #!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

import types
from pyon.core.bootstrap import CFG, get_service_registry, IonObject
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher
from pyon.util.log import log
from pyon.core.exception import BadRequest, Inconsistent
from pyon.ion.resource import RT, PRED, LCS, OT
from pyon.core.governance.policy.policy_decision import PolicyDecisionPointManager
from pyon.event.event import EventSubscriber
from interface.services.coi.ipolicy_management_service import PolicyManagementServiceProcessClient
from interface.services.coi.iresource_registry_service import ResourceRegistryServiceProcessClient
from interface.services.coi.iorg_management_service import OrgManagementServiceProcessClient
from pyon.core.exception import NotFound, Unauthorized
from pyon.util.containers import get_ion_ts, get_safe

#These constants are ubiquitous, so define in the container
DEFAULT_ACTOR_ID = 'anonymous'
ORG_MANAGER_ROLE = 'ORG_MANAGER'  # Can only act upon resource within the specific Org
ORG_MEMBER_ROLE = 'ORG_MEMBER'    # Can only access resources within the specific Org
ION_MANAGER = 'ION_MANAGER'   # Can act upon resources across all Orgs - like a Super User access

class GovernanceController(object):


    def __init__(self,container):
        log.debug('GovernanceController.__init__()')
        self.container = container
        self.enabled = False
        self.interceptor_by_name_dict = dict()
        self.interceptor_order = []
        self.policy_decision_point_manager = None
        self.governance_dispatcher = None

        # Holds a list per service operation of policy methods to check before the op in a process is allowed to be called
        self._service_op_preconditions = dict()

        self._is_container_org_boundary = False
        self._container_org_name = None
        self._container_org_id = None

    def start(self):

        log.debug("GovernanceController starting ...")

        self.enabled = CFG.get_safe('interceptor.interceptors.governance.config.enabled', False)

        log.info("GovernanceInterceptor enabled: %s" % str(self.enabled))

        self.resource_policy_event_subscriber = None
        self.service_policy_event_subscriber = None

        #containers default to not Org Boundary and ION Root Org
        self._is_container_org_boundary = CFG.get_safe('container.org_boundary',False)
        self._container_org_name = CFG.get_safe('container.org_name', CFG.get_safe('system.root_org', 'ION'))
        self._container_org_id = None
        self._system_root_org_name = CFG.get_safe('system.root_org', 'ION')

        self._is_root_org_container = (self._container_org_name == self._system_root_org_name)

        if self.enabled:

            config = CFG.get_safe('interceptor.interceptors.governance.config')

            self.initialize_from_config(config)

            self.resource_policy_event_subscriber = EventSubscriber(event_type="ResourcePolicyEvent", callback=self.resource_policy_event_callback)
            self.resource_policy_event_subscriber.start()

            self.service_policy_event_subscriber = EventSubscriber(event_type="ServicePolicyEvent", callback=self.service_policy_event_callback)
            self.service_policy_event_subscriber.start()

            self.rr_client = ResourceRegistryServiceProcessClient(node=self.container.node, process=self.container)
            self.policy_client = PolicyManagementServiceProcessClient(node=self.container.node, process=self.container)

    def initialize_from_config(self, config):

        self.governance_dispatcher = GovernanceDispatcher()

        self.policy_decision_point_manager = PolicyDecisionPointManager(self)

        if 'interceptor_order' in config:
            self.interceptor_order = config['interceptor_order']

        if 'governance_interceptors' in config:
            gov_ints = config['governance_interceptors']

            for name in gov_ints:
                interceptor_def = gov_ints[name]

                # Instantiate and put in by_name array
                parts = interceptor_def["class"].split('.')
                modpath = ".".join(parts[:-1])
                classname = parts[-1]
                module = __import__(modpath, fromlist=[classname])
                classobj = getattr(module, classname)
                classinst = classobj()

                # Put in by_name_dict for possible re-use
                self.interceptor_by_name_dict[name] = classinst

    def stop(self):
        log.debug("GovernanceController stopping ...")

        if self.resource_policy_event_subscriber is not None:
            self.resource_policy_event_subscriber.stop()

        if self.service_policy_event_subscriber is not None:
            self.service_policy_event_subscriber.stop()

    @property
    def _rr(self):
        """
        Returns the active resource registry instance or client.

        Used to directly contact the resource registry via the container if available,
        otherwise the messaging client to the RR service is returned.
        """
        if self.container.has_capability('RESOURCE_REGISTRY'):
            return self.container.resource_registry

        return self.rr_client

    def is_container_org_boundary(self):
        return self._is_container_org_boundary

    def is_root_org_container(self):
        return self._is_root_org_container

    def get_container_org_boundary_name(self):
        return self._container_org_name

    def get_container_org_boundary_id(self):

        if not self._is_container_org_boundary:
            return None

        if self._container_org_id is None:
            org, _ = self._rr.find_resources(restype=RT.Org,name=self._container_org_name)

            if org:
                self._container_org_id = org[0]._id

        return self._container_org_id

    def process_incoming_message(self,invocation):

        self.process_message(invocation, self.interceptor_order,'incoming' )
        return self.governance_dispatcher.handle_incoming_message(invocation)

    def process_outgoing_message(self,invocation):
        self.process_message(invocation, reversed(self.interceptor_order),'outgoing')
        return self.governance_dispatcher.handle_outgoing_message(invocation)

    def process_message(self,invocation,interceptor_list, method):

        for int_name in interceptor_list:
            class_inst = self.interceptor_by_name_dict[int_name]
            getattr(class_inst, method)(invocation)

            #Stop processing message if an issue with the message was found by an interceptor.
            if ( invocation.message_annotations.has_key(GovernanceDispatcher.CONVERSATION__STATUS_ANNOTATION) and invocation.message_annotations[GovernanceDispatcher.CONVERSATION__STATUS_ANNOTATION] == GovernanceDispatcher.STATUS_REJECT) or\
               ( invocation.message_annotations.has_key(GovernanceDispatcher.POLICY__STATUS_ANNOTATION) and invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] == GovernanceDispatcher.STATUS_REJECT) :
                break

        return invocation

    #Helper methods

    def get_role_message_headers(self, org_roles):
        '''
        Iterate the Org(s) that the user belongs to and create a header that lists only the role names per Org assigned
        to the user; i.e. {'ION': ['Member', 'Operator'], 'Org2': ['Member']}
        @param org_roles:
        @return:
        '''
        role_header = dict()
        try:
            for org in org_roles:
                role_header[org] = []
                for role in org_roles[org]:
                    role_header[org].append(role.name)
            return role_header

        except Exception, e:
            log.error(e)
            return role_header


    def build_actor_header(self, actor_id=DEFAULT_ACTOR_ID, actor_roles=None):
        '''
        Use this to build the message header used by governance to identify the actor and roles.
        @param actor_id:
        @param actor_roles:
        @return:
        '''
        actor_roles = actor_roles or {}
        return {'ion-actor-id': actor_id, 'ion-actor-roles': actor_roles }

    def get_actor_header(self, actor_id):
        '''
        Returns the actor related message headers for a specific actorid - will return anonymous if the actor_id is not found.
        @param actor_id:
        @return:
        '''
        actor_header = self.build_actor_header(DEFAULT_ACTOR_ID, {})

        if actor_id:
            try:
                header_roles = self.find_roles_by_actor(actor_id)
                actor_header = self.build_actor_header(actor_id, header_roles)
            except Exception, e:
                log.error(e)

        return actor_header

    def has_org_role(self, role_header=None, org_name=None, role_name=None):
        '''
        Check the ion-actor-roles message header to see if this actor has the specified role in the specified Org.
        Parameter role_name can be a string with the name of a user role or a list of user role names, which will
        recursively call this same method for each role name in the list until one is found or the list is exhausted.
        @param role_header:
        @param org_name:
        @param role_name:
        @return:
        '''
        if role_header is None or org_name is None or role_name is None:
            raise BadRequest("One of the parameters to this method are not set")

        if isinstance(role_name, list):
            for role in role_name:
                if self.has_org_role(role_header, org_name, role):
                    return True
        else:
            if role_header.has_key(org_name):
                if role_name in role_header[org_name]:
                    return True

        return False


    def find_roles_by_actor(self, actor_id=None):
        '''
        Returns a dict of all User Roles roles by Org Name associated with the specified actor
        @param actor_id:
        @return:
        '''
        if actor_id is None or not len(actor_id):
            raise BadRequest("The actor_id parameter is missing")

        role_dict = dict()

        role_list,_ = self._rr.find_objects(actor_id, PRED.hasRole, RT.UserRole)

        for role in role_list:

            if not role_dict.has_key(role.org_name):
                role_dict[role.org_name] = list()

            role_dict[role.org_name].append(role.name)

        #Membership in ION Org is implied
        if not role_dict.has_key(self._system_root_org_name):
            role_dict[self._system_root_org_name] = list()

        role_dict[self._system_root_org_name].append(ORG_MEMBER_ROLE)


        return role_dict


    def get_system_actor(self):
        '''
        Returns the ION System Actor defined in the Resource Registry
        @return:
        '''
        try:
            system_actor, _ = self._rr.find_resources(RT.ActorIdentity,name=get_safe(CFG, "system.system_actor", "ionsystem"), id_only=False)
            if not system_actor:
                return None

            return system_actor[0]

        except Exception, e:
            log.error(e)
            return None

    def is_system_actor(self, actor_id):
        '''
        Is this the specified actor_id the system actor
        @param actor_id:
        @return:
        '''
        system_actor = self.get_system_actor()
        if system_actor is not None and system_actor._id == actor_id:
            return True

        return False

    def get_system_actor_header(self, system_actor=None):
        '''
        Returns the actor related message headers for a the ION System Actor
        @param system_actor:
        @return:
        '''
        try:
            if system_actor is None:
                system_actor = self.get_system_actor()

            if not system_actor or system_actor is None:
                log.warn('The ION System Actor Identity was not found; defaulting to anonymous actor')
                actor_header = self.get_actor_header(None)
            else:
                actor_header = self.get_actor_header(system_actor._id)

            return actor_header

        except Exception, e:
            log.error(e)
            return self.get_actor_header(None)


    def get_governance_resource_header_values(self, headers, resource_id_required=True):
        '''
        A helper function for retriving op, actor_id, actor_roles, resource_id from the message header
        @param headers:
        @return op, actor_id, actor_roles, resource_id:
        '''

        if headers.has_key('op'):
            op = headers['op']
        else:
            op = "Unknown operation"

        if headers.has_key('ion-actor-id'):
            actor_id = headers['ion-actor-id']
        else:
            raise Inconsistent('%s(%s) has been denied since the ion-actor-id can not be found in the message headers'% (self.name, op))

        if headers.has_key('ion-actor-roles'):
            actor_roles = headers['ion-actor-roles']
        else:
            raise Inconsistent('%s(%s) has been denied since the ion-actor-roles can not be found in the message headers'% (self.name, op))

        if headers.has_key('resource-id'):
            resource_id = headers['resource-id']
        else:
            if resource_id_required:
                raise Inconsistent('%s(%s) has been denied since the resource-id can not be found in the message headers'% (self.name, op))
            resource_id = ''

        return op, actor_id, actor_roles, resource_id


    def get_resource_commitments(self, actor_id, resource_id):
        '''
        Returns the list of commitments for the specified user and resource
        @param actor_id:
        @param resource_id:
        @return:
        '''
        log.debug("Finding commitments for actor_id: %s and resource_id: %s" % (actor_id, resource_id))

        try:

            commitments,_ = self._rr.find_objects(resource_id, PRED.hasCommitment, RT.Commitment)
            if not commitments:
                return None

            cur_time = int(get_ion_ts())
            commitment_list = []
            for com in commitments:  #TODO - update when Retired is removed from find_objects
                if com.consumer == actor_id and com.lcstate != LCS.RETIRED and ( com.expiration == 0 or \
                ( com.expiration > 0 and cur_time < com.expiration)):
                    commitment_list.append(com)

            if commitment_list:
                return commitment_list

        except Exception, e:
            log.error(e)

        return None

    def has_resource_commitments(self, actor_id, resource_id):
        '''
        Returns a ResourceCommitmentStatus object indicating the commitment status between this resource/actor
        Can only have an exclusive commitment if actor already has a shared commitment.
        @param actor_id:
        @param resource_id:
        @return:
        '''
        ret_status = IonObject(OT.ResourceCommitmentStatus)
        commitments = self.get_resource_commitments(actor_id, resource_id)
        if commitments is None:
            #No commitments were found between this resource_id and actor_id
            return ret_status

        ret_status.shared = True

        for com in commitments:
            if com.commitment.exclusive == True:
                #Found an exclusive commitment
                ret_status.exclusive = True
                return ret_status

        #Only a shared commitment was found
        return ret_status

    def is_resource_owner(self, actor_id=None, resource_id=None):
        '''
        Returns True if the specified actor_id is an Owner of the specified resource id, otherwise False
        @param actor_id:
        @param resource_id:
        @return:
        '''
        if actor_id is None or resource_id is None:
            raise BadRequest('One or all of the method parameters are not set')

        owners =  self._rr.find_objects(subject=resource_id, predicate=PRED.hasOwner, object_type=RT.ActorIdentity, id_only=True)

        if actor_id not in owners[0]:
            return False

        return True

    def has_shared_resource_commitment(self, actor_id=None, resource_id=None):
        '''
        This method returns True if the specified actor_id has acquired shared access for the specified resource id, otherwise False.
        @param msg:
        @param headers:
        @return:
        '''
        if actor_id is None or resource_id is None:
            raise BadRequest('One or all of the method parameters are not set')

        commitment_status =  self.has_resource_commitments(actor_id, resource_id)

        return commitment_status.shared


    def has_exclusive_resource_commitment(self, actor_id=None, resource_id=None):
        '''
        This method returns True if the specified actor_id has acquired exclusive access for the specified resource id, otherwise False.
        @param msg:
        @param headers:
        @return:
        '''
        if actor_id is None or resource_id is None:
            raise BadRequest('One or all of the method parameters are not set')

        commitment_status =  self.has_resource_commitments(actor_id, resource_id)

        #If the resource has not been acquired for sharing, then it can't have been acquired exclusively
        if not commitment_status.shared:
            return False

        return commitment_status.exclusive

    #Manage all of the policies in the container

    def resource_policy_event_callback(self, *args, **kwargs):

        resource_policy_event = args[0]
        log.debug('Resouce related policy event received: %s', str(resource_policy_event.__dict__))

        policy_id = resource_policy_event.origin
        resource_id = resource_policy_event.resource_id
        resource_type = resource_policy_event.resource_type
        resource_name = resource_policy_event.resource_name
        delete_policy = True if resource_policy_event.sub_type == 'DeletePolicy' else False

        self.update_resource_access_policy(resource_id, delete_policy)

    def service_policy_event_callback(self, *args, **kwargs):
        service_policy_event = args[0]
        log.debug('Service related policy event received: %s', str(service_policy_event.__dict__))

        policy_id = service_policy_event.origin
        service_name = service_policy_event.service_name
        service_op = service_policy_event.op
        delete_policy = True if service_policy_event.sub_type == 'DeletePolicy' else False

        if service_name:
            if self.container.proc_manager.is_local_service_process(service_name):
                self.update_service_access_policy(service_name, service_op, delete_policy)
            elif self.container.proc_manager.is_local_agent_process(service_name):
                self.update_service_access_policy(service_name, service_op, delete_policy)

        else:

            if self.policy_decision_point_manager is not None:
                try:
                    rules = self.policy_client.get_active_service_access_policy_rules('', self._container_org_name)
                    self.policy_decision_point_manager.load_common_service_policy_rules(rules)

                    #Reload all policies for existing services
                    for service_name in self.policy_decision_point_manager.get_list_service_policies():
                        if self.container.proc_manager.is_local_service_process(service_name):
                            self.update_service_access_policy(service_name, delete_policy)

                except Exception, e:
                    #If the resource does not exist, just ignore it - but log a warning.
                    log.warn("There was an error applying access policy: %s" % e.message)


    def safe_update_resource_access_policy(self, resource_id):

        if self._is_policy_management_service_available():
            self.update_resource_access_policy(resource_id)

    def update_resource_access_policy(self, resource_id, delete_policy=False):

        if self.policy_decision_point_manager is not None:

            try:
                policy_rules = self.policy_client.get_active_resource_access_policy_rules(resource_id)
                self.policy_decision_point_manager.load_resource_policy_rules(resource_id, policy_rules)

            except Exception, e:
                #If the resource does not exist, just ignore it - but log a warning.
                log.warn("The resource %s is not found or there was an error applying access policy: %s" % ( resource_id, e.message))


    def safe_update_service_access_policy(self, service_name, service_op=''):

        if  self._is_policy_management_service_available():
            self.update_service_access_policy(service_name)

    def update_service_access_policy(self, service_name, service_op='', delete_policy=False):

        if self.policy_decision_point_manager is not None:

            try:
                #First update any access policy rules
                rules = self.policy_client.get_active_service_access_policy_rules(service_name, self._container_org_name)
                self.policy_decision_point_manager.load_service_policy_rules(service_name, rules)

            except Exception, e:
                #If the resource does not exist, just ignore it - but log a warning.
                log.warn("The service %s is not found or there was an error applying access policy: %s" % ( service_name, e.message))

            #Next update any precondition policies
            try:
                proc = self.container.proc_manager.get_a_local_process(service_name)
                if proc is not None:
                    op_preconditions = self.policy_client.get_active_process_operation_preconditions(service_name, service_op, self._container_org_name)
                    if op_preconditions:
                        for op in op_preconditions:
                            for pre in op.preconditions:
                                self.unregister_process_operation_precondition(proc,op.op, pre)
                                if not delete_policy:
                                    self.register_process_operation_precondition(proc, op.op, pre )
                    else:
                        #Unregister all...just in case
                        self.unregister_all_process_operation_precondition(proc,service_op)

            except Exception, e:
                #If the resource does not exist, just ignore it - but log a warning.
                log.warn("The process %s is not found for op %s or there was an error applying access policy: %s" % ( service_name, service_op, e.message))


    def _is_policy_management_service_available(self):
        """
        Method to verify if the Policy Management Service is running in the system. If the container cannot connect to
        the RR then assume it is remote container so do not try to access Policy Management Service
        """
        policy_service = get_service_registry().is_service_available('policy_management', True)
        if policy_service:
            return True
        return False

    # Methods for managing operation specific policy
    def get_process_operation_dict(self, process_name):
        if self._service_op_preconditions.has_key(process_name):
            return self._service_op_preconditions[process_name]

        self._service_op_preconditions[process_name] = dict()
        return self._service_op_preconditions[process_name]


    def register_process_operation_precondition(self, process, operation, precondition):
        '''
        This method is used to register service operation precondition functions with the governance controller. The endpoint
        code will call check_process_operation_preconditions() below before calling the business logic operation and if any of
        the precondition functions return False, then the request is denied as Unauthorized.

        At some point, this should be refactored to by another interceptor, but at the operation level.

        @param process:
        @param operation:
        @param precondition:
        @param policy_object:
        @return:
        '''

        if not hasattr(process, operation):
            raise NotFound("The operation %s does not exist for the %s service" % (operation, process.name))

        if type(precondition) == types.MethodType and precondition.im_self != process:
            raise NotFound("The method %s does not exist for the %s service." % (str(precondition), process.name))
        elif type(precondition) == types.StringType:
            #Convert string to instancemethod if it exists..if not store as potential precondition to execute
            method = getattr(process, precondition, None)
            if method:
                precondition = method

        process_op_conditions = self.get_process_operation_dict(process.name)
        if process_op_conditions.has_key(operation):
            process_op_conditions[operation].append(precondition)
        else:
            preconditions = list()
            preconditions.append(precondition)
            process_op_conditions[operation] = preconditions

    def unregister_all_process_operation_precondition(self, process, operation):
        '''
        This method removes all precondition functions registerd with an operation on a process. Care should be taken with this
        call, as it can remove "hard wired" preconditions that are coded directly and not as part of policy objects, such as
        with SA resource lifecycle preconditions.

        @param process:
        @param operation:
        @return:
        '''
        process_op_conditions = self.get_process_operation_dict(process.name)
        if process_op_conditions.has_key(operation):
            del process_op_conditions[operation]

    def unregister_process_operation_precondition(self, process, operation, precondition):

        #Just skip this if there operation is not passed in.
        if operation is None:
            return

        if not hasattr(process, operation):
            raise NotFound("The operation %s does not exist for the %s service" % (operation, process.name))

        if type(precondition) == types.StringType:
            #Convert string to instancemethod
            method = getattr(process, precondition, None)
            if method:
                precondition = method

        process_op_conditions = self.get_process_operation_dict(process.name)
        if process_op_conditions.has_key(operation):
            preconditions = process_op_conditions[operation]
            preconditions[:] = [pre for pre in preconditions if not pre == precondition]
            if not preconditions:
                del process_op_conditions[operation]


    def check_process_operation_preconditions(self, process, msg, headers):
        operation      = headers.get('op', None)
        if operation is None:
            return

        process_op_conditions = self.get_process_operation_dict(process.name)
        if process_op_conditions.has_key(operation):
            preconditions = process_op_conditions[operation]
            for precond in reversed(preconditions):
                if type(precond) == types.MethodType or type(precond) == types.FunctionType:
                    #Handle precondition which are built-in functions
                    try:
                        ret_val, ret_message = precond(msg, headers)
                    except Exception, e:
                        #TODD - Catching all exceptions and logging as errors, don't want to stop processing for this right now
                        log.error('Executing precondition function: %s for operation: %s - %s so it will be ignored.' % (precond.__name__, operation, e.message))
                        ret_val = True
                        ret_message = ''

                    if not ret_val:
                        raise Unauthorized(ret_message)

                elif type(precond) == types.StringType:

                    try:
                        exec precond
                        pref = locals()["precondition_func"]
                        ret_val, ret_message = pref(process, msg, headers)

                    except Exception, e:
                        #TODD - Catching all exceptions and logging as errors, don't want to stop processing for this right now
                        log.error('Executing precondition function: %s for operation: %s - %s so it will be ignored.' % (precond, operation, e.message))
                        ret_val = True
                        ret_message = ''

                    if not ret_val:
                        raise Unauthorized(ret_message)



