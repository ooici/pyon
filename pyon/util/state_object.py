#!/usr/bin/env python

"""Base classes for objects that are controlled by an underlying state machine."""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.util.fsm import FSM

from collections import Iterable

class LifecycleException(Exception):
    pass

class InvalidEventException(LifecycleException):
    pass

class ActionFailedException(LifecycleException):
    pass

class BasicLifecycleStateMixin(object):
    """
    Provides a basic standard life-cycle management for internal pyon objects.
    States: NEW - ACTIVE - ERROR
    Transitions: NEW -> ACTIVE, ACTIVE -> QUIT, NEW/ACTIVE -> ERROR
    Note: invalid events and failed actions don't lead to error state
    """

    # States
    S_NEW = "NEW"
    S_ACTIVE = "ACTIVE"
    S_QUIT = "QUIT"
    S_ERROR = "ERROR"

    # Input events
    E_START = "start"
    E_STOP = "stop"
    E_ERROR = "error"

    # Actions
    A_START = "on_start"
    A_STOP = "on_stop"
    A_ERROR = "on_error"

    ERR_INVALID_EVENT = "invalid_event"
    ERR_ACTION_FAILED = "action_failed"
    ERR_INDUCED = "induced"

    TRANSITIONS = {
        (S_NEW, E_START): (S_ACTIVE, A_START),
        (S_ACTIVE, E_STOP): (S_QUIT, A_STOP),

        (S_NEW, A_ERROR): (S_ERROR, A_ERROR),
        (S_ACTIVE, A_ERROR): (S_ERROR, A_ERROR),
    }

    def _smprocess(self, event, *args, **kwargs):
        """
        Process event against current object state.
        TODO: Process with a mutex if requested (danger: deadlock)
        """
        # In case the init was not called, assume we're in NEW state if unset
        if not hasattr(self,"_state"):
            self._state = self.S_NEW
            self._new_state = None
            self._event = None

        res = None
        try:
            old_state = self._state
            new_state, action = self.TRANSITIONS.get((self._state, event), (None, None))
            self._new_state = new_state
            self._event = event
            if new_state and action:
                actionfunc = getattr(self, action)
                if event == self.E_ERROR:
                    # This calls the error action function
                    res = actionfunc(self.ERR_INDUCED, *args, **kwargs)
                else:
                    # This calls the action function
                    res = actionfunc(*args, **kwargs)

                # Change the state
                self._state = new_state
                self._new_state = None
                self._event = None
            else:
                # Invalid event in this state. No transition found
                res = self.on_error(self.ERR_INVALID_EVENT, *args, **kwargs)

        except StandardError, ex:
            # Process to NEXT state failed (no Deferred) -> forward to ERROR
            log.exception("ERROR in LifecycleMixin _smprocess(event=%s,state=%s)" % (event,self._state))
            try:
                res = self.on_error(self.ERR_ACTION_FAILED, *args, **kwargs)
                raise ex
            except Exception, ex1:
                log.exception("ERROR in LifecycleMixin on_error()")
                raise ex

        return res

    def _smtransition(self):
        """
        Transitions the current state to the new state, as currently processed
        in an action function. Can be called by the action function to switch a
        pre-action handler into a post-action handler.
        @return True if transitioned, False otherwise
        """
        if self._new_state is not None and self._state != self._new_state:
            self._state = self._new_state
            return True
        else:
            return False

    def _smerror(self, reason, *args, **kwargs):
        return self.on_error(self.ERR_ACTION_FAILED, *args, **kwargs)

    def _instate(self,states):
        if isinstance(states, Iterable):
            return self._state in states
        else:
            return self._state == str(states)

    # Public class lifecycle API:

    def start(self, *args, **kwargs):
        return self._smprocess(self.E_START, *args, **kwargs)

    def stop(self, *args, **kwargs):
        return self._smprocess(self.E_STOP, *args, **kwargs)


    # Internal lifecycle action hooks:

    def on_start(self, *args, **kwargs):
        """Lifecycle hook called before transition to ACTIVE state"""

    def on_stop(self, *args, **kwargs):
        """Lifecycle hook called before transition to READY state"""

    def on_error(self, reason, *args, **kwargs):
        """Lifecycle hook called before transition to ERROR state.
        Return False to remain in current state"""

        if reason == self.ERR_INVALID_EVENT:
            log.info("Invalid event %s in state %s" % (self._event,self._state))
            raise InvalidEventException("Invalid event %s in state %s" % (self._event,self._state))

class LifecycleStateMixin(BasicLifecycleStateMixin):
    """
    Provides an efficent extended life-cycle management for internal pyon objects.
    States: NEW - READY - ACTIVE - QUIT - ERROR
    Transitions: NEW -> READY, READY -> ACTIVE, ACTIVE -> READY, READY -> QUIT, ACTIVE -> QUIT,
                 NEW/READY/ACTIVE -> ERROR
    Note: invalid events and failed actions don't lead to error state
    """

    # States
    S_NEW = "NEW"
    S_READY = "READY"
    S_ACTIVE = "ACTIVE"
    S_QUIT = "QUIT"
    S_ERROR = "ERROR"

    # Input events
    E_INIT = "init"
    E_START = "start"
    E_STOP = "stop"
    E_QUIT = "quit"
    E_ERROR = "error"

    # Actions
    A_INIT = "on_init"
    A_START = "on_start"
    A_STOP = "on_stop"
    A_QUIT = "on_quit"
    A_ERROR = "on_error"

    TRANSITIONS = {
        (S_NEW, E_INIT): (S_READY, A_INIT),
        (S_READY, E_START): (S_ACTIVE, A_START),
        (S_ACTIVE, E_STOP): (S_READY, A_STOP),
        (S_READY, E_QUIT): (S_QUIT, A_QUIT),
        (S_ACTIVE, E_QUIT): (S_QUIT, A_QUIT),

        (S_NEW, A_ERROR): (S_ERROR, A_ERROR),
        (S_READY, A_ERROR): (S_ERROR, A_ERROR),
        (S_ACTIVE, A_ERROR): (S_ERROR, A_ERROR),
    }

    def init(self, *args, **kwargs):
        return self._smprocess(self.E_INIT, *args, **kwargs)

    def quit(self, *args, **kwargs):
        return self._smprocess(self.E_QUIT, *args, **kwargs)

    def on_init(self, *args, **kwargs):
        """Lifecycle hook called before transition to READY state"""

    def on_quit(self, *args, **kwargs):
        """Lifecycle hook called before transition to QUIT state"""
