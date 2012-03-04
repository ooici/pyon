#!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'



from pyon.util.log import log
from pyon.core.exception import Unauthorized


class GovernanceDispatcher(object):

    #Annotations to be used as the message is passed between interceptors.
    POLICY__STATUS_ANNOTATION = 'POLICY_STATUS'



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
        log.info('GovernanceDispatcher.__init__()')


    def handle_incoming_message(self, invocation):

        receiver = invocation.get_header_value('receiver', 'Unknown')
        op = invocation.get_header_value('op', 'Unknown')
        actor_id = invocation.get_header_value('ion-actor-id', 'anonymous')

        if invocation.message_annotations.has_key(GovernanceDispatcher.POLICY__STATUS_ANNOTATION) and \
           invocation.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION] == GovernanceDispatcher.STATUS_REJECT:
            raise Unauthorized("The request from user %s for operation %s(%s) has been denied" % (actor_id,receiver, op) )

        return invocation

    def handle_outgoing_message(self, invocation):
        return invocation
