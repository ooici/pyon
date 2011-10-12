#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

class BaseService(object):
    """
    Something that provides a 'service'.
    Not dependent on messaging.
    Probably will have a simple start/stop interface.
    """

    name = None
    running = 0

    def service_init(self):
        """
        Method to be overridden as neccessary by
        implementing service classes to perform
        initialization actions prior to service
        start.  Configuration parameters are
        accessible via the self.CFG dict.
        """
        pass

    def service_start(self):
        """
        Method called at service startup.
        """
        pass

services_by_name = {}

def build_service_map():
    global services_by_name

    for cls in BaseService.__subclasses__():
        if cls.name is None:
            raise AssertionError('Service class must define name value. Service class in error: %s' % (str(cls)))
        services_by_name[cls.name] = cls

def add_service_by_name(name, service):
    services_by_name[name] = service

def get_service_by_name(name):
    if name in services_by_name:
        return services_by_name[name]
    else:
        return None

build_service_map()
