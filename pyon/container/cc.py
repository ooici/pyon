#!/usr/bin/env python
"""
TODO:
[ ] server and client name argument is a short cut
[ ] generic server and client delivery loop
[ ] decide on how Channel Type is passed/associated with gen server/client
[ ] Endpoint might be better as a 'factory' that can make handler instances
per request. This will also facilitate the Endpoint holding 'business'
objects/resources that each request has access to. This will keep the
actual handlers functional. 
"""
from pyon.net.endpoint import RPCServer, RPCClient, BinderListener

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from zope.interface import providedBy

from pyon.public import CFG, SERVICE_CFG, messaging, channel, GreenProcessSupervisor
from pyon.service.service import add_service_by_name, get_service_by_name

from pyon.util.log import log
from pyon.util.containers import DotDict

class Container(object):
    """
    The Capability Container. Its purpose is to spawn/monitor processes and services
    that do the bulk of the work in the ION system.
    """
    node = None
    def __init__(self, *args, **kwargs):
        self.proc_sup = GreenProcessSupervisor()

    def start(self, server=True):
        log.debug("In Container.start")
        log.debug("server: %s" % str(server))
        self.proc_sup.start() 
        self.node, self.ioloop = messaging.makeNode() # shortcut hack
        self.proc_sup.spawn('green', self.ioloop.join)

        if server == True:
            # Read the config file and start services defined there
            # TODO likely should be done elsewhere
            service_names = self.readConfig()
            log.debug("service_names: %s" % str(service_names))

            # Iterate over service name list, starting services
            for serviceName in service_names:
                log.debug("serviceName: %s" % str(serviceName))
                self.start_service(serviceName)

    def readConfig(self):
        log.debug("In Container.readConfig")
        # Loop through configured services and start them
        services = SERVICE_CFG['apps']
        # Return value.  Will contain list of
        # service names from the config file
        service_names = []
        for service_def in services:
            log.debug("service_def: %s" % str(service_def))
            name = service_def["name"]

            config_params = {}
            if service_def.has_key("config"):
                config_params = service_def["config"]

            # Service is described in processapp tuple
            # Field 1 is the module name
            # Field 2 is the class name
            module = service_def["processapp"][1]
            cls = service_def["processapp"][2]

            service_instance = self.forname(module, cls, config_params)

            # Inject dependencies
            service_instance.clients = DotDict()
            for dependency in service_instance.dependencies:
                dependency_service = get_service_by_name(dependency)
                dependency_interface = list(providedBy(dependency_service))[0]

                # @TODO: start_client call instead?
                client = RPCClient(node=self.node, name=dependency, iface=dependency_interface)
                service_instance.clients[dependency] = client

            # Add to global dict
            add_service_by_name(name, service_instance)

            service_names.append(name)

        return service_names

    def forname(self, modpath, classname, config_params={}):
        ''' Returns a class of "classname" from module "modname". '''
        log.debug("In Container.forname")
        log.debug("modpath: %s" % modpath)
        log.debug("classname: %s" % classname)
        log.debug("config_params: %s" % str(config_params))
        firstTime = True
        module = __import__(modpath, fromlist=[classname])
        classobj = getattr(module, classname)
        return classobj(config_params)


    def stop(self):
        log.debug("In Container.stop")
        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)

    def start_service(self, name):
        log.debug("In Container.start_service")
        log.debug("name: %s" % name)

        svc = get_service_by_name(name)
        rsvc = RPCServer(node=self.node, name=name, service=svc)

        # @TODO: this commented out line makes each request handler spawn in a proc_sup managed greenlet
        #listener = BinderListener(self.node, name, rsvc, None, lambda cb, *args: self.proc_sup.spawn('green', cb, *args))
        listener = BinderListener(self.node, name, rsvc, None, None)
        self.proc_sup.spawn('green', listener.listen)

    def serve_forever(self):
        log.debug("In Container.serve_forever")
        if not self.proc_sup.running:
            #self.start()
            pass
        self.proc_sup.join_children()
