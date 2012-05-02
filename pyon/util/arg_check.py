#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@file pyon/util/arg_check.py
@description Utility for managing validations in a contained, decisive and deterministic manner
'''

from pyon.core.exception import BadRequest
from pyon.util.log import log
import sys

class ArgCheck(object):
    '''
    Utility for handling argument validations and preconditions
    '''
    def __init__(self,name, exception=None):
        self.name = name
        self.exception = exception or BadRequest
    def validation(self, conditional,message, lineno):
        if not conditional:
            log.name = self.name
            log.exception('[%s] %s: %s', lineno or '?',self.exception.__name__,message)
            raise self.exception(message)



import_paths = [__name__]
def scoped_validation():
    '''
    Determines the calling module and line number.
    Allows us to determine the file and line number where the validation is made.
    Inspired by pyon/util/log.py (Adam Smith)
    '''
    frame = sys._getframe(1)
    name = frame.f_globals.get('__name__',None)
    lineno = frame.f_lineno
    while name in import_paths and frame.f_back:
        frame = frame.f_back
        name = frame.f_globals.get('__name__', None)
        lineno = frame.f_lineno
    return name,lineno


def validate_true(conditional, message='', exception=None):
    '''
    Manages an validation
    @param conditional The conditional statement to be evaluated
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if not conditional:
        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)

def validate_equal(a,b,message='',exception=None):
    '''
    Raises an exception if a != b
    @param a 
    @param b
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if a!=b:
        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)

def validate_not_equal(a,b,message='',exception=None):
    '''
    Raises an exception if a == b
    @param a
    @param b
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if a==b:
        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)

def validate_false(conditional, message='', exception=None):
    '''
    Raises an exception if conditional evaluates to False
    @param conditional The conditional statement to be evaluated
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if conditional:
        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)

def validate_is(a,b, message='', exception=None):
    '''
    Raises an exception if a does not points to the same object as b
    @param a
    @param b
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if not a is b:
        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)

def validate_is_not(a,b, message='', exception=None):
    '''
    Raises an exception if a points to the same object as b
    @param a
    @param b
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if a is b:
        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)

def validate_is_not_none(conditional, message='', exception=None):
    '''
    Raises an exception if conditional is None, does not point to anything and is not a number.
    @param conditional The conditional statement to be evaluated
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if conditional is None:

        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)

def validate_in(needle,haystack, message='', exception=None):
    '''
    Raises an exception if needle is not in haystack
    @param needle Item to be evaluated for
    @param haystack List or structure where the keyword 'in' can be used to evaluate a member exists within
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if not needle in haystack:
        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)

def validate_not_in(needle,haystack, message='', exception=None):
    '''
    Raises an exception if needle is in haystack
    @param needle Item to be evaluated for
    @param haystack List or structure where the keyword 'in' can be used to evaluate a member exists within
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if needle in haystack:
        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)

def validate_is_instance(a,cls,message='',exception=None):
    '''
    Raises an exception if a is not an instance of cls
    @param a Object
    @param cls Class
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if not isinstance(a,cls):
        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)

def validate_not_is_instance(a,cls, message='', exception=None):
    '''
    Raises an exception if a is an instance of cls
    @param a Object
    @param cls Class
    @param message Error message to be included with the exception
    @param Exception, exception module to use in lieu of default
    @throws BadRequest if conditional is evaluated to False
    '''
    if isinstance(a,cls):
        name,l = scoped_validation()
        ArgCheck(name,exception).validation(False,message,l)



