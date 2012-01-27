from pyon.core.interceptor.interceptor import Interceptor
from pyon.core.bootstrap import obj_registry
from pyon.core.object import IonObjectDeserializer, IonObjectSerializer, walk
from pyon.util.log import log
try:
    import numpy as np
    _have_numpy = True
except ImportError as e:
    _have_numpy = False

if _have_numpy:
    from pyon.core.object import NumpyObjectDeserialization, NumpyObjectSerialization
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
        if _have_numpy:
            if isinstance(invocation.message,np.ndarray):
                serializer = NumpyObjectSerialization()
                invocation.message = serializer.transform(invocation.message)
                log.debug('Numpy:\n  Message: %s', invocation.message)


        invocation.message = self._io_serializer.serialize(invocation.message)
        log.debug("Payload, post-transform: %s", invocation.message)

        return invocation

    def incoming(self, invocation):
        log.debug("CodecInterceptor.incoming: %s", invocation)

        payload = invocation.message

        log.debug("Payload, pre-transform: %s", payload)

        if _have_numpy:
            if isinstance(invocation.message,dict):
                msg = invocation.message.get('numpy',False)
                if msg:
                    deserializer = NumpyObjectDeserialization()
                    invocation.message = deserializer.transform(msg)
                    log.debug("Payload, post-transform: %s", invocation.message)
                    return invocation



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
