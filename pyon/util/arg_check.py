#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@file pyon/util/arg_check.py
@description Utility for managing assertions in a contained, decisive and deterministic manner
'''

from pyon.core.exception import BadRequest
from pyon.util.log import log
import sys

class ArgCheck(object):
    '''
    Utility for handling argument assertions and preconditions
    '''
    def __init__(self,name, exception=None):
        self.name = name
        self.exception = exception or BadRequest
    def assertion(self, conditional, message):
        if not conditional:
            log.name = self.name
            log.exception(message)
            raise self.exception(message)


import_paths = [__name__]
def scoped_assertion():
    frame = sys._getframe(1)
    name = frame.f_globals.get('__name__',None)
    while name in import_paths and frame.f_back:
        frame = frame.f_back
        name = frame.f_globals.get('__name__', None)
    return name


def assertTrue(conditional, message='', exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(conditional,message)

def assertEqual(a,b,message='',exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(a==b,message)

def assertNotEqual(a,b,message='',exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(a!=b,message)

def assertFalse(conditional, message='', exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(not conditional,message)

def assertIs(a,b, message='', exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(a is b,message)

def assertIsNot(a,b, message='', exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(a is not b,message)

def assertIsNotNone(conditional, message='', exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(conditional is not None,message)

def assertIn(needle,haystack, message='', exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(needle in haystack,message)

def assertNotIn(needle,haystack, message='', exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(not (needle in haystack),message)

def assertIsInstance(a,cls,message='',exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(isinstance(a,cls),message)

def assertNotIsInstance(a,cls, message='', exception=None):
    name = scoped_assertion()
    ArgCheck(name,exception).assertion(not isinstance(a,cls),message)


