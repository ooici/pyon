#!/usr/bin/env python

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.util.state_object import StateObject, BasicFSMFactory, BasicStates

class IonLifecycleMixin(StateObject):
    """
    A StateObject with a basic life cycle, as determined by the BasicFSMFactory.
    @see BasicFSMFactory
    @todo Add precondition checker
    """

    def __init__(self, *args, **kwargs):
        super(IonLifecycleMixin, self).__init__(*args, **kwargs)
        factory = BasicFSMFactory()
        fsm = factory.create_fsm(self)
        self._so_set_fsm(fsm)

    def initialize(self, *args, **kwargs):
        return self._so_process(BasicStates.E_INITIALIZE, *args, **kwargs)

    def activate(self, *args, **kwargs):
        return self._so_process(BasicStates.E_ACTIVATE, *args, **kwargs)

    def deactivate(self, *args, **kwargs):
        return self._so_process(BasicStates.E_DEACTIVATE, *args, **kwargs)

    def terminate(self, *args, **kwargs):
        return self._so_process(BasicStates.E_TERMINATE, *args, **kwargs)

    def error(self, *args, **kwargs):
        return self._so_process(BasicStates.E_ERROR, *args, **kwargs)

    def on_initialize(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_activate(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_deactivate(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_terminate_active(self, *args, **kwargs):
        """
        @brief this is a shorthand delegating to on_terminate from the ACTIVE
            state. Subclasses can override this action handler with more specific
            functionality
        """
        return self.on_terminate(*args, **kwargs)

    def on_terminate(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")

    def on_error(self, *args, **kwargs):
        raise NotImplementedError("Not implemented")
