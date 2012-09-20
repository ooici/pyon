import msgpack

from pyon.core.interceptor.interceptor import Interceptor
from pyon.util.log import log
import numpy as np

numpy_floats  = (np.float, np.float16, np.float32, np.float64)
numpy_ints    = (np.int, np.int8, np.int16, np.int64, np.uint8, np.uint16, np.uint32, np.uint64, np.uint64)
numpy_bool    = (np.bool)
numpy_complex = (np.complex, np.complex64, np.complex128)

def decode_ion( obj):
    """
    MsgPack object hook to decode any ion object as part of the message pack walk rather than implementing it again in
    pyon
    """

    if "__set__" in obj:
        return set(obj['tuple'])

    elif "__list__" in obj:
        return list(obj['tuple'])

    elif "__ion_array__" in obj:
        # Shape is currently implicit because tolist encoding makes a list of lists for a 2d array.
        return np.array(obj['content'],dtype=np.dtype(obj['header']['type']))

    elif '__complex__' in obj:
        return complex(obj['real'], obj['imag'])
        ## Always return object
    elif '__dtype__' in obj:
        dt = np.dtype(obj['__dtype__'])
        return dt.type(obj['val'])
    return obj

def encode_ion( obj):
    """
    MsgPack object hook to encode any ion object as part of the message pack walk rather than implementing it again in
    pyon
    """

    if isinstance(obj, list):
        return {"__list__":True, 'tuple':tuple(obj)}

    if isinstance(obj, set):
        return {"__set__":True, 'tuple':tuple(obj)}

    if isinstance(obj, np.ndarray):
        if obj.ndim == 0:
            raise ValueError('Can not encode a np array with rank 0')
        return {"header":{"type":str(obj.dtype),"nd":obj.ndim,"shape":obj.shape},"content":obj.tolist(),"__ion_array__":True}

    if isinstance(obj, complex):
        return {'__complex__': True, 'real': obj.real, 'imag': obj.imag}

    if isinstance(obj, np.number):
        if isinstance(obj,numpy_floats):
            return {'__dtype__': obj.dtype.str, 'val':obj.astype(float)}
        elif isinstance(obj, numpy_ints):
            return {'__dtype__': obj.dtype.str, 'val':obj.astype(int)}
        else:
            raise TypeError('Unsupported type "%s"', str(type(obj)))



    # Must raise type error to avoid recursive failure
    raise TypeError('Unknown type "%s" in user specified encoder: "%s"' % (str(type(obj)), str(obj)))



class EncodeInterceptor(Interceptor):
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
        return invocation

    def incoming(self, invocation):
        log.debug("EncodeInterceptor.incoming: %s", invocation)
        # Logging binary stuff caused nose capture output to blow up when
        # there's an exception
        # log.debug("Pre-transform: %s", invocation.message)
        invocation.message = msgpack.unpackb(invocation.message, object_hook=decode_ion, use_list=1)
        log.debug("Post-transform: %s", invocation.message)
        return invocation
