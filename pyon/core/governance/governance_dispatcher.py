#!/usr/bin/env python


__author__ = 'Stephen P. Henrie'




from pyon.util.log import log
from pyon.core.exception import Unauthorized, Inconsistent


class GovernanceDispatcher(object):

    #Annotations to be used as the message is passed between interceptors.
    CONVERSATION__STATUS_ANNOTATION = 'CONVERSATION_STATUS'
    CONVERSATION__STATUS_REASON_ANNOTATION = 'CONVERSATION_STATUS_REASON'
    POLICY__STATUS_ANNOTATION = 'POLICY_STATUS'
    POLICY__STATUS_REASON_ANNOTATION = 'POLICY_STATUS_REASON'

    # The interceptor was skipped for some reason
    STATUS_SKIPPED = 'skipped'

    # Event processing should proceed
    STATUS_STARTED = 'started'

    # Event processing is complete.
    STATUS_COMPLETE = 'complete'

    # Event processing should stop and event dropped with no action
    STATUS_DROP = 'drop'

    # Event processing should proceed with lower priority process, if any
    STATUS_REJECT = 'reject'

    # An error has occurred and event processing should stop
    STATUS_ERROR = 'error'

    def __init__(self, *args, **kwargs):
        log.debug('GovernanceDispatcher.__init__()')


    def handle_incoming_message(self, invocation):

        receiver = invocation.get_message_receiver()
        op = invocation.get_header_value('op', 'Unknown')
        actor_id = invocation.get_header_value('ion-actor-id', 'anonymous')

        #Raise Inconsistent message if conversation interceptor found a problem
        #TODO - May just want to drop this message instead of returning in case of DOS attack
        if invocation.message_annotations.has_key(GovernanceDispatcher.CONVERSATION__STATUS_ANNOTATION) and\
           invocation.message_annotations[GovernanceDispatcher.CONVERSATION__STATUS_ANNOTATION] == GovernanceDispatcher.STATUS_REJECT:
            if invocation.message_annotations.has_key(GovernanceDispatcher.CONVERSATION__STATUS_REASON_ANNOTATION):
                raise Inconsistent("The message from user %s for operation %s(%s) has an error: %s" % (actor_id,receiver, op, invocation.message_annotations[GovernanceDispatcher.CONVERSATION__STATUS_REASON_ANNOTATION]) )
            else:
                raise Inconsistent("The message from user %s for operation %s(%s) is inconsistent with the specified protocol" % (actor_id,receiver, op))

        #Raise Unauthorized exception if policy denies access.
        if invocation.message_annotations.has_key(GovernanceDispatcher.POLICY__STATUS_ANNOTATION) and \
           invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] == GovernanceDispatcher.STATUS_REJECT:

            if invocation.message_annotations.has_key(GovernanceDispatcher.POLICY__STATUS_REASON_ANNOTATION):
                raise Unauthorized(invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_REASON_ANNOTATION])

            raise Unauthorized("The request from user %s for operation %s(%s) has been denied" % (actor_id,receiver, op) )

        return invocation

    def handle_outgoing_message(self, invocation):
        return invocation
