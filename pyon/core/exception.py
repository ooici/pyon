import inspect
import sys

from ooi.exception import ApplicationException


__author__ = 'Thomas R. Lennan'


BAD_REQUEST = 400
UNAUTHORIZED = 401
NOT_FOUND = 404
TIMEOUT = 408
CONFLICT = 409
SERVER_ERROR = 500
SERVICE_UNAVAILABLE = 503


class IonException(ApplicationException):
    status_code = -1

    def __init__(self, *a, **b):
        super(IonException, self).__init__(*a, **b)

    def get_status_code(self):
        return self.status_code

    def get_error_message(self):
        return self.message

    def __str__(self):
        return str(self.get_status_code()) + " - " + str(self.get_error_message())

class StreamException(IonException):
    
    def __init__(self, *a, **b):
        super(StreamException, self).__init__(*a, **b)

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

class FilesystemError(StreamException):
    """
    """
    status_code = 411

class StreamingError(StreamException):
    """
    """
    status_code = 412

class CorruptionError(StreamException):
    """
    """
    status_code = 413

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


class InstDriverClientTimeoutError(IonInstrumentError):
    """
    A special kind of timeout that only applies at the driver client level (not an instrument timeout).
    """
    status_code = 691

class ResourceError(IonException):
    """
    A taskable resource error occurred.
    """
    status_code = 700


# must appear after ServerError in python module
class ExceptionFactory(object):
    def __init__(self, default_type=ServerError):
        self._default = default_type
        self._exception_map = {}
        for name, obj in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(obj):
                if hasattr(obj, "status_code"):
                    self._exception_map[str(obj.status_code)] = obj

    def create_exception(self, code, message, stacks=None):
        """ build IonException from code, message, and optionally one or more stack traces """
        if str(code) in self._exception_map:
            out = self._exception_map[str(code)](message)
        else:
            out = self._default(message)
# TEMPORARY: disable adding stacks here until JIRA OOIION-1093 fixed to avoid memory leak
#        if stacks:
#            for label, stack in stacks:
#                out.add_stack(label, stack)
        return out


