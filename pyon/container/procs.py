#!/usr/bin/env python

"""Part of the container that manages ION processes etc."""

__author__ = 'Michael Meisinger'

from zope.interface import providedBy, implementedBy
from zope.interface import Interface, implements

from pyon.core.bootstrap import CFG
from pyon.ion.process import IonProcessSupervisor
from pyon.net.channel import PubSub
from pyon.net.endpoint import BinderListener, ProcessRPCServer, ProcessRPCClient, Subscriber
from pyon.net.messaging import IDPool
from pyon.service.service import BaseService, get_service_by_name
from pyon.util.containers import DictModifier, DotDict, for_name
from pyon.util.log import log


class ProcManager(object):
    def __init__(self, container):
        self.container = container

        # Define the callables that can be added to Container public API
        self.container_api = [self.spawn_process]

        # Add the public callables to Container
        for call in self.container_api:
            setattr(self.container, call.__name__, call)

        self.proc_id_pool = IDPool()

        # Temporary registry of running processes
        self.procs = {}

        # The pyon worker process supervisor
        self.proc_sup = IonProcessSupervisor(heartbeat_secs=CFG.cc.timeout.heartbeat)

    def start(self):
        log.debug("ProcManager: start")

        self.proc_sup.start()

    def stop(self):
        log.debug("ProcManager: stop")

        # Call quit on procs to give them ability to clean up
        for procname, proc in self.procs.iteritems():
            try:
                # These are service processes with full life cycle
                proc.quit()
            except Exception, ex:
                log.exception("Process %s quit failed" % procname)

        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)

    def spawn_process(self, name=None, module=None, cls=None, config=None):
        """
        Spawn a process within the container.
        """
        log.debug("AppManager.spawn_process(name=%s, module=%s)" % (name, module))

        if config is None:
            config = DictModifier(CFG)

        errcause = "instantiating service"
        try:
            log.debug("AppManager.spawn_process: for_name(mod=%s, cls=%s)" % (module, cls))
            process_instance = for_name(module, cls)
            assert isinstance(process_instance, BaseService), "Instantiated process not a BaseService %r" % process_instance

            # Prepare process instance
            process_instance.id = "%s.%s" % (self.container.id, self.proc_id_pool.get_id())
            process_instance.container = self.container
            process_instance.CFG = config

            # Set dependencies (clients)
            errcause = "setting service dependencies"
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
            errcause = "initializing service"
            process_instance.init()

            # Add to process dict
            self.procs[name] = process_instance
            errcause = "setting process messaging endpoints"

            process_type = config.get("process",{}).get("type", "service")
            listen_name = config.get("process",{}).get("listen_name", name)

            if process_type == "service":
                # Service RPC endpoint
                rsvc = ProcessRPCServer(node=self.container.node, name=name, service=process_instance, process=process_instance)
                # Start an ION process with the right kind of endpoint factory
                listener = BinderListener(self.container.node, listen_name, rsvc, None, None)
                self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener)
                # Wait for app to spawn
                listener.get_ready_event().get()
                log.debug("Process %s service listener ready: %s", name, listen_name)

            elif process_type == "stream_process":
                # Start pubsub listener
                sub = Subscriber(node=self.container.node, name=listen_name,
                                 callback=lambda m,h: process_instance.process(m))
                listener = BinderListener(self.container.node, listen_name, sub, PubSub, None)
                self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener)
                # Wait for app to spawn
                listener.get_ready_event().get()
                log.debug("Process %s stream listener ready: %s", name, listen_name)

            elif process_type == "agent":
                # TODO: Determine special treatment of agents
                pass

            elif process_type == "immediate":
                # One off process. No extra listeners
                pass

            elif process_type == "simple":
                # In this case we don't want any extra listeners
                pass

            else:
                raise Exception("Unknown process type: %s" % process_type)

            # Process exclusive RPC endpoint
            rsvc_proc = ProcessRPCServer(node=self.container.node, name=process_instance.id, service=process_instance, process=process_instance)
            # Start an ION process with the right kind of endpoint factory
            # TODO: Don't start in its own Greenlet!
            listener1 = BinderListener(self.container.node, process_instance.id, rsvc_proc, None, None)
            self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener1)
            # Wait for app to spawn
            listener1.get_ready_event().get()
            log.debug("Process %s pid listener ready: %s", name, process_instance.id)

            errcause = "registering"
            self.container.directory.register("/Containers/%s/Processes" % self.container.id, process_instance.id, name=name)

            errcause = "starting service"
            process_instance.start()

            log.info("AppManager.spawn_process: %s.%s -> id=%s OK" % (module, cls, process_instance.id))
            return True
        except Exception as ex:
            log.exception("Error %s for process: %s.%s" % (errcause, module, cls))
            return False
