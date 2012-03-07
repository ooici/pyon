#!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

from pyon.core.governance.governance_interceptor import BaseInternalGovernanceInterceptor
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher

from pyon.util.log import log

from ndg.xacml.core.context.result import Decision

class PolicyInterceptor(BaseInternalGovernanceInterceptor):

    def outgoing(self, invocation):

        if invocation.args.has_key('process'):
            log.debug("PolicyInterceptor.outgoing: %s", invocation.args['process'])
        else:
            log.debug("PolicyInterceptor.outgoing: %s", invocation)

        return invocation

    def incoming(self, invocation):


        if invocation.args.has_key('process'):
            log.debug("PolicyInterceptor.incoming: %s", invocation.args['process'])
        else:
            log.debug("PolicyInterceptor.incoming: %s", invocation)

        #If missing default to request just to be safe
        msg_performative = invocation.get_header_value('performative', 'request')

        #No need to check policy for response or failure messages
        if msg_performative != 'inform-result' and msg_performative != 'failure':

            #checking policy
            #Annotate the message has started policy checking
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_STARTED

            if self.governance_controller is not None:
                ret = self.governance_controller.policy_decision_point_manager.check_policies(invocation)

            log.debug("Policy Decision: " + str(ret))

            #Annonate the message has completed policy checking
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_COMPLETE

            if ret == Decision.DENY_STR:
                self.policy_denied_message(invocation)

        return invocation


    def policy_denied_message(self, invocation):
        #TODO - Fix this to use the proper annotation reference and figure out special cases
        if invocation.headers.has_key('op') and invocation.headers['op'] != 'start_rel_from_url':
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_REJECT
