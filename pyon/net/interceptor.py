from zope.interface import implements, Interface
from pyon.util.log import log

class IInvocation(Interface):
    pass

class Invocation(object):
    """
    Container object for parameters of events/messages passed to internal
    capability container processes
    """
    implements(IInvocation)

    # Event inbound processing path
    PATH_IN = 'in'

    # Event outbound processing path
    PATH_OUT = 'out'

    # Event processing path
    PATH_ANY = 'any'

    # Event processing should proceed
    STATUS_PROCESS = 'process'

    # Event processing is completed.
    STATUS_DONE = 'done'

    # Event processing should stop and event dropped with no action
    STATUS_DROP = 'drop'

    # Event processing should proceed with lower priority process, if any
    STATUS_REJECT = 'reject'

    # An error has occurred and event processing should stop
    STATUS_ERROR = 'error'

    # Malformed message
    CODE_BAD_REQUEST = 400

    # Authorization error
    CODE_UNAUTHORIZED = 401

    def __init__(self, **kwargs):
        """
        @param path A path designator str, e.g. a constant or other
        @param message the message envelope
        @param content the message content
        @param status the processing status
        @param route None or a str indicating subsequent routing
        """
        self.args = kwargs
        self.path = str(kwargs.get('path', Invocation.PATH_ANY))
        self.message = kwargs.get('message', None)
        self.content = kwargs.get('content', None)
        self.process = kwargs.get('process', None)
        self.status = kwargs.get('status', Invocation.STATUS_PROCESS)
        self.route = str(kwargs.get('route', ""))
        self.workbench = kwargs.get('workbench',None)
        self.note = None
        self.code = None

    def drop(self, note=None, code=None):
        self.note = note
        self.code = code
        self.status = Invocation.STATUS_DROP

    def done(self, note=None):
        self.note = note
        self.status = Invocation.STATUS_DONE

    def error(self, note=None):
        self.note = note
        self.status = Invocation.STATUS_ERROR

    def proceed(self, route=""):
        self.status = Invocation.STATUS_PROCESS
        self.route = str(route)


class Interceptor(object):
    """
    Basic interceptor model. Derive and override process.
    """
    def process(self, invocation):
        pass

class EnvelopeInterceptor(object):
    """
    Interceptor that can process messages in the in-path and out-path. Just a
    wrapper for code to keep both complementing actions together.
    Note: There is NO guanantee that for one incoming message there is one
    outgoing message
    """
    def process(self, invocation):
        """
        @param invocation container object for parameters
        @retval invocation instance, may be modified
        """
        if invocation.path == Invocation.PATH_IN:
            return self.int_in(invocation)
        elif invocation.path == Invocation.PATH_OUT:
            return self.int_out(invocation)
        else:
            # @TODO: exception type
            raise Exception("Illegal EnvelopeInterceptor path: %s" % invocation.path)

    def int_in(self, invocation):
        return invocation
    def int_out(self, invocation):
        return invocation


class SampleInterceptor(EnvelopeInterceptor):

    def int_out(self, invocation):
        log.warn("SampleInterceptor.int_out: %s", invocation)
        invocation.message['header']['sample_interceptor'] = 'intercepted'
        return invocation

    def int_in(self, invocation):
        log.warn("SampleInterceptor.int_in: %s", invocation)
        if invocation.message['header'].has_key('sample_interceptor'):
            log.warn("This message has been sampleintercepted!")
        else:
            log.warn("This message was NOT sample intercepted!")
        return invocation


class SampleProcessOnlyInterceptor(EnvelopeInterceptor):
    def int_out(self, invocation):
        log.warn("SampleProcessOnlyInterceptor.int_out: %s", invocation)
        invocation.message['header']['process_only'] = 'process_only_inteceptor'
        return invocation

    def int_in(self, invocation):
        log.warn("SampleProcessOnlyInterceptor.int_in: %s", invocation)
        if invocation.message['header'].has_key('process_only'):
            log.warn("This message has been PROCESS ONLY SAMPLE INTERCEPTED!")
        else:
            log.warn("This message was NOT process only sample intercepted!")
        return invocation