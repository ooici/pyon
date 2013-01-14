#!/usr/bin/env python

"""Capability Container"""

__author__ = 'Adam R. Smith, Michael Meisinger, Dave Foster <dfoster@asascience.com>'

from pyon.container.apps import AppManager
from pyon.container.procs import ProcManager
from pyon.core import bootstrap
from pyon.core.bootstrap import CFG
from pyon.core.exception import ContainerError
from pyon.core.governance.governance_controller import GovernanceController
from pyon.datastore.datastore import DataStore, DatastoreManager
from pyon.event.event import EventRepository, EventPublisher
from pyon.ion.directory import Directory
from pyon.ion.exchange import ExchangeManager
from pyon.ion.resregistry import ResourceRegistry
from pyon.ion.state import StateRepository
from pyon.ion.endpoint import ProcessRPCServer
from pyon.net.transport import LocalRouter
from pyon.util.containers import get_default_container_id
from pyon.util.file_sys import FileSystem
from pyon.util.log import log
from pyon.util.sflow import SFlowManager
from pyon.util.context import LocalContextMixin
from pyon.util.greenlet_plugin import GreenletLeak

from interface.objects import ContainerStateEnum
from interface.services.icontainer_agent import BaseContainerAgent

import atexit
import msgpack
import os
import signal
import traceback
import sys
import gevent
from contextlib import contextmanager


