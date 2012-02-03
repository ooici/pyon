#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

import threading

from pyon.util.log import log
from pyon.core.process import GreenProcess, PythonProcess, GreenProcessSupervisor
from pyon.net import messaging, endpoint

class IonProcessBase(object):
    """
    Form the base of an ION process.
    Just add greenlets or python processes to complete.
    """

    def __init__(self, listener=None, name=None):
        self.listener   = listener
        self.name       = name

    def target(self, *args, **kwargs):
        """ Control entrypoint. Setup the base properties for this process (mainly a listener)."""
        if self.name:
            threading.current_thread().name = self.name
        self.listener.listen()

    def _notify_stop(self):
        self.listener.close()
        super(IonProcessBase, self)._notify_stop()

class GreenIonProcess(IonProcessBase, GreenProcess):

    def __init__(self, target=None, listener=None, name=None, *args, **kwargs):
        IonProcessBase.__init__(self, listener=listener, name=name)
        GreenProcess.__init__(self, target=target, *args, **kwargs)

    def get_ready_event(self):
        return self.listener.get_ready_event()

class PythonIonProcess(IonProcessBase, PythonProcess):
    pass

class IonProcessSupervisor(GreenProcessSupervisor):
    type_callables = {
          'green': GreenIonProcess
        , 'python': PythonIonProcess
    }
