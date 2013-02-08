#!/usr/bin/env python
'''

'''
try:
    import numpy as np
    has_np=True
except ImportError:
    has_np=False
    
def hash_any(value, hv=None):
    hv = hv or 0
    if value is None or isinstance(value, (str, unicode, int, long, float, bool)):
#        log.debug('is primitive:  value=%s  hv=%s', value, hv)
        hv = hash(value) ^ hv
    elif  has_np and np.isscalar(value):
#        log.debug('is numpy.scalar:  value=%s  hv=%s', value, hv)
        hf = hash(value) ^ hv
    elif isinstance(value, (list, tuple, set)):
#        log.debug('is list/tuple/set:  value=%s  hv=%s', value, hv)
        for x in value:
            hv = hash_any(x, hv)
    elif isinstance(value, dict):
#        log.debug('is dict:  value=%s  hv=%s', value, hv)
        for k,v in value.iteritems():
            hv = hash_any(k, hv)
            hv = hash_any(v, hv)
    elif isinstance(value, slice):
        # Hash a tuple of the slice components
        hv = hash((value.start, value.stop, value.step)) ^ hv
    elif isinstance(value, object):
#        log.debug('is object:  value=%s  hv=%s', value, hv)
        hv = hash_any(value.__dict__, hv)

    return hv
