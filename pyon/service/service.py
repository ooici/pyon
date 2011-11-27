#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.util.containers import named_any
from pyon.util.context import LocalContextMixin

class BaseService(LocalContextMixin):
    """
    Base class providing a 'service'. Pure Python class. Not dependent on messaging.
    Such services can be executed by ION processes.
    """

    # The following are set one per implementation (class)
    name = None
    running = 0
    dependencies = []

    def __init__(self, *args, **kwargs):
        self.id = None
        self._proc_name = None
        self._proc_type = None
        self.errcause = None
        self.container = None
        self.CFG = None
        super(BaseService, self).__init__()

    def init(self):
        return self.on_init()

    def on_init(self):
        """
        Method to be overridden as necessary by implementing service classes to perform
        initialization actions prior to service start.  Configuration parameters are
        accessible via the self.CFG dict.
        """

    def start(self):
        return self.on_start()

    def on_start(self):
        """
        Method called at service startup.
        """

    def stop(self):
        return self.on_stop()

    def on_stop(self):
        """
        Method called at service stop. (May not be called if service is terminated immediately).
        """

    def quit(self):
        return self.on_quit()

    def on_quit(self):
        """
        Method called just before service termination.
        """

    def __str__(self):
        return "".join((self.__class__.__name__,"(",
                        "name=", self._proc_name,
                        ",id=", self.id,
                        ",type=", self._proc_type,
                        ")"))

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


