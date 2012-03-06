#!/usr/bin/env python

"""
Capability Container base class
"""

__author__ = 'Adam R. Smith, Michael Meisinger, Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

import atexit
import msgpack
import os
import signal
import string

from pyon.container.apps import AppManager
from pyon.container.procs import ProcManager
from pyon.core import bootstrap
from pyon.core.bootstrap import CFG, bootstrap_pyon
from pyon.core.exception import ContainerError
from pyon.datastore.datastore import DataStore, DatastoreManager
from pyon.event.event import EventRepository
from pyon.ion.directory import Directory
from pyon.ion.exchange import ExchangeManager
from pyon.ion.resregistry import ResourceRegistry
from pyon.ion.state import StateRepository
from pyon.net.endpoint import ProcessRPCServer
from pyon.net import messaging
from pyon.util.file_sys import FileSystem
from pyon.util.log import log
from pyon.util.containers import DictModifier, dict_merge
from pyon.core.governance.governance_controller import GovernanceController

from interface.services.icontainer_agent import BaseContainerAgent
from contextlib import contextmanager


class Container(BaseContainerAgent):
    """
    The Capability Container. Its purpose is to spawn/monitor processes and services
    that do the bulk of the work in the ION system.
    """

    # Singleton static variables
    node        = None
    id          = None
    name        = None
    pidfile     = None
    instance    = None

    def __init__(self, *args, **kwargs):
        BaseContainerAgent.__init__(self, *args, **kwargs)

        self._is_started = False

        # set id and name (as they are set in base class call)
        self.id = string.replace('%s_%d' % (os.uname()[1], os.getpid()), ".", "_")
        self.name = "cc_agent_%s" % self.id

        Container.instance = self

        # TODO: Bug: Replacing CFG instance not work because references are already public. Update directly
        dict_merge(CFG, kwargs, inplace=True)
        from pyon.core import bootstrap
        bootstrap.container_instance = self
        bootstrap.assert_configuration(CFG)
        log.debug("Container (sysname=%s) initializing ..." % bootstrap.get_sys_name())

        # Keep track of the overrides from the command-line, so they can trump app/rel file data
        self.spawn_args = kwargs

        # Load object and service registry etc.
        bootstrap_pyon()

        # Create this Container's specific ExchangeManager instance
        self.ex_manager = ExchangeManager(self)

        # Create this Container's specific ProcManager instance
        self.proc_manager = ProcManager(self)

        # Create this Container's specific AppManager instance
        self.app_manager = AppManager(self)

        # DatastoreManager - controls access to Datastores (both mock and couch backed)
        self.datastore_manager = DatastoreManager()

        # File System - Interface to the OS File System, using correct path names and setups
        self.file_system = FileSystem(CFG)

        # Governance Controller - manages the governance related interceptors
        self.governance_controller = GovernanceController()

        # Coordinates the container start
        self._is_started = False
        self._capabilities = []
        self._status = "INIT"

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
                            'container-xp': bootstrap.get_sys_name() }
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

        self._capabilities.append("EXCHANGE_CONNECTION")

        self.datastore_manager.start()
        self._capabilities.append("DATASTORE_MANAGER")

        # Instantiate Directory and self-register
        self.directory = Directory()
        self.directory.register("/Containers", self.id, cc_agent=self.name)
        self._capabilities.append("DIRECTORY")

        # Local resource registry
        self.resource_registry = ResourceRegistry()
        self._capabilities.append("RESOURCE_REGISTRY")

        # Create other repositories to make sure they are there and clean if needed

        self.datastore_manager.get_datastore("objects", DataStore.DS_PROFILE.OBJECTS)

        self.state_repository = StateRepository()
        self._capabilities.append("STATE_REPOSITORY")

        self.event_repository = EventRepository()
        self._capabilities.append("EVENT_REPOSITORY")

        # Start ExchangeManager, which starts the node (broker connection)
        self.node, self.ioloop = self.ex_manager.start()
        self._capabilities.append("EXCHANGE_MANAGER")

        self.proc_manager.start()
        self._capabilities.append("PROC_MANAGER")

        self.app_manager.start()
        self._capabilities.append("APP_MANAGER")

        self.governance_controller.start()
        self._capabilities.append("GOVERNANCE_CONTROLLER")


        # Start the CC-Agent API
        rsvc = ProcessRPCServer(node=self.node, from_name=self.name, service=self, process=self)

        # Start an ION process with the right kind of endpoint factory
        proc = self.proc_manager.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=rsvc)
        self.proc_manager.proc_sup.ensure_ready(proc)
        self._capabilities.append("CONTAINER_AGENT")

        self._is_started    = True
        self._status        = "RUNNING"

        log.info("Container started, OK.")

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

    def stop(self):
        log.info("=============== Container stopping... ===============")

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

    def start_rel_from_url(self, rel_url=''):
        with self._push_status("START_REL_FROM_URL"):
            return self.app_manager.start_rel_from_url(rel_url=rel_url)

    def _stop_capability(self, capability):
        if capability == "CONTAINER_AGENT":
            pass

        elif capability == "APP_MANAGER":
            self.app_manager.stop()

        elif capability == "PROC_MANAGER":
            self.proc_manager.stop()

        elif capability == "EXCHANGE_MANAGER":
            self.ex_manager.stop()

        elif capability == "EVENT_REPOSITORY":
            # close event repository (possible CouchDB connection)
            self.event_repository.close()

        elif capability == "STATE_REPOSITORY":
            # close state repository (possible CouchDB connection)
            self.state_repository.close()

        elif capability == "RESOURCE_REGISTRY":
            # close state resource registry (possible CouchDB connection)
            self.resource_registry.close()

        elif capability == "DIRECTORY":
            # Unregister from directory
            self.directory.unregister_safe("/Containers", self.id)

            # Close directory (possible CouchDB connection)
            self.directory.close()

        elif capability == "DATASTORE_MANAGER":
            # close any open connections to datastores
            self.datastore_manager.stop()

        elif capability == "EXCHANGE_CONNECTION":
            self.node.client.close()
            self.ioloop.kill()
            self.node.client.ioloop.start()     # loop until connection closes
            # destroy AMQP connection

        elif capability == "GOVERNANCE_CONTROLLER":
            self.governance_controller.stop()

        elif capability == "PID_FILE":
            self._cleanup_pid()

        else:
            raise ContainerError("Cannot stop capability: %s" % capability)

    def fail_fast(self, err_msg=""):
        """
        Container needs to shut down and NOW.
        """
        log.error("Fail Fast: %s", err_msg)
        self.stop()
        log.error("Fail Fast: killing container")

        # The exit code of the terminated process is set to non-zero
        os.kill(os.getpid(), signal.SIGTERM)
