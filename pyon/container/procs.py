#!/usr/bin/env python

"""Part of the container that manages ION processes etc."""

__author__ = 'Michael Meisinger'

import time
from zope.interface import implementedBy

from pyon.agent.agent import ResourceAgent
from pyon.agent.simple_agent import SimpleResourceAgent
from pyon.core import exception
from pyon.core.bootstrap import CFG, IonObject, get_sys_name
from pyon.core.exception import ContainerConfigError, BadRequest, NotFound
from pyon.ion.endpoint import ProcessRPCServer
from pyon.ion.stream import StreamPublisher, StreamSubscriber
from pyon.ion.process import IonProcessThreadManager
from pyon.net.messaging import IDPool
from pyon.service.service import BaseService
from pyon.util.containers import DotDict, for_name, named_any, dict_merge, get_safe, is_valid_identifier
from pyon.util.log import log
from pyon.ion.resource import RT, PRED
from pyon.net.channel import RecvChannel
from pyon.net.transport import NameTrio, TransportError

from interface.objects import ProcessStateEnum, CapabilityContainer, Service, Process


class ProcManager(object):
    def __init__(self, container):
        self.container = container

        # Define the callables that can be added to Container public API
        self.container_api = [self.spawn_process, self.terminate_process]

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
        self.proc_sup = IonProcessThreadManager(heartbeat_secs=CFG.cc.timeout.heartbeat, failure_notify_callback=self._spawned_proc_failed)

    def start(self):
        log.debug("ProcManager starting ...")
        self.proc_sup.start()

        # Register container as resource object
        cc_obj = CapabilityContainer(name=self.container.id, cc_agent=self.container.name)
        self.cc_id, _ = self.container.resource_registry.create(cc_obj)

        #Create an association to an Org object if not the rot ION org and only if found
        if CFG.container.org_name and CFG.container.org_name != CFG.system.root_org:
            org,_ = self.container.resource_registry.find_resources(restype=RT.Org,name=CFG.container.org_name, id_only=True )
            if org:
                self.container.resource_registry.create_association(org[0],PRED.hasResource, self.cc_id)  #TODO - replace with proper association



        log.debug("ProcManager started, OK.")

    def stop(self):
        log.debug("ProcManager stopping ...")

        from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
        stats1 = CouchDB_DataStore._stats.get_stats()

        # Call quit on procs to give them ability to clean up
        # @TODO terminate_process is not gl-safe
