#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.exception import BadRequest
from pyon.util.log import log
from pyon.util.containers import named_any
from pyon.util.context import LocalContextMixin

class BaseClients(object):
    """
    Basic object to hold clients for a service. Derived in implementations.
    Placeholder, may not need any functionality.
    """
    pass

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
        self._on_init()
        return self.on_init()

    def _on_init(self):
        """Framework hook to initialize"""

    def on_init(self):
        """
        Method to be overridden as necessary by implementing service classes to perform
        initialization actions prior to service start.  Configuration parameters are
        accessible via the self.CFG dict.
        """

    def start(self):
        self._on_start()
        return self.on_start()

    def _on_start(self):
        """Framework hook to start"""

    def on_start(self):
        """
        Method called at service startup.
        """

    def stop(self):
        res = self.on_stop()
        self._on_stop()
        return res

    def _on_stop(self):
        """Framework hook to stop"""

    def on_stop(self):
        """
        Method called at service stop. (May not be called if service is terminated immediately).
        """

    def quit(self):
        res = self.on_quit()
        self._on_quit()
        return res

    def _on_quit(self):
        """Framework hook to quit"""

    def on_quit(self):
        """
        Method called just before service termination.
        """

    def assert_condition(self, condition, errorstr):
        if not condition:
            raise BadRequest(errorstr)

    def __str__(self):
        return "".join((self.__class__.__name__,"(",
                        "name=", self._proc_name,
                        ",id=", self.id,
                        ",type=", self._proc_type,
                        ")"))

class MultiService():
    """
    A metaclass taking a list of service classes as an argument, returning a specializes class object
    that multiple inherits from the service classes. This way, more than one service can be combined.
    """
    pass


# Module variable keeping services
# TODO: Move to directory or container
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


