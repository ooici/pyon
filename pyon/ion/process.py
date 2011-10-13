#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from pyon.public import GreenProcess, PythonProcess, GreenProcessSupervisor, messaging, endpoint, log
from pyon.ion.lifecycle import IonLifecycleMixin

class IonActorMixin(object):
    """
    Basic messaging coordination for a process.
    Combine with various process types to implement the actor model for ION processes.
    """

    def __init__(self):
        super(IonActorMixin, self).__init__()
        
        # TODO: Fill this out with actually useful messaging
        self.node = messaging.makeNode()
        #self.endpoint = endpoint.RPCClient()
        self.queue = None

    def send(self, name, msg):
        """ Send 'msg' to the endpoint 'name'. """
        pass

    def recv(self):
        """ Pull a message off the queue, blocking-style. """
        return None

class IonProcessBase(IonActorMixin, IonLifecycleMixin):
    """
    Combine actors and lifecycle to form the base of an ION process.
    Just add greenlets or python processes to complete.
    """

    def target(self):
        """ Kick-start the FSM to the init state when this process starts. """
        self.initialize()

class GreenIonProcess(GreenProcess, IonProcessBase):
    pass
class PythonIonProcess(PythonProcess, IonProcessBase):
    pass

class IonProcessSupervisor(GreenProcessSupervisor):
    type_callables = {
          'green': GreenIonProcess
        , 'python': PythonIonProcess
    }

if __name__ == '__main__':
    ips = IonProcessSupervisor()
    
    def target():
        print 'foo'
    p = ips.spawn('green', target)
    p.join()

    class DummyIonProcess(GreenIonProcess):
        def on_activate(self, *args, **kwargs):
            print 'activate'
        def on_deactivate(self, *args, **kwargs):
            print 'deactivate'
        def on_error(self, *args, **kwargs):
            print 'error'
        def on_initialize(self, *args, **kwargs):
            print 'initialize'
        def on_terminate(self, *args, **kwargs):
            print 'terminate'
        def on_terminate_active(self, *args, **kwargs):
            print 'terminate_active'

        def target(self):
            print 'running the target'
            super(DummyIonProcess, self).target()


    p = ips.spawn(DummyIonProcess, None)
    p.join()
    