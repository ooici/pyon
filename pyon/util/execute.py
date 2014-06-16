#!/usr/bin/env python

'''
This module handle the dynamic execution of methods
'''

__author__ = 'Stephen Henrie'



import inspect

from pyon.core.bootstrap import get_service_registry
from pyon.util.log import log

# This method will dynamically call the specified method. It will look for the method in the current class
# and also in the class specified by the service_provider
def execute_method(execution_object, method_name, *args, **kwargs):
    """
    This function will execute a method either remotely through messaging or look for the method
    in the execution object or in the service_provider field of the execution object if specified
    @param execution_object:  the location of the function
    @param method_name:
    @param args:
    @param kwargs:
    @return:
    """

    #First look to see if this is a remote method
    if method_name.find('.') > 0:

        service_client, operation = get_remote_info(execution_object, method_name)

        methodToCall = getattr(service_client, operation)
        param_dict = get_method_arguments(service_client, operation, **kwargs)
        ret = methodToCall(*args, **param_dict )
        return ret

    else:
        #For local methods, first look for the method in the current class
        func = getattr(execution_object, method_name, None)
        if func:
            param_dict = get_method_arguments(execution_object, method_name, **kwargs)
            return func(*args, **param_dict)
        elif getattr(execution_object, 'service_provider', None) is not None:
            #Next look to see if the method exists in the service provider process
            func = getattr(execution_object.service_provider, method_name, None)
            if func:
                param_dict = get_method_arguments(execution_object.service_provider,method_name, **kwargs)
                return func(*args, **param_dict)

    return None


def get_remote_info(execution_object, method_name):
    """
    Returns the service client and operation name

    @param method_name:
    @return:
    """
    #This is a remote method.
    rmi_call = method_name.split('.')
    #Retrieve service definition
    service_name = rmi_call[0]
    operation = rmi_call[1]
    if service_name == 'resource_registry':
        service_client = execution_object._rr
    else:
        target_service = get_service_registry().get_service_by_name(service_name)
        service_client = target_service.client(node=execution_object.service_provider.container.instance.node, process=execution_object.service_provider)

    return service_client, operation


def get_method_arguments(module, method_name, **kwargs):
    """
    Returns a dict of the allowable method parameters
    @param module:
    @param method_name:
    @param kwargs:
    @return:
    """
    param_dict = {}

    if hasattr(module,method_name):
        try:
            #This will fail running unit tests with mock objects - BOO!  
            method_args = inspect.getargspec(getattr(module,method_name))
            for arg in method_args[0]:
                if kwargs.has_key(arg):
                    param_dict[arg] = kwargs[arg]

        except Exception, e:
            #Log a warning and simply return an empty dict
            log.warn('Cannot determine the arguments for method: %s in module: %s: %s',module, method_name, e.message )

    return param_dict