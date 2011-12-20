#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import __builtin__
import logging
import sys

# List of module names that will pass-through for the magic import scoping. This can be modified.
import_paths = [__name__]

def get_logger(loggername=__name__):
    """
    Creates an instance of a logger.
    Adds any registered handlers with this factory.

    Note: as this method is called typically on module load, if you haven't
    registered a handler at this time, that instance of a logger will not
    have that handler.
    """
    logger = logging.getLogger(loggername)

    return logger

# Special placeholder object, to be swapped out for each module that imports this one
log = None

def get_scoped_log(framestoskip=1):
    frame = sys._getframe(framestoskip)
    name = frame.f_locals.get('__name__', None)

    while name in import_paths and frame.f_back:
        frame = frame.f_back
        name = frame.f_locals.get('__name__', None)

    log = get_logger(name) if name else None
    return log

_orig___import__ = __import__
def _import(name, globals=None, locals=None, fromlist=None, level=-1):
    """
    Magic import mechanism  to get a logger that's auto-scoped to the importing module. Example:
    from pyon.public import scoped_log as log

    Inspects the stack; should be harmless since this is just syntactic sugar for module declarations.
    """
    kwargs = dict()
    if globals:
        kwargs['globals'] = globals
    if locals:
        kwargs['locals'] = locals
    if fromlist:
        kwargs['fromlist'] = fromlist
    kwargs['level'] = level
    module = _orig___import__(name, **kwargs)
    if name in import_paths and ('log' in fromlist or '*' in fromlist):
        log = get_scoped_log(2)
        setattr(module, 'log', log)

    return module
__builtin__.__import__ = _import

# Workaround a quirk in python 2.7 with custom imports
from logging.config import BaseConfigurator
BaseConfigurator.importer = staticmethod(_import)

log = get_scoped_log()

