#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

class IonException(Exception):
    pass

class BadRequest(IonException):
    '''
    Incorrectly formatted client request
    '''
    pass

class Unauthorized(IonException):
    '''
    Client failed policy enforcement
    '''
    pass

class NotFound(IonException):
    ''''
    Requested resource not found
    '''
    pass

class Timeout(IonException):
    '''
    Client request timed out
    '''
    pass

class ServerError(IonException):
    '''
    For reporting generic service failure
    '''
    pass

class ServiceUnavailable(IonException):
    '''
    Requested service not started or otherwise unavailable
    '''
    pass