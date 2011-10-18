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

from pyon.net import messaging, channel
from pyon.core.bootstrap import CFG
from pyon.service.service import add_service_by_name, get_service_by_name

from pyon.util.config import Config
from pyon.util.log import log
from pyon.util.containers import DictModifier, DotDict

from pyon.ion.process import IonProcessSupervisor

from zope.interface import providedBy

class Container(object):
    """
    The Capability Container. Its purpose is to spawn/monitor processes and services
    that do the bulk of the work in the ION system.
    """
    node = None
    def __init__(self, *args, **kwargs):
        log.debug("Container.__init__")
        self.proc_sup = IonProcessSupervisor(heartbeat_secs=CFG.cc.timeout.heartbeat)

        # Keep track of the overrides from the command-line, so they can trump app/rel file data
        self.spawn_args = DictModifier(CFG, kwargs)

    def start(self, server=True):
        log.debug("In Container.start")
        log.debug("server: %s" % str(server))
        self.proc_sup.start() 
        self.node, self.ioloop = messaging.makeNode() # shortcut hack
        self.proc_sup.spawn(('green', self.ioloop.join))

    def start_rel(self, rel_file):
        # Read the config file and start services defined there.
        # Saving the current rel block in CFG.deploy, not sure I like this. - Adam

        rel_data = Config([rel_file]).data
        CFG.deploy = rel_data.deploy

        server_listen_ready_list = []

        service_names = self.read_config()
        log.debug("service_names: %s" % str(service_names))

        # Iterate over service name list, starting services
        for serviceName in service_names:
            log.debug("serviceName: %s" % str(serviceName))
            listen_ready = self.start_service(serviceName)
            server_listen_ready_list.append(listen_ready)

        return server_listen_ready_list

    def read_config(self):
        log.debug("In Container.readConfig")
        # Loop through configured services and start them
        services = CFG.deploy.apps
        # Return value.  Will contain list of
        # service names from the config file
        service_names = []
        for service_def in services:
            name = service_def.name

            # TODO fix this
            # For now service is described in processapp tuple in rel file
            # Field 1 is the module name
            # Field 2 is the class name
            module, cls = service_def.processapp

            service_instance = self.forname(module, cls)

            # Inject dependencies
            service_instance.clients = DotDict()
            for dependency in service_instance.dependencies:
                dependency_service = get_service_by_name(dependency)
                dependency_interface = list(providedBy(dependency_service))[0]

                # @TODO: start_client call instead?
                client = RPCClient(node=self.node, name=dependency, iface=dependency_interface)
                service_instance.clients[dependency] = client

            # Call method to blend config values
            service_config = self.get_service_config(name)
            service_instance.CFG = service_config

            # Call method to allow service to self-init
            service_instance.service_init()

            # Add to global dict
            add_service_by_name(name, service_instance)

            service_names.append(name)

        return service_names

    def forname(self, modpath, classname):
        ''' Returns a class of "classname" from module "modname". '''
        log.debug("In Container.forname")
        log.debug("modpath: %s" % modpath)
        log.debug("classname: %s" % classname)
        module = __import__(modpath, fromlist=[classname])
        classobj = getattr(module, classname)
        return classobj()

    def get_service_config(self, appname):
        # Base is global config
        cfg_dict = DictModifier(CFG)

        app_path = ['res/apps/' + appname + '.app']
        app_cfg = Config(app_path).data
        if 'config' in app_cfg:
            # Apply config from app file
            app_cfg_dict = DotDict(app_cfg.config)
            cfg_dict.update(app_cfg_dict)

        # Find service definition in rel file
        for app_def in CFG.deploy.apps:
            if app_def.name == appname:
                rel_def = app_def
                break
        if 'config' in rel_def:
            # Nest dict modifier and apply config from rel file
            cfg_dict = DictModifier(cfg_dict, rel_def.config)

        if self.spawn_args:
            # Nest dict modifier and apply config from spawn args
            cfg_dict = DictModifier(cfg_dict, self.spawn_args)

        return cfg_dict

    def stop(self):
        log.debug("In Container.stop")
        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)

    def start_service(self, name):
        log.debug("In Container.start_service")
        log.debug("name: %s" % name)

        svc = get_service_by_name(name)
        rsvc = RPCServer(node=self.node, name=name, service=svc)

        # Start an ION process with the right kind of endpoint factory
        listener = BinderListener(self.node, name, rsvc, None, None)
        self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener)

        return listener.get_ready_event()

    def serve_forever(self):
        """ Run the container until killed. """
        
        log.debug("In Container.serve_forever")
        
        if not self.proc_sup.running:
            self.start()
            
        try:
            self.proc_sup.join_children()
        except (KeyboardInterrupt, SystemExit) as ex:
            log.info('Received a kill signal, shutting down the container.')
        except:
            log.exception('Unhandled error! Forcing container shutdown')

        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)
            
