#!/usr/bin/env python

"""Part of the container that manages ION processes etc."""

__author__ = 'Michael Meisinger'

from copy import deepcopy
import time
from zope.interface import implementedBy

from pyon.agent.agent import ResourceAgent
from pyon.agent.simple_agent import SimpleResourceAgent
from pyon.core import exception
from pyon.core.bootstrap import CFG, IonObject, get_sys_name
from pyon.core.exception import ContainerConfigError, BadRequest, NotFound
from pyon.ion.endpoint import ProcessRPCServer
from pyon.ion.conversation import ConversationRPCServer
from pyon.ion.stream import StreamPublisher, StreamSubscriber
from pyon.ion.process import IonProcessThreadManager, IonProcessError
from pyon.net.messaging import IDPool
from pyon.service.service import BaseService
from pyon.util.containers import DotDict, for_name, named_any, dict_merge, get_safe, is_valid_identifier
from pyon.util.log import log
from pyon.ion.resource import RT, PRED
from pyon.net.channel import RecvChannel
from pyon.net.transport import NameTrio, TransportError

from interface.objects import ProcessStateEnum, CapabilityContainer, Service, Process, ServiceStateEnum

from couchdb.http import ResourceNotFound

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

        # mapping of greenlets we spawn to process_instances for error handling
        self._spawned_proc_to_process = {}

        # The pyon worker process supervisor
        self.proc_sup = IonProcessThreadManager(heartbeat_secs=CFG.cc.timeout.heartbeat, failure_notify_callback=self._spawned_proc_failed)

        # list of callbacks for process state changes
        self._proc_state_change_callbacks = []

    def start(self):
        log.debug("ProcManager starting ...")
        self.proc_sup.start()

        # Register container as resource object
        cc_obj = CapabilityContainer(name=self.container.id, cc_agent=self.container.name)
        self.cc_id, _ = self.container.resource_registry.create(cc_obj)

        #Create an association to an Org object if not the rot ION org and only if found
        if CFG.container.org_name and CFG.container.org_name != CFG.system.root_org:
            org, _ = self.container.resource_registry.find_resources(restype=RT.Org, name=CFG.container.org_name, id_only=True)
            if org:
                self.container.resource_registry.create_association(org[0], PRED.hasResource, self.cc_id)  # TODO - replace with proper association

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
        try:
            self.container.resource_registry.delete(self.cc_id, del_associations=True)
        except NotFound:
            # already gone, this is ok
            pass
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
        process_id = process_id or "%s.%s" % (self.container.id, self.proc_id_pool.get_id())
        log.debug("ProcManager.spawn_process(name=%s, module.cls=%s.%s, config=%s) as pid=%s", name, module, cls, config, process_id)

        process_cfg = deepcopy(CFG)
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

        process_start_mode = get_safe(config, "process.start_mode")

        process_instance = None

        # alert we have a spawning process, but we don't have the instance yet, so give the class instead (more accurate than name)
        self._call_proc_state_changed("%s.%s" % (module, cls), ProcessStateEnum.PENDING)

        try:
            # spawn service by type
            if process_type == "service":
                process_instance = self._spawn_service_process(process_id, name, module, cls, process_cfg)

            elif process_type == "stream_process":
                process_instance = self._spawn_stream_process(process_id, name, module, cls, process_cfg)

            elif process_type == "agent":
                process_instance = self._spawn_agent_process(process_id, name, module, cls, process_cfg)

            elif process_type == "standalone":
                process_instance = self._spawn_standalone_process(process_id, name, module, cls, process_cfg)

            elif process_type == "immediate":
                process_instance = self._spawn_immediate_process(process_id, name, module, cls, process_cfg)

            elif process_type == "simple":
                process_instance = self._spawn_simple_process(process_id, name, module, cls, process_cfg)

            else:
                raise BadRequest("Unknown process type: %s" % process_type)

            process_instance._proc_type = process_type
            self._register_process(process_instance, name)

            process_instance.errcause = "OK"
            log.info("ProcManager.spawn_process: %s.%s -> pid=%s OK", module, cls, process_id)

            if process_type == 'immediate':
                log.info('Terminating immediate process: %s', process_instance.id)
                self.terminate_process(process_instance.id)

                # terminate process also triggers TERMINATING/TERMINATED
                self._call_proc_state_changed(process_instance, ProcessStateEnum.EXITED)
            else:
                #Shouldn't be any policies for immediate processes
                self.update_container_policies(process_instance)

            return process_instance.id

        except IonProcessError:
            errcause = process_instance.errcause if process_instance else "instantiating process"
            log.exception("Error spawning %s %s process (process_id: %s): %s", name, process_type, process_id, errcause)
            return None

        except Exception:
            errcause = process_instance.errcause if process_instance else "instantiating process"
            log.exception("Error spawning %s %s process (process_id: %s): %s", name, process_type, process_id, errcause)

            # trigger failed notification - catches problems in init/start
            self._call_proc_state_changed(process_instance, ProcessStateEnum.FAILED)

            raise

    #This must be called after registering the process
    def update_container_policies(self, process_instance):

        if not self.container.governance_controller:
            return

        if process_instance._proc_type == "service":

            # look to load any existing policies for this service
            self.container.governance_controller.safe_update_service_access_policy(process_instance._proc_listen_name)

        if process_instance._proc_type == "agent":

            # look to load any existing policies for this agent service
            if process_instance.resource_type is None:
                self.container.governance_controller.safe_update_service_access_policy(process_instance.name)
            else:
                self.container.governance_controller.safe_update_service_access_policy(process_instance.resource_type)

            if process_instance.resource_id:
                # look to load any existing policies for this resource
                self.container.governance_controller.safe_update_resource_access_policy(process_instance.resource_id)



    def list_local_processes(self, process_type=''):
        """
        Returns a list of the running ION processes in the container or filtered by the process_type
        """
        if not process_type:
            return self.procs.values()

        return [p for p in self.procs.itervalues() if p.process_type == process_type]

    def get_a_local_process(self, proc_name=''):
        """
        Returns a running ION processes in the container for the specified name
        """
        for p in self.procs.itervalues():

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
        prc = self._spawned_proc_to_process.get(gproc, None)
