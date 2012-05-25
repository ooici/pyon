#!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'
import copy
from pyon.core.bootstrap import CFG
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher
from pyon.util.log import log
from pyon.ion.resource import RT, PRED
from pyon.core.governance.policy.policy_decision import PolicyDecisionPointManager
from pyon.event.event import EventSubscriber
from interface.services.coi.ipolicy_management_service import PolicyManagementServiceProcessClient
from interface.services.coi.iresource_registry_service import ResourceRegistryServiceProcessClient
from interface.services.coi.iorg_management_service import OrgManagementServiceProcessClient

class GovernanceController(object):


    def __init__(self,container):
        log.debug('GovernanceController.__init__()')
        self.container = container
        self.enabled = False
        self.interceptor_by_name_dict = dict()
        self.interceptor_order = []
        self.policy_decision_point_manager = None
        self.governance_dispatcher = None

    def start(self):

        log.debug("GovernanceController starting ...")

        config = CFG.interceptor.interceptors.governance.config

        if config is None:
            config['enabled'] = False

        if "enabled" in config:
            self.enabled = config["enabled"]

        log.debug("GovernanceInterceptor enabled: %s" % str(self.enabled))

        self.resource_policy_event_subscriber = None

        if self.enabled:
            self.initialize_from_config(config)

            self.resource_policy_event_subscriber = EventSubscriber(event_type="ResourcePolicyEvent", callback=self.policy_event_callback)
            self.resource_policy_event_subscriber.activate()

            self.rr_client = ResourceRegistryServiceProcessClient(node=self.container.node, process=self.container)
            self.policy_client = PolicyManagementServiceProcessClient(node=self.container.node, process=self.container)
            self.org_client = OrgManagementServiceProcessClient(node=self.container.node, process=self.container)

    def initialize_from_config(self, config):

        self.governance_dispatcher = GovernanceDispatcher()

        self.policy_decision_point_manager = PolicyDecisionPointManager()

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
            self.resource_policy_event_subscriber.deactivate()


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

        return invocation

    def policy_event_callback(self, *args, **kwargs):
        resource_policy_event = args[0]

        policy_id = resource_policy_event.origin
        resource_id = resource_policy_event.resource_id
        resource_type = resource_policy_event.resource_type
        resource_name = resource_policy_event.resource_name

        log.debug("Resource policy modified: %s" % policy_id)

        if resource_type == 'ServiceDefinition':  #TODO - REDO this to tear services like resources and have a configurable Org bounrady by container
            ion_org = self.org_client.find_org()
            policy_rules = self.policy_client.get_active_service_policy_rules(ion_org._id, resource_name)
            self.update_resource_policy(resource_name, policy_rules)
        elif  resource_type == 'Org':
            policy_rules = self.policy_client.get_active_resource_policy_rules(resource_id)
            if self.policy_decision_point_manager is not None:
                self.policy_decision_point_manager.load_org_policy_rules(policy_rules)
                self.update_all_resource_policies(resource_id)
        else:
            policy_rules = self.policy_client.get_active_resource_policy_rules(resource_id)
            self.update_resource_policy(resource_id, policy_rules)


    def update_resource_policy(self, resource_name, policy_rules):

        #Notify policy decision point of updated rules
        if self.policy_decision_point_manager is not None:
            log.debug("Loading policy for resource: %s" % resource_name)
            self.policy_decision_point_manager.load_policy_rules(resource_name, policy_rules)


    def update_all_resource_policies(self, org_id):

        #Notify policy decision point of updated rules for all existing service policies
        if self.policy_decision_point_manager is not None:
            for res_name in self.policy_decision_point_manager.policy_decision_point:
                try:
                    policy_rules = self.policy_client.get_active_service_policy_rules(org_id, res_name)
                    self.update_resource_policy(res_name, policy_rules)
                except Exception, e:
                    log.error(e.message)
