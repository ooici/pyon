#!/usr/bin/env python


__author__ = 'Adam R. Smith, Michael Meisinger, Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.core.process import GreenProcess, GreenProcessSupervisor
from pyon.service.service import BaseService
from gevent.event import Event, waitall, AsyncResult
from gevent.queue import Queue
from gevent import greenlet
from pyon.util.async import wait, spawn
import threading

class GreenIonProcess(GreenProcess):
    """
    Form the base of an ION process.
    Just add greenlets or python processes to complete.
    """

    def __init__(self, target=None, listeners=None, name=None, **kwargs):
        self.listeners      = listeners
        self.name           = name
        self._child_procs   = []
        self._ctrl_queue    = Queue()

        GreenProcess.__init__(self, target=target, **kwargs)

    def _child_failed(self, child):
        """
        Occurs when any child greenlet fails.

        Propogates the error up to the process supervisor.
        """
        self.proc.throw(child.exception)

    def target(self, *args, **kwargs):
        """
        Control entrypoint. Setup the base properties for this process (mainly a listener).
        """
        if self.name:
            threading.current_thread().name = self.name

        # - tell all listeners they need to call here for sync
        # - spawn listen loops
        for listener in self.listeners:
            listener.routing_call = self._routing_call
            self._child_procs.append(spawn(listener.listen))

        # spawn control flow loop
        self._child_procs.append(spawn(self._control_flow))

        # link them all to a failure handler
        map(lambda x: x.link_exception(self._child_failed), self._child_procs)

        # wait on them
        wait(self._child_procs)

    def _routing_call(self, call, callargs):
        """
        Endpoints call into here to synchronize across the entire IonProcess.

        Returns immediately with an AsyncResult that can be waited on. Calls
        are made by the loop in _control_flow. We pass in the calling greenlet so
        exceptions are raised in the correct context.
        """
        ar = AsyncResult()

        self._ctrl_queue.put((greenlet.getcurrent(), ar, call, callargs))
        return ar

    def _control_flow(self):
        """
        Main process thread of execution method.

        This method is run inside a greenlet and exists for each ION process. Listeners
        attached to the process, either RPC Servers or Subscribers, synchronize their calls
        by placing future calls into the queue by calling _routing_call.  This is all done
        automatically for you by the Container's Process Manager.

        This method blocks until there are calls to be made in the synchronized queue, and
        then calls from within this greenlet.  Any exception raised is caught and re-raised
        in the greenlet that originally scheduled the call.  If successful, the AsyncResult
        created at scheduling time is set with the result of the call.
        """
        for calltuple in self._ctrl_queue:
            calling_gl, ar, call, callargs = calltuple
            log.debug("control_flow making call: %s %s", call, callargs)

            res = None
            try:
                res = call(**callargs)
            except Exception as e:
                # raise the exception in the calling greenlet, and don't
                # wait for it to die - it's likely not going to do so.
                calling_gl.kill(exception=e, block=False)

            ar.set(res)

    def _notify_stop(self):
        """
        Called when the process is about to be shut down.

        Instructs all listeners to close, puts a StopIteration into the synchronized queue,
        and waits for the listeners to close and for the control queue to exit.
        """
        map(lambda x: x.close(), self.listeners)
        self._ctrl_queue.put(StopIteration)

        wait(self._child_procs)

        GreenProcess._notify_stop(self)

    def get_ready_event(self):
        """
        Returns an Event that is set when all the listeners in this Process are running.
        """
        ev = Event()
        def allready(ev):
            waitall([x.get_ready_event() for x in self.listeners])
            ev.set()

        spawn(allready, ev)
        return ev

class IonProcessSupervisor(GreenProcessSupervisor):
    type_callables = {
          'green': GreenIonProcess
#        , 'python': PythonIonProcess
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
