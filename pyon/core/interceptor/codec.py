#!/usr/bin/env python

from pyon.core.interceptor.interceptor import Interceptor
from pyon.core.bootstrap import get_obj_registry
from pyon.core.object import IonObjectDeserializer, IonObjectSerializer, IonObjectBlameDeserializer, IonObjectBlameSerializer
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
        # NOTE: Skipping this step, because the encode interceptor now handles IonObject
        #invocation.message = self._io_serializer.serialize(invocation.message)

        return invocation

    def incoming(self, invocation):
        # NOTE: Skipping this step, because the encode interceptor now handles IonObject
        #payload = invocation.message
        #invocation.message = self._io_deserializer.deserialize(payload)

        return invocation


class BlameCodecInterceptor(CodecInterceptor):
    """
    Transforms IonObject <-> dict and adds "blame_" attribute
    """
    def __init__(self):
        Interceptor.__init__(self)
        self._io_serializer = IonObjectBlameSerializer()
        self._io_deserializer = IonObjectBlameDeserializer(obj_registry=get_obj_registry())
