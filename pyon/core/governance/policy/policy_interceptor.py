#!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

from pyon.core.governance.governance_interceptor import BaseInternalGovernanceInterceptor
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher

from pyon.util.log import log

from ndg.xacml.core.context.result import Decision

class PolicyInterceptor(BaseInternalGovernanceInterceptor):

    def outgoing(self, invocation):

        log.debug("PolicyInterceptor.outgoing: %s", invocation.get_arg_value('process',invocation))

        return invocation

    def incoming(self, invocation):

        log.debug("PolicyInterceptor.incoming: %s", invocation.get_arg_value('process',invocation))

        #If missing default to request just to be safe
        msg_performative = invocation.get_header_value('performative', 'request')

        #No need to check policy for response or failure messages
        if msg_performative != 'inform-result' and msg_performative != 'failure':

            #checking policy
            #Annotate the message has started policy checking
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_STARTED

            ret = ''
            if self.governance_controller is not None:

                #First check for Org boundary policies if the container is configured as such
                org_id = self.governance_controller.get_container_org_boundary_id()
                if org_id is not None:
                    ret = self.governance_controller.policy_decision_point_manager.check_resource_request_policies(invocation, org_id)

                if str(ret) != Decision.DENY_STR:
                    #Next check endpoint process specific policies
                    process_type = invocation.get_invocation_process_type()
                    if process_type == 'agent':
                        ret = self.governance_controller.policy_decision_point_manager.check_agent_request_policies(invocation)

                    elif process_type == 'service':
                        ret = self.governance_controller.policy_decision_point_manager.check_service_request_policies(invocation)

                    #TODO - what to do if process type is unknown?

            log.debug("Policy Decision: " + str(ret))

            #Annonate the message has completed policy checking
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_COMPLETE

            if str(ret) == Decision.DENY_STR:
                self.policy_denied_message(invocation)

        return invocation


    def policy_denied_message(self, invocation):
        #TODO - Fix this to use the proper annotation reference and figure out special cases
        if invocation.headers.has_key('op') and invocation.headers['op'] != 'start_rel_from_url':
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_REJECT
