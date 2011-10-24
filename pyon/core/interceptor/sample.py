from pyon.core.interceptor.interceptor import Interceptor
from pyon.util.log import log

class SampleInterceptor(Interceptor):
    def outgoing(self, invocation):
        log.warn("SampleInterceptor.outgoing: %s", invocation)
        invocation.transformed_message['header']['sample_interceptor'] = 'intercepted'
        return invocation

    def incoming(self, invocation):
        log.warn("SampleInterceptor.incoming: %s", invocation)
        if invocation.message['header'].has_key('sample_interceptor'):
            log.warn("This message has been sampleintercepted!")
        else:
            log.warn("This message was NOT sample intercepted!")
        return invocation

class SampleProcessOnlyInterceptor(Interceptor):
    def outgoing(self, invocation):
        log.warn("SampleProcessOnlyInterceptor.outgoing: %s", invocation)
        invocation.transformed_message['header']['process_only'] = 'process_only_inteceptor'
        return invocation

    def incoming(self, invocation):
        log.warn("SampleProcessOnlyInterceptor.incoming: %s", invocation)
        if invocation.message['header'].has_key('process_only'):
            log.warn("This message has been PROCESS ONLY SAMPLE INTERCEPTED!")
        else:
            log.warn("This message was NOT process only sample intercepted!")
        return invocation
