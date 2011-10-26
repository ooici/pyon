#!/usr/bin/env python

"""Classes to build and manage pyon container worker processes."""

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from pyon.util.async import *
from pyon.util.log import log

import time
import multiprocessing as mp
import os
import signal

class PyonProcessError(Exception):
    pass

class PyonProcess(object):
    """
    @brief Process abstract base class for doing work in the container.
    There will be subclasses for various process kinds like greenlets and OS processes.
    """

    def __init__(self, target=None, *args, **kwargs):
        """
        @param target The Callable to start as independent process
        @param args  Provided as spawn args to process
        @param kwargs  Provided as spawn kwargs to process
        """
        super(PyonProcess, self).__init__()

        if target is not None or not hasattr(self, 'target'):   # Allow setting target at class level
            self.target = target
        self.spawn_args = args
        self.spawn_kwargs = kwargs

        self.proc = None
        self.supervisor = None

    # Implement the next few methods in derived classes
    def _pid(self):
        pass

    def _spawn(self):
        pass

    def _join(self, timeout=None):
        pass

    def _notify_stop(self):
        """ Get ready, you're about to get shutdown. """
    
    def _stop(self):
        pass

    def _running(self):
        pass

    @property
    def pid(self):
        """ Return the process ID for the spawned process. If not spawned yet, return 0. """
        if self.proc is None:
            return 0
        return self._pid()

    @property
    def running(self):
        """ Is the process actually running? """
        return bool(self.proc and self._running())

    def start(self):
        self.proc = self._spawn()
        return self

    def notify_stop(self):
        """ Get ready, you're about to get shutdown. """
        self._notify_stop()

    def stop(self):
        if self.running:
            self._stop()

        self.proc = None

        if self.supervisor is not None:
                self.supervisor.child_stopped(self)

        return self

    def join(self, timeout=None):
        if self.proc is not None:
            self._join(timeout)
            self.stop()
            
        return self


class GreenProcess(PyonProcess):
    """
    @brief A BaseProcess that uses a greenlet to do its work.
    """

    def _pid(self):
        return id(self.proc)

    def _spawn(self):
        return spawn(self.target, *self.spawn_args, **self.spawn_kwargs)

    def _join(self, timeout=None):
        return self.proc.join(timeout)

    def _stop(self):
        return self.proc.kill()

    def _running(self):
        return self.proc.started

class PythonProcess(PyonProcess):
    """
    @brief A BaseProcess that uses a full OS process to do its work.
    """

    def _pid(self):
        return self.proc.pid

    def _spawn(self):
        proc = mp.Process(target=self.target, args=self.spawn_args, kwargs=self.spawn_kwargs)
        proc.daemon = True
        proc.start()
        return proc

    def _join(self, timeout=None):
        return self.proc.join(timeout)

    def _stop(self):
        return self.proc.terminate()

    def _running(self):
        return self.proc.is_alive()

class ProcessSupervisor(object):
    """
    @brief Manage spawning processes of multiple kinds and ensure they're alive.
    TODO: Add heartbeats with zeromq for monitoring and restarting.
    """

    type_callables = {
          'green': GreenProcess
        , 'python': PythonProcess
    }

    def __init__(self, heartbeat_secs=10.0):
        super(ProcessSupervisor, self).__init__()

        # NOTE: Assumes that pids never overlap between the various process types
        self.children = set()
        self.heartbeat_secs = heartbeat_secs
        self._shutting_down = False

    def spawn(self, type_and_target, *args, **kwargs):
        """
        @brief Spawn a pyon process
        @param type_and_target should either be a tuple of (type, target) where type is a string in type_callables
        and target is a callable, or a subclass of PyonProcess that defines its own "target" method.
        """
        if isinstance(type_and_target, tuple):
            proc_type, proc_target = type_and_target
            proc_callable = self.type_callables[proc_type]
            proc = proc_callable(proc_target, *args, **kwargs)
        elif isinstance(type_and_target, PyonProcess) and hasattr(type_and_target, 'target'):
            proc = type_and_target(*args, **kwargs)
        else:
            raise PyonProcessError('Invalid proc_type (must be tuple or PyonProcess subclass with a target method)')

        proc.supervisor = self

        proc.start()
        self.children.add(proc)
        return proc

    def child_stopped(self, proc):
        if proc in self.children: self.children.remove(proc)

    def join_children(self, timeout=None):
        """ Give child processes "timeout" seconds to shutdown, then forcibly terminate. """

        time_start = time.time()
        child_count = len(self.children)

        while len(self.children):
            proc = self.children.pop()
            
            time_elapsed = time.time() - time_start
            if timeout is not None:
                time_remaining = timeout - time_elapsed

                if time_remaining > 0:
                    # The nice way; let it do cleanup
                    proc.notify_stop()
                    proc.join(time_remaining)
                else:
                    # Out of time. Cya, sucker
                    proc.stop()
            else:
                proc.join()

        time_elapsed = time.time() - time_start
        log.debug('Took %.2fs to shutdown %d child processes' % (time_elapsed, child_count))

        return time_elapsed

    def target(self):
        # TODO: Implement monitoring and such
        while True:
            #self.send_heartbeats()
            time.sleep(self.heartbeat_secs)

    def shutdown(self, timeout=30.0):
        """
        @brief Give child processes "timeout" seconds to shutdown, then forcibly terminate.
        """

        unset = shutdown_or_die(timeout)        # Failsafe in case the following doesn't work
        elapsed = self.join_children(timeout)
        self.stop()

        unset()
        return elapsed

class GreenProcessSupervisor(ProcessSupervisor, GreenProcess):
    """
    A supervisor that runs in a greenlet and can spawn either greenlets or python subprocesses.
    """
    pass

def shutdown_or_die(delay_sec=0):
    """
    Wait the given number of seconds and forcibly kill this process if it's still running.
    """

    def diediedie(sig=None, frame=None):
        pid = os.getpid()
        print 'Container did not shutdown correctly. Forcibly terminating with SIGKILL (pid %d).' % (pid)
        os.kill(pid, signal.SIGKILL)

    def dontdie():
        signal.alarm(0)

    if delay_sec > 0:
        try:
            old = signal.signal(signal.SIGALRM, diediedie)
            signal.alarm(int(delay_sec))

            if old:
                print 'Warning: shutdown_or_die found a previously registered ALARM and overrode it.'
        except ValueError, ex:
            print 'Failed to set failsafe shutdown signal. This only works on UNIX platforms.'
            pass
    else:
        diediedie()

    return dontdie

if __name__ == '__main__':
    unset = shutdown_or_die(3)
    unset()
    while True:
        pass
    