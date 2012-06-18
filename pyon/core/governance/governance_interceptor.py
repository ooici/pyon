#!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

from pyon.public import Container
from pyon.core.interceptor.interceptor import Interceptor
from pyon.util.log import log

#
# This class is used as a base class for the internal interceptors managed by the governance framework
class BaseInternalGovernanceInterceptor(Interceptor):

    def __init__(self, *args, **kwargs):
        pass

    @property
    def governance_controller(self):
        """
        Property to get governance controller from Container, if the container exists.
        """
        if Container.instance is not None:
            return Container.instance.governance_controller
        return None

    def outgoing(self, invocation):
        pass

    def incoming(self, invocation):
        pass


class GovernanceInterceptor(BaseInternalGovernanceInterceptor):


    def configure(self, config):
        if "enabled" in config:
            self.enabled = config["enabled"]

        log.debug("GovernanceInterceptor enabled: %s" % str(self.enabled))


    def outgoing(self,invocation):

        if not self.enabled:
            return invocation

        if invocation.args.has_key('process'):
            log.debug("GovernanceInterceptor.outgoing: %s", invocation.args['process'])
        else:
            log.debug("GovernanceInterceptor.outgoing: %s", invocation)

        if self.governance_controller is not None:
            self.governance_controller.process_outgoing_message(invocation)

        return invocation

    def incoming(self,invocation):

        if not self.enabled:
            return invocation

        if invocation.args.has_key('process'):
            log.debug("GovernanceInterceptor.incoming: %s", invocation.args['process'])
        else:
            log.debug("GovernanceInterceptor.incoming: %s", invocation)

        if self.governance_controller is not None:
            self.governance_controller.process_incoming_message(invocation)

        return invocation


