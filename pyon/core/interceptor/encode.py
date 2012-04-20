import msgpack

from pyon.core.interceptor.interceptor import Interceptor
from pyon.util.log import log
import numpy

"""
@todod Add other ion object stuff here...
"""


def decode_ion( obj):
    """
    MsgPack object hook to decode any ion object as part of the message pack walk rather than implementing it again in
    pyon
    """
    if "__ion_array__" in obj:
        # Shape is currently implicit because tolist encoding makes a list of lists for a 2d array.
        return numpy.array(obj['content'],dtype=numpy.dtype(obj['header']['type']))

    elif '__complex__' in obj:
        return complex(obj['real'], obj['imag'])
        ## Always return object
    return obj

def encode_ion( obj):
    """
    MsgPack object hook to encode any ion object as part of the message pack walk rather than implementing it again in
    pyon
    """
    if isinstance(obj, numpy.ndarray):
        return {"header":{"type":str(obj.dtype),"nd":len(obj.shape),"shape":obj.shape},"content":obj.tolist(),"__ion_array__":True}

    elif isinstance(obj, complex):
        return {'__complex__': True, 'real': obj.real, 'imag': obj.imag}

    if isinstance(obj, (numpy.float, numpy.float16, numpy.float32, numpy.float64)):
        raise ValueError('Can not encode numpy scalars!')

    else:
        # Must raise type error to avoid recursive failure
        raise TypeError('Unknown type "%s" in user specified encoder: "%s"' % (str(type(obj)), str(obj)))
    return obj



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

        log.debug("Post-transform: %s", invocation.message)
        return invocation

    def incoming(self, invocation):
        log.debug("EncodeInterceptor.incoming: %s", invocation)
        log.debug("Pre-transform: %s", invocation.message)
        invocation.message = msgpack.unpackb(invocation.message, object_hook=decode_ion)
        log.debug("Post-transform: %s", invocation.message)
        return invocation
