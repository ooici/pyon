import msgpack
from zope.interface import implements, Interface
from pyon.core.bootstrap import IonObject
from pyon.core.object import IonObjectBase
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
        raise NotImplementedError()
    def int_out(self, invocation):
        raise NotImplementedError()


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

def walk(o, cb):
    """
    Utility method to do recursive walking of a possible iterable (inc dicts) and do inline transformations.
    You supply a callback which receives an object. That object may be an iterable (which will then be walked
    after you return it, as long as it remains an iterable), or it may be another object inside of that.

    If a dict is discovered, your callback will receive the dict as a whole and the contents of values only. Keys are left untouched.

    @TODO move to a general utils area?
    """
    if hasattr(o, '__iter__'):
        newo = cb(o)

        # still an iterable? iterate it.
        if hasattr(newo, '__iter__'):
            if isinstance(newo, dict):
                return dict(((k, walk(v, cb)) for k,v in newo.iteritems()))
            else:
                return [walk(x, cb) for x in newo]
        else:
            return newo
    else:
        return cb(o)

class CodecInterceptor(EnvelopeInterceptor):
    """
    Transforms IonObject <-> dict
    """
    def int_out(self, invocation):
        log.debug("CodecInterceptor.int_out: %s", invocation)

        payload = invocation.message['payload']
        log.debug("Payload, pre-transform: %s", payload)

        def translate_ionobj(obj):
            if isinstance(obj, IonObjectBase):
                res = obj.__dict__
                res["__isAnIonObject"] = obj._def.type.name
                return res
            return obj

        payload = walk(payload, translate_ionobj)
        invocation.message['payload'] = payload

        log.debug("Payload, post-transform: %s", payload)
        return invocation

    def int_in(self, invocation):
        log.debug("CodecInterceptor.int_in: %s", invocation)

        print "hello sirs", str(invocation.message)

        payload = invocation.message['payload']
        log.debug("Payload, pre-transform: %s", payload)

        def untranslate_ionobj(obj):
            if isinstance(obj, dict) and "__isAnIonObject" in obj:
                type = obj.pop("__isAnIonObject")
                ionObj = IonObject(type.encode('ascii'), obj)
                return ionObj
            return obj

        payload = walk(payload, untranslate_ionobj)
        invocation.message['payload'] = payload

        log.debug("Payload, post-transform: %s", payload)
        return invocation

class EncoderInterceptor(EnvelopeInterceptor):
    def int_out(self, invocation):
        log.debug("EncoderInterceptor.int_out: %s", invocation)
        log.debug("Pre-transform: %s", invocation.message)
        invocation.message = msgpack.dumps(invocation.message)
        log.debug("Post-transform: %s", invocation.message)
        return invocation

    def int_in(self, invocation):
        log.debug("EncoderInterceptor.int_in: %s", invocation)
        log.debug("Pre-transform: %s", invocation.message)
        invocation.message = msgpack.loads(invocation.message)
        log.debug("Post-transform: %s", invocation.message)
        return invocation