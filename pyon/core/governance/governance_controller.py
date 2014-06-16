    #!/usr/bin/env python


__author__ = 'Stephen P. Henrie'


import types

from pyon.core.bootstrap import CFG, get_service_registry, is_testing
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher
from pyon.util.log import log
from pyon.ion.resource import RT, OT
from pyon.core.governance import get_system_actor_header, get_system_actor
from pyon.core.governance.policy.policy_decision import PolicyDecisionPointManager
from pyon.ion.event import EventSubscriber
from pyon.core.exception import NotFound, Unauthorized
from pyon.container.procs import SERVICE_PROCESS_TYPE, AGENT_PROCESS_TYPE
from pyon.util.containers import get_ion_ts, DictDiffer

from interface.services.coi.ipolicy_management_service import PolicyManagementServiceProcessClient
from interface.services.coi.iresource_registry_service import ResourceRegistryServiceProcessClient

class GovernanceController(object):
    """
    This is a singleton object which handles governance functionality in the container.
    """

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

        # For policy debugging purposes. Keeps a list of most recent policy updates for later readout
        self._policy_update_log = []
        self._policy_snapshot = None

    def start(self):

        log.debug("GovernanceController starting ...")

        self._CFG = CFG

        self.enabled = CFG.get_safe('interceptor.interceptors.governance.config.enabled', False)

        log.info("GovernanceInterceptor enabled: %s" % str(self.enabled))

        self.policy_event_subscriber = None

        #containers default to not Org Boundary and ION Root Org
        self._is_container_org_boundary = CFG.get_safe('container.org_boundary',False)
        self._container_org_name = CFG.get_safe('container.org_name', CFG.get_safe('system.root_org', 'ION'))
        self._container_org_id = None
        self._system_root_org_name = CFG.get_safe('system.root_org', 'ION')

        self._is_root_org_container = (self._container_org_name == self._system_root_org_name)

        self.system_actor_id = None
        self.system_actor_user_header = None

        if self.enabled:

            config = CFG.get_safe('interceptor.interceptors.governance.config')

            self.initialize_from_config(config)

            self.policy_event_subscriber = EventSubscriber(event_type=OT.PolicyEvent, callback=self.policy_event_callback)
            self.policy_event_subscriber.start()

            self.rr_client = ResourceRegistryServiceProcessClient(node=self.container.node, process=self.container)
            self.policy_client = PolicyManagementServiceProcessClient(node=self.container.node, process=self.container)

            self._policy_snapshot = self._get_policy_snapshot()
            self._log_policy_update("start_governance_ctrl", message="Container start")

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

        if self.policy_event_subscriber is not None:
            self.policy_event_subscriber.stop()


    @property
    def is_container_org_boundary(self):
        return self._is_container_org_boundary

    @property
    def container_org_name(self):
        return self._container_org_name

    @property
    def system_root_org_name(self):
        return self._system_root_org_name

    @property
    def is_root_org_container(self):
        return self._is_root_org_container

    @property
    def CFG(self):
        return self._CFG


    @property
    def rr(self):
        """
        Returns the active resource registry instance or client.

        Used to directly contact the resource registry via the container if available,
        otherwise the messaging client to the RR service is returned.
        """
        if self.container.has_capability('RESOURCE_REGISTRY'):
            return self.container.resource_registry

        return self.rr_client


    def get_container_org_boundary_id(self):
        """
        Returns the permanent org identifier configured for this container
        @return:
        """

        if not self._is_container_org_boundary:
            return None

        if self._container_org_id is None:
            orgs, _ = self.rr.find_resources(restype=RT.Org)
            for org in orgs:
                if org.org_governance_name == self._container_org_name:
                    self._container_org_id = org._id
                    break

        return self._container_org_id

    def process_incoming_message(self,invocation):
        """
        The GovernanceController hook into the incoming message interceptor stack
        @param invocation:
        @return:
        """
        self.process_message(invocation, self.interceptor_order,'incoming' )
        return self.governance_dispatcher.handle_incoming_message(invocation)

    def process_outgoing_message(self,invocation):
        """
        The GovernanceController hook into the outgoing message interceptor stack
        @param invocation:
        @return:
        """
        self.process_message(invocation, reversed(self.interceptor_order),'outgoing')
        return self.governance_dispatcher.handle_outgoing_message(invocation)

    def process_message(self,invocation,interceptor_list, method):
        """
        The GovernanceController hook to iterate over the interceptors to call each one and evaluate the annotations
        to see what actions should be done.
        @TODO - may want to make this more dynamic instead of hard coded for the moment.
        @param invocation:
        @param interceptor_list:
        @param method:
        @return:
        """
        for int_name in interceptor_list:
            class_inst = self.interceptor_by_name_dict[int_name]
            getattr(class_inst, method)(invocation)

            #Stop processing message if an issue with the message was found by an interceptor.
            if ( invocation.message_annotations.has_key(GovernanceDispatcher.CONVERSATION__STATUS_ANNOTATION) and invocation.message_annotations[GovernanceDispatcher.CONVERSATION__STATUS_ANNOTATION] == GovernanceDispatcher.STATUS_REJECT) or\
               ( invocation.message_annotations.has_key(GovernanceDispatcher.POLICY__STATUS_ANNOTATION) and invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] == GovernanceDispatcher.STATUS_REJECT) :
                break

        return invocation



    # Manage all of the policies in the container

    def policy_event_callback(self, policy_event, *args, **kwargs):
        """
        The generic policy event call back for dispatching policy related events
        """
        # Need to check to set here to set after the system actor is created
        if self.system_actor_id is None:
            system_actor = get_system_actor()
            if system_actor is not None:
                self.system_actor_id = system_actor._id
                self.system_actor_user_header = get_system_actor_header()

        log.info("Policy event callback received: %s" % policy_event)

        if policy_event.type_ == OT.ResourcePolicyEvent:
            self.resource_policy_event_callback(policy_event, *args, **kwargs)
        elif policy_event.type_ == OT.RelatedResourcePolicyEvent:
            self.resource_policy_event_callback(policy_event, *args, **kwargs)
        elif policy_event.type_ == OT.ServicePolicyEvent:
            self.service_policy_event_callback(policy_event, *args, **kwargs)

        self._log_policy_update("policy_event_callback",
                                message="Event processed",
                                event=policy_event)

    def resource_policy_event_callback(self, resource_policy_event, *args, **kwargs):
        """
        The ResourcePolicyEvent handler
        """
        log.debug('Resource policy event received: %s', str(resource_policy_event.__dict__))

        policy_id = resource_policy_event.origin
        resource_id = resource_policy_event.resource_id
        delete_policy = True if resource_policy_event.sub_type == 'DeletePolicy' else False

        self.update_resource_access_policy(resource_id, delete_policy)

    def service_policy_event_callback(self, service_policy_event, *args, **kwargs):
        """
        The ServicePolicyEvent handler

        @param args:
        @param kwargs:
        @return:
        """
        log.debug('Service policy event received: %s', str(service_policy_event.__dict__))

        policy_id = service_policy_event.origin
        service_name = service_policy_event.service_name
        service_op = service_policy_event.op
        delete_policy = True if service_policy_event.sub_type == 'DeletePolicy' else False

        if service_name:
            if self.container.proc_manager.is_local_service_process(service_name):
                self.update_service_access_policy(service_name, service_op, delete_policy=delete_policy)
            elif self.container.proc_manager.is_local_agent_process(service_name):
                self.update_service_access_policy(service_name, service_op, delete_policy=delete_policy)

        else:
            self.update_common_service_access_policy()


    def reset_policy_cache(self):
        """
        The function to empty and reload the container's policy caches

        @return:
        """
        log.info('Resetting policy cache')

        #First remove all cached polices and precondition functions that are not hard-wired
        self._reset_container_policy_caches()

        #Then load the common service access policies since they are shared across services
        self.update_common_service_access_policy()

        #Now iterate over the processes running in the container and reload their policies
        proc_list = self.container.proc_manager.list_local_processes()
        for proc in proc_list:
            self.update_container_policies(proc)

        self._log_policy_update("reset_policy_cache")


    def _reset_container_policy_caches(self):
        self.policy_decision_point_manager.clear_policy_cache()
        self.unregister_all_process_policy_preconditions()

    def _get_policy_snapshot(self):
        policy_snap = {}
        policy_snap["snap_ts"] = get_ion_ts()

        policies = self.get_active_policies()
        common_list = []
        policy_snap["common_pdp"] = common_list
        for rule in policies.get("common_service_access", {}).policy.rules:
            rule_dict = dict(id=rule.id, description=rule.description, effect=rule.effect.value)
            common_list.append(rule_dict)

        service_dict = {}
        policy_snap["service_pdp"] = service_dict
        for (svc_name, sp) in policies.get("service_access", {}).iteritems():
            for rule in sp.policy.rules:
                if svc_name not in service_dict:
                    service_dict[svc_name] = []
                rule_dict = dict(id=rule.id, description=rule.description, effect=rule.effect.value)
                service_dict[svc_name].append(rule_dict)

        service_pre_dict = {}
        policy_snap["service_precondition"] = service_pre_dict
        for (svc_name, sp) in policies.get("service_operation", {}).iteritems():
            for op, f in sp.iteritems():
                if svc_name not in service_pre_dict:
                    service_pre_dict[svc_name] = []
                service_pre_dict[svc_name].append(op)

        resource_dict = {}
        policy_snap["resource_pdp"] = resource_dict
        for (res_name, sp) in policies.get("resource_access", {}).iteritems():
            for rule in sp.policy.rules:
                if res_name not in service_dict:
                    resource_dict[res_name] = []
                rule_dict = dict(id=rule.id, description=rule.description, effect=rule.effect.value)
                resource_dict[res_name].append(rule_dict)

        return policy_snap

    def _log_policy_update(self, update_type=None, message=None, event=None, process=None):
        policy_update_dict = {}
        policy_update_dict["update_ts"] = get_ion_ts()
        policy_update_dict["update_type"] = update_type or ""
        policy_update_dict["message"] = message or ""
        if event:
            policy_update_dict["event._id"] = getattr(event, "_id", "")
            policy_update_dict["event.ts_created"] = getattr(event, "ts_created", "")
            policy_update_dict["event.type_"] = getattr(event, "type_", "")
            policy_update_dict["event.sub_type"] = getattr(event, "sub_type", "")
        if process:
            policy_update_dict["proc._proc_name"] = getattr(process, "_proc_name", "")
            policy_update_dict["proc.name"] = getattr(process, "name", "")
            policy_update_dict["proc._proc_listen_name"] = getattr(process, "_proc_listen_name", "")
            policy_update_dict["proc.resource_type"] = getattr(process, "resource_type", "")
            policy_update_dict["proc.resource_id"] = getattr(process, "resource_id", "")
        any_change = False   # Change can only be detected in number/names of policy not content
        snapshot = self._policy_snapshot
        policy_now = self._get_policy_snapshot()
        # Comparison of snapshot to current policy
        try:
            def compare_policy(pol_cur, pol_snap, key, res):
                pol_cur_set = {d["id"] if isinstance(d, dict) else d for d in pol_cur}
                pol_snap_set = {d["id"] if isinstance(d, dict) else d for d in pol_snap}
                if pol_cur_set != pol_snap_set:
                    policy_update_dict["snap.%s.%s.added" % (key, res)] = pol_cur_set - pol_snap_set
                    policy_update_dict["snap.%s.%s.removed" % (key, res)] = pol_snap_set - pol_cur_set
                    log.debug("Policy changed for %s.%s: %s vs %s" % (key, res, pol_cur_set, pol_snap_set))
                    return True
                return False
            policy_update_dict["snap.snap_ts"] = snapshot["snap_ts"]
            for key in ("common_pdp", "service_pdp", "service_precondition", "resource_pdp"):
                pol_snap = snapshot[key]
                pol_cur = policy_now[key]
                if isinstance(pol_cur, dict):
                    for res in pol_cur.keys():
                        pol_list = pol_cur[res]
                        snap_list = pol_snap.get(res, [])
                        any_change = compare_policy(pol_list, snap_list, key, res) or any_change
                elif isinstance(pol_cur, list):
                    any_change = compare_policy(pol_cur, pol_snap, key, "common") or any_change

            policy_update_dict["snap.policy_changed"] = str(any_change)
        except Exception as ex:
            log.warn("Cannot compare current policy to prior snapshot", exc_info=True)

        self._policy_update_log.append(policy_update_dict)
        self._policy_update_log = self._policy_update_log[-100:]
        self._policy_snapshot = policy_now

        if any_change:
            log.info("Container policy changed. Cause: %s/%s" % (update_type, message))
        else:
            log.debug("Container policy checked but no change. Cause: %s/%s" % (update_type, message))

    def update_container_policies(self, process_instance, safe_mode=False):
        """
        Load any applicable process policies. To be called by the container proc manager after
        registering a new process.
        @param process_instance  The ION process for which to load policy
        @param safe_mode  If True, will not attempt to read policy if Policy MS not available
        """
        # This method can be called before policy management service is available during system startup
        if safe_mode and not self._is_policy_management_service_available():
            if not is_testing() and (process_instance.name not in (
                "resource_registry", "system_management", "directory", "identity_management") and
                process_instance._proc_name != "event_persister"):
                # We are in the early phases of bootstrapping
                log.warn("update_container_policies(%s) - No update. Policy MS not available" % process_instance._proc_name)

            self._log_policy_update("update_container_policies",
                                    message="No update. Policy MS not available",
                                    process=process_instance)
            return

        # Need to check to set here to set after the system actor is created
        if self.system_actor_id is None:
            system_actor = get_system_actor()
            if system_actor is not None:
                self.system_actor_id = system_actor._id
                self.system_actor_user_header = get_system_actor_header()

        if process_instance._proc_type == SERVICE_PROCESS_TYPE:
            # look to load any existing policies for this service

            self.update_service_access_policy(process_instance._proc_listen_name)

        elif process_instance._proc_type == AGENT_PROCESS_TYPE:
            # look to load any existing policies for this agent service
            if process_instance.resource_type is None:
                self.update_service_access_policy(process_instance.name)
            else:
                self.update_service_access_policy(process_instance.resource_type)

            if process_instance.resource_id:
                # look to load any existing policies for this resource
                self.update_resource_access_policy(process_instance.resource_id)

        self._log_policy_update("update_container_policies",
                                message="Checked",
                                process=process_instance)


    def update_resource_access_policy(self, resource_id, delete_policy=False):

        if self.policy_decision_point_manager is not None:

            try:
                policy_rules = self.policy_client.get_active_resource_access_policy_rules(resource_id, headers=self.system_actor_user_header)
                self.policy_decision_point_manager.load_resource_policy_rules(resource_id, policy_rules)

            except Exception, e:
                #If the resource does not exist, just ignore it - but log a warning.
                log.warn("The resource %s is not found or there was an error applying access policy: %s" % ( resource_id, e.message))


    def update_common_service_access_policy(self, delete_policy=False):

        if self.policy_decision_point_manager is not None:
            try:
                rules = self.policy_client.get_active_service_access_policy_rules(service_name='', org_name=self._container_org_name, headers=self.system_actor_user_header)
                self.policy_decision_point_manager.load_common_service_policy_rules(rules)

                #Reload all policies for existing services
                for service_name in self.policy_decision_point_manager.list_service_policies():
                    if self.container.proc_manager.is_local_service_process(service_name):
                        self.update_service_access_policy(service_name, delete_policy=delete_policy)

            except Exception, e:
                #If the resource does not exist, just ignore it - but log a warning.
                log.warn("There was an error applying access policy: %s" % e.message)


    def update_service_access_policy(self, service_name, service_op='', delete_policy=False):

        if self.policy_decision_point_manager is not None:

            try:
                #First update any access policy rules
                rules = self.policy_client.get_active_service_access_policy_rules(service_name=service_name, org_name=self._container_org_name, headers=self.system_actor_user_header)
                self.policy_decision_point_manager.load_service_policy_rules(service_name, rules)

            except Exception, e:
                #If the resource does not exist, just ignore it - but log a warning.
                log.warn("The service %s is not found or there was an error applying access policy: %s" % ( service_name, e.message))

            #Next update any precondition policies
            try:
                proc = self.container.proc_manager.get_a_local_process(service_name)
                if proc is not None:
                    op_preconditions = self.policy_client.get_active_process_operation_preconditions(process_name=service_name, op=service_op, org_name=self._container_org_name, headers=self.system_actor_user_header)
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


    def get_active_policies(self):

        container_policies = dict()
        container_policies['service_access'] = dict()
        container_policies['service_operation'] = dict()
        container_policies['resource_access'] = dict()

        container_policies['service_access'].update(self.policy_decision_point_manager.service_policy_decision_point)
        container_policies['common_service_access'] = self.policy_decision_point_manager.load_common_service_pdp
        container_policies['service_operation'].update(self._service_op_preconditions)
        container_policies['resource_access'].update(self.policy_decision_point_manager.resource_policy_decision_point)

        #log.info(container_policies)

        return container_policies

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
    def get_process_operation_dict(self, process_name, auto_add=True):
        if self._service_op_preconditions.has_key(process_name):
            return self._service_op_preconditions[process_name]

        if auto_add:
            self._service_op_preconditions[process_name] = dict()
            return self._service_op_preconditions[process_name]


        return None

    def register_process_operation_precondition(self, process, operation, precondition):
        """
        This method is used to register service operation precondition functions with the governance controller. The endpoint
        code will call check_process_operation_preconditions() below before calling the business logic operation and if any of
        the precondition functions return False, then the request is denied as Unauthorized.

        At some point, this should be refactored to by another interceptor, but at the operation level.

        @param process:
        @param operation:
        @param precondition:
        @param policy_object:
        @return:
        """

        if not hasattr(process, operation):
            raise NotFound("The operation %s does not exist for the %s service" % (operation, process.name))

        if type(precondition) == types.MethodType and precondition.im_self != process:
            raise NotFound("The method %s does not exist for the %s service." % (str(precondition), process.name))

        process_op_conditions = self.get_process_operation_dict(process.name)
        if process_op_conditions.has_key(operation):
            process_op_conditions[operation].append(precondition)
        else:
            preconditions = list()
            preconditions.append(precondition)
            process_op_conditions[operation] = preconditions

    def unregister_all_process_operation_precondition(self, process, operation):
        """
        This method removes all precondition functions registerd with an operation on a process. Care should be taken with this
        call, as it can remove "hard wired" preconditions that are coded directly and not as part of policy objects, such as
        with SA resource lifecycle preconditions.

        @param process:
        @param operation:
        @return:
        """
        process_op_conditions = self.get_process_operation_dict(process.name, auto_add=False)
        if process_op_conditions is not None and process_op_conditions.has_key(operation):
            del process_op_conditions[operation]




    def unregister_process_operation_precondition(self, process, operation, precondition):
        """
        This method removes a specific precondition function registerd with an operation on a process. Care should be taken with this
        call, as it can remove "hard wired" preconditions that are coded directly and not as part of policy objects, such as
        with SA resource lifecycle preconditions.
        @param process:
        @param operation:
        @param precondition:
        @return:
        """
        #Just skip this if there operation is not passed in.
        if operation is None:
            return

        if not hasattr(process, operation):
            raise NotFound("The operation %s does not exist for the %s service" % (operation, process.name))

        process_op_conditions = self.get_process_operation_dict(process.name, auto_add=False)
        if process_op_conditions is not None and process_op_conditions.has_key(operation):
            preconditions = process_op_conditions[operation]
            preconditions[:] = [pre for pre in preconditions if not pre == precondition]
            if not preconditions:
                del process_op_conditions[operation]


    def unregister_all_process_policy_preconditions(self):
        """
        This method removes all precondition functions registerd with an operation on a process. it will not remove
        "hard wired" preconditions that are coded directly and not as part of policy objects, such as
        with SA resource lifecycle preconditions.

        @param process:
        @param operation:
        @return:
        """
        for proc in self._service_op_preconditions:
            process_op_conditions = self.get_process_operation_dict(proc, auto_add=False)
            if process_op_conditions is not None:
                for op in process_op_conditions:
                    preconditions = process_op_conditions[op]
                    preconditions[:] = [pre for pre in preconditions if type(pre) == types.FunctionType]


    def check_process_operation_preconditions(self, process, msg, headers):
        """
        This method is called by the ion endpoint to execute any process operation preconditions functions before
        allowing the operation to be called.
        @param process:
        @param msg:
        @param headers:
        @return:
        """
        operation = headers.get('op', None)
        if operation is None:
            return

        process_op_conditions = self.get_process_operation_dict(process.name, auto_add=False)
        if process_op_conditions is not None and process_op_conditions.has_key(operation):
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
                        #See if this is method within the endpoint process, if so call it
                        method = getattr(process, precond, None)
                        if method:
                            ret_val, ret_message = method(msg, headers)
                        else:
                            #It is not a method in the process, so try to execute as a simple python function
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



