#!/usr/bin/env python

"""Mechanisms for ION services and service management infrastructure"""

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

from zope.interface import implementedBy

from pyon.core.exception import BadRequest
from pyon.util.log import log
from pyon.util.containers import named_any, itersubclasses
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
    running = False
    dependencies = []
    process_type = "service"

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
        self.running = True

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
        self.running = False

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
        self.running = False

    def on_quit(self):
        """
        Method called just before service termination.
        """

    def assert_condition(self, condition, errorstr):
        if not condition:
            raise BadRequest(errorstr)

    def __str__(self):
        proc_name = 'Unknown proc_name' if self._proc_name is None else self._proc_name
        proc_type = 'Unknown proc_type' if self._proc_type is None else self._proc_type
        return "".join((self.__class__.__name__,"(",
                        "name=", proc_name,
                        ",id=", self.id,
                        ",type=", proc_type,
                        ")"))

# -----------------------------------------------------------------------------------------------
# Service management infrastructure

class IonServiceDefinition(object):
    """
    Provides a walkable structure for ION service metadata and object definitions.
    """
    def __init__(self, name, dependencies=[], version=''):
        self.name = name
        self.dependencies = list(dependencies)
        self.version = version
        self.operations = []

        # Points to service (Zope) interface
        self.interface = None

        # Points to abstract base class
        self.base = None

        # Points to implementation class
        self.impl = []

        # Points to process client class
        self.client = None

        # Points to non-process client class
        self.simple_client = None

    def __str__(self):
        return "IonServiceDefinition(name=%s):%s" % (self.name, self.__dict__)

    def __repr__(self):
        return str(self)

class IonServiceOperation(object):
    def __init__(self, name):
        self.name = name
        self.docstring = ''
        self.in_object_type = None
        self.out_object_type = None
        self.throws = []

    def __str__(self):
        return "IonServiceOperation(name=%s):%s" % (self.name, self.__dict__)

    def __repr__(self):
        return str(self)

class IonServiceRegistry(object):
    def __init__(self):
        self.services = {}
        self.services_by_name = {}
        self.classes_loaded = False
        self.operations = None

    def add_servicedef_entry(self, name, key, value, append=False):
        if not name:
            #log.warning("No name for key=%s, value=%s" % (key, value))
            return

        if not name in self.services:
            svc_def = IonServiceDefinition(name)
            self.services[name] = svc_def
        else:
            svc_def = self.services[name]

        oldvalue = getattr(svc_def, key, None)
        if oldvalue is not None:
            if append:
                assert type(oldvalue) is list, "Cannot append to non-list: %s" % oldvalue
                oldvalue.append(value)
            else:
                log.warning("Service %s, key=%s exists. Old=%s, new=%s" % (name, key, getattr(svc_def, key), value))

        if not append:
            setattr(svc_def, key, value)

    @classmethod
    def load_service_mods(cls, path):
        import pkgutil
        import string
        mod_prefix = string.replace(path, "/", ".")

        for mod_imp, mod_name, is_pkg in pkgutil.iter_modules([path]):
            if is_pkg:
                cls.load_service_mods(path+"/"+mod_name)
            else:
                mod_qual = "%s.%s" % (mod_prefix, mod_name)
                #print "Import", mod_qual
                try:
                    named_any(mod_qual)
                except Exception, ex:
                    log.warning("Import module '%s' failed: %s" % (mod_qual, ex))


    def build_service_map(self):
        """
        Adds all known service definitions to service registry.
        @todo: May be a bit fragile due to using BaseService.__subclasses__
        """
        for cls in BaseService.__subclasses__():
            assert hasattr(cls,'name'), 'Service class must define name value. Service class in error: %s' % cls
            if cls.name:
                self.services_by_name[cls.name] = cls
                self.add_servicedef_entry(cls.name, "base", cls)
                interfaces = list(implementedBy(cls))
                if interfaces:
                    self.add_servicedef_entry(cls.name, "interface", interfaces[0])
                if cls.__name__.startswith("Base"):
                    try:
                        client = "%s.%sProcessClient" % (cls.__module__, cls.__name__[4:])
                        self.add_servicedef_entry(cls.name, "client", named_any(client))
                        sclient = "%s.%sClient" % (cls.__module__, cls.__name__[4:])
                        self.add_servicedef_entry(cls.name, "simple_client", named_any(sclient))
                    except Exception, ex:
                        log.warning("Cannot find client for service %s" % (cls.name))

    def discover_service_classes(self):
        """
        Walk implementation directories and find service implementation classes.
        @todo Only works for ion packages and submodules
        """
        IonServiceRegistry.load_service_mods("ion")

        sclasses = [s for s in itersubclasses(BaseService) if not s.__subclasses__()]

        for scls in sclasses:
            self.add_servicedef_entry(scls.name, "impl", scls, append=True)

        self.classes_loaded = True

    def get_service_base(self, name):
        """
        Returns the service base class with interface for the given service name or None.
        """
        if name in self.services:
            return getattr(self.services[name], 'base', None)
        else:
            return None

    def get_service_by_name(self, name):
        """
        Returns the service definition for the given service name or None.
        """
        if name in self.services:
            return self.services[name]
        else:
            return None



