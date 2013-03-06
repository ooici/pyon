    #!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

import types

from pyon.core.bootstrap import CFG, get_service_registry
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher
from pyon.util.log import log
from pyon.ion.resource import RT, OT
from pyon.core.governance.policy.policy_decision import PolicyDecisionPointManager
from pyon.event.event import EventSubscriber
from interface.services.coi.ipolicy_management_service import PolicyManagementServiceProcessClient
from interface.services.coi.iresource_registry_service import ResourceRegistryServiceProcessClient
from pyon.core.exception import NotFound, Unauthorized
from pyon.container.procs import SERVICE_PROCESS_TYPE, AGENT_PROCESS_TYPE

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

        if self.enabled:

            config = CFG.get_safe('interceptor.interceptors.governance.config')

            self.initialize_from_config(config)

            self.policy_event_subscriber = EventSubscriber(event_type=OT.PolicyEvent, callback=self.policy_event_callback)
            self.policy_event_subscriber.start()

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
            org, _ = self.rr.find_resources(restype=RT.Org,name=self._container_org_name)

            if org:
                self._container_org_id = org[0]._id

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



    #Manage all of the policies in the container

    def policy_event_callback(self, *args, **kwargs):
        """
        The generic policy event call back for dispatching policy related events

        @param args:
        @param kwargs:
        @return:
        """
        policy_event = args[0]
        if policy_event.type_ == OT.ResourcePolicyEvent:
            self.resource_policy_event_callback(*args, **kwargs)
        elif policy_event.type_ == OT.ServicePolicyEvent:
            self.service_policy_event_callback(*args, **kwargs)
        elif policy_event.type_ == OT.PolicyCacheResetEvent:
            self.policy_cache_reset_event_callback(*args, **kwargs)


    def resource_policy_event_callback(self, *args, **kwargs):
        """
        The ResourcePolicyEvent handler

        @param args:
        @param kwargs:
        @return:
        """
        resource_policy_event = args[0]
        log.debug('Resource related policy event received: %s', str(resource_policy_event.__dict__))

        policy_id = resource_policy_event.origin
        resource_id = resource_policy_event.resource_id
        resource_type = resource_policy_event.resource_type
        resource_name = resource_policy_event.resource_name
        delete_policy = True if resource_policy_event.sub_type == 'DeletePolicy' else False

        self.update_resource_access_policy(resource_id, delete_policy)

    def service_policy_event_callback(self, *args, **kwargs):
        """
        The ServicePolicyEvent handler

        @param args:
        @param kwargs:
        @return:
        """
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
            self.update_common_service_access_policy()



    def policy_cache_reset_event_callback(self, *args, **kwargs):
        """
        The PolicyCacheResetEvent handler

        @return:
        """
        policy_reset_event = args[0]
        log.info('Policy cache reset event received: %s', str(policy_reset_event.__dict__))

        #First remove all cached polices and precondition functions that are not hard-wired
        self.policy_decision_point_manager.clear_policy_cache()
        self.unregister_all_process_policy_preconditions()

        #Then load the common service access policies since they are shared across services
        self.update_common_service_access_policy()

        #Now iterate over the processes running in the container and reload their policies
        proc_list = self.container.proc_manager.list_local_processes()
        for proc in proc_list:
            self.update_container_policies(proc)



    def update_container_policies(self, process_instance, safe_mode=False):
        """
        This must be called after registering a new process to load any applicable policies

        @param process_instance:
        @return:
        """

        #This method can be called before policy management service is available during system startup
        if safe_mode and not self._is_policy_management_service_available():
            return

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


    def update_resource_access_policy(self, resource_id, delete_policy=False):

        if self.policy_decision_point_manager is not None:

            try:
                policy_rules = self.policy_client.get_active_resource_access_policy_rules(resource_id)
                self.policy_decision_point_manager.load_resource_policy_rules(resource_id, policy_rules)

            except Exception, e:
                #If the resource does not exist, just ignore it - but log a warning.
                log.warn("The resource %s is not found or there was an error applying access policy: %s" % ( resource_id, e.message))


    def update_common_service_access_policy(self, delete_policy=False):

        if self.policy_decision_point_manager is not None:
            try:
                rules = self.policy_client.get_active_service_access_policy_rules('', self._container_org_name)
                self.policy_decision_point_manager.load_common_service_policy_rules(rules)

                #Reload all policies for existing services
                for service_name in self.policy_decision_point_manager.list_service_policies():
                    if self.container.proc_manager.is_local_service_process(service_name):
                        self.update_service_access_policy(service_name, delete_policy)

            except Exception, e:
                #If the resource does not exist, just ignore it - but log a warning.
                log.warn("There was an error applying access policy: %s" % e.message)


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


    def get_active_policies(self):

        container_policies = dict()
        container_policies['service_access'] = dict()
        container_policies['service_operation'] = dict()
        container_policies['resource_access'] = dict()

        container_policies['service_access'].update(self.policy_decision_point_manager.service_policy_decision_point)
        container_policies['common_service_access'] = self.policy_decision_point_manager.load_common_service_pdp
        container_policies['service_operation'].update(self._service_op_preconditions)
        container_policies['resource_access'].update(self.policy_decision_point_manager.resource_policy_decision_point)

        log.info(container_policies)

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

        if type(precondition) == types.StringType:
            #Convert string to instancemethod
            method = getattr(process, precondition, None)
            if method:
                precondition = method

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