#        gls = map(lambda k: spawn(self.terminate_process, k), self.procs.keys())
#        join(gls)
        procs_list = sorted(self.procs.values(), key=lambda proc: proc._proc_start_time, reverse=True)

        for proc in procs_list:
            try:
                self.terminate_process(proc.id)
            except Exception as ex:
                log.warn("Failed to terminate process (%s): %s", proc.id, ex)

        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)

        if self.procs:
            log.warn("ProcManager procs not empty: %s", self.procs)
        if self.procs_by_name:
            log.warn("ProcManager procs_by_name not empty: %s", self.procs_by_name)

        # Remove Resource registration
        self.container.resource_registry.delete(self.cc_id, del_associations=True)
        # TODO: Check associations to processes

        stats2 = CouchDB_DataStore._stats.get_stats()

        stats3 = CouchDB_DataStore._stats.diff_stats(stats2, stats1)
        log.debug("Datastore stats difference during stop(): %s", stats3)

        log.debug("ProcManager stopped, OK.")

    def spawn_process(self, name=None, module=None, cls=None, config=None, process_id=None):
        """
        Spawn a process within the container. Processes can be of different type.
        """

        if process_id and not is_valid_identifier(process_id, ws_sub='_'):
            raise BadRequest("Given process_id %s is not a valid identifier" % process_id)

        # Generate a new process id if not provided
        # TODO: Ensure it is system-wide unique
        process_id =  process_id or "%s.%s" % (self.container.id, self.proc_id_pool.get_id())
        log.debug("ProcManager.spawn_process(name=%s, module.cls=%s.%s, config=%s) as pid=%s", name, module, cls, config, process_id)

        process_cfg = CFG.copy()
        if config:
            # Use provided config. Must be dict or DotDict
            if not isinstance(config, DotDict):
                config = DotDict(config)
            dict_merge(process_cfg, config, inplace=True)
            if self.container.spawn_args:
                # Override config with spawn args
                dict_merge(process_cfg, self.container.spawn_args, inplace=True)

        #log.debug("spawn_process() pid=%s process_cfg=%s", process_id, process_cfg)

        # PROCESS TYPE. Determines basic process context (messaging, service interface)
        # One of: service, stream_process, agent, simple, immediate

        service_cls = named_any("%s.%s" % (module, cls))
        process_type = get_safe(process_cfg, "process.type") or getattr(service_cls, "process_type", "service")

        service_instance = None
        try:
            # spawn service by type
            if process_type == "service":
                service_instance = self._spawn_service_process(process_id, name, module, cls, process_cfg)

            elif process_type == "stream_process":
                service_instance = self._spawn_stream_process(process_id, name, module, cls, process_cfg)

            elif process_type == "agent":
                service_instance = self._spawn_agent_process(process_id, name, module, cls, process_cfg)

            elif process_type == "standalone":
                service_instance = self._spawn_standalone_process(process_id, name, module, cls, process_cfg)

            elif process_type == "immediate":
                service_instance = self._spawn_immediate_process(process_id, name, module, cls, process_cfg)

            elif process_type == "simple":
                service_instance = self._spawn_simple_process(process_id, name, module, cls, process_cfg)

            else:
                raise BadRequest("Unknown process type: %s" % process_type)

            service_instance._proc_type = process_type
            self._register_process(service_instance, name)

            service_instance.errcause = "OK"
            log.info("ProcManager.spawn_process: %s.%s -> pid=%s OK", module, cls, process_id)

            if process_type == 'immediate':
                log.info('Terminating immediate process: %s', service_instance.id)
                self.terminate_process(service_instance.id)

            return service_instance.id

        except Exception:
            errcause = service_instance.errcause if service_instance else "instantiating service"
            log.exception("Error spawning %s %s process (process_id: %s): %s", name, process_type, process_id, errcause)
            raise

    def list_local_processes(self, process_type=''):
        '''
        Returns a list of the running ION processes in the container or filtered by the process_type
        '''
        ret = list()
        for p in self.procs.values():
            if process_type and p.process_type != process_type:
                continue

            ret.append(p)

        return ret


    def get_a_local_process(self, proc_name=''):
        '''
        Returns a running ION processes in the container for the specified name
        '''
        for p in self.procs.values():

            if p.name == proc_name:
                return p

            if p.process_type == 'agent' and p.resource_type == proc_name:
                return p

        return None


    def is_local_service_process(self, service_name):
        local_services = self.list_local_processes('service')
        for p in local_services:
            if p.name == service_name:
                return True

        return False

    def is_local_agent_process(self, resource_type):
        local_agents = self.list_local_processes('agent')
        for p in local_agents:
            if p.resource_type == resource_type:
                return True
        return False


    def _spawned_proc_failed(self, gproc):
        log.error("ProcManager._spawned_proc_failed: %s, %s", gproc, gproc.exception)

        # for now - don't worry about the mapping, if we get a failure, just kill the container.
        # leave the mapping in place for potential expansion later.

#        # look it up in mapping
#        if not gproc in self._spawned_proc_to_process:
#            log.warn("No record of gproc %s in our map (%s)", gproc, self._spawned_proc_to_process)
#            return
#
        svc = self._spawned_proc_to_process.get(gproc, "Unknown")
