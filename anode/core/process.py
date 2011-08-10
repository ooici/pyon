#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import multiprocessing as mp

from anode.util.async import *

class AnodeProcessError(Exception):
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

    def _join(self):
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

    def join(self):
        if self.proc is not None:
            self._join()
            self.stop()


class GreenProcess(BaseProcess):
    """ An BaseProcess that uses a greenlet to do its work. """

    def _pid(self):
        return id(self.proc)

    def _spawn(self):
        return spawn(self.target, *self.spawn_args, **self.spawn_kwargs)

    def _join(self):
        return self.proc.join()

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

    def _join(self):
        return self.proc.join()

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

    def spawn(self, type='green', target=None, *args, **kwargs):
        proc_callable = self.type_callables[type]
        proc = proc_callable(target, *args, **kwargs)
        proc.supervisor = self

        proc.start()
        self.children.add(proc)

    def child_stopped(self, proc):
        if proc in self.children: self.children.remove(proc)

    def join_children(self):
        while len(self.children):
            self.children.pop().join()

    def target(self):
        # TODO: Implement monitoring and such
        pass

class GreenProcessSupervisor(ProcessSupervisor, GreenProcess):
    """ A supervisor that runs in a greenlet and can spawn either greenlets or python subprocesses. """
    pass

