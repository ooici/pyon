#!/usr/bin/env python

__author__ = 'Adam R. Smith'

import gevent
from collections import Iterable
from functools import wraps

spawn = gevent.spawn

def spawnf(f):
    """ Decorator to spawn this function in a greenlet. """
    @wraps(f)
    def wrapper(*args, **kwargs):
        return gevent.spawn(f, *args, **kwargs)
    return wrapper

def asyncf(f):
    """ Decorator to spawn this function in a greenlet and return the result inline. """
    @wraps(f)
    def wrapper(*args, **kwargs):
        g = gevent.spawn(f, *args, **kwargs)
        return g.get()
    return wrapper

def switch():
    """ Shortcut to give control from the current greenlet back to the gevent hub. """
    gevent.getcurrent().switch()

def join(green_stuff):
    """ Universal way to join on either a single greenlet or a list of them. """
    if isinstance(green_stuff, Iterable):
        return gevent.joinall(green_stuff)
    return gevent.join(green_stuff)

def wait(green_stuff):
    """ Universal way to join on either a single greenlet or a list of them and get return value inline. """
    if isinstance(green_stuff, Iterable):
        gevent.joinall(green_stuff)
        return [g.get() for g in green_stuff]
    return green_stuff.get()
