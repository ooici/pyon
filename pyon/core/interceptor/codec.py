from pyon.core.interceptor.interceptor import Interceptor, walk
from pyon.core.bootstrap import obj_registry
from pyon.core.object import IonObjectBase, IonObjectDeserializer, IonObjectSerializer
from pyon.util.log import log

class CodecInterceptor(Interceptor):
    """
    Transforms IonObject <-> dict
    """
    def __init__(self):
        Interceptor.__init__(self)
        self._io_serializer = IonObjectSerializer()
        self._io_deserializer = IonObjectDeserializer(obj_registry=obj_registry)

    def outgoing(self, invocation):
        log.debug("CodecInterceptor.outgoing: %s", invocation)

        log.debug("Payload, pre-transform: %s", invocation.message)
        invocation.message = self._io_serializer.serialize(invocation.message)
        log.debug("Payload, post-transform: %s", invocation.message)

        return invocation

    def incoming(self, invocation):
        log.debug("CodecInterceptor.incoming: %s", invocation)

        log.debug("Payload, pre-transform: %s", invocation.message)
        invocation.message = self._io_deserializer.deserialize(invocation.message)
        log.debug("Payload, post-transform: %s", invocation.message)

        return invocation
