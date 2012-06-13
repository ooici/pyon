#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

BAD_REQUEST = 400
UNAUTHORIZED = 401
NOT_FOUND = 404
TIMEOUT = 408
CONFLICT = 409
SERVER_ERROR = 500
SERVICE_UNAVAILABLE = 503

class IonException(Exception):
    status_code = -1

    def get_status_code(self):
        return self.status_code

    def get_error_message(self):
        return self.message

    def __str__(self):
        return str(self.get_status_code()) + " - " + str(self.get_error_message())

class BadRequest(IonException):
    '''
    Incorrectly formatted client request
    '''
    status_code = 400

class Unauthorized(IonException):
    '''
    Client failed policy enforcement
    '''
    status_code = 401

class NotFound(IonException):
    ''''
    Requested resource not found
    '''
    status_code = 404

class Timeout(IonException):
    '''
    Client request timed out
    '''
    status_code = 408

class Conflict(IonException):
    '''
    Client request failed due to conflict with the current state of the resource
    '''
    status_code = 409

class Inconsistent(IonException):
    '''
    Client request failed due to internal error of the datastore
    '''
    status_code = 410

class ServerError(IonException):
    '''
    For reporting generic service failure
    '''
    status_code = 500

class ServiceUnavailable(IonException):
    '''
    Requested service not started or otherwise unavailable
    '''
    status_code = 503

class ConfigNotFound(IonException):
    '''
    '''
    status_code = 540

class ContainerError(IonException):
    '''
    '''
    status_code = 550

class ContainerConfigError(ContainerError):
    '''
    '''
    status_code = 551

class ContainerStartupError(ContainerError):
    '''
    '''
    status_code = 553

class ContainerAppError(ContainerError):
    '''
    '''
    status_code = 554

class IonInstrumentError(IonException):
    """
    """
    status_code = 600
    
class InstConnectionError(IonInstrumentError):
    """
    """
    status_code = 610
    
class InstNotImplementedError(IonInstrumentError):
    """
    """
    status_code = 620
    
class InstParameterError(IonInstrumentError):
    """
    """
    status_code = 630

class InstProtocolError(IonInstrumentError):
    """
    """
    status_code = 640

class InstSampleError(IonInstrumentError):
    """
    """
    status_code = 650

class InstStateError(IonInstrumentError):
    """
    """
    status_code = 660

class InstUnknownCommandError(IonInstrumentError):
    """
    """
    status_code = 670

class InstDriverError(IonInstrumentError):
    """
    """
    status_code = 680

class InstTimeoutError(IonInstrumentError):
    """
    """
    status_code = 690

# @WARN: GLOBAL STATE
exception_map = {}
import inspect
import sys
# @WARN: STATIC CODE
for name, obj in inspect.getmembers(sys.modules[__name__]):
    if inspect.isclass(obj):
        if hasattr(obj, "status_code"):
            exception_map[str(obj.status_code)] = obj
