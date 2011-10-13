#!/usr/bin/env python

"""
Base classes for objects that are controlled by an underlying state machine.
"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.public import log
from pyon.util.fsm import FSM

class Actionable(object):
    """
    @brief Provides an object that supports the execution of actions as consequence
        of FSM transitions.
    """

    def _action(self, action, fsm):
        """
        @brief Execute action identified by argument
        @param action A str with the action to execute
        @param fsm the FSM instance that triggered the action.
        @retval Maybe a Deferred
        """
        raise NotImplementedError("Not implemented")

class StateObject(Actionable):
    """
    @brief Base class for an object instance that has an underlying FSM that
        determines which inputs are allowed at any given time; inputs trigger
        actions as defined by the FSM.
        This is the class that specialized classes inherit from.
        The underlying FSM can be set explicitly.
    """

    def __init__(self):
        # The FSM instance
        self.__fsm = None

        super(StateObject, self).__init__()

    # Function prefix _so is for StateObject control functions

    def _so_set_fsm(self, fsm_inst):
        """
        @brief Set the "engine" FSM that drives the calling of the _action functions
        """
        assert not self.__fsm, "FSM already set"
        assert isinstance(fsm_inst, FSM), "Given object not a FSM"
        self.__fsm = fsm_inst

    def _so_process(self, event, *args, **kwargs):
        """
        @brief Trigger the FSM with an event. Leads to action functions being called.
        @retval Result of FSM process
        @todo Improve the error catching, forwarding and reporting
        """
        assert self.__fsm, "FSM not set"
        self.__fsm.input_args = args
        self.__fsm.input_kwargs = kwargs
        self.__fsm.error_cause = None
        try:
            old_state = self.__fsm.current_state
            # This is the main invocation of the FSM. It will lead to calls to
            # the _action function in normal configuration.
            res = self.__fsm.process(event)

        except StandardError, ex:
            # Process to NEXT state failed (no Deferred) -> forward to ERROR
            log.exception("ERROR in StateObject process(event=%s)" % (event))
            try:
                res1 = self._so_error(ex)
                raise ex
            except Exception, ex1:
                log.exception("Subsequent ERROR in StateObject error(), ND-ND")
                raise ex

        return res

    def _so_error(self, *args, **kwargs):
        """
        @brief Brings the StateObject explicitly into the error state, because
            of some action error.
        """
        error = args[0] if args else None
        self.__fsm.error_cause = error

        # Is it OK to override the original args?
        self.__fsm.input_args = args
        self.__fsm.input_kwargs = kwargs

        return self.__fsm.process(BasicStates.E_ERROR)

    def _action(self, action, fsm):
        """
        Generic action function that invokes.
        """
        func = getattr(self, action)
        args = self.__fsm.input_args
        kwargs = self.__fsm.input_kwargs
        if action == BasicStates.E_ERROR:
            res = func(self.__fsm.error_cause, *args, **kwargs)
        else:
            res = func(*args, **kwargs)
        return res

    def _so_transition(self):
        """
        @brief To be called from a pre-action event handler to explicitly
            transition the FSM's state and turn the handler into a post-action.
        """
        assert self.__fsm, "FSM not set"
        return self.__fsm._transition()

    def _get_state(self):
        assert self.__fsm, "FSM not set"
        return self.__fsm.current_state

class FSMFactory(object):
    """
    A factory for FSMs to be used in StateObjects
    """

    def _create_action_func(self, target, action):
        """
        @retval a function with a closure with the action name
        """
        def action_target(fsm):
            return target(action, fsm)
        return action_target

    def create_fsm(self, target, memory=None):
        """
        @param a StateObject that is the
        @param memory a state vector. if None will be set to empty list
        @retval basic FSM with initial state 'INIT' and no transitions, and an
            empty list as state vector
        """
        assert isinstance(target, Actionable)
        memory = memory or []
        fsm = FSM('INIT', memory)
        return fsm

class BasicStates(object):
    """
    @brief Defines constants for basic state and lifecycle FSMs.
    """
    # States
    # Note: The INIT state is active before the initialize input is received
    S_INIT = "INIT"
    S_READY = "READY"
    S_ACTIVE = "ACTIVE"
    S_TERMINATED = "TERMINATED"
    S_ERROR = "ERROR"

    # Input events
    E_INITIALIZE = "initialize"
    E_ACTIVATE = "activate"
    E_DEACTIVATE = "deactivate"
    E_TERMINATE = "terminate"
    E_ERROR = "error"

    # Actions - in general called the same as the triggering event
    A_ACTIVE_TERMINATE = "terminate_active"

class BasicFSMFactory(FSMFactory):
    """
    A FSM factory for FSMs with basic state model.
    """

    def _create_action_func(self, target, action):
        """
        @retval a function with a closure with the action name
        """
        def action_target(fsm):
            return target("on_%s" % action, fsm)
        return action_target

    def create_fsm(self, target, memory=None):
        fsm = FSMFactory.create_fsm(self, target, memory)

        actf = target._action

        actionfct = self._create_action_func(actf, BasicStates.E_INITIALIZE)
        fsm.add_transition(BasicStates.E_INITIALIZE, BasicStates.S_INIT, actionfct, BasicStates.S_READY)

        actionfct = self._create_action_func(actf, BasicStates.E_ACTIVATE)
        fsm.add_transition(BasicStates.E_ACTIVATE, BasicStates.S_READY, actionfct, BasicStates.S_ACTIVE)

        actionfct = self._create_action_func(actf, BasicStates.E_DEACTIVATE)
        fsm.add_transition(BasicStates.E_DEACTIVATE, BasicStates.S_ACTIVE, actionfct, BasicStates.S_READY)

        actionfct = self._create_action_func(actf, BasicStates.E_TERMINATE)
        fsm.add_transition(BasicStates.E_TERMINATE, BasicStates.S_READY, actionfct, BasicStates.S_TERMINATED)

        actionfct = self._create_action_func(actf, BasicStates.A_ACTIVE_TERMINATE)
        fsm.add_transition(BasicStates.E_TERMINATE, BasicStates.S_ACTIVE, actionfct, BasicStates.S_TERMINATED)

        actionfct = self._create_action_func(actf, BasicStates.E_ERROR)
        fsm.set_default_transition(actionfct, BasicStates.S_ERROR)

        return fsm