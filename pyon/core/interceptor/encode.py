import msgpack

from pyon.core.interceptor.interceptor import Interceptor
from pyon.util.log import log

class EncodeInterceptor(Interceptor):
    def outgoing(self, invocation):
        log.debug("EncodeInterceptor.outgoing: %s", invocation)
        log.debug("Pre-transform: %s", invocation.message)
        invocation.message = msgpack.dumps(invocation.message)
        log.debug("Post-transform: %s", invocation.message)
        return invocation

    def incoming(self, invocation):
        log.debug("EncodeInterceptor.incoming: %s", invocation)
        log.debug("Pre-transform: %s", invocation.message)
        invocation.message = msgpack.loads(invocation.message)
        log.debug("Post-transform: %s", invocation.message)
        return invocation
