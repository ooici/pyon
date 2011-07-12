#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import ihooks
import logging
import sys

# List of module names that will pass-through for the magic import scoping. This can be modified.
import_paths = [__name__]
handlers = []

def get_logger(loggername=__name__):
    """
    Creates an instance of a logger.
    Adds any registered handlers with this factory.

    Note: as this method is called typically on module load, if you haven't
    registered a handler at this time, that instance of a logger will not
    have that handler.
    """
    logger = logging.getLogger(loggername)
    for handler in handlers:
        logger.addHandler(handler)
    
    return logger

# Special placeholder object, to be swapped out for each module that imports this one
log = None

def get_scoped_log(framestoskip=1):
    frame = sys._getframe(framestoskip)
    name = frame.f_locals.get('__name__', None)

    while name in import_paths:
        frame = frame.f_back
        name = frame.f_locals.get('__name__', None)

    log = get_logger(name) if name else None
    return log
    
class LogImportHook(ihooks.ModuleImporter):
    """
    Magic import mechanism  to get a logger that's auto-scoped to the importing module. Example:
    from ion.base import scoped_log as log

    Inspects the stack; should be harmless since this is just syntactic sugar for module declarations.
    """
    def import_module(self, name, globals=None, locals=None, fromlist=None):
        module = ihooks.ModuleImporter.import_module(self, name, globals, locals, fromlist)

        if name in import_paths and ('log' in fromlist or '*' in fromlist):
            log = get_scoped_log(2)
            setattr(module, 'log', log)

        return module

LogImportHook().install()
log = get_scoped_log()

