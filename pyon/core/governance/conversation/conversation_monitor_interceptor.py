#!/usr/bin/env python

__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'


from pyon.core.governance.governance_interceptor import BaseInternalGovernanceInterceptor
from pyon.util.log import log


class ConversationMonitorInterceptor(BaseInternalGovernanceInterceptor):

    def outgoing(self, invocation):

        if invocation.args.has_key('process'):
            log.debug("ConversationMonitorInterceptor.outgoing: %s", invocation.args['process'])
        else:
            log.debug("ConversationMonitorInterceptor.outgoing: %s", invocation)

        return invocation

    def incoming(self, invocation):


        if invocation.args.has_key('process'):
            log.debug("ConversationMonitorInterceptor.incoming: %s", invocation.args['process'])
        else:
            log.debug("ConversationMonitorInterceptor.incoming: %s", invocation)


        return invocation