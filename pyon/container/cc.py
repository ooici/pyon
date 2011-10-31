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
[ ] Determine a container ID
[ ] Use the unique container ID in the name
"""

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

from zope.interface import providedBy
from zope.interface import Interface, implements

import string
import os
import msgpack

from pyon.container.apps import AppManager
from pyon.core.bootstrap import CFG, sys_name, populate_registry
from pyon.net.endpoint import RPCServer, BinderListener
from pyon.net import messaging
from pyon.util.log import log
from pyon.util.containers import DictModifier

from pyon.ion.exchange import ExchangeManager
from pyon.ion.process import IonProcessSupervisor


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

class Container(object):
    implements(IContainerAgent)
    """
    The Capability Container. Its purpose is to spawn/monitor processes and services
    that do the bulk of the work in the ION system.
    """
    node = None
    id = string.replace('%s.%d' % (os.uname()[1], os.getpid()), ".", "_")
    name = "cc_agent_%s" % (id)
    pidfile = None

    def __init__(self, *args, **kwargs):
        log.debug("Container.__init__")

        # Create this Container's specific ExchangeManager instance
        self.ex_manager = ExchangeManager(self)

        # Create this Container's specific AppManager instance
        self.app_manager = AppManager(self)

        # The pyon worker process supervisor
        self.proc_sup = IonProcessSupervisor(heartbeat_secs=CFG.cc.timeout.heartbeat)

        # Keep track of the overrides from the command-line, so they can trump app/rel file data
        self.spawn_args = DictModifier(CFG, kwargs)

    def start(self):
        log.debug("In Container.start")

        # Bootstrap object registry
        populate_registry()

        self.pidfile = "cc-pid-%d" % os.getpid()
        if os.path.exists(self.pidfile):
            raise Exception("Existing pid file already found: %s" % self.pidfile)

        self.proc_sup.start()

        self.node, self.ioloop = messaging.make_node() # TODO: shortcut hack

        # Start ExchangeManager. In particular establish broker connection
        self.ex_manager.start()

        # Start the CC-Agent API
        rsvc = RPCServer(node=self.node, name=self.name, service=self)

        # Start an ION process with the right kind of endpoint factory
        listener = BinderListener(self.node, self.name, rsvc, None, None)
        self.proc_sup.spawn((CFG.cc.proctype or 'green', None), listener=listener)

        # write out a PID file containing our agent messaging name
        with open(self.pidfile, 'w') as f:
            pid_contents = {'messaging': dict(CFG.server.amqp),
                            'container-agent': self.name,
                            'container-xp': sys_name }
            f.write(msgpack.dumps(pid_contents))


        self.app_manager.start()

        return listener.get_ready_event()


    def stop(self):
        log.debug("In Container.stop")
        # TODO: Have a choice of shutdown behaviors for waiting on children, timeouts, etc
        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)
        try:
            os.unlink(self.pidfile)
        except Exception, e:
            log.warn("Pidfile did not unlink: %s" % str(e))

    def serve_forever(self):
        """ Run the container until killed. """
        log.debug("In Container.serve_forever")
        
        if not self.proc_sup.running:
            self.start()
            
        try:
            self.proc_sup.join_children()
        except (KeyboardInterrupt, SystemExit) as ex:
            log.info('Received a kill signal, shutting down the container.')
        except:
            log.exception('Unhandled error! Forcing container shutdown')

        self.proc_sup.shutdown(CFG.cc.timeout.shutdown)
            
