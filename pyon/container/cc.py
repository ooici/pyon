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

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import os

from pyon.net.endpoint import RPCServer, RPCClient, BinderListener

from pyon.net import messaging
from pyon.core.bootstrap import CFG, sys_name, populate_registry
from pyon.service.service import add_service_by_name, get_service_by_name

from pyon.util.config import Config
from pyon.util.log import log
from pyon.util.containers import DictModifier, DotDict

from pyon.ion.process import IonProcessSupervisor

from zope.interface import providedBy
from zope.interface import Interface, implements

class IContainerAgent(Interface):

    def start_app(processapp=[], config={}):
        pass

    def start_rel(rel={}):
        pass

    def start_rel_from_url(rel_url=""):
        pass

class Container(object):
    implements(IContainerAgent)
    """
    The Capability Container. Its purpose is to spawn/monitor processes and services
    that do the bulk of the work in the ION system.
    """
    node = None
    name = "container_agent-%s-%d" % (sys_name, os.getpid())
    def __init__(self, *args, **kwargs):
        log.debug("Container.__init__")
        self.proc_sup = IonProcessSupervisor(heartbeat_secs=CFG.cc.timeout.heartbeat)

        # Keep track of the overrides from the command-line, so they can trump app/rel file data
        self.spawn_args = DictModifier(CFG, kwargs)

    def start(self):
        log.debug("In Container.start")

        # Bootstrap object registry
        populate_registry()

        self.proc_sup.start()
        self.node, self.ioloop = messaging.makeNode() # shortcut hack

        rsvc = RPCServer(node=self.node, name=self.name, service=self)

        # Start an ION process with the right kind of endpoint factory
        listener = BinderListener(self.node, self.name, rsvc, None, None)
        self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener)

        return listener.get_ready_event()

    def start_app(self, processapp=[], config={}):
        log.debug("In Container.start_app processapp: %s config: %s"%(str(processapp),str(config)))
        # Start process defined by processapp with specified config
        name, module, cls = processapp

        service_instance = self._for_name(module, cls)

        # Inject dependencies
        service_instance.clients = DotDict()
        log.debug("In Container.start_app dependencies: %s"%str(service_instance.dependencies))
        for dependency in service_instance.dependencies:
            dependency_service = get_service_by_name(dependency)
            dependency_interface = list(providedBy(dependency_service))[0]

            # @TODO: start_client call instead?
            client = RPCClient(node=self.node, name=dependency, iface=dependency_interface)
            service_instance.clients[dependency] = client

        # Init service
        service_instance.CFG = config
        service_instance.service_init()

        # Add to global dict
        add_service_by_name(name, service_instance)

        rsvc = RPCServer(node=self.node, name=name, service=service_instance)

        # Start an ION process with the right kind of endpoint factory
        listener = BinderListener(self.node, name, rsvc, None, None)
        self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener)

        # Wait for app to spawn
        log.debug("Waiting for server %s listener ready", name)
        listener.get_ready_event().get()
        log.debug("Server %s listener ready", name)

    def start_rel(self, rel={}):
        # Recurse over the rel and start apps defined there.
        log.debug("In Container.start_rel  rel: %s" % str(rel))

        for rel_app_cfg in rel.apps:
            name = rel_app_cfg.name
            log.debug("rel definition: %s" % str(rel_app_cfg))

            app_file_path = ['res/apps/' + name + '.app']
            app_file_cfg = Config(app_file_path).data
            log.debug("app file definition: %s" % str(app_file_cfg))

            # Overlay app file and rel config as appropriate
            config = DictModifier(CFG)
            if 'config' in app_file_cfg:
                # Apply config from app file
                app_file_cfg = DotDict(app_file_cfg.config)
                config.update(app_file_cfg)

            if 'config' in rel_app_cfg:
                # Nest dict modifier and apply config from rel file
                config = DictModifier(config, rel_app_cfg.config)

            if 'processapp' in rel_app_cfg:
                processapp = rel_app_cfg.processapp
            else:
                processapp = app_file_cfg.processapp

            self.start_app(processapp, config)

    def start_rel_from_url(self, rel_url=""):
        # Read the rel file and call start_rel
        log.debug("In Container.start_rel_from_url  rel_url: %s" % str(rel_url))
        rel = Config([rel_url]).data
        self.start_rel(rel)

    def stop(self):
        log.debug("In Container.stop")
        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)

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
            
    def _for_name(self, modpath, classname):
        ''' Returns a class of "classname" from module "modname". '''
        log.debug("In Container._forname")
        log.debug("modpath: %s" % modpath)
        log.debug("classname: %s" % classname)
        module = __import__(modpath, fromlist=[classname])
        classobj = getattr(module, classname)
        return classobj()
