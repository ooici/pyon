#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from anode.base import log

class BaseService(object):
    """
    Something that provides a 'service'.
    Not dependent on messaging.
    Probably will have a simple start/stop interface.
    """

    name = None
    running = 0

