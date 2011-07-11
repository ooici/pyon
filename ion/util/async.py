#!/usr/bin/env python

__author__ = 'Adam R. Smith'

import gevent
from functools import wraps

def spawn(f):
    """ Decorator to spawn this function in a greenlet. """
    @wraps(f)
    def wrapper(*args, **kwds):
        return gevent.spawn(f, *args, **kwds)
    return wrapper

def switch():
    """ Shortcut to give control from the current greenlet back to the gevent hub. """
    gevent.getcurrent().switch()