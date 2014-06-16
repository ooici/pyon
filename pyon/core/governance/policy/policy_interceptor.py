    #!/usr/bin/env python


__author__ = 'Stephen P. Henrie'

import pickle

from pyon.core.bootstrap import CFG
from pyon.core.governance.governance_interceptor import BaseInternalGovernanceInterceptor
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher
from pyon.core.object import IonObjectBase
from pyon.core.registry import is_ion_object, message_classes, has_class_decorator
from pyon.util.containers import current_time_millis
from pyon.util.log import log

from ndg.xacml.core.context.result import Decision

PERMIT_SUB_CALLS = 'PERMIT_SUB_CALLS'

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

        #log.trace("PolicyInterceptor.outgoing: %s", invocation.get_arg_value('process', invocation))


        #Check for a field with the ResourceId decorator and if found, then set resource-id
        # in the header with that field's value or if the decorator specifies a field within an object,
        #then use the object's field value ( ie. _id)
        try:
            if isinstance(invocation.message, IonObjectBase):
                decorator = 'ResourceId'
                field = invocation.message.find_field_for_decorator(decorator)
                if field is not None and hasattr(invocation.message,field):
                    deco_value = invocation.message.get_decorator_value(field, decorator)
                    if deco_value:
                        #Assume that if there is a value, then it is specifying a field in the object
                        fld_value = getattr(invocation.message,field)
                        if getattr(fld_value, deco_value) is not None:
                            invocation.headers['resource-id'] = getattr(fld_value, deco_value)
                    else:
                        if getattr(invocation.message,field) is not None:
                            invocation.headers['resource-id'] = getattr(invocation.message,field)

        except Exception, ex:
            log.exception(ex)


        return invocation

    def incoming(self, invocation):

        #log.trace("PolicyInterceptor.incoming: %s", invocation.get_arg_value('process', invocation))

        #print "========"
        #print invocation.headers

        #If missing the performative header, consider it as a failure message.
        msg_performative = invocation.get_header_value('performative', 'failure')
        message_format = invocation.get_header_value('format', '')
        op = invocation.get_header_value('op', 'unknown')
        process_type = invocation.get_invocation_process_type()
        sender, sender_type = invocation.get_message_sender()

        #TODO - This should be removed once better process security is implemented
        #THis fix infers that all messages that do not specify an actor id are TRUSTED wihtin the system
        policy_loaded = CFG.get_safe('system.load_policy', False)
        if policy_loaded:
            actor_id = invocation.get_header_value('ion-actor-id', None)
        else:
            actor_id = invocation.get_header_value('ion-actor-id', 'anonymous')

        #Only check messages marked as the initial rpc request - TODO - remove the actor_id is not None when headless process have actor_ids
        if msg_performative == 'request' and actor_id is not None:

            receiver = invocation.get_message_receiver()

            #Can's check policy if the controller is not initialized
            if self.governance_controller is None:
                log.debug("Skipping policy check for %s(%s) since governance_controller is None", receiver, op)
                invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_SKIPPED
                return invocation

            #No need to check for requests from the system actor - should increase performance during startup
            if actor_id == self.governance_controller.system_actor_id:
                log.debug("Skipping policy check for %s(%s) for the system actor", receiver, op)
                invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_SKIPPED
                return invocation


            #Check to see if there is a AlwaysVerifyPolicy decorator
            always_verify_policy = False
            if is_ion_object(message_format):
                try:
                    msg_class = message_classes[message_format]
                    always_verify_policy = has_class_decorator(msg_class,'AlwaysVerifyPolicy')
                except Exception:
                    pass

            #For services only - if this is a sub RPC request from a higher level service that has already been validated and set a token
            #then skip checking policy yet again - should help with performance and to simplify policy
            #All calls from the RMS must be checked
            if not always_verify_policy and process_type == 'service' and sender != 'resource_management' and self.has_valid_token(invocation, PERMIT_SUB_CALLS):
                #log.debug("Skipping policy check for service call %s %s since token is valid", receiver, op)
                #print "skipping call to " + receiver + " " + op + " from " + actor_id + " process_type: " + process_type
                invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_SKIPPED
                return invocation

            #log.debug("Checking request for %s: %s(%s) from %s  ", process_type, receiver, op, actor_id)

            #Annotate the message has started policy checking
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_STARTED

            ret = None

            #First check for Org boundary policies if the container is configured as such
            org_id = self.governance_controller.get_container_org_boundary_id()
            if org_id is not None:
                ret = self.governance_controller.policy_decision_point_manager.check_resource_request_policies(invocation, org_id)

            if str(ret) != Decision.DENY_STR:
                #Next check endpoint process specific policies
                if process_type == 'agent':
                    ret = self.governance_controller.policy_decision_point_manager.check_agent_request_policies(invocation)

                elif process_type == 'service':
                    ret = self.governance_controller.policy_decision_point_manager.check_service_request_policies(invocation)

            #log.debug("Policy Decision: %s", ret)

            #Annonate the message has completed policy checking
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_COMPLETE

            if ret is not None:
                if str(ret) == Decision.DENY_STR:
                    self.annotate_denied_message(invocation)
                else:
                    self.permit_sub_rpc_calls_token(invocation)

        else:
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_SKIPPED

        return invocation

    def annotate_denied_message(self, invocation):
        #TODO - Fix this to use the proper annotation reference and figure out special cases
        if invocation.headers.has_key('op') and invocation.headers['op'] != 'start_rel_from_url':
            invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] = GovernanceDispatcher.STATUS_REJECT

    def permit_sub_rpc_calls_token(self, invocation):
        actor_tokens = invocation.get_header_value('ion-actor-tokens', None)
        if actor_tokens is None:
            actor_tokens = list()
            invocation.headers['ion-actor-tokens'] = actor_tokens

        #See if this token exists already
        for tok in actor_tokens:
            pol_tok = pickle.loads(tok)
            if pol_tok.is_token(PERMIT_SUB_CALLS):
                return

        #Not found, so create a new one
        container_id = invocation.get_header_value('origin-container-id', None)
        actor_id = invocation.get_header_value('ion-actor-id', 'anonymous')
        requesting_message = invocation.get_header_value('format', 'Unknown')

        #TODO - investigate adding information about parent conversation when available

        #Create a token that subsequent resource_registry calls are allowed
        token = create_policy_token(container_id, actor_id, requesting_message, PERMIT_SUB_CALLS)
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


