#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import multiprocessing as mp
from ion.util.async import *

class IonProcessError(Exception):
    pass

class IonProcess(object):
    """
    Base process class for doing work. There will be subclasses for various process kinds like greenlets.
    """

    def __init__(self, target, *args, **kwargs):
        self.proc = None
        self.target = target
        self.spawn_args = args
        self.spawn_kwargs = kwargs

    def _pid(self):
        pass

    def _spawn(self):
        pass

    def _join(self):
        pass

    @property
    def pid(self):
        """ Return the process ID for the spawned process. If not spawned yet, return 0. """
        if not self.proc:
            return 0
        return self._pid()

    def start(self):
        self.proc = self._spawn()

    def stop(self):
        self._stop()
        self.proc = None

    def join(self):
        if self.proc:
            self._join()

class GreenProcess(IonProcess):
    """ An IonProcess that uses a greenlet to do its work. """

    def _pid(self):
        return id(self.proc)

    def _spawn(self):
        return spawn(self.target, *self.spawn_args, **self.spawn_kwargs)

    def _join(self):
        return self.proc.join()

class PythonProcess(IonProcess):
    """ An IonProcess that uses a full OS process to do its work. """

    def _pid(self):
        return self.proc.pid

    def _spawn(self):
        proc = mp.Process(target=self.target, args=self.spawn_args, kwargs=self.spawn_kwargs)
        proc.start()
        return proc

    def _join(self):
        return self.proc.join()
    
