#!/usr/bin/env python

__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'


from pyon.core.governance.governance_interceptor import BaseInternalGovernanceInterceptor
from pyon.util.log import log


class ConversationMonitorInterceptor(BaseInternalGovernanceInterceptor):

    def outgoing(self, invocation):

        log.debug("ConversationMonitorInterceptor.outgoing: %s", invocation.get_arg_value('process',invocation))

        return invocation

    def incoming(self, invocation):

        log.debug("ConversationMonitorInterceptor.incoming: %s", invocation.get_arg_value('process',invocation))

        return invocation