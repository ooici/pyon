#!/usr/bin/env python

"""Part of the container that manages ION processes etc."""
from pyon.core import exception

__author__ = 'Michael Meisinger'

from zope.interface import implementedBy

from pyon.core.bootstrap import CFG
from pyon.ion.endpoint import ProcessRPCServer, ProcessRPCClient, ProcessSubscriber
from pyon.ion.endpoint import StreamSubscriberRegistrar, StreamSubscriberRegistrarError, StreamPublisher, StreamPublisherRegistrar
from pyon.ion.process import IonProcessSupervisor
from pyon.net.messaging import IDPool
from pyon.service.service import BaseService
from pyon.util.containers import DictModifier, DotDict, for_name, named_any
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

        # mapping of greenlets we spawn to service_instances for error handling
        self._spawned_proc_to_process = {}

        # The pyon worker process supervisor
        self.proc_sup = IonProcessSupervisor(heartbeat_secs=CFG.cc.timeout.heartbeat, failure_notify_callback=self._spawned_proc_failed)

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
            except Exception:
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
        log.debug("ProcManager.spawn_process(name=%s, module.cls=%s.%s, proc_type=%s) as pid=%s", name, module, cls, process_type, process_id)

        if config is None:
            config = DictModifier(CFG)

        log.debug("spawn_process() pid=%s config=%s", process_id, config)

        # PROCESS TYPE.
        # One of: service, stream_process, agent, simple, immediate

        service_cls = named_any("%s.%s" % (module, cls))
        process_type = process_type or getattr(service_cls, "process_type", "service")

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
            return process_id

        except Exception:
            errcause = service_instance.errcause if service_instance else "instantiating service"
            log.exception("Error spawning %s %s process (process_id: %s): %s" % (name, process_type, process_id, errcause))
            raise

    def _spawned_proc_failed(self, proc_sup, gproc):
        log.error("ProcManager._spawned_proc_failed: %s", gproc)

        # look it up in mapping
        if not gproc in self._spawned_proc_to_process:
            log.warn("No record of gproc %s in our map (%s)", gproc, self._spawned_proc_to_process)
            return

        svc = self._spawned_proc_to_process[gproc]

        # make sure svc is in our list
        if not svc in self.procs.values():
            log.warn("svc %s not found in procs list", svc)
            return

        self.container.fail_fast("Container's only process (%s) failed: %s" % (svc, gproc.exception))

    def _spawn_service_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as a service worker.
        Attach to service queue with service definition, attach to service pid
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)
        self._service_init(service_instance)

        listen_name = config.get("process", {}).get("listen_name", service_instance.name)
        log.debug("Service Process (%s) listen_name: %s", name, listen_name)

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

        listen_name = config.get("process", {}).get("listen_name", name)
        # Throws an exception if no listen name is given!
        self._set_subscription_endpoint(service_instance, listen_name)

        # Spawn the greenlet
        self._service_start(service_instance)

        publish_streams = config.get("process", {}).get("publish_streams", None)
        # Add the publishers if any...
        self._set_publisher_endpoints(service_instance, publish_streams)

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

        # start service dependencies (RPC clients)
        self._start_service_dependencies(service_instance)
        
        return service_instance

    def _start_service_dependencies(self, service_instance):
        service_instance.errcause = "setting service dependencies"
        log.debug("spawn_process dependencies: %s" % service_instance.dependencies)
        # TODO: Service dependency != process dependency
        for dependency in service_instance.dependencies:
            client = getattr(service_instance.clients, dependency)
            assert client, "Client for dependency not found: %s" % dependency

            # @TODO: should be in a start_client in RPCClient chain
            client.process  = service_instance
            client.node     = self.container.node

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
        proc = self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=rsvc, name=listen_name)
        self.proc_sup.ensure_ready(proc, "_set_service_endpoint for listen_name: %s" % listen_name)

        # map gproc to service_instance
        self._spawned_proc_to_process[proc.proc] = service_instance

        log.debug("Process %s service listener ready: %s", service_instance.id, listen_name)

    def _set_subscription_endpoint(self, service_instance, listen_name):
        service_instance.errcause = "setting process subscription endpoint"

        service_instance.stream_subscriber_registrar = StreamSubscriberRegistrar(process=service_instance, node=self.container.node)

        sub = service_instance.stream_subscriber_registrar.create_subscriber(exchange_name=listen_name,callback=lambda m,h: service_instance.process(m))

        proc = self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=sub, name=listen_name)
        self.proc_sup.ensure_ready(proc, '_set_subscription_endpoint for listen_name: %s' % listen_name)

        # map gproc to service_instance
        self._spawned_proc_to_process[proc.proc] = service_instance

        log.debug("Process %s stream listener ready: %s", service_instance.id, listen_name)

    def _set_publisher_endpoints(self, service_instance, publisher_streams=None):

        service_instance.stream_publisher_registrar = StreamPublisherRegistrar(process=service_instance, node=self.container.node)

        publisher_streams = publisher_streams or {}

        for name, stream_id in publisher_streams.iteritems():
            # problem is here
            pub = service_instance.stream_publisher_registrar.create_publisher(stream_id)

            setattr(service_instance, name, pub)



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

        # find the proc
        lp = list(self.proc_sup.children)
        lps = [p for p in lp if p.listener._process == service_instance]
        assert len(lps) > 0

        for p in lps:
            p.notify_stop()
            p.stop()

        del self.procs[process_id]
