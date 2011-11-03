#!/usr/bin/env python

"""Part of the container that manages rels, apps, processes etc."""

__author__ = 'Michael Meisinger'

from zope.interface import providedBy
from zope.interface import Interface, implements

from pyon.core.bootstrap import CFG
from pyon.net.endpoint import BinderListener, ProcessRPCServer, ProcessRPCClient
from pyon.service.service import add_service_by_name, get_service_by_name
from pyon.util.config import Config
from pyon.util.containers import DictModifier, DotDict, for_name
from pyon.util.log import log
from pyon.util.state_object import  LifecycleStateMixin

class AppManager(LifecycleStateMixin):
    def on_init(self, container, *args, **kwargs):
        self.container = container

        # Define the callables that can be added to Container public API
        self.container_api = [self.spawn_process,
                              self.start_app,
                              self.start_app_from_url,
                              self.start_rel,
                              self.start_rel_from_url]

        # Add the public callables to Container
        for call in self.container_api:
            setattr(self.container, call.__name__, call)

        self.apps = {}

    def on_start(self, *args, **kwargs):
        log.debug("AppManager: start")

    def start_rel_from_url(self, rel_url=""):
        """
        @brief Read the rel file and call start_rel
        """
        log.debug("In AppManager.start_rel_from_url  rel_url: %s" % str(rel_url))
        # TODO: Catch URL not exist error
        rel = Config([rel_url]).data
        self.start_rel(rel)

    def start_rel(self, rel=None):
        """
        @brief Recurse over the rel and start apps defined there.
        Note: apps in a rel file can come in one of 2 forms:
        1 processapp: In-line defined process to be started as app
        2 app file: Reference to an app definition in an app file
        """
        log.debug("In AppManager.start_rel  rel: %s" % str(rel))

        if rel is None: rel = {}

        for rel_app_cfg in rel.apps:
            name = rel_app_cfg.name
            log.debug("app definition in rel: %s" % str(rel_app_cfg))

            if 'processapp' in rel_app_cfg:
                # Case 1: Rel contains definition of process to start as app
                name, module, cls = rel_app_cfg.processapp

                if 'config' in rel_app_cfg:
                    # Nest dict modifier and apply config from rel file
                    config = DictModifier(CFG, rel_app_cfg.config)
                else:
                    config = DictModifier(CFG)

                self.spawn_process(name, module, cls, config)
                self.apps[name] = rel_app_cfg.processapp

            else:
                # Case 2: Rel contains reference to app file to start
                app_file_path = 'res/apps/%s.yml' % (name)
                self.start_app_from_url(app_file_path, config=rel_app_cfg.get('config', None))

    def start_app_from_url(self, app_url="", config=None):
        """
        @brief Read the app file and call start_app
        """
        log.debug("In AppManager.start_app_from_url  app_url: %s" % app_url)
        # TODO: Catch URL not exist error
        app = Config([app_url]).data
        self.start_app(appdef=app, config=config)

    def start_app(self, appdef=None, config=None):
        """
        @brief Start an app from an app definition.
        Note: apps can come in one of 2 variants:
        1 processapp: In-line defined process to be started
        2 regular app: Full app definition
        """
        log.debug("app file definition: %s" % appdef)

        app_config = DictModifier(CFG)

        if 'config' in appdef:
            # Apply config from app file
            app_file_cfg = DotDict(appdef.config)
            app_config.update(app_file_cfg)

        if config:
            # Nest dict modifier and apply config from rel file
            app_config = DictModifier(app_config, config)

        if 'processapp' in appdef:
            # Case 1: Appdef contains definition of process to start
            name, module, cls = appdef.processapp

            self.spawn_process(name, module, cls, app_config)
            self.apps[name] = appdef.processapp
        else:
            # Case 2: Appdef contains full app start params
            raise NotImplementedError("Cannot start app from appdef yet: %s" % (appdef))

    def spawn_process(self, name=None, module=None, cls=None, config=None):
        """
        Spawn a process locally.
        """
        log.debug("In AppManager.spawn_process(name=%s, module=%s, config=%s)" % (name, module, config))

        # TODO: Process should get its own immutable copy of config, no matter what
        if config is None: config = DictModifier(CFG)

        log.debug("In AppManager.spawn_process: for_name(mod=%s, cls=%s)" % (module, cls))
        process_instance = for_name(module, cls)
        # TODO: Check that this is a proper instance (interface)

        # Inject dependencies
        process_instance.clients = DotDict()
        log.debug("In AppManager.spawn_process dependencies: %s" % process_instance.dependencies)
        for dependency in process_instance.dependencies:
            dependency_service = get_service_by_name(dependency)
            dependency_interface = list(providedBy(dependency_service))[0]

            # @TODO: start_client call instead?
            client = ProcessRPCClient(node=self.container.node, name=dependency, iface=dependency_interface, process=process_instance)
            process_instance.clients[dependency] = client

        # Init process
        process_instance.CFG = config
        process_instance.service_init()

        # Add to global dict
        # TODO: This needs to go into the process list
        add_service_by_name(name, process_instance)

        rsvc = ProcessRPCServer(node=self.container.node, name=name, service=process_instance, process=process_instance)

        # Start an ION process with the right kind of endpoint factory
        listener = BinderListener(self.container.node, name, rsvc, None, None)
        self.container.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener)

        # Wait for app to spawn
        log.debug("Waiting for server %s listener ready", name)
        listener.get_ready_event().get()
        log.debug("Server %s listener ready", name)
