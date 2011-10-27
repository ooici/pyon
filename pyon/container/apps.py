#!/usr/bin/env python

"""Part of the container that manages rels, apps, processes etc."""

__author__ = 'Michael Meisinger'

from pyon.core.bootstrap import CFG
from pyon.net.endpoint import RPCServer, RPCClient, BinderListener
from pyon.service.service import add_service_by_name, get_service_by_name
from pyon.util.config import Config
from pyon.util.containers import DictModifier, DotDict, for_name
from pyon.util.log import log

from zope.interface import providedBy
from zope.interface import Interface, implements

class AppManager(object):
    def __init__(self, container):
        self.container = container

        # Define the callables that can be added to Container public API
        self.container_api = [self.spawn_process,
                              self.start_app,
                              self.start_app_from_url,
                              self.start_rel,
                              self.start_rel_from_url]
    def start(self):
        pass

    def start_app_from_url(self, app_url=""):
        """
        @brief Read the app file and call start_app
        """
        log.debug("In Container.start_app_from_url  app_url: %s" % app_url)
        app = Config([app_url]).data
        self.start_app(appdef=app)

    def start_app(self, appdef=None, processapp=None, config=None):
        if processapp:

            # Start process defined by processapp with specified config
            name, module, cls = processapp
            self.spawn_process(name, module, cls, config)

        else:
            # TODO: App file case
            log.error("Cannot start app from appdef: %s" % (appdef))

    def spawn_process(self, name=None, module=None, cls=None, config=None):
        """
        Spawn a process locally.
        """
        log.debug("In AppManager.spawn_process(name=%s, module=%s, config=%s)" % (name, module, config))

        # TODO: Process should get its own immutable copy of config, no matter what
        if config is None: config = {}

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
            client = RPCClient(node=self.container.node, name=dependency, iface=dependency_interface)
            process_instance.clients[dependency] = client

        # Init process
        process_instance.CFG = config
        process_instance.service_init()

        # Add to global dict
        add_service_by_name(name, process_instance)

        rsvc = RPCServer(node=self.container.node, name=name, service=process_instance)

        # Start an ION process with the right kind of endpoint factory
        listener = BinderListener(self.container.node, name, rsvc, None, None)
        self.container.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener)

        # Wait for app to spawn
        log.debug("Waiting for server %s listener ready", name)
        listener.get_ready_event().get()
        log.debug("Server %s listener ready", name)


    def start_rel(self, rel=None):
        """
        @brief Recurse over the rel and start apps defined there.
        """
        log.debug("In AppManager.start_rel  rel: %s" % str(rel))

        if rel is None: rel = {}

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

            self.start_app(processapp=processapp, config=config)

    def start_rel_from_url(self, rel_url=""):
        """
        @brief Read the rel file and call start_rel
        """
        log.debug("In AppManager.start_rel_from_url  rel_url: %s" % str(rel_url))
        rel = Config([rel_url]).data
        self.start_rel(rel)