#
#        # make sure svc is in our list
#        if not svc in self.procs.values():
#            log.warn("svc %s not found in procs list", svc)
#            return

        self.container.fail_fast("Container process (%s) failed: %s" % (svc, gproc.exception))


    def _cleanup_method(self, queue_name, ep=None):
        """
        Common method to be passed to each spawned ION process to clean up their process-queue.

        @TODO Leaks implementation detail, should be using XOs
        """
        if not ep._chan._queue_auto_delete:
            # only need to delete if AMQP didn't handle it for us already!
            # @TODO this will not work with XOs (future)
            try:
                ch = self.container.node.channel(RecvChannel)
                ch._recv_name = NameTrio(get_sys_name(), "%s.%s" % (get_sys_name(), queue_name))
                ch._destroy_queue()
            except TransportError as ex:
                log.warn("Cleanup method triggered an error, ignoring: %s", ex)


    # -----------------------------------------------------------------
    # PROCESS TYPE: service
    def _spawn_service_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as a service worker.
        Attach to service queue with service definition, attach to service pid
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)

        listen_name = get_safe(config, "process.listen_name") or service_instance.name
        log.debug("Service Process (%s) listen_name: %s", name, listen_name)
        service_instance._proc_listen_name = listen_name

        # Service RPC endpoint
        rsvc1 = ProcessRPCServer(node=self.container.node,
            from_name=listen_name,
            service=service_instance,
            process=service_instance)
        # Named local RPC endpoint
        rsvc2 = ProcessRPCServer(node=self.container.node,
            from_name=service_instance.id,
            service=service_instance,
            process=service_instance)

        # cleanup method to delete process queue
        cleanup = lambda _: self._cleanup_method(service_instance.id, rsvc2)

        # Start an ION process with the right kind of endpoint factory
        proc = self.proc_sup.spawn(name=service_instance.id,
                                   service=service_instance,
                                   listeners=[rsvc1, rsvc2],
                                   proc_name=service_instance._proc_name,
                                   cleanup_method=cleanup)
        self.proc_sup.ensure_ready(proc, "_spawn_service_process for %s" % ",".join((listen_name, service_instance.id)))

        # map gproc to service_instance
        self._spawned_proc_to_process[proc.proc] = service_instance

        # set service's reference to process
        service_instance._process = proc

        self._service_init(service_instance)
        self._service_start(service_instance)

        proc.start_listeners()

        # look to load any existing policies for this service
        if self.container.governance_controller:
            self.container.governance_controller.safe_update_service_access_policy(service_instance._proc_listen_name)

        return service_instance

    # -----------------------------------------------------------------
    # PROCESS TYPE: stream process
    def _spawn_stream_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as a data stream process.
        Attach to subscription queue with process function.
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)

        listen_name = get_safe(config, "process.listen_name") or name
        service_instance._proc_listen_name = listen_name

        service_instance.stream_subscriber = StreamSubscriber(process=service_instance, exchange_name=listen_name, callback=service_instance.call_process)


        # Add publishers if any...
        publish_streams = get_safe(config, "process.publish_streams")
        self._set_publisher_endpoints(service_instance, publish_streams)

        rsvc = ProcessRPCServer(node=self.container.node,
            from_name=service_instance.id,
            service=service_instance,
            process=service_instance)

        # cleanup method to delete process queue (@TODO: leaks a bit here - should use XOs)
        cleanup = lambda _: self._cleanup_method(service_instance.id, rsvc)

        proc = self.proc_sup.spawn(name=service_instance.id,
                                   service=service_instance,
                                   listeners=[rsvc, service_instance.stream_subscriber],
                                   proc_name=service_instance._proc_name,
                                   cleanup_method=cleanup)
        self.proc_sup.ensure_ready(proc, "_spawn_stream_process for %s" % service_instance._proc_name)

        # map gproc to service_instance
        self._spawned_proc_to_process[proc.proc] = service_instance

        # set service's reference to process
        service_instance._process = proc

        self._service_init(service_instance)
        self._service_start(service_instance)

        proc.start_listeners()

        return service_instance

    # -----------------------------------------------------------------
    # PROCESS TYPE: agent
    def _spawn_agent_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as agent process.
        Attach to service pid.
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)
        if not isinstance(service_instance, ResourceAgent) and not isinstance(service_instance, SimpleResourceAgent):
             raise ContainerConfigError("Agent process must extend ResourceAgent")
        listeners = []

        # Set the resource ID if we get it through the config
        resource_id = get_safe(service_instance.CFG, "agent.resource_id")
        if resource_id:
            service_instance.resource_id = resource_id

            alistener = ProcessRPCServer(node=self.container.node,
                                         from_name=resource_id,
                                         service=service_instance,
                                         process=service_instance)

            listeners.append(alistener)

        rsvc = ProcessRPCServer(node=self.container.node,
            from_name=service_instance.id,
            service=service_instance,
            process=service_instance)

        listeners.append(rsvc)

        # cleanup method to delete process/agent queue (@TODO: leaks a bit here - should use XOs)
        def agent_cleanup(x):
            self._cleanup_method(service_instance.id, rsvc)
            if resource_id:
                self._cleanup_method(service_instance.id, alistener)

        proc = self.proc_sup.spawn(name=service_instance.id,
                                   service=service_instance,
                                   listeners=listeners,
                                   proc_name=service_instance._proc_name,
                                   cleanup_method=agent_cleanup)
        self.proc_sup.ensure_ready(proc, "_spawn_agent_process for %s" % service_instance.id)

        # map gproc to service_instance
        self._spawned_proc_to_process[proc.proc] = service_instance

        # set service's reference to process
        service_instance._process = proc

        # Now call the on_init of the agent.
        self._service_init(service_instance)

        if not service_instance.resource_id:
            log.warn("New agent pid=%s has no resource_id set" % process_id)

        self._service_start(service_instance)

        proc.start_listeners()

        # look to load any existing policies for this agent service
        if self.container.governance_controller:
            if service_instance.resource_type is None:
                self.container.governance_controller.safe_update_service_access_policy(service_instance.name)
            else:
                self.container.governance_controller.safe_update_service_access_policy(service_instance.resource_type)


        if service_instance.resource_id:
            # look to load any existing policies for this resource
            if self.container.governance_controller:
                self.container.governance_controller.safe_update_resource_access_policy(service_instance.resource_id)
        else:
            log.warn("Agent process id=%s does not define resource_id!!" % service_instance.id)

        return service_instance

    # -----------------------------------------------------------------
    # PROCESS TYPE: standalone
    def _spawn_standalone_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as standalone process.
        Attach to service pid.
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)
        rsvc = ProcessRPCServer(node=self.container.node,
            from_name=service_instance.id,
            service=service_instance,
            process=service_instance)

        # cleanup method to delete process queue (@TODO: leaks a bit here - should use XOs)
        cleanup = lambda _: self._cleanup_method(service_instance.id, rsvc)

        proc = self.proc_sup.spawn(name=service_instance.id,
                                   service=service_instance,
                                   listeners=[rsvc],
                                   proc_name=service_instance._proc_name,
                                   cleanup_method=cleanup)
        self.proc_sup.ensure_ready(proc, "_spawn_standalone_process for %s" % service_instance.id)

        # map gproc to service_instance
        self._spawned_proc_to_process[proc.proc] = service_instance

        # set service's reference to process
        service_instance._process = proc

        self._service_init(service_instance)
        self._service_start(service_instance)

        # Add publishers if any...
        publish_streams = get_safe(config, "process.publish_streams")
        self._set_publisher_endpoints(service_instance, publish_streams)

        proc.start_listeners()

        return service_instance

    # -----------------------------------------------------------------
    # PROCESS TYPE: simple
    def _spawn_simple_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as simple process.
        No attachments.
        """
        service_instance = self._create_service_instance(process_id, name, module, cls, config)
        self._service_init(service_instance)
        self._service_start(service_instance)

        # Add publishers if any...
        publish_streams = get_safe(config, "process.publish_streams")
        self._set_publisher_endpoints(service_instance, publish_streams)

        return service_instance

    # -----------------------------------------------------------------
    # PROCESS TYPE: immediate
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
        """
        Creates an instance of a "service", be it a Service, Agent, Stream, etc.

        @rtype BaseService
        @return An instance of a "service"
        """
        # SERVICE INSTANCE.
        service_instance = for_name(module, cls)
        if not isinstance(service_instance, BaseService):
            raise ContainerConfigError("Instantiated service not a BaseService %r" % service_instance)

        # Prepare service instance
        service_instance.errcause = ""
        service_instance.id = process_id
        service_instance.container = self.container
        service_instance.CFG = config
        service_instance._proc_name = name
        service_instance._proc_start_time = time.time()

        # start service dependencies (RPC clients)
        self._start_service_dependencies(service_instance)
        
        return service_instance

    def _start_service_dependencies(self, service_instance):
        service_instance.errcause = "setting service dependencies"
        log.debug("spawn_process dependencies: %s", service_instance.dependencies)
        # TODO: Service dependency != process dependency
        for dependency in service_instance.dependencies:
            client = getattr(service_instance.clients, dependency)
            assert client, "Client for dependency not found: %s" % dependency

            # @TODO: should be in a start_client in RPCClient chain
            client.process  = service_instance
            client.node     = self.container.node

            # ensure that dep actually exists and is running
            # MM: commented out - during startup (init actually), we don't need to check for service dependencies
            # MM: TODO: split on_init from on_start; start consumer in on_start; check for full queues on restart
#            if service_instance.name != 'bootstrap' or (service_instance.name == 'bootstrap' and service_instance.CFG.level == dependency):
#                svc_de = self.container.resource_registry.find_resources(restype="Service", name=dependency, id_only=True)
#                if not svc_de:
#                    raise ContainerConfigError("Dependency for service %s not running: %s" % (service_instance.name, dependency))

    def _service_init(self, service_instance):
        # Init process
        service_instance.errcause = "initializing service"
        service_instance.init()

    def _service_start(self, service_instance):
        # Start process
        # TODO: Check for timeout
        service_instance.errcause = "starting service"
        service_instance.start()

    def _set_publisher_endpoints(self, service_instance, publisher_streams=None):

        publisher_streams = publisher_streams or {}

        for name, stream_id in publisher_streams.iteritems():
            # problem is here
            pub = StreamPublisher(process=service_instance, stream_id=stream_id)


            setattr(service_instance, name, pub)

    def _register_process(self, service_instance, name):
        """
        Performs all actions related to registering the new process in the system.
        Also performs process type specific registration, such as for services and agents
        """
        # Add process instance to container's process dict
        if name in self.procs_by_name:
            log.warn("Process name already registered in container: %s" % name)
        self.procs_by_name[name] = service_instance
        self.procs[service_instance.id] = service_instance

        # Add Process to resource registry
        # Note: In general the Process resource should be created by the CEI PD, but not all processes are CEI
        # processes. How to deal with this?
        service_instance.errcause = "registering"

        if service_instance._proc_type != "immediate":
            proc_obj = Process(name=service_instance.id, label=name, proctype=service_instance._proc_type)
            proc_id, _ = self.container.resource_registry.create(proc_obj)
            service_instance._proc_res_id = proc_id

            # Associate process with container resource
            self.container.resource_registry.create_association(self.cc_id, "hasProcess", proc_id)
        else:
            service_instance._proc_res_id = None

        # Process type specific registration
        # TODO: Factor out into type specific handler functions
        if service_instance._proc_type == "service":
            # Registration of SERVICE process: in resource registry
            service_list, _ = self.container.resource_registry.find_resources(restype="Service", name=service_instance.name)
            if service_list:
                service_instance._proc_svc_id = service_list[0]._id
            else:
                # We are starting the first process of a service instance
                # TODO: This should be created by the HA Service agent in the future
                svc_obj = Service(name=service_instance.name, exchange_name=service_instance._proc_listen_name)
                service_instance._proc_svc_id, _ = self.container.resource_registry.create(svc_obj)

                # Create association to service definition resource
                svcdef_list, _ = self.container.resource_registry.find_resources(restype="ServiceDefinition",
                    name=service_instance.name)
                if svcdef_list:
                    self.container.resource_registry.create_association(service_instance._proc_svc_id,
                        "hasServiceDefinition", svcdef_list[0]._id)
                else:
                    log.error("Cannot find ServiceDefinition resource for %s", service_instance.name)

            self.container.resource_registry.create_association(service_instance._proc_svc_id, "hasProcess", proc_id)

        elif service_instance._proc_type == "agent":
            # Registration of AGENT process: in Directory
            caps = service_instance.get_capabilities()
            self.container.directory.register("/Agents", service_instance.id,
                **dict(name=service_instance._proc_name,
                    container=service_instance.container.id,
                    resource_id=service_instance.resource_id,
                    agent_id=service_instance.agent_id,
                    def_id=service_instance.agent_def_id,
                    capabilities=caps))

        # Trigger a real-time event. At this time, everything persistent has to be completed and consistent.
        self.container.event_pub.publish_event(event_type="ProcessLifecycleEvent",
            origin=service_instance.id,
            origin_type="ContainerProcess",
            sub_type="SPAWN",
            container_id=self.container.id,
            process_type=service_instance._proc_type,
            process_name=service_instance._proc_name,
            state=ProcessStateEnum.SPAWN)



    def terminate_process(self, process_id):
        """
        Terminates a process and all its resources. Termination is graceful with timeout.
        """
        log.debug("terminate_process: %s", process_id)
        service_instance = self.procs.get(process_id, None)
        if not service_instance:
            raise BadRequest("Cannot terminate. Process id='%s' unknown on container id='%s'" % (
                                        process_id, self.container.id))

        # Give the process notice to quit doing stuff.
        service_instance.quit()

        # Terminate IonProcessThread (may not have one, i.e. simple process)
        if getattr(service_instance,'_process', None) is not None and service_instance._process:
            service_instance._process.notify_stop()
            service_instance._process.stop()

        self._unregister_process(process_id, service_instance)

        # Send out real-time notice that process was terminated. At this point, everything persistent
        # has to be consistent.
        self.container.event_pub.publish_event(event_type="ProcessLifecycleEvent",
            origin=service_instance.id, origin_type="ContainerProcess",
            sub_type="TERMINATE",
            container_id=self.container.id,
            process_type=service_instance._proc_type, process_name=service_instance._proc_name,
            state=ProcessStateEnum.TERMINATE)

    def _unregister_process(self, process_id, service_instance):
        # Remove process registration in resource registry
        if service_instance._proc_res_id:
            self.container.resource_registry.delete(service_instance._proc_res_id, del_associations=True)

        # Cleanup for specific process types
        if service_instance._proc_type == "service":
            # Check if this is the last process for this service and do auto delete service resources here
            svcproc_list, _ = self.container.resource_registry.find_objects(service_instance._proc_svc_id,
                "hasProcess", "Process", id_only=True)
            if not svcproc_list:
                self.container.resource_registry.delete(service_instance._proc_svc_id, del_associations=True)

        elif service_instance._proc_type == "agent":
            self.container.directory.unregister_safe("/Agents", service_instance.id)


        # Remove internal registration in container
        del self.procs[process_id]
        if service_instance._proc_name in self.procs_by_name:
            del self.procs_by_name[service_instance._proc_name]
        else:
            log.warn("Process name %s not in local registry", service_instance.name)