#
#        # make sure prc is in our list
#        if not prc in self.procs.values():
#            log.warn("prc %s not found in procs list", prc)
#            return

        # stop the rest of the process
        if prc is not None:
            try:
                self.terminate_process(prc.id, False)
            except Exception as e:
                log.warn("Problem while stopping rest of failed process %s: %s", prc, e)
            finally:
                self._call_proc_state_changed(prc, ProcessStateEnum.FAILED)
        else:
            log.warn("No ION process found for failed proc manager child: %s", gproc)

        #self.container.fail_fast("Container process (%s) failed: %s" % (svc, gproc.exception))

    def _cleanup_method(self, queue_name, ep=None):
        """
        Common method to be passed to each spawned ION process to clean up their process-queue.

        @TODO Leaks implementation detail, should be using XOs
        """
        if  ep._chan is not None and not ep._chan._queue_auto_delete:
            # only need to delete if AMQP didn't handle it for us already!
            # @TODO this will not work with XOs (future)
            try:
                ch = self.container.node.channel(RecvChannel)
                ch._recv_name = NameTrio(get_sys_name(), "%s.%s" % (get_sys_name(), queue_name))
                ch._destroy_queue()
            except TransportError as ex:
                log.warn("Cleanup method triggered an error, ignoring: %s", ex)

    def add_proc_state_changed_callback(self, cb):
        """
        Adds a callback to be called when a process' state changes.

        The callback should take three parameters: The process, the state, and the container.
        """
        self._proc_state_change_callbacks.append(cb)

    def remove_proc_state_changed_callback(self, cb):
        """
        Removes a callback from the process state change callback list.

        If the callback is not registered, this method does nothing.
        """
        if cb in self._proc_state_change_callbacks:
            self._proc_state_change_callbacks.remove(cb)

    def _call_proc_state_changed(self, svc, state):
        """
        Internal method to call all registered process state change callbacks.
        """
        log.debug("Proc State Changed (%s): %s", ProcessStateEnum._str_map.get(state, state), svc)
        for cb in self._proc_state_change_callbacks:
            cb(svc, state, self.container)

    def _create_listening_endpoint(self, **kwargs):
        """
        Creates a listening endpoint for spawning processes.

        This method exists to be able to override the type created via configuration.
        In most cases it will create a ConversationRPCServer.
        """
        eptypestr = CFG.get_safe('container.messaging.endpoint.proc_listening_type', None)
        if eptypestr is not None:
            module, cls     = eptypestr.rsplit('.', 1)
            mod             = __import__(module, fromlist=[cls])
            eptype          = getattr(mod, cls)
            ep              = eptype(**kwargs)
        else:
            conv_enabled = CFG.get_safe('container.messaging.endpoint.rpc_conversation_enabled', False)
            if conv_enabled:
                ep = ConversationRPCServer(**kwargs)
            else:
                ep = ProcessRPCServer(**kwargs)
        return ep

    # -----------------------------------------------------------------
    # PROCESS TYPE: service
    def _spawn_service_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as a service worker.
        Attach to service queue with service definition, attach to service pid
        """
        process_instance = self._create_process_instance(process_id, name, module, cls, config)

        listen_name = get_safe(config, "process.listen_name") or process_instance.name
        log.debug("Service Process (%s) listen_name: %s", name, listen_name)
        process_instance._proc_listen_name = listen_name

        # Service RPC endpoint
        rsvc1 = self._create_listening_endpoint(node=self.container.node,
                                                from_name=listen_name,
                                                service=process_instance,
                                                process=process_instance)
        # Named local RPC endpoint
        rsvc2 = self._create_listening_endpoint(node=self.container.node,
                                                from_name=process_instance.id,
                                                service=process_instance,
                                                process=process_instance)

        # cleanup method to delete process queue
        cleanup = lambda _: self._cleanup_method(process_instance.id, rsvc2)

        # Start an ION process with the right kind of endpoint factory
        proc = self.proc_sup.spawn(name=process_instance.id,
                                   service=process_instance,
                                   listeners=[rsvc1, rsvc2],
                                   proc_name=process_instance._proc_name,
                                   cleanup_method=cleanup)
        self.proc_sup.ensure_ready(proc, "_spawn_service_process for %s" % ",".join((listen_name, process_instance.id)))

        # map gproc to process_instance
        self._spawned_proc_to_process[proc.proc] = process_instance

        # set service's reference to process
        process_instance._process = proc

        self._process_init(process_instance)
        self._process_start(process_instance)

        try:
            proc.start_listeners()
        except IonProcessError:
            self._process_quit(process_instance)
            self._call_proc_state_changed(process_instance, ProcessStateEnum.FAILED)
            raise

        return process_instance

    # -----------------------------------------------------------------
    # PROCESS TYPE: stream process
    def _spawn_stream_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as a data stream process.
        Attach to subscription queue with process function.
        """
        process_instance = self._create_process_instance(process_id, name, module, cls, config)

        listen_name = get_safe(config, "process.listen_name") or name
        log.debug("Stream Process (%s) listen_name: %s", name, listen_name)
        process_instance._proc_listen_name = listen_name

        process_instance.stream_subscriber = StreamSubscriber(process=process_instance, exchange_name=listen_name, callback=process_instance.call_process)

        # Add publishers if any...
        publish_streams = get_safe(config, "process.publish_streams")
        pub_names = self._set_publisher_endpoints(process_instance, publish_streams)

        rsvc = self._create_listening_endpoint(node=self.container.node,
                                               from_name=process_instance.id,
                                               service=process_instance,
                                               process=process_instance)

        # cleanup method to delete process queue (@TODO: leaks a bit here - should use XOs)
        def cleanup(*args):
            self._cleanup_method(process_instance.id, rsvc)
            for name in pub_names:
                p = getattr(process_instance, name)
                p.close()

        proc = self.proc_sup.spawn(name=process_instance.id,
                                   service=process_instance,
                                   listeners=[rsvc, process_instance.stream_subscriber],
                                   proc_name=process_instance._proc_name,
                                   cleanup_method=cleanup)
        self.proc_sup.ensure_ready(proc, "_spawn_stream_process for %s" % process_instance._proc_name)

        # map gproc to process_instance
        self._spawned_proc_to_process[proc.proc] = process_instance

        # set service's reference to process
        process_instance._process = proc

        self._process_init(process_instance)
        self._process_start(process_instance)

        try:
            proc.start_listeners()
        except IonProcessError:
            self._process_quit(process_instance)
            self._call_proc_state_changed(process_instance, ProcessStateEnum.FAILED)
            raise

        return process_instance

    # -----------------------------------------------------------------
    # PROCESS TYPE: agent
    def _spawn_agent_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as agent process.
        Attach to service pid.
        """
        process_instance = self._create_process_instance(process_id, name, module, cls, config)
        if not isinstance(process_instance, ResourceAgent) and not isinstance(process_instance, SimpleResourceAgent):
            raise ContainerConfigError("Agent process must extend ResourceAgent")
        listeners = []

        # Set the resource ID if we get it through the config
        resource_id = get_safe(process_instance.CFG, "agent.resource_id")
        if resource_id:
            process_instance.resource_id = resource_id

            alistener = self._create_listening_endpoint(node=self.container.node,
                                                        from_name=resource_id,
                                                        service=process_instance,
                                                        process=process_instance)

            listeners.append(alistener)

        rsvc = self._create_listening_endpoint(node=self.container.node,
                                               from_name=process_instance.id,
                                               service=process_instance,
                                               process=process_instance)

        listeners.append(rsvc)

        # cleanup method to delete process/agent queue (@TODO: leaks a bit here - should use XOs)
        def agent_cleanup(x):
            self._cleanup_method(process_instance.id, rsvc)
            if resource_id:
                pass
                #self._cleanup_method(resource_id, alistener)
                # disabled, it's probably not architecturally correct to delete this queue

        proc = self.proc_sup.spawn(name=process_instance.id,
                                   service=process_instance,
                                   listeners=listeners,
                                   proc_name=process_instance._proc_name,
                                   cleanup_method=agent_cleanup)
        self.proc_sup.ensure_ready(proc, "_spawn_agent_process for %s" % process_instance.id)

        # map gproc to process_instance
        self._spawned_proc_to_process[proc.proc] = process_instance

        # set service's reference to process
        process_instance._process = proc

        # Now call the on_init of the agent.
        self._process_init(process_instance)

        if not process_instance.resource_id:
            log.warn("New agent pid=%s has no resource_id set" % process_id)

        self._process_start(process_instance)

        try:
            proc.start_listeners()
        except IonProcessError:
            self._process_quit(process_instance)
            self._call_proc_state_changed(process_instance, ProcessStateEnum.FAILED)
            raise

        if not process_instance.resource_id:
            log.warn("Agent process id=%s does not define resource_id!!" % process_instance.id)

        return process_instance

    # -----------------------------------------------------------------
    # PROCESS TYPE: standalone
    def _spawn_standalone_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as standalone process.
        Attach to service pid.
        """
        process_instance = self._create_process_instance(process_id, name, module, cls, config)
        rsvc = self._create_listening_endpoint(node=self.container.node,
                                               from_name=process_instance.id,
                                               service=process_instance,
                                               process=process_instance)

        # Add publishers if any...
        publish_streams = get_safe(config, "process.publish_streams")
        pub_names = self._set_publisher_endpoints(process_instance, publish_streams)

        # cleanup method to delete process queue (@TODO: leaks a bit here - should use XOs)
        def cleanup(*args):
            self._cleanup_method(process_instance.id, rsvc)
            for name in pub_names:
                p = getattr(process_instance, name)
                p.close()

        proc = self.proc_sup.spawn(name=process_instance.id,
                                   service=process_instance,
                                   listeners=[rsvc],
                                   proc_name=process_instance._proc_name,
                                   cleanup_method=cleanup)
        self.proc_sup.ensure_ready(proc, "_spawn_standalone_process for %s" % process_instance.id)

        # map gproc to process_instance
        self._spawned_proc_to_process[proc.proc] = process_instance

        # set service's reference to process
        process_instance._process = proc

        self._process_init(process_instance)
        self._process_start(process_instance)

        try:
            proc.start_listeners()
        except IonProcessError:
            self._process_quit(process_instance)
            self._call_proc_state_changed(process_instance, ProcessStateEnum.FAILED)
            raise

        return process_instance

    # -----------------------------------------------------------------
    # PROCESS TYPE: simple
    def _spawn_simple_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as simple process.
        No attachments.
        """
        process_instance = self._create_process_instance(process_id, name, module, cls, config)
        # Add publishers if any...
        publish_streams = get_safe(config, "process.publish_streams")
        pub_names = self._set_publisher_endpoints(process_instance, publish_streams)

        # cleanup method to delete process queue (@TODO: leaks a bit here - should use XOs)
        def cleanup(*args):
            for name in pub_names:
                p = getattr(process_instance, name)
                p.close()

        proc = self.proc_sup.spawn(name=process_instance.id,
                                   service=process_instance,
                                   listeners=[],
                                   proc_name=process_instance._proc_name,
                                   cleanup_method=cleanup)
        self.proc_sup.ensure_ready(proc, "_spawn_simple_process for %s" % process_instance.id)

        self._process_init(process_instance)
        self._process_start(process_instance)

        return process_instance

    # -----------------------------------------------------------------
    # PROCESS TYPE: immediate
    def _spawn_immediate_process(self, process_id, name, module, cls, config):
        """
        Spawn a process acting as immediate one off process.
        No attachments.
        """
        process_instance = self._create_process_instance(process_id, name, module, cls, config)
        self._process_init(process_instance)
        self._process_start(process_instance)
        return process_instance

    def _create_process_instance(self, process_id, name, module, cls, config):
        """
        Creates an instance of a "service", be it a Service, Agent, Stream, etc.

        @rtype BaseService
        @return An instance of a "service"
        """
        # SERVICE INSTANCE.
        process_instance = for_name(module, cls)
        if not isinstance(process_instance, BaseService):
            raise ContainerConfigError("Instantiated service not a BaseService %r" % process_instance)

        # Prepare service instance
        process_instance.errcause = ""
        process_instance.id = process_id
        process_instance.container = self.container
        process_instance.CFG = config
        process_instance._proc_name = name
        process_instance._proc_start_time = time.time()

        #Unless the process has been started as part of another Org, default to the container Org or the ION Org
        if config.has_key('org_name'):
            process_instance.org_name = config['org_name']
        else:
            process_instance.org_name = CFG.get_safe('container.org_name', CFG.get_safe('system.root_org', 'ION'))


        # Add stateful process operations
        if hasattr(process_instance, "_flush_state"):
            def _flush_state():
                if not hasattr(process_instance, "_proc_state"):
                    process_instance._proc_state = {}
                    process_instance._proc_state_changed = False
                    return
                process_instance.container.state_repository.put_state(process_instance.id, process_instance._proc_state)
                process_instance._proc_state_changed = False

            def _load_state():
                if not hasattr(process_instance, "_proc_state"):
                    process_instance._proc_state = {}
                try:
                    new_state = process_instance.container.state_repository.get_state(process_instance.id)
                    process_instance._proc_state.clear()
                    process_instance._proc_state.update(new_state)
                    process_instance._proc_state_changed = False
                except Exception as ex:
                    log.warn("Process %s load state failed: %s", process_instance.id, str(ex))
            process_instance._flush_state = _flush_state
            process_instance._load_state = _load_state

        process_start_mode = get_safe(config, "process.start_mode")
        if process_start_mode == "RESTART":
            if hasattr(process_instance, "_load_state"):
                process_instance._load_state()

        # start service dependencies (RPC clients)
        self._start_process_dependencies(process_instance)

        return process_instance

    def _start_process_dependencies(self, process_instance):
        process_instance.errcause = "setting service dependencies"
        log.debug("spawn_process dependencies: %s", process_instance.dependencies)
        # TODO: Service dependency != process dependency
        for dependency in process_instance.dependencies:
            client = getattr(process_instance.clients, dependency)
            assert client, "Client for dependency not found: %s" % dependency

            # @TODO: should be in a start_client in RPCClient chain
            client.process  = process_instance
            client.node     = self.container.node

            # ensure that dep actually exists and is running
            # MM: commented out - during startup (init actually), we don't need to check for service dependencies
            # MM: TODO: split on_init from on_start; start consumer in on_start; check for full queues on restart
#            if process_instance.name != 'bootstrap' or (process_instance.name == 'bootstrap' and process_instance.CFG.level == dependency):
#                svc_de = self.container.resource_registry.find_resources(restype="Service", name=dependency, id_only=True)
#                if not svc_de:
#                    raise ContainerConfigError("Dependency for service %s not running: %s" % (process_instance.name, dependency))

    def _process_init(self, process_instance):
        # Init process
        process_instance.errcause = "initializing service"
        process_instance.init()

    def _process_start(self, process_instance):
        # Start process
        # THIS SHOULD BE CALLED LATER THAN SPAWN
        # TODO: Check for timeout
        process_instance.errcause = "starting service"
        process_instance.start()

    def _process_quit(self, process_instance):
        """
        Common method to handle process stopping.
        """
        process_instance.errcause = "quitting process"

        # Give the process notice to quit doing stuff.
        process_instance.quit()

        # Terminate IonProcessThread (may not have one, i.e. simple process)
        # @TODO: move this into process' on_quit()
        if getattr(process_instance, '_process', None) is not None and process_instance._process:
            process_instance._process.notify_stop()
            process_instance._process.stop()

    def _set_publisher_endpoints(self, process_instance, publisher_streams=None):

        publisher_streams = publisher_streams or {}
        names = []

        for name, stream_id in publisher_streams.iteritems():
            # problem is here
            pub = StreamPublisher(process=process_instance, stream_id=stream_id)

            setattr(process_instance, name, pub)
            names.append(name)

        return names

    def _register_process(self, process_instance, name):
        """
        Performs all actions related to registering the new process in the system.
        Also performs process type specific registration, such as for services and agents
        """
        # Add process instance to container's process dict
        if name in self.procs_by_name:
            log.warn("Process name already registered in container: %s" % name)
        self.procs_by_name[name] = process_instance
        self.procs[process_instance.id] = process_instance

        # Add Process to resource registry
        # Note: In general the Process resource should be created by the CEI PD, but not all processes are CEI
        # processes. How to deal with this?
        process_instance.errcause = "registering"

        if process_instance._proc_type != "immediate":
            proc_obj = Process(name=process_instance.id, label=name, proctype=process_instance._proc_type)
            proc_id, _ = self.container.resource_registry.create(proc_obj)
            process_instance._proc_res_id = proc_id

            # Associate process with container resource
            self.container.resource_registry.create_association(self.cc_id, "hasProcess", proc_id)
        else:
            process_instance._proc_res_id = None

        # Process type specific registration
        # TODO: Factor out into type specific handler functions
        if process_instance._proc_type == "service":
            # Registration of SERVICE process: in resource registry
            service_list, _ = self.container.resource_registry.find_resources(restype="Service", name=process_instance.name)
            if service_list:
                process_instance._proc_svc_id = service_list[0]._id
            else:
                # We are starting the first process of a service instance
                # TODO: This should be created by the HA Service agent in the future
                svc_obj = Service(name=process_instance.name, exchange_name=process_instance._proc_listen_name, state=ServiceStateEnum.READY)
                process_instance._proc_svc_id, _ = self.container.resource_registry.create(svc_obj)

                # Create association to service definition resource
                svcdef_list, _ = self.container.resource_registry.find_resources(restype="ServiceDefinition",
                    name=process_instance.name)
                if svcdef_list:
                    self.container.resource_registry.create_association(process_instance._proc_svc_id,
                        "hasServiceDefinition", svcdef_list[0]._id)
                else:
                    log.error("Cannot find ServiceDefinition resource for %s", process_instance.name)

            self.container.resource_registry.create_association(process_instance._proc_svc_id, "hasProcess", proc_id)

        elif process_instance._proc_type == "agent":
            # Registration of AGENT process: in Directory
            caps = process_instance.get_capabilities()
            self.container.directory.register("/Agents", process_instance.id,
                **dict(name=process_instance._proc_name,
                    container=process_instance.container.id,
                    resource_id=process_instance.resource_id,
                    agent_id=process_instance.agent_id,
                    def_id=process_instance.agent_def_id,
                    capabilities=caps))

        self._call_proc_state_changed(process_instance, ProcessStateEnum.RUNNING)

    def terminate_process(self, process_id, do_notifications=True):
        """
        Terminates a process and all its resources. Termination is graceful with timeout.

        @param  process_id          The id of the process to terminate. Should exist in the container's
                                    list of processes or this will raise.
        @param  do_notifications    If True, emits process state changes for TERMINATING and TERMINATED.
                                    If False, supresses any state changes. Used near EXITED and FAILED.
        """
        process_instance = self.procs.get(process_id, None)
        if not process_instance:
            raise BadRequest("Cannot terminate. Process id='%s' unknown on container id='%s'" % (
                                        process_id, self.container.id))

        log.info("ProcManager.terminate_process: %s -> pid=%s", process_instance._proc_name, process_id)

        if do_notifications:
            self._call_proc_state_changed(process_instance, ProcessStateEnum.TERMINATING)

        self._process_quit(process_instance)

        self._unregister_process(process_id, process_instance)

        if do_notifications:
            self._call_proc_state_changed(process_instance, ProcessStateEnum.TERMINATED)

    def _unregister_process(self, process_id, process_instance):
        # Remove process registration in resource registry
        if process_instance._proc_res_id:
            try:
                self.container.resource_registry.delete(process_instance._proc_res_id, del_associations=True)
            except NotFound: #, HTTPException):
                # if it's already gone, it's already gone!
                pass

        # Cleanup for specific process types
        if process_instance._proc_type == "service":
            # Check if this is the last process for this service and do auto delete service resources here
            svcproc_list = []
            try:
                svcproc_list, _ = self.container.resource_registry.find_objects(process_instance._proc_svc_id,
                    "hasProcess", "Process", id_only=True)
            except ResourceNotFound:
                # if it's already gone, it's already gone!
                pass

            if not svcproc_list:
                try:
                    self.container.resource_registry.delete(process_instance._proc_svc_id, del_associations=True)
                except NotFound:
                    # if it's already gone, it's already gone!
                    pass

        elif process_instance._proc_type == "agent":
            self.container.directory.unregister_safe("/Agents", process_instance.id)

        # Remove internal registration in container
        del self.procs[process_id]
        if process_instance._proc_name in self.procs_by_name:
            del self.procs_by_name[process_instance._proc_name]
        else:
            log.warn("Process name %s not in local registry", process_instance.name)
