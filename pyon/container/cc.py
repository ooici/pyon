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
from pyon.ion.state import StateRepository
from pyon.net.endpoint import ProcessRPCServer
from pyon.net import messaging
from pyon.util.file_sys import FileSystem
from pyon.util.log import log
from pyon.util.containers import DictModifier, dict_merge

from interface.services.icontainer_agent import BaseContainerAgent


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
        bootstrap.sys_name = CFG.system.name or bootstrap.sys_name
        log.debug("Container (sysname=%s) initializing ..." % bootstrap.sys_name)

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

        # Coordinates the container start
        self._is_started = False
        self._capabilities = []

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
            from pyon.core.bootstrap import get_sys_name
            pid_contents = {'messaging': dict(CFG.server.amqp),
                            'container-agent': self.name,
                            'container-xp': get_sys_name() }
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

        # Create other repositories to make sure they are there and clean if needed
        self.datastore_manager.get_datastore("resources", DataStore.DS_PROFILE.RESOURCES)

        self.datastore_manager.get_datastore("objects", DataStore.DS_PROFILE.OBJECTS)

        self.state_repository = StateRepository()
        self._capabilities.append("STATE_REPOSITORY")

        self.event_repository = EventRepository()
        self._capabilities.append("EVENT_REPOSITORY")

        # Start ExchangeManager. In particular establish broker connection
        self.ex_manager.start()

        # TODO: Move this in ExchangeManager - but there is an error
        self.node, self.ioloop = messaging.make_node() # TODO: shortcut hack
        self._capabilities.append("EXCHANGE_MANAGER")

        self.proc_manager.start()
        self._capabilities.append("PROC_MANAGER")

        self.app_manager.start()
        self._capabilities.append("APP_MANAGER")

        # Start the CC-Agent API
        rsvc = ProcessRPCServer(node=self.node, name=self.name, service=self, process=self)

        # Start an ION process with the right kind of endpoint factory
        proc = self.proc_manager.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=rsvc)
        self.proc_manager.proc_sup.ensure_ready(proc)
        self._capabilities.append("CONTAINER_AGENT")

        self._is_started = True

        log.info("Container started, OK.")

    def serve_forever(self):
        """ Run the container until killed. """
        log.debug("In Container.serve_forever")
        
        if not self.proc_manager.proc_sup.running:
            self.start()
            
        try:
            # This just waits in this Greenlet for all child processes to complete,
            # which is triggered somewhere else.
            self.proc_manager.proc_sup.join_children()
        except (KeyboardInterrupt, SystemExit) as ex:
            log.info('Received a kill signal, shutting down the container.')
        except:
            log.exception('Unhandled error! Forcing container shutdown')

        self.proc_manager.proc_sup.shutdown(CFG.cc.timeout.shutdown)
            
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

    def _stop_capability(self, capability):
        if capability == "CONTAINER_AGENT":
            pass

        elif capability == "APP_MANAGER":
            self.app_manager.stop()

        elif capability == "PROC_MANAGER":
            self.proc_manager.stop()

        elif capability == "EXCHANGE_MANAGER":
            self.ex_manager.stop()


        elif capability == "DIRECTORY":
            # Unregister from directory
            self.directory.unregister_safe("/Container", self.id)

            # Close directory (possible CouchDB connection)
            self.directory.close()

        elif capability == "EVENT_REPOSITORY":
            # close event repository (possible CouchDB connection)
            self.event_repository.close()

        elif capability == "STATE_REPOSITORY":
            # close state repository (possible CouchDB connection)
            self.state_repository.close()

        elif capability == "DATASTORE_MANAGER":
            # close any open connections to datastores
            self.datastore_manager.stop()

        elif capability == "EXCHANGE_CONNECTION":
            self.node.client.close()
            self.ioloop.kill()
            self.node.client.ioloop.start()     # loop until connection closes
            # destroy AMQP connection

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