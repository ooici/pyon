#!/usr/bin/env python


__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.core.process import GreenProcess, PythonProcess, GreenProcessSupervisor
from pyon.net import messaging, endpoint
from pyon.service.service import BaseService
from gevent.event import Event, waitall
from gevent.queue import Queue
import time
from pyon.util.async import wait, spawn
import threading

class IonProcessBase(object):
    """
    Form the base of an ION process.
    Just add greenlets or python processes to complete.
    """

    def __init__(self, listeners=None, name=None, routing_obj=None):
        self.listeners      = listeners
        self.name           = name
        self.routing_obj    = routing_obj       # where the requests go
        self._child_procs   = []
        self._ctrl_queue    = Queue()

    def _child_failed(self, child):
        """
        Occurs when any child greenlet fails.

        Propogates the error up to the process supervisor.
        """
        self.proc.throw(child.value)

    def target(self, *args, **kwargs):
        """
        Control entrypoint. Setup the base properties for this process (mainly a listener).
        """
        if self.name:
            threading.current_thread().name = self.name

        for listener in self.listeners:
            self._child_procs.append(spawn(listener.listen))

        # spawn control flow loop
        self._child_procs.append(spawn(self._control_flow))

        # link them all to a failure handler
        map(lambda x: x.link_exception(self._child_failed), self._child_procs)

        # wait on them
        self._wait_children()

    def _control_flow(self):
        for call in self._ctrl_queue:
            # @TODO!
            pass

    def _notify_stop(self):
        map(lambda x: x.close(), self.listeners)
        self._ctrl_queue.put(StopIteration)

        self._wait_children()

        super(IonProcessBase, self)._notify_stop()

    def _wait_children(self):
        pass

class GreenIonProcess(IonProcessBase, GreenProcess):

    def __init__(self, target=None, listeners=None, name=None, **kwargs):
        IonProcessBase.__init__(self, listeners=listeners, name=name)
        GreenProcess.__init__(self, target=target, **kwargs)

    def get_ready_event(self):
        ev = Event()
        def allready(ev):
            waitall([x.get_ready_event() for x in self.listeners])
            ev.set()

        spawn(allready, ev)
        return ev

    def _wait_children(self):
        wait(self._child_procs)

class PythonIonProcess(IonProcessBase, PythonProcess):
    pass

class IonProcessSupervisor(GreenProcessSupervisor):
    type_callables = {
          'green': GreenIonProcess
        , 'python': PythonIonProcess
    }

# ---------------------------------------------------------------------------------------------------

class StandaloneProcess(BaseService):
    """
    A process is an ION process of type "standalone" that has an incoming messaging
    attachment for the process and operations as defined in a service YML.
    """
    process_type = "standalone"

class SimpleProcess(BaseService):
    """
    A simple process is an ION process of type "simple" that has no incoming messaging
    attachment.
    """
    process_type = "simple"

class ImmediateProcess(BaseService):
    """
    An immediate process is an ION process of type "immediate" that does its action in
    the on_init and on_start hooks, and that it terminated immediately after completion.
    Has no messaging attachment.
    """
    process_type = "immediate"
