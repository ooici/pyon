from pyon.core.interceptor.interceptor import Interceptor
from pyon.util.log import log


class SampleInterceptor(Interceptor):
    def outgoing(self, invocation):
        log.debug("SampleInterceptor.outgoing: %s", invocation)
        invocation.headers['sample_interceptor'] = 'intercepted'
        return invocation

    def incoming(self, invocation):
        log.debug("SampleInterceptor.incoming: %s", invocation)
        if invocation.headers.has_key('sample_interceptor'):
            log.debug("This message has been sampleintercepted!")
        else:
            log.debug("This message was NOT sample intercepted!")
        return invocation


class SampleProcessOnlyInterceptor(Interceptor):
    def outgoing(self, invocation):
        log.debug("SampleProcessOnlyInterceptor.outgoing: %s", invocation)
        invocation.headers['process_only'] = 'process_only_inteceptor'
        return invocation

    def incoming(self, invocation):
        log.debug("SampleProcessOnlyInterceptor.incoming: %s", invocation)
        if invocation.headers.has_key('process_only'):
            log.debug("This message has been PROCESS ONLY SAMPLE INTERCEPTED!")
        else:
            log.debug("This message was NOT process only sample intercepted!")
        return invocation
