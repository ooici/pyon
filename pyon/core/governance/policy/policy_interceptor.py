    #!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'
import pickle

from pyon.core.bootstrap import CFG
from pyon.core.governance.governance_interceptor import BaseInternalGovernanceInterceptor
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher
from pyon.util.containers import current_time_millis
from pyon.util.log import log

from ndg.xacml.core.context.result import Decision

ALLOW_RESOURCE_REGISTRY_SUB_CALLS = 'ALLOW_RESOURCE_REGISTRY_SUB_CALLS'

#TODO - will need to iterate on this


#Factory method
def create_policy_token(originating_container, actor_id, requesting_message, token):
    p = PolicyToken(originating_container, actor_id, requesting_message, token)
    return pickle.dumps(p)


class PolicyToken:

    def __init__(self, originating_container, actor_id, requesting_message, token):
        self.originator = originating_container
        self.actor_id = actor_id
        self.requesting_message = requesting_message
        self.token = token

        timeout = CFG.get_safe('endpoint.receive.timeout', 10)
        self.expire_time = current_time_millis() + (timeout * 1000)  # Set the expire time to current time + timeout in ms

    def is_expired(self):
        if current_time_millis() > self.expire_time:
            return True
        return False

    def is_token(self, token):
        if self.token == token:
            return True
        return False


class PolicyInterceptor(BaseInternalGovernanceInterceptor):

    def outgoing(self, invocation):

        log.debug("PolicyInterceptor.outgoing: %s", invocation.get_arg_value('process', invocation))

        return invocation

    def incoming(self, invocation):

        log.debug("PolicyInterceptor.incoming: %s", invocation.get_arg_value('process', invocation))

        #If missing the performative header, consider it as a failure message.
        msg_performative = invocation.get_header_value('performative', 'failure')

        #TODO - This should be removed once better process security is implemented
        #THis fix infers that all messages that do not specify an actor id are TRUSTED wihtin the system
        policy_loaded = CFG.get_safe('system.load_policy', False)
        if policy_loaded:
            actor_id = invocation.get_header_value('ion-actor-id', None)
        else:
            actor_id = invocation.get_header_value('ion-actor-id', 'anonymous')

        #Only check messages marked as the initial rpc request - TODO - remove the last check at some point
        if msg_performative == 'request' and actor_id is not None:

            #checking policy - if needed
            receiver = invocation.get_message_receiver()

            #If this is a sub RPC request to the RR service from a higher level service that has already been validated and set a token
            #then skip checking policy yet again - should help with performance and to simplify policy
            if receiver == 'resource_registry' and self.has_valid_token(invocation, ALLOW_RESOURCE_REGISTRY_SUB_CALLS):
                return invocation

            #Annotate the message has started policy checking
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_STARTED

            ret = None
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


            log.debug("Policy Decision: " + str(ret))

            #Annonate the message has completed policy checking
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_COMPLETE

            if ret is not None:
                if str(ret) == Decision.DENY_STR:
                    self.annotate_denied_message(invocation)
                elif str(ret) == Decision.PERMIT:
                    self.permit_registry_calls_token(invocation)

        return invocation

    def annotate_denied_message(self, invocation):
        #TODO - Fix this to use the proper annotation reference and figure out special cases
        if invocation.headers.has_key('op') and invocation.headers['op'] != 'start_rel_from_url':
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_REJECT

    def permit_registry_calls_token(self, invocation):
        actor_tokens = invocation.get_header_value('ion-actor-tokens', None)
        if actor_tokens is None:
            actor_tokens = list()
            invocation.headers['ion-actor-tokens'] = actor_tokens

        #See if this token exists already
        for tok in actor_tokens:
            pol_tok = pickle.loads(tok)
            if pol_tok.is_token(ALLOW_RESOURCE_REGISTRY_SUB_CALLS):
                return

        #Not found, so create a new one
        container_id = invocation.get_header_value('origin-container-id', None)
        actor_id = invocation.get_header_value('ion-actor-id', 'anonymous')
        requesting_message = invocation.get_header_value('format', 'Unknown')

        #TODO - investigate adding information about parent conversation when available

        #Create a token that subsequent resource_registry calls are allowed
        token = create_policy_token(container_id, actor_id, requesting_message, ALLOW_RESOURCE_REGISTRY_SUB_CALLS)
        actor_tokens.append(token)

    def has_valid_token(self, invocation, token):

        actor_tokens = invocation.get_header_value('ion-actor-tokens', None)
        if actor_tokens is None:
            return False

        #See if this token exists already
        for tok in actor_tokens:
            pol_tok = pickle.loads(tok)
            if pol_tok.is_token(token) and not pol_tok.is_expired():
                return True

        return False


