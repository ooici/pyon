from pyon.core.interceptor.interceptor import Interceptor, walk
from pyon.core.bootstrap import IonObject
from pyon.core.object import IonObjectBase
from pyon.util.log import log

class CodecInterceptor(Interceptor):
    """
    Transforms IonObject <-> dict
    """
    def outgoing(self, invocation):
        log.debug("CodecInterceptor.outgoing: %s", invocation)

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

    def incoming(self, invocation):
        log.debug("CodecInterceptor.incoming: %s", invocation)

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
