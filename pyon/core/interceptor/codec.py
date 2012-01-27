from pyon.core.interceptor.interceptor import Interceptor
from pyon.core.bootstrap import obj_registry
from pyon.core.object import IonObjectDeserializer, IonObjectSerializer, walk
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

        payload = invocation.message

        log.debug("Payload, pre-transform: %s", payload)




        # Horrible, hacky workaround for msgpack issue
        # See http://jira.msgpack.org/browse/MSGPACK-15
        def convert_tuples_to_lists(obj):
            if isinstance(obj, tuple):
                res = list(obj)
                return res
            return obj

        payload = walk(payload, convert_tuples_to_lists)

        invocation.message = self._io_deserializer.deserialize(payload)
        log.debug("Payload, post-transform: %s", invocation.message)

        return invocation
