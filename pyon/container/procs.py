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
        self.procs_by_name = {}
        self.procs = {}

        # The pyon worker process supervisor
        self.proc_sup = IonProcessSupervisor(heartbeat_secs=CFG.cc.timeout.heartbeat)

    def start(self):
        log.debug("ProcManager starting ...")
        self.proc_sup.start()
        log.debug("ProcManager started, OK.")

    def stop(self):
        log.debug("ProcManager stopping ...")

        # Call quit on procs to give them ability to clean up
        # TODO: This can be done concurrently
        for procid, proc in self.procs.iteritems():
            try:
                # These are service processes with full life cycle
                proc.quit()
            except Exception, ex:
                log.exception("Process %s quit failed" % procid)

        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)
        log.debug("ProcManager stopped, OK.")

    def spawn_process(self, name=None, module=None, cls=None, config=None, process_type=None):
        """
        Spawn a process within the container. Processes can be of different type.
        """
        # Generate a new process id
        # TODO: Ensure it is system-wide unique
        process_id = str(self.proc_id_pool.get_id())
        log.debug("ProcManager.spawn_process(name=%s, module.cls=%s.%s) as pid=%s" % (name, module, cls, process_id))

        if config is None:
            config = DictModifier(CFG)

        log.debug("spawn_process() pid=%s config=%s", process_id, config)

        # PROCESS TYPE.
        # One of: service, stream_process, agent, simple, immediate
        process_type = process_type or config.get("process",{}).get("type", "service")

        service_instance = None
        try:
            # spawn service by type
            if process_type == "service":
                service_instance = self._spawn_service_process(process_id, name, module, cls, config)

            elif process_type == "stream_process":
                service_instance = self._spawn_stream_process(process_id, name, module, cls, config)

            elif process_type == "agent":
                service_instance = self._spawn_agent_process(process_id, name, module, cls, config)

            elif process_type == "immediate":
                service_instance = self._spawn_immediate_process(process_id, name, module, cls, config)

            elif process_type == "simple":
                service_instance = self._spawn_simple_process(process_id, name, module, cls, config)

            else:
                raise Exception("Unknown process type: %s" % process_type)

            service_instance._proc_type = process_type
            self._register_process(service_instance, name)
            
            service_instance.errcause = "OK"
            log.info("AppManager.spawn_process: %s.%s -> pid=%s OK" % (module, cls, process_id))
            return True
        
        except Exception as ex:
            errcause = service_instance.errcause if service_instance else "instantiating service"
            log.exception("Error spawning process %s: %s" % (process_id, errcause))
            return False

    def _spawn_service_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as a service worker.
        Attach to service queue with service definition, attach to service pid
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)
        self._service_init(service_instance)
        listen_name = config.get("process",{}).get("listen_name", name)
        print "**********", name, listen_name
        self._set_service_endpoint(service_instance, listen_name)
        self._set_service_endpoint(service_instance, service_instance.id)
        self._service_start(service_instance)
        return service_instance

    def _spawn_stream_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as a data stream process.
        Attach to subscription queue with process function.
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)
        self._service_init(service_instance)
        listen_name = config.get("process",{}).get("listen_name", name)
        self._set_subscription_endpoint(service_instance, listen_name)
        self._service_start(service_instance)
        return service_instance

    def _spawn_agent_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as agent process.
        Attach to service pid.
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)
        self._service_init(service_instance)
        self._set_service_endpoint(service_instance, service_instance.id)
        self._service_start(service_instance)
        return service_instance

    def _spawn_simple_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as simple process.
        No attachments.
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)
        self._service_init(service_instance)
        self._service_start(service_instance)
        return service_instance

    def _spawn_immediate_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as immediate one off process.
        No attachments.
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)
        self._service_init(service_instance)
        self._service_start(service_instance)
        return service_instance

    def _create_service_instance(self, process_id, name, module, cls, config):
        # SERVICE INSTANCE.
        service_instance = for_name(module, cls)
        assert isinstance(service_instance, BaseService), "Instantiated service not a BaseService %r" % service_instance

        # Prepare service instance
        service_instance.errcause = ""
        service_instance.id = "%s.%s" % (self.container.id, process_id)
        service_instance.container = self.container
        service_instance.CFG = config
        service_instance._proc_name = name

        # Set service dependencies (RPC clients)
        self._set_service_dependencies(service_instance)
        
        return service_instance

    def _set_service_dependencies(self, service_instance):
        service_instance.errcause = "setting service dependencies"
        service_instance.clients = DotDict()
        log.debug("spawn_process dependencies: %s" % service_instance.dependencies)
        # TODO: Service dependency != process dependency
        for dependency in service_instance.dependencies:
            dependency_service = get_service_by_name(dependency)
            dependency_interface = list(implementedBy(dependency_service))[0]

            # @TODO: start_client call instead?
            client = ProcessRPCClient(node=self.container.node, name=dependency, iface=dependency_interface, process=service_instance)
            service_instance.clients[dependency] = client

    def _service_init(self, service_instance):
        # Init process
        service_instance.errcause = "initializing service"
        service_instance.init()

    def _service_start(self, service_instance):
        # Start process
        # TODO: Check for timeout
        service_instance.errcause = "starting service"
        service_instance.start()

    def _set_service_endpoint(self, service_instance, listen_name):
        service_instance.errcause = "setting process service endpoint"

        # Service RPC endpoint
        rsvc = ProcessRPCServer(node=self.container.node,
                                name=listen_name,
                                service=service_instance,
                                process=service_instance)
        # Start an ION process with the right kind of endpoint factory
        listener = BinderListener(self.container.node, listen_name, rsvc, None, None)
        self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener, name=listen_name)
        # Wait for app to spawn
        listener.get_ready_event().get()
        log.debug("Process %s service listener ready: %s", service_instance.id, listen_name)

    def _set_subscription_endpoint(self, service_instance, listen_name):
        service_instance.errcause = "setting process subscription endpoint"

        # Start pubsub listener
        # TODO: Use Refactored ION endpoint for streams once ready.
        sub = Subscriber(node=self.container.node,
                         name=listen_name,
                         callback=lambda m,h: service_instance.process(m))
        listener = BinderListener(self.container.node, listen_name, sub, PubSub, None)
        self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener, name=listen_name)
        # Wait for app to spawn
        listener.get_ready_event().get()
        log.debug("Process %s stream listener ready: %s", service_instance.id, listen_name)

    def _register_process(self, service_instance, name):
        # Add to local process dict
        self.procs_by_name[name] = service_instance
        self.procs[service_instance.id] = service_instance

        # Add to directory
        service_instance.errcause = "registering"
        self.container.directory.register("/Containers/%s/Processes" % self.container.id,
                                          service_instance.id, name=name)

    def terminate_process(self, process_id):
        service_instance = self.procs.get(process_id, None)
        if not service_instance: return

        service_instance.quit()
        # TODO: Cleanup messaging attachments

        del self.procs[process_id]
