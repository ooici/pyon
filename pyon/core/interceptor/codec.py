from pyon.core.interceptor.interceptor import Interceptor
from pyon.core.bootstrap import get_obj_registry
from pyon.core.object import IonObjectDeserializer, IonObjectSerializer, IonObjectBlameDeserializer, IonObjectBlameSerializer, walk
from pyon.util.log import log

class CodecInterceptor(Interceptor):
    """
    Transforms IonObject <-> dict
    """
    def __init__(self):
        Interceptor.__init__(self)
        self._io_serializer = IonObjectSerializer()
        self._io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())

    def outgoing(self, invocation):
        log.debug("CodecInterceptor.outgoing: %s", invocation)

        log.debug("Payload, pre-transform: %s", invocation.message)
        invocation.message = self._io_serializer.serialize(invocation.message)
        log.debug("Payload, post-transform: %s", invocation.message)

        return invocation

    def incoming(self, invocation):
        log.debug("CodecInterceptor.incoming: %s", invocation)

        payload = invocation.message
        log.debug("Payload, pre-transform: %s", payload)

        invocation.message = self._io_deserializer.deserialize(payload)
        log.debug("Payload, post-transform: %s", invocation.message)

        return invocation


class BlameCodecInterceptor(CodecInterceptor):
    """
    Transforms IonObject <-> dict and adds "blame_" attribute
    """
    def __init__(self):
        Interceptor.__init__(self)
        self._io_serializer = IonObjectBlameSerializer()
        self._io_deserializer = IonObjectBlameDeserializer(obj_registry=get_obj_registry())
