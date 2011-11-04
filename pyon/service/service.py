#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.state_object import LifecycleStateMixin

class BaseService(LifecycleStateMixin):
    """
    A process class that provides a 'service'.
    Not dependent on messaging.
    """

    name = None
    running = 0

    def __init__(self, *args, **kwargs):
        LifecycleStateMixin.__init__(self, *args, autoinit=False, **kwargs)

    def on_init(self, *args, **kwargs):
        """
        Method to be overridden as neccessary by
        implementing service classes to perform
        initialization actions prior to service
        start.  Configuration parameters are
        accessible via the self.CFG dict.
        """

    def on_start(self, *args, **kwargs):
        """
        Method called at service startup.
        """

    def on_stop(self, *args, **kwargs):
        """
        Method called at service stop.
        """

    def on_quit(self, *args, **kwargs):
        """
        Method called at service quit.
        """

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
