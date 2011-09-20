#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from ion.util.async import *
from ion.util.log import log

import time
import multiprocessing as mp

class IonProcessError(Exception):
    pass

class BaseProcess(object):
    """
    Base process class for doing work. There will be subclasses for various process kinds like greenlets.
    """

    def __init__(self, target=None, *args, **kwargs):
        super(BaseProcess, self).__init__()

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

    def stop(self):
        if self.running:
            self._stop()

        self.proc = None

        if self.supervisor is not None:
                self.supervisor.child_stopped(self)

    def join(self, timeout=None):
        if self.proc is not None:
            self._join(timeout)
            self.stop()


class GreenProcess(BaseProcess):
    """ An BaseProcess that uses a greenlet to do its work. """

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

class PythonProcess(BaseProcess):
    """ An BaseProcess that uses a full OS process to do its work. """

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
    Manage spawning processes of multiple kinds and ensure they're alive.
    TODO: Add heartbeats with zeromq for monitoring and restarting.
    """

    type_callables = {
          'green': GreenProcess
        , 'python': PythonProcess
    }
    def __init__(self):
        super(ProcessSupervisor, self).__init__()

        # NOTE: Assumes that pids never overlap between the various process types
        self.children = set()

    def spawn(self, type, target, *args, **kwargs):
        proc_callable = self.type_callables[type]
        proc = proc_callable(target, *args, **kwargs)
        proc.supervisor = self

        proc.start()
        self.children.add(proc)

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
                    proc.join(time_remaining)
                else:
                    proc.stop()
            else:
                proc.join()

        time_elapsed = time.time() - time_start
        log.debug('Took %.2fs to shutdown %d child processes' % (time_elapsed, child_count))

        return time_elapsed

    def target(self):
        # TODO: Implement monitoring and such
        pass

    def shutdown(self, timeout=30.0):
        """ Give child processes "timeout" seconds to shutdown, then forcibly terminate. """

        # TODO: use signals to absolutely guarantee shutdown even if there are busy loops in greenlets
        elapsed = self.join_children(timeout)
        self.stop()

        return elapsed

class GreenProcessSupervisor(ProcessSupervisor, GreenProcess):
    """ A supervisor that runs in a greenlet and can spawn either greenlets or python subprocesses. """
    pass

