#!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'
from pyon.core.bootstrap import CFG
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher
from pyon.util.log import log
from pyon.core.governance.policy.policy_decision import PolicyDecisionPointManager



class GovernanceController(object):


    def __init__(self, *args, **kwargs):
        log.debug('GovernanceController.__init__()')
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

        if self.enabled:
            self.initialize_from_config(config)

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

    #TODO - refactor as callback for listener when policy changes
    def load_policy_for_service(self, service_name, policy_rules):

        #Notify policy decision point of updated rules
        if self.policy_decision_point_manager is not None:
            self.policy_decision_point_manager.load_policy_rules(service_name, policy_rules)