class Container(BaseContainerAgent):
    """
    The Capability Container. Its purpose is to spawn/monitor processes and services
    that do the bulk of the work in the ION system. It also manages connections to the Exchange
    and the various forms of datastores in the systems.
    """

    # Singleton static variables
    #node        = None
    id          = None
    name        = None
    pidfile     = None
    instance    = None

    def __init__(self, *args, **kwargs):
        BaseContainerAgent.__init__(self, *args, **kwargs)

        self._is_started = False
        # set container id and cc_agent name (as they are set in base class call)
        self.id = get_default_container_id()
        self.name = "cc_agent_%s" % self.id
        self._capabilities = []

        bootstrap.container_instance = self
        Container.instance = self

        log.debug("Container (sysname=%s) initializing ..." % bootstrap.get_sys_name())

        # Keep track of the overrides from the command-line, so they can trump app/rel file data
        self.spawn_args = kwargs

        # DatastoreManager - controls access to Datastores (both mock and couch backed)
        self.datastore_manager = DatastoreManager()

        # TODO: Do not start a capability here. Symmetric start/stop
        self.datastore_manager.start()
        self._capabilities.append("DATASTORE_MANAGER")

        # Instantiate Directory
        self.directory = Directory()

        # internal router
        self.local_router = None

        # Create this Container's specific ExchangeManager instance
        self.ex_manager = ExchangeManager(self)

        # Create this Container's specific ProcManager instance
        self.proc_manager = ProcManager(self)

        # Create this Container's specific AppManager instance
        self.app_manager = AppManager(self)

        # File System - Interface to the OS File System, using correct path names and setups
        self.file_system = FileSystem(CFG)

        # Governance Controller - manages the governance related interceptors
        self.governance_controller = GovernanceController(self)

        # sFlow manager - controls sFlow stat emission
        self.sflow_manager = SFlowManager(self)

        # Coordinates the container start
        self._status = "INIT"

        # protection for when the container itself is used as a Process for clients
        self.container = self

        # publisher, initialized in start()
        self.event_pub = None

        # context-local storage
        self.context = LocalContextMixin()

        log.debug("Container initialized, OK.")

    def start(self):
        log.debug("Container starting...")
        if self._is_started:
            raise ContainerError("Container already started")

        # Check if this UNIX process already runs a Container.
        self.pidfile = "cc-pid-%d" % os.getpid()
        if os.path.exists(self.pidfile):
            raise ContainerError("Container.on_start(): Container is a singleton per UNIX process. Existing pid file found: %s" % self.pidfile)

        # write out a PID file containing our agent messaging name
        with open(self.pidfile, 'w') as f:
            pid_contents = {'messaging': dict(CFG.server.amqp),
                            'container-agent': self.name,
                            'container-xp': bootstrap.get_sys_name()}
            f.write(msgpack.dumps(pid_contents))
            atexit.register(self._cleanup_pid)
            self._capabilities.append("PID_FILE")

        # set up abnormal termination handler for this container
        def handl(signum, frame):
            try:
                self._cleanup_pid()     # cleanup the pidfile first
                self.quit()             # now try to quit - will not error on second cleanup pidfile call
            finally:
                signal.signal(signal.SIGTERM, self._normal_signal)
                os.kill(os.getpid(), signal.SIGTERM)
        self._normal_signal = signal.signal(signal.SIGTERM, handl)

        # set up greenlet debugging signal handler
        gevent.signal(signal.SIGUSR2, self._handle_sigusr2)

        self.datastore_manager.start()
        self._capabilities.append("DATASTORE_MANAGER")

        self._capabilities.append("DIRECTORY")

        # Event repository
        self.event_repository = EventRepository()
        self.event_pub = EventPublisher()
        self._capabilities.append("EVENT_REPOSITORY")

        # Local resource registry
        self.resource_registry = ResourceRegistry()
        self._capabilities.append("RESOURCE_REGISTRY")

        # Persistent objects
        self.datastore_manager.get_datastore("objects", DataStore.DS_PROFILE.OBJECTS)

        # State repository
        self.state_repository = StateRepository()
        self._capabilities.append("STATE_REPOSITORY")

        # internal router for local transports
        self.local_router = LocalRouter(bootstrap.get_sys_name())
        self.local_router.start()
        self.local_router.ready.wait(timeout=2)
        self._capabilities.append("LOCAL_ROUTER")

        # Start ExchangeManager, which starts the node (broker connection)
        self.ex_manager.start()
        self._capabilities.append("EXCHANGE_MANAGER")

        self.proc_manager.start()
        self._capabilities.append("PROC_MANAGER")

        self.app_manager.start()
        self._capabilities.append("APP_MANAGER")

        self.governance_controller.start()
        self._capabilities.append("GOVERNANCE_CONTROLLER")

        if CFG.get_safe('container.sflow.enabled', False):
            self.sflow_manager.start()
            self._capabilities.append("SFLOW_MANAGER")

        # Start the CC-Agent API
        rsvc = ProcessRPCServer(node=self.node, from_name=self.name, service=self, process=self)

        cleanup = lambda _: self.proc_manager._cleanup_method(self.name, rsvc)

        # Start an ION process with the right kind of endpoint factory
        proc = self.proc_manager.proc_sup.spawn(name=self.name, listeners=[rsvc], service=self, cleanup_method=cleanup)
        self.proc_manager.proc_sup.ensure_ready(proc)
        proc.start_listeners()
        self._capabilities.append("CONTAINER_AGENT")

        self.event_pub.publish_event(event_type="ContainerLifecycleEvent",
                                     origin=self.id, origin_type="CapabilityContainer",
                                     sub_type="START",
                                     state=ContainerStateEnum.START)

        self._is_started    = True
        self._status        = "RUNNING"

        log.info("Container (%s) started, OK." , self.id)

    def _handle_sigusr2(self):#, signum, frame):
        """
        Handles SIGUSR2, prints debugging greenlet information.
        """
        gls = GreenletLeak.get_greenlets()

        allgls = []

        for gl in gls:
            status = GreenletLeak.format_greenlet(gl)

            # build formatted output:
            # Greenlet at 0xdeadbeef
            #     self: <EndpointUnit at 0x1ffcceef>
            #     func: bound, EndpointUnit.some_func

            status[0].insert(0, "%s at %s:" % (gl.__class__.__name__, hex(id(gl))))
            # indent anything in status a second time
            prefmt = [s.replace("\t", "\t\t") for s in status[0]]
            prefmt.append("traceback:")

            for line in status[1]:
                for subline in line.split("\n")[0:2]:
                    prefmt.append(subline)

            glstr = "\n\t".join(prefmt)

            allgls.append(glstr)

        # print it out!
        print >>sys.stderr, "\n\n".join(allgls)
        with open("gls-%s" % os.getpid(), "w") as f:
            f.write("\n\n".join(allgls))


    @property
    def node(self):
        """
        Returns the active/default Node that should be used for most communication in the system.

        Defers to exchange manager, but only if it has been started, otherwise returns None.
        """
        if "EXCHANGE_MANAGER" in self._capabilities:
            return self.ex_manager.default_node

        return None

    @contextmanager
    def _push_status(self, new_status):
        """
        Temporarily sets the internal status flag.
        Use this as a decorator or in a with-statement before calling a temporary status changing
        method, like start_rel_from_url.
        """
        curstatus = self._status
        self._status = new_status
        try:
            yield
        finally:
            self._status = curstatus

    def serve_forever(self):
        """ Run the container until killed. """
        log.debug("In Container.serve_forever")

        if not self.proc_manager.proc_sup.running:
            self.start()

        # serve forever short-circuits if immediate is on and children len is ok
        num_procs = len(self.proc_manager.proc_sup.children)
        immediate = CFG.system.get('immediate', False)
        if not (immediate and num_procs == 1):  # only spawned greenlet is the CC-Agent

            # print a warning just in case
            if immediate and num_procs != 1:
                log.warn("CFG.system.immediate=True but number of spawned processes is not 1 (%d)", num_procs)

            try:
                # This just waits in this Greenlet for all child processes to complete,
                # which is triggered somewhere else.
                self.proc_manager.proc_sup.join_children()
            except (KeyboardInterrupt, SystemExit) as ex:
                log.info('Received a kill signal, shutting down the container.')

                if hasattr(self, 'gl_parent_watch') and self.gl_parent_watch is not None:
                    self.gl_parent_watch.kill()

            except:
                log.exception('Unhandled error! Forcing container shutdown')
        else:
            log.debug("Container.serve_forever short-circuiting due to CFG.system.immediate")

        self.proc_manager.proc_sup.shutdown(CFG.cc.timeout.shutdown)

    def status(self):
        """
        Returns the internal status.
        """
        return self._status

    def _cleanup_pid(self):
        if self.pidfile:
            log.debug("Cleanup pidfile: %s", self.pidfile)
            try:
                os.remove(self.pidfile)
            except Exception, e:
                log.warn("Pidfile could not be deleted: %s" % str(e))
            self.pidfile = None

    def has_capability(self, capability):
        """
        Returns True if the given capability is in the list of container capabilities.
        """
        return capability in self._capabilities

    def stop(self):
        log.info("=============== Container stopping... ===============")

        if self.event_pub is not None:
            self.event_pub.publish_event(event_type="ContainerLifecycleEvent",
                                         origin=self.id, origin_type="CapabilityContainer",
                                         sub_type="TERMINATE",
                                         state=ContainerStateEnum.TERMINATE)

        while self._capabilities:
            capability = self._capabilities.pop()
            log.debug("stop(): Stopping '%s'" % capability)
            try:
                self._stop_capability(capability)
            except Exception as ex:
                log.exception("Container stop(): Error stop %s" % capability)

        Container.instance = None
        from pyon.core import bootstrap
        bootstrap.container_instance = None

        self._is_started = False

        log.debug("Container stopped, OK.")

    def start_app(self, appdef=None, config=None):
        with self._push_status("START_APP"):
            return self.app_manager.start_app(appdef=appdef, config=config)

    def start_app_from_url(self, app_url=''):
        with self._push_status("START_APP_FROM_URL"):
            return self.app_manager.start_app_from_url(app_url=app_url)

    def start_rel(self, rel=None):
        with self._push_status("START_REL"):
            return self.app_manager.start_rel(rel=rel)

    def start_rel_from_url(self, rel_url='', config=None):
        with self._push_status("START_REL_FROM_URL"):
            return self.app_manager.start_rel_from_url(rel_url=rel_url, config=config)

    def _stop_capability(self, capability):
        if capability == "CONTAINER_AGENT":
            pass

        elif capability == "APP_MANAGER":
            self.app_manager.stop()

        elif capability == "PROC_MANAGER":
            self.proc_manager.stop()

        elif capability == "EXCHANGE_MANAGER":
            self.ex_manager.stop()

        elif capability == "LOCAL_ROUTER":
            if self.local_router is not None:
                self.local_router.stop()

        elif capability == "EVENT_REPOSITORY":
            # close event repository (possible CouchDB connection)
            self.event_repository.close()
            self.event_pub.close()

        elif capability == "STATE_REPOSITORY":
            # close state repository (possible CouchDB connection)
            self.state_repository.close()

        elif capability == "RESOURCE_REGISTRY":
            # close state resource registry (possible CouchDB connection)
            self.resource_registry.close()

        elif capability == "DIRECTORY":
            # Close directory (possible CouchDB connection)
            self.directory.close()

        elif capability == "DATASTORE_MANAGER":
            # close any open connections to datastores
            self.datastore_manager.stop()

        elif capability == "GOVERNANCE_CONTROLLER":
            self.governance_controller.stop()

        elif capability == "PID_FILE":
            self._cleanup_pid()

        elif capability == "SFLOW_MANAGER":
            self.sflow_manager.stop()

        else:
            raise ContainerError("Cannot stop capability: %s" % capability)

    def fail_fast(self, err_msg="", skip_stop=False):
        """
        Container needs to shut down and NOW.
        """
        log.error("Fail Fast: %s", err_msg)
        if not skip_stop:
            self.stop()
        log.error("Fail Fast: killing container")

        traceback.print_exc()

        # The exit code of the terminated process is set to non-zero
        os.kill(os.getpid(), signal.SIGTERM)
