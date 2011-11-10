#!/usr/bin/env python

"""Part of the container that manages ION processes etc."""

__author__ = 'Michael Meisinger'

import os

from zope.interface import providedBy, implementedBy
from zope.interface import Interface, implements

from pyon.core.bootstrap import CFG
from pyon.service.service import BaseService, services_by_name
from pyon.net.endpoint import BinderListener, ProcessRPCServer, ProcessRPCClient
from pyon.net.messaging import IDPool
from pyon.service.service import add_service_by_name, get_service_by_name
from pyon.util.containers import DictModifier, DotDict, for_name, named_any
from pyon.util.log import log
from pyon.util.state_object import  LifecycleStateMixin

from pyon.ion.process import IonProcessSupervisor

class ProcManager(LifecycleStateMixin):
    def on_init(self, container, *args, **kwargs):
        self.container = container

        # Define the callables that can be added to Container public API
        self.container_api = [self.spawn_process]

        # Add the public callables to Container
        for call in self.container_api:
            setattr(self.container, call.__name__, call)

        self.proc_id_pool = IDPool()

        self.procs = {}


        # The pyon worker process supervisor
        self.proc_sup = IonProcessSupervisor(heartbeat_secs=CFG.cc.timeout.heartbeat)


    def on_start(self, *args, **kwargs):
        log.debug("ProcManager: start")

        self.proc_sup.start()

    def on_quit(self, *args, **kwargs):
        log.debug("ProcManager: quit")

        # Call quit on procs to give them ability to clean up
        for procname, proc in self.procs.iteritems():
            try:
                proc.quit()
            except Exception, ex:
                log.exception("Process %s quit failed" % procname)

        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)

    def spawn_process(self, name=None, module=None, cls=None, config=None):
        """
        Spawn a process within the container.
        """
        log.debug("AppManager.spawn_process(name=%s, module=%s, config=%s)" % (name, module, config))

        if config is None:
            config = DictModifier(CFG)

        log.debug("AppManager.spawn_process: for_name(mod=%s, cls=%s)" % (module, cls))
        process_instance = for_name(module, cls)
        assert isinstance(process_instance, BaseService), "Instantiated process not a BaseService %r" % process_instance

        # Prepare process instance
        process_instance.id = "%s.%s" % (self.container.id, self.proc_id_pool.get_id())
        process_instance.container = self.container

        # Inject dependencies
        process_instance.clients = DotDict()
        log.debug("AppManager.spawn_process dependencies: %s" % process_instance.dependencies)
        # TODO: Service dependency != process dependency
        for dependency in process_instance.dependencies:
            dependency_service = get_service_by_name(dependency)
            dependency_interface = list(implementedBy(dependency_service))[0]

            # @TODO: start_client call instead?
            client = ProcessRPCClient(node=self.container.node, name=dependency, iface=dependency_interface, process=process_instance)
            process_instance.clients[dependency] = client

        # Init process
        process_instance.CFG = config
        process_instance.init()

        # Add to global dict
        # TODO: This needs to go into the process list
        #add_service_by_name(name, process_instance)
        self.procs[name] = process_instance

        rsvc = ProcessRPCServer(node=self.container.node, name=name, service=process_instance, process=process_instance)

        # Service RPC endpoint
        # Start an ION process with the right kind of endpoint factory
        listener = BinderListener(self.container.node, name, rsvc, None, None)
        self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener)

        # Wait for app to spawn
        log.debug("Waiting for server %s listener ready", name)
        listener.get_ready_event().get()
        log.debug("Server %s listener ready", name)

        rsvc_proc = ProcessRPCServer(node=self.container.node, name=process_instance.id, service=process_instance, process=process_instance)

        # Process exclusive RPC endpoint
        # Start an ION process with the right kind of endpoint factory
        listener1 = BinderListener(self.container.node, process_instance.id, rsvc_proc, None, None)
        self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener1)

        # Wait for app to spawn
        log.debug("Waiting for server %s listener ready", process_instance.id)
        listener1.get_ready_event().get()
        log.debug("Server %s listener ready", process_instance.id)

        process_instance.start()
