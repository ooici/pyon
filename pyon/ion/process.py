#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.core.process import GreenProcess, PythonProcess, GreenProcessSupervisor
from pyon.net import messaging, endpoint
from pyon.ion.lifecycle import IonLifecycleMixin

class IonActorMixin(object):
    """
    Basic messaging coordination for a process.
    Combine with various process types to implement the actor model for ION processes.
    """
    
    def setup(self, listener=None):
        self.listener = listener

    def send(self, name, msg):
        """ Send 'msg' to the endpoint 'name'. """
        pass

    def recv(self):
        """ Pull a message off the queue, blocking-style. """
        return None

    def close(self):
        self.listener.close()

class IonProcessBase(IonActorMixin, IonLifecycleMixin):
    """
    Combine actors and lifecycle to form the base of an ION process.
    Just add greenlets or python processes to complete.
    """

    def target(self, *args, **kwargs):
        """ Kick-start the FSM to the init state when this process starts. """
        self.initialize(*args, **kwargs)
        self.activate()

    def _notify_stop(self):
        self.terminate()
        super(IonProcessBase, self)._notify_stop()

    def on_initialize(self, *args, **kwargs):
        """ Setup the base properties for this process (mainly an endpoint factory). """
        self.setup(*args, **kwargs)

    def on_activate(self, *args, **kwargs):
        self.listener.listen()

    def on_terminate(self, *args, **kwargs):
        self.close()

    def on_error(self, *args, **kwargs):
        log.error('Unhandled error in a Lifecycle object!')

        # TODO: remove this once the sporadic StateObject on_error bug is fixed
        import traceback
        traceback.print_stack()

class GreenIonProcess(IonProcessBase, GreenProcess):
    pass
class PythonIonProcess(IonProcessBase, PythonProcess):
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
    