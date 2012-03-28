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
    def assertion(self, conditional,message, lineno):
        if not conditional:
            log.name = self.name
            log.exception('[%s] %s: %s', lineno or '?',self.exception.__name__,message)
            raise self.exception(message)



import_paths = [__name__]
def scoped_assertion():
    frame = sys._getframe(1)
    name = frame.f_globals.get('__name__',None)
    lineno = frame.f_lineno
    while name in import_paths and frame.f_back:
        frame = frame.f_back
        name = frame.f_globals.get('__name__', None)
        lineno = frame.f_lineno
    return name,lineno


def assertTrue(conditional, message='', exception=None):
    if not conditional:
        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)

def assertEqual(a,b,message='',exception=None):
    if not a==b:
        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)

def assertNotEqual(a,b,message='',exception=None):
    if a==b:
        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)

def assertFalse(conditional, message='', exception=None):
    if conditional:
        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)

def assertIs(a,b, message='', exception=None):
    if not a is b:
        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)

def assertIsNot(a,b, message='', exception=None):
    if a is b:
        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)

def assertIsNotNone(conditional, message='', exception=None):
    if conditional is None:

        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)

def assertIn(needle,haystack, message='', exception=None):
    if not needle in haystack:
        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)

def assertNotIn(needle,haystack, message='', exception=None):
    if needle in haystack:
        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)

def assertIsInstance(a,cls,message='',exception=None):
    if not isinstance(a,cls):
        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)

def assertNotIsInstance(a,cls, message='', exception=None):
    if isinstance(a,cls):
        name,l = scoped_assertion()
        ArgCheck(name,exception).assertion(False,message,l)


