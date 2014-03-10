#!/usr/bin/env python

"""Messaging object encoder/decoder for IonObjects and numpy data"""

import msgpack
import sys
import numpy as np

from pyon.core.bootstrap import get_obj_registry
from pyon.core.exception import BadRequest
from pyon.core.interceptor.interceptor import Interceptor
from pyon.core.object import IonObjectBase, IonMessageObjectBase
from pyon.util.containers import get_safe, DotDict
from pyon.util.log import log

numpy_floats = (np.float, np.float16, np.float32, np.float64)
numpy_ints = (np.int, np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64)
numpy_bool = (np.bool, )
numpy_complex = (np.complex, np.complex64, np.complex128)


class EncodeTypes(object):
    SET = 's'
    LIST = 'l'
    NPARRAY = 'a'
    COMPLEX = 'c'
    DTYPE = 'd'
    SLICE = 'i'
    NPVAL = 'n'


# Global lazy load reference to the Pyon object registry (we be set on first use, not on load).
# Note: We need this here so that the decode_ion/encode_ion functions can be imported (i.e. be static).
obj_registry = None


def decode_ion(obj):
    """msgpack object hook to decode granule (numpy) types and IonObjects.
    This works for nested IonObjects as well"""

    # NOTE: Just matching on dict with "type_" is a bit weak
    if "type_" in obj:
        if "__noion__" in obj:
            # INTERNAL: Allow dicts to mask as IonObject without being decoded (with all defaults set and validated)
            obj.pop("__noion__")
            return obj

        global obj_registry
        if obj_registry is None:
            obj_registry = get_obj_registry()

        ion_obj = obj_registry.new(obj["type_"])
        for k, v in obj.iteritems():
            # unicode translate to utf8
            # Note: This is not recursive within dicts/list or any other types
            if isinstance(v, unicode):
                v = v.encode('utf8')
            if k != "type_":
                setattr(ion_obj, k, v)
        return ion_obj

    if 't' not in obj:
        return obj

    objt = obj['t']

    if objt == EncodeTypes.LIST:
        return list(obj['o'])

    elif objt == EncodeTypes.NPARRAY:
        return np.array(obj['o'], dtype=np.dtype(obj['d']))

    elif objt == EncodeTypes.COMPLEX:
        return complex(obj['o'][0], obj['o'][1])

    elif objt == EncodeTypes.DTYPE:
        return np.dtype(obj['o'])

    elif objt == EncodeTypes.SLICE:
        return slice(obj['o'][0], obj['o'][1], obj['o'][2])

    elif objt == EncodeTypes.SET:
        return set(obj['o'])

    elif objt == EncodeTypes.NPVAL:
        dt = np.dtype(obj['d'])
        return dt.type(obj['o'])

    return obj


def encode_ion(obj):
    """
    msgpack object hook to encode granule/numpy types and IonObjects.
    This hook works also for non-basic types nested within other types, e.g.
    it will be called for a top level IonObject and for any potential nested IonObjects.
    """

    if isinstance(obj, IonObjectBase):
        # There must be a type_ in here so that the object can be decoded
        if not isinstance(obj, IonMessageObjectBase) and not hasattr(obj, "type_"):
            log.error("IonObject with no type_: %s", obj)
        return obj.__dict__

    if isinstance(obj, list):
        return {'t': EncodeTypes.LIST, 'o': tuple(obj)}

    if isinstance(obj, set):
        return {'t': EncodeTypes.SET, 'o': tuple(obj)}

    if isinstance(obj, np.ndarray):
        return {'t': EncodeTypes.NPARRAY, 'o': obj.tolist(), 'd': obj.dtype.str}

    if isinstance(obj, complex):
        return {'t': EncodeTypes.COMPLEX, 'o': (obj.real, obj.imag)}

    if isinstance(obj, np.number):
        if isinstance(obj, numpy_floats):
            return {'t': EncodeTypes.NPVAL, 'o': float(obj.astype(float)), 'd': obj.dtype.str}
        elif isinstance(obj, numpy_ints):
            return {'t': EncodeTypes.NPVAL, 'o': int(obj.astype(int)), 'd': obj.dtype.str}
        else:
            raise TypeError('Unsupported type "%s"' % type(obj))

    if isinstance(obj, slice):
        return {'t': EncodeTypes.SLICE, 'o': (obj.start, obj.stop, obj.step)}

    if isinstance(obj, np.dtype):
        return {'t': EncodeTypes.DTYPE, 'o': obj.str}

    # Must raise type error for any unknown object
    raise TypeError('Unknown type "%s" in user specified encoder: "%s"' % (type(obj), obj))


class EncodeInterceptor(Interceptor):

    def __init__(self):
        self.max_message_size = sys.maxint  # Will be set appropriately from interceptor config

    def configure(self, config):
        self.max_message_size = get_safe(config, 'max_message_size', 20000000)
        log.debug("EncodeInterceptor enabled")

    def outgoing(self, invocation):
        payload = invocation.message

        # Compliance: Make sure sent message objects support DotDict as arguments.
        # Although DotDict is subclass of dict, msgpack does not like it
        if isinstance(payload, IonMessageObjectBase):
            for k, v in payload.__dict__.iteritems():
                if isinstance(v, DotDict):
                    setattr(payload, k, v.as_dict())

        # Msgpack the content to binary str - does nested IonObject encoding
        try:
            invocation.message = msgpack.packb(payload, default=encode_ion)
        except Exception:
            log.error("Illegal type in IonObject attributes: %s", payload)
            raise BadRequest("Illegal type in IonObject attributes")

        # Make sure no Nones exist in headers - this indicates a problem somewhere up the stack.
        # pika will choke hard on them as well, masking the actual problem, so we catch here.
        nonelist = [(k, v) for k, v in invocation.headers.iteritems() if v is None]
        if nonelist:
            raise BadRequest("Invalid headers containing None values: %s" % str(nonelist))

        msg_size = len(invocation.message)
        if msg_size > self.max_message_size:
            raise BadRequest('The message size %s is larger than the max_message_size value of %s' % (
                msg_size, self.max_message_size))

        return invocation


    def incoming(self, invocation):
        # Un-Msgpack the content from binary string - does IonObject decoding
        invocation.message = msgpack.unpackb(invocation.message, object_hook=decode_ion, use_list=1)

        # At this point there could be a recursive unicode treatment, if necessary

        return invocation
