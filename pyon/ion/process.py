#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger, Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.core.thread import PyonThreadManager, PyonThread, ThreadManager, PyonThreadTraceback, PyonHeartbeatError
from pyon.ion.service import BaseService
from gevent.event import Event, waitall, AsyncResult
from gevent.queue import Queue
from gevent import greenlet, Timeout
from pyon.util.async import spawn
from pyon.core.exception import IonException, ContainerError
from pyon.core.exception import Timeout as IonTimeout
from pyon.util.containers import get_ion_ts, get_ion_ts_millis
from pyon.core.bootstrap import CFG
import threading
import traceback

STAT_INTERVAL_LENGTH = 60000  # Interval time for process saturation stats collection


class OperationInterruptedException(BaseException):
    """
    Interrupted exception. Used by external items timing out execution in the
    IonProcessThread's control thread.

    Derived from BaseException to specifically avoid try/except Exception blocks,
    such as in Publisher's publish_event.
    """
    pass


class IonProcessError(StandardError):
    pass


class IonProcessThread(PyonThread):
    """
    Form the base of an ION process.
    """

    def __init__(self, target=None, listeners=None, name=None, service=None, cleanup_method=None, heartbeat_secs=10, **kwargs):
        """
        Constructs an ION process.

        You don't create one of these directly, the IonProcessThreadManager run by a container does this for
        you via the ProcManager interface. Call the container's spawn_process method and this method will run.

        @param  target          A callable to run in the PyonThread. If None (typical), will use the target method
                                defined in this class.
        @param  listeners       A list of listening endpoints attached to this thread.
        @param  name            The name of this ION process.
        @param  service         An instance of the BaseService derived class which contains the business logic for
                                an ION process.
        @param  cleanup_method  An optional callable to run when the process is stopping. Runs after all other
                                notify_stop calls have run. Should take one param, this instance.
        @param  heartbeat_secs  Number of seconds to wait in between heartbeats.
        """
        self._startup_listeners = listeners or []
        self.listeners          = []
        self._listener_map      = {}
        self.name               = name
        self.service            = service
        self._cleanup_method    = cleanup_method

        self.thread_manager     = ThreadManager(failure_notify_callback=self._child_failed) # bubbles up to main thread manager
        self._dead_children     = []        # save any dead children for forensics
        self._ctrl_thread       = None
        self._ctrl_queue        = Queue()
        self._ready_control     = Event()
        self._errors            = []
        self._ctrl_current      = None      # set to the AR generated by _routing_call when in the context of a call

        # processing vs idle time (ms)
        self._start_time        = None
        self._proc_time         = 0   # busy time since start
        self._proc_time_prior   = 0   # busy time at the beginning of the prior interval
        self._proc_time_prior2  = 0   # busy time at the beginning of 2 interval's ago
        self._proc_interval_num = 0   # interval num of last record

        # for heartbeats, used to detect stuck processes
        self._heartbeat_secs    = heartbeat_secs    # amount of time to wait between heartbeats
        self._heartbeat_stack   = None              # stacktrace of last heartbeat
        self._heartbeat_time    = None              # timestamp of heart beat last matching the current op
        self._heartbeat_op      = None              # last operation (by AR)
        self._heartbeat_count   = 0                 # number of times this operation has been seen consecutively

        PyonThread.__init__(self, target=target, **kwargs)

    def heartbeat(self):
        """
        Returns a tuple indicating everything is ok.

        Should only be called after the process has been started.
        Checks the following:
            - All attached endpoints are alive + listening (this means ready)
            - The control flow greenlet is alive + listening or processing

        @return 3-tuple indicating (listeners ok, ctrl thread ok, heartbeat status). Use all on it for a
                boolean indication of success.
        """
        listeners_ok = True
        for l in self.listeners:
            if not (l in self._listener_map and not self._listener_map[l].proc.dead and l.get_ready_event().is_set()):
                listeners_ok = False

        ctrl_thread_ok = self._ctrl_thread.running

        # are we currently processing something?
        heartbeat_ok = True
        if self._ctrl_current is not None:
            st = traceback.extract_stack(self._ctrl_thread.proc.gr_frame)

            if self._ctrl_current == self._heartbeat_op:

                if st == self._heartbeat_stack:
                    self._heartbeat_count += 1  # we've seen this before! increment count

                    # we've been in this for the last X ticks, or it's been X seconds, fail this part of the heartbeat
                    if self._heartbeat_count > CFG.get_safe('cc.timeout.heartbeat_proc_count_threshold', 30) or \
                       get_ion_ts_millis() - int(self._heartbeat_time) >= CFG.get_safe('cc.timeout.heartbeat_proc_time_threshold', 30) * 1000:
                        heartbeat_ok = False
                else:
                    # it's made some progress
                    self._heartbeat_count = 1
                    self._heartbeat_stack = st
                    self._heartbeat_time  = get_ion_ts()
            else:
                self._heartbeat_op      = self._ctrl_current
                self._heartbeat_count   = 1
                self._heartbeat_time    = get_ion_ts()
                self._heartbeat_stack   = st

        else:
            self._heartbeat_op      = None
            self._heartbeat_count   = 0

        return (listeners_ok, ctrl_thread_ok, heartbeat_ok)

    @property
    def time_stats(self):
        """
        Returns a 5-tuple of (total time, idle time, processing time, time since prior interval start,
        busy since prior interval start), all in ms (int).
        """
        now = get_ion_ts_millis()
        running_time = now - self._start_time
        idle_time = running_time - self._proc_time

        cur_interval = now / STAT_INTERVAL_LENGTH
        now_since_prior = now - (cur_interval - 1) * STAT_INTERVAL_LENGTH

        if cur_interval == self._proc_interval_num:
            proc_time_since_prior = self._proc_time-self._proc_time_prior2
        elif cur_interval-1 == self._proc_interval_num:
            proc_time_since_prior = self._proc_time-self._proc_time_prior
        else:
            proc_time_since_prior = 0

        return (running_time, idle_time, self._proc_time, now_since_prior, proc_time_since_prior)

    def _child_failed(self, child):
        """
        Occurs when any child greenlet fails.

        Propogates the error up to the process supervisor.
        """
        # remove the child from the list of children (so we can shut down cleanly)
        for x in self.thread_manager.children:
            if x.proc == child:
                self.thread_manager.children.remove(x)
                break
        self._dead_children.append(child)

        # kill this main, we should be noticed by the container's proc manager
        self.proc.kill(child.exception)

    def add_endpoint(self, listener):
        """
        Adds a listening endpoint to be managed by this ION process.

        Spawns the listen loop and sets the routing call to synchronize incoming messages
        here. If this process hasn't been started yet, adds it to the list of listeners
        to start on startup.
        """
        if self.proc:
            listener.routing_call           = self._routing_call

            if self.name:
                svc_name = "unnamed-service"
                if self.service is not None and hasattr(self.service, 'name'):
                    svc_name = self.service.name

                listen_thread_name          = "%s-%s-listen-%s" % (svc_name, self.name, len(self.listeners)+1)
            else:
                listen_thread_name          = "unknown-listener-%s" % (len(self.listeners)+1)

            gl = self.thread_manager.spawn(listener.listen, thread_name=listen_thread_name)
            gl.proc._glname = "ION Proc listener %s" % listen_thread_name
            self._listener_map[listener] = gl
            self.listeners.append(listener)
        else:
            self._startup_listeners.append(listener)

    def remove_endpoint(self, listener):
        """
        Removes a listening endpoint from management by this ION process.

        If the endpoint is unknown to this ION process, raises an error.

        @return The PyonThread running the listen loop, if it exists. You are
                responsible for closing it when appropriate.
        """

        if listener in self.listeners:
            self.listeners.remove(listener)
            return self._listener_map.pop(listener)
        elif listener in self._startup_listeners:
            self._startup_listeners.remove(listener)
            return None
        else:
            raise IonProcessError("Cannot remove unrecognized listener: %s" % listener)

    def target(self, *args, **kwargs):
        """
        Control entrypoint. Setup the base properties for this process (mainly a listener).
        """
        if self.name:
            threading.current_thread().name = "%s-target" % self.name

        # start time
        self._start_time = get_ion_ts_millis()
        self._proc_interval_num = self._start_time / STAT_INTERVAL_LENGTH

        # spawn control flow loop
        self._ctrl_thread = self.thread_manager.spawn(self._control_flow)
        self._ctrl_thread.proc._glname = "ION Proc CL %s" % self.name

        # wait on control flow loop, heartbeating as appropriate
        while not self._ctrl_thread.ev_exit.wait(timeout=self._heartbeat_secs):
            hbst = self.heartbeat()

            if not all(hbst):
                log.warn("Heartbeat status for process %s returned %s", self, hbst)
                if self._heartbeat_stack is not None:
                    stack_out = "".join(traceback.format_list(self._heartbeat_stack))
                else:
                    stack_out = "N/A"

                #raise PyonHeartbeatError("Heartbeat failed: %s, stacktrace:\n%s" % (hbst, stack_out))
                log.warn("Heartbeat failed: %s, stacktrace:\n%s", hbst, stack_out)

        # this is almost a no-op as we don't fall out of the above loop without
        # exiting the ctrl_thread, but having this line here makes testing much
        # easier.
        self._ctrl_thread.join()

    def _routing_call(self, call, context, *callargs, **callkwargs):
        """
        Endpoints call into here to synchronize across the entire IonProcess.

        Returns immediately with an AsyncResult that can be waited on. Calls
        are made by the loop in _control_flow. We pass in the calling greenlet so
        exceptions are raised in the correct context.

        @param  call        The call to be made within this ION processes' calling greenlet.
        @param  callargs    The keyword args to pass to the call.
        @param  context     Optional process-context (usually the headers of the incoming call) to be
                            set. Process-context is greenlet-local, and since we're crossing greenlet
                            boundaries, we must set it again in the ION process' calling greenlet.
        """
        ar = AsyncResult()

        if len(callargs) == 0 and len(callkwargs) == 0:
            log.trace("_routing_call got no arguments for the call %s, check your call's parameters", call)

        self._ctrl_queue.put((greenlet.getcurrent(), ar, call, callargs, callkwargs, context))
        return ar

    def has_pending_call(self, ar):
        """
        Returns true if the call (keyed by the AsyncResult returned by _routing_call) is still pending.
        """
        for _, qar, _, _, _, _ in self._ctrl_queue.queue:
            if qar == ar:
                return True

        return False

    def _cancel_pending_call(self, ar):
        """
        Cancels a pending call (keyed by the AsyncResult returend by _routing_call).

        @return True if the call was truly pending.
        """
        if self.has_pending_call(ar):
            ar.set(False)
            return True

        return False

    def _interrupt_control_thread(self):
        """
        Signal the control flow thread that it needs to abort processing, likely due to a timeout.
        """
        self._ctrl_thread.proc.kill(exception=OperationInterruptedException, block=False)

    def cancel_or_abort_call(self, ar):
        """
        Either cancels a future pending call, or aborts the current processing if the given AR is unset.

        The pending call is keyed by the AsyncResult returned by _routing_call.
        """
        if not self._cancel_pending_call(ar) and not ar.ready():
            self._interrupt_control_thread()

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
        if self.name:
            svc_name = "unnamed-service"
            if self.service is not None and hasattr(self.service, 'name'):
                svc_name = self.service.name
            threading.current_thread().name = "%s-%s-ctrl" % (svc_name, self.name)

        self._ready_control.set()

        for calltuple in self._ctrl_queue:
            calling_gl, ar, call, callargs, callkwargs, context = calltuple
            #log.debug("control_flow making call: %s %s %s (has context: %s)", call, callargs, callkwargs, context is not None)

            res = None
            start_proc_time = get_ion_ts_millis()
            self._record_proc_time(start_proc_time)

            # check context for expiration
            if context is not None and 'reply-by' in context:
                if start_proc_time >= int(context['reply-by']):
                    log.info("control_flow: attempting to process message already exceeding reply-by, ignore")

                    # raise a timeout in the calling thread to allow endpoints to continue processing
                    e = IonTimeout("Reply-by time has already occurred (reply-by: %s, op start time: %s)" % (context['reply-by'], start_proc_time))
                    calling_gl.kill(exception=e, block=False)

                    continue

            # also check ar if it is set, if it is, that means it is cancelled
            if ar.ready():
                log.info("control_flow: attempting to process message that has been cancelled, ignore")
                continue

            try:
                with self.service.push_context(context):
                    with self.service.container.context.push_context(context):
                        self._ctrl_current = ar
                        res = call(*callargs, **callkwargs)
            except OperationInterruptedException:
                # endpoint layer takes care of response as it's the one that caused this
                log.debug("Operation interrupted")
                pass
            except Exception as e:
                # raise the exception in the calling greenlet, and don't
                # wait for it to die - it's likely not going to do so.

                # try decorating the args of the exception with the true traceback
                # this should be reported by ThreadManager._child_failed
                exc = PyonThreadTraceback("IonProcessThread _control_flow caught an exception (call: %s, *args %s, **kwargs %s, context %s)\nTrue traceback captured by IonProcessThread' _control_flow:\n\n%s" % (call, callargs, callkwargs, context, traceback.format_exc()))
                e.args = e.args + (exc,)

                # HACK HACK HACK
                # we know that we only handle TypeError and IonException derived things, so only forward those if appropriate
                if isinstance(e, (TypeError, IonException)):
                    calling_gl.kill(exception=e, block=False)
                else:
                    # otherwise, swallow/record/report and hopefully we can continue on our way
                    self._errors.append((call, callargs, callkwargs, context, e, exc))

                    log.warn(exc)
                    log.warn("Attempting to continue...")

                    # have to raise something friendlier on the client side
                    calling_gl.kill(exception=ContainerError(str(exc)), block=False)
            finally:
                self._compute_proc_stats(start_proc_time)

                self._ctrl_current = None

            ar.set(res)

    def _record_proc_time(self, cur_time):
        """Keep the _proc_time of the prior and prior-prior intervals for stats computation"""
        cur_interval = cur_time / STAT_INTERVAL_LENGTH
        if cur_interval == self._proc_interval_num:
            # We're still in the same interval - no update
            pass
        elif cur_interval-1 == self._proc_interval_num:
            # Record the stats from the prior interval
            self._proc_interval_num = cur_interval
            self._proc_time_prior2 = self._proc_time_prior
            self._proc_time_prior = self._proc_time
        elif cur_interval-1 > self._proc_interval_num:
            # We skipped an entire interval - everything is prior2
            self._proc_interval_num = cur_interval
            self._proc_time_prior2 = self._proc_time
            self._proc_time_prior = self._proc_time

    def _compute_proc_stats(self, start_proc_time):
        cur_time = get_ion_ts_millis()
        self._record_proc_time(cur_time)
        proc_time = cur_time - start_proc_time
        self._proc_time += proc_time

    def start_listeners(self):
        """
        Starts all listeners in managed greenlets.

        This must be called after starting this IonProcess. Currently, the Container's ProcManager
        will handle this for you, but if using an IonProcess manually, you must remember to call
        this method or no attached listeners will run.
        """
        try:
            # disable normal error reporting, this method should only be called from startup
            self.thread_manager._failure_notify_callback = None

            # spawn all listeners in startup listeners (from initializer, or added later)
            for listener in self._startup_listeners:
                self.add_endpoint(listener)

            with Timeout(seconds=CFG.get_safe('cc.timeout.start_listener', 10)):
                waitall([x.get_ready_event() for x in self.listeners])

        except Timeout:

            # remove failed endpoints before reporting failure above
            for listener, proc in self._listener_map.iteritems():
                if proc.proc.dead:
                    log.info("removed dead listener: %s", listener)
                    self.listeners.remove(listener)
                    self.thread_manager.children.remove(proc)

            raise IonProcessError("start_listeners did not complete in expected time")

        finally:
            self.thread_manager._failure_notify_callback = self._child_failed

    def _notify_stop(self):
        """
        Called when the process is about to be shut down.

        Instructs all listeners to close, puts a StopIteration into the synchronized queue,
        and waits for the listeners to close and for the control queue to exit.
        """
        for listener in self.listeners:
            try:
                listener.close()
            except Exception as ex:
                tb = traceback.format_exc()
                log.warn("Could not close listener, attempting to ignore: %s\nTraceback:\n%s", ex, tb)

        self._ctrl_queue.put(StopIteration)

        # wait_children will join them and then get() them, which may raise an exception if any of them
        # died with an exception.
        self.thread_manager.wait_children(30)

        PyonThread._notify_stop(self)

        # run the cleanup method if we have one
        if self._cleanup_method is not None:
            try:
                self._cleanup_method(self)
            except Exception as ex:
                log.warn("Cleanup method error, attempting to ignore: %s\nTraceback: %s", ex, traceback.format_exc())

    def get_ready_event(self):
        """
        Returns an Event that is set when the control greenlet is up and running.
        """
        return self._ready_control


class IonProcessThreadManager(PyonThreadManager):

    def _create_thread(self, target=None, **kwargs):
        return IonProcessThread(target=target, heartbeat_secs=self.heartbeat_secs, **kwargs)


# ---------------------------------------------------------------------------------------------------
# Process type variants

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


# ---------------------------------------------------------------------------------------------------
# Process helpers

def get_ion_actor_id(process):
    """Given an ION process, return the ion-actor-id from the context, if set and present"""
    ion_actor_id = None
    if process:
        ctx = process.get_context()
        ion_actor_id = ctx.get('ion-actor-id', None) if ctx else None
    return ion_actor_id
