import msgpack
import sys

from pyon.core.exception import BadRequest
from pyon.core.interceptor.interceptor import Interceptor
from pyon.util.containers import get_safe
from pyon.util.log import log
import numpy as np

numpy_floats  = (np.float, np.float16, np.float32, np.float64)
numpy_ints    = (np.int, np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64)
numpy_bool    = (np.bool)
numpy_complex = (np.complex, np.complex64, np.complex128)

class EncodeTypes(object):
    SET = 's'
    LIST = 'l'
    NPARRAY = 'a'
    COMPLEX = 'c'
    DTYPE = 'd'
    SLICE = 'i'
    NPVAL = 'n'




def decode_ion(obj):
    """
    MsgPack object hook to decode any ion object as part of the message pack walk rather than implementing it again in
    pyon
    """

    if not 't' in obj:
        return obj

    if obj['t'] == EncodeTypes.LIST:
        return list(obj['o'])

    elif obj['t'] == EncodeTypes.NPARRAY:
        return np.array(obj['o'], dtype=np.dtype(obj['d']))

    elif obj['t'] == EncodeTypes.COMPLEX:
        return complex(obj['o'][0], obj['o'][1])
    
    elif obj['t'] == EncodeTypes.DTYPE:
        return np.dtype(obj['o'])

    elif obj['t'] == EncodeTypes.SLICE:
        return slice(obj['o'][0], obj['o'][1], obj['o'][2])

    elif obj['t'] == EncodeTypes.SET:
        return set(obj['o'])

    elif obj['t'] == EncodeTypes.NPVAL:
        dt = np.dtype(obj['d'])
        return dt.type(obj['o'])

    return obj


def encode_ion(obj):
    """
    MsgPack object hook to encode any ion object as part of the message pack walk rather than implementing it again in
    pyon
    """

    if isinstance(obj, list):
        return {'t':EncodeTypes.LIST,'o':tuple(obj)}

    if isinstance(obj, set):
        return {'t':EncodeTypes.SET, 'o':tuple(obj)}

    if isinstance(obj, np.ndarray):
        return {'t':EncodeTypes.NPARRAY, 'o':obj.tolist(), 'd':obj.dtype.str}

    if isinstance(obj, complex):
        return {'t':EncodeTypes.COMPLEX, 'o':tuple(obj.real, obj.imag)}

    if isinstance(obj, np.number):
        if isinstance(obj,numpy_floats):
            return {'t':EncodeTypes.NPVAL, 'o':float(obj.astype(float)), 'd':obj.dtype.str}
        elif isinstance(obj, numpy_ints):
            return {'t':EncodeTypes.NPVAL, 'o':int(obj.astype(int)), 'd':obj.dtype.str}
        else:
            raise TypeError('Unsupported type "%s"', str(type(obj)))

    if isinstance(obj, slice):
        return {'t':EncodeTypes.SLICE, 'o':(obj.start, obj.stop, obj.step)}

    if isinstance(obj,np.dtype):
        return {'t':EncodeTypes.DTYPE, 'o':obj.str}

    # Must raise type error to avoid recursive failure
    raise TypeError('Unknown type "%s" in user specified encoder: "%s"' % (str(type(obj)), str(obj)))


class EncodeInterceptor(Interceptor):

    def __init__(self):
        self.max_message_size = sys.maxint  # Will be set appropriately from configuration

    def configure(self, config):
        self.max_message_size = get_safe(config, 'container.messaging.max_message_size', 20000000)
        log.debug("EncodeInterceptor enabled")

    def outgoing(self, invocation):
        log.debug("EncodeInterceptor.outgoing: %s", invocation)
        log.debug("Pre-transform: %s", invocation.message)

        # msgpack the content (ensures string)
        invocation.message = msgpack.packb(invocation.message, default=encode_ion)

        # make sure no Nones exist in headers - this indicates a problem somewhere up the stack
        # pika will choke hard on them as well, masking the actual problem, so we catch here.
        nonelist = [(k, v) for k, v in invocation.headers.iteritems() if v is None]
        assert len(nonelist) == 0, "Invalid headers containing Nones: %s" % str(nonelist)

        # Logging binary stuff caused nose capture output to blow up when
        # there's an exception
        # log.debug("Post-transform: %s", invocation.message)

        msg_size = len(invocation.message)
        log.debug("message size: %s", msg_size)
        if msg_size > self.max_message_size:
            raise BadRequest('The message size %s is larger than the max_message_size value of %s' % (msg_size,self.max_message_size) )

        return invocation

    def incoming(self, invocation):
        log.debug("EncodeInterceptor.incoming: %s", invocation)
        # Logging binary stuff caused nose capture output to blow up when
        # there's an exception
        # log.debug("Pre-transform: %s", invocation.message)
        invocation.message = msgpack.unpackb(invocation.message, object_hook=decode_ion, use_list=1)
        log.debug("Post-transform: %s", invocation.message)
        return invocation
