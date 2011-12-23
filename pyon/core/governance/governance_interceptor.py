#!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

from pyon.core.governance.governance_controller import GovernanceController
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher
from pyon.core.interceptor.interceptor import Interceptor
from pyon.util.log import log

#
# This class is used as a base class for the internal interceptors managed by the governance framework
class BaseInternalGovernanceInterceptor(Interceptor):


    def outgoing(self, invocation):
        pass

    def incoming(self, invocation):
        pass


class GovernanceInterceptor(Interceptor):

    def __init__(self, *args, **kwargs):
        self.governance_controller = GovernanceController()

    def configure(self, config):
        if "enabled" in config:
            self.enabled = config["enabled"]

        log.debug("GovernanceInterceptor enabled: %s" % str(self.enabled))

        if self.enabled:
            self.governance_controller.initialize(config)



    def outgoing(self,invocation):

        if not self.enabled:
            return invocation

        if invocation.args.has_key('process'):
            log.debug("GovernanceInterceptor.outgoing: %s", invocation.args['process'])
        else:
            log.debug("GovernanceInterceptor.outgoing: %s", invocation)

        self.governance_controller.process_outgoing_message(invocation)

        return invocation

    def incoming(self,invocation):

        if not self.enabled:
            return invocation

        if invocation.args.has_key('process'):
            log.debug("GovernanceInterceptor.incoming: %s", invocation.args['process'])
        else:
            log.debug("GovernanceInterceptor.incoming: %s", invocation)

        #TODO - Fudging some message headers until they are fixed in endpoint properly
        invocation.headers['receiver'] = invocation.args['process'].name

        self.governance_controller.process_incoming_message(invocation)

        return invocation


