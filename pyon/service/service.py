#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.util.state_object import LifecycleStateMixin
from pyon.util.containers import named_any
from pyon.util.context import LocalContextMixin

class BaseService(LifecycleStateMixin, LocalContextMixin):
    """
    A process class that provides a 'service'.
    Not dependent on messaging.
    """

    name = None
    running = 0

    def __init__(self, *args, **kwargs):
        LifecycleStateMixin.__init__(self, *args, autoinit=False, **kwargs)
        LocalContextMixin.__init__(self)

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

def load_service_mods(path):
    import pkgutil
    import string
    mod_prefix = string.replace(path, "/", ".")

    for mod_imp, mod_name, is_pkg in pkgutil.iter_modules([path]):
        if is_pkg:
            load_service_mods(path+"/"+mod_name)
        else:
            mod_qual = "%s.%s" % (mod_prefix, mod_name)
            #print "Import", mod_qual
            try:
                named_any(mod_qual)
            except Exception, ex:
                log.warning("Import module '%s' failed: %s" % (mod_qual, ex))

def build_service_map():
    global services_by_name

    for cls in BaseService.__subclasses__():
        assert hasattr(cls,'name'), 'Service class must define name value. Service class in error: %s' % cls
        services_by_name[cls.name] = cls

def add_service_by_name(name, service):
    services_by_name[name] = service

def get_service_by_name(name):
    if name in services_by_name:
        return services_by_name[name]
    else:
        return None

load_service_mods('interface/services')
build_service_map()

