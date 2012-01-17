import msgpack

from pyon.core.interceptor.interceptor import Interceptor
from pyon.util.log import log

class EncodeInterceptor(Interceptor):
    def outgoing(self, invocation):
        log.debug("EncodeInterceptor.outgoing: %s", invocation)
        log.debug("Pre-transform: %s", invocation.message)

        # msgpack the content (ensures string)
        invocation.message = msgpack.dumps(invocation.message)

        # make sure no Nones exist in headers - this indicates a problem somewhere up the stack
        # pika will choke hard on them as well, masking the actual problem, so we catch here.
        nonelist = [(k, v) for k, v in invocation.headers.iteritems() if v is None]
        assert len(nonelist) == 0, "Invalid headers containing Nones: %s" % str(nonelist)

        log.debug("Post-transform: %s", invocation.message)
        return invocation

    def incoming(self, invocation):
        log.debug("EncodeInterceptor.incoming: %s", invocation)
        log.debug("Pre-transform: %s", invocation.message)
        invocation.message = msgpack.loads(invocation.message)
        log.debug("Post-transform: %s", invocation.message)
        return invocation
