#!/usr/bin/env python

"""
Capability Container base class
TODO:
[ ] server and client name argument is a short cut
[ ] generic server and client delivery loop
[ ] decide on how Channel Type is passed/associated with gen server/client
[ ] Endpoint might be better as a 'factory' that can make handler instances
per request. This will also facilitate the Endpoint holding 'business'
objects/resources that each request has access to. This will keep the
actual handlers functional.
"""
import sys

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

from zope.interface import providedBy
from zope.interface import Interface, implements

import string
import os
import msgpack
import atexit
import signal

from pyon.core.bootstrap import CFG, sys_name, bootstrap_pyon

from pyon.container.apps import AppManager
from pyon.container.procs import ProcManager
from pyon.directory.directory import Directory
from pyon.net.endpoint import ProcessRPCServer, RPCServer
from pyon.net import messaging
from pyon.util.log import log
from pyon.util.containers import DictModifier, dict_merge
from pyon.ion.exchange import ExchangeManager


class IContainerAgent(Interface):

    def spawn_process(name=None, module=None, cls=None, config=None):
        pass

    def start_app(appdef=None, processapp=None, config=None):
        pass

    def start_app_from_url(app_url=""):
        pass

    def start_rel(rel=None):
        pass

    def start_rel_from_url(rel_url=""):
        pass

    def stop():
        pass

class Container(object):
    implements(IContainerAgent)
    """
    The Capability Container. Its purpose is to spawn/monitor processes and services
    that do the bulk of the work in the ION system.
    """
    node = None
    id = string.replace('%s_%d' % (os.uname()[1], os.getpid()), ".", "_")
    name = "cc_agent_%s" % (id)
    pidfile = None
    instance = None

    def __init__(self, *args, **kwargs):
        Container.instance = self

        # TODO: Bug: Replacing CFG instance not work because references are already public. Update directly
        dict_merge(CFG, kwargs)
        from pyon.core import bootstrap
        bootstrap.sys_name = CFG.system.name or bootstrap.sys_name
        log.debug("Container (sysname=%s) initializing ..." % bootstrap.sys_name)

        # Keep track of the overrides from the command-line, so they can trump app/rel file data
        self.spawn_args = DictModifier(CFG, kwargs)

        # Load object and service registry
        bootstrap_pyon()

        # Create this Container's specific ExchangeManager instance
        self.ex_manager = ExchangeManager(self)

        # Create this Container's specific ProcManager instance
        self.proc_manager = ProcManager(self)

        # Create this Container's specific AppManager instance
        self.app_manager = AppManager(self)
        
        log.debug("Container initialized, OK.")


    def start(self):
        log.debug("Container starting...")

        # Check if this UNIX process already runs a Container.
        self.pidfile = "cc-pid-%d" % os.getpid()
        if os.path.exists(self.pidfile):
            raise Exception("Container.on_start(): Container is a singleton per UNIX process. Existing pid file found: %s" % self.pidfile)

        # write out a PID file containing our agent messaging name
        with open(self.pidfile, 'w') as f:
            pid_contents = {'messaging': dict(CFG.server.amqp),
                            'container-agent': self.name,
                            'container-xp': sys_name }
            f.write(msgpack.dumps(pid_contents))
            atexit.register(self._cleanup_pid)

        # set up abnormal termination handler for this container
        def handl(signum, frame):
            try:
                self._cleanup_pid()     # cleanup the pidfile first
                self.quit()             # now try to quit - will not error on second cleanup pidfile call
            finally:
                signal.signal(signal.SIGTERM, self._normal_signal)
                os.kill(os.getpid(), signal.SIGTERM)
        self._normal_signal = signal.signal(signal.SIGTERM, handl)


        # Start ExchangeManager. In particular establish broker connection
        self.ex_manager.start()

        # TODO: Move this in ExchangeManager - but there is an error
        self.node, self.ioloop = messaging.make_node() # TODO: shortcut hack


        # Instantiate Directory singleton and self-register
        # TODO: At this point, there is no special config override
        self.directory = Directory()
        self.directory.register("/Containers", self.id, cc_agent=self.name)

        self.proc_manager.start()

        self.app_manager.start()

        # Start the CC-Agent API
        #rsvc = ProcessRPCServer(node=self.node, name=self.name, service=self)
        # @TODO: must have a process (currently BaseService??) to pass into ProcessRPCServer, so use regular RPCServer for now
        rsvc = RPCServer(node=self.node, name=self.name, service=self)

        # Start an ION process with the right kind of endpoint factory
        self.proc_manager.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=rsvc)
        rsvc.get_ready_event().wait(timeout=10)   # @TODO: no hardcode
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
        log.debug("Container stopping...")

        self.app_manager.stop()

        self.proc_manager.stop()

        self.ex_manager.stop()

        # Unregister from directory
        self.directory.unregister("/Container", self.id)

        self._cleanup_pid()
        log.debug("Container stopped, OK.")

        Container.instance = None
