#!/usr/bin/env python

"""
@package ion.agents.instrument.instrument_fsm Instrument Finite State Machine
@file ion/agents.instrument/instrument_fsm.py
@author Edward Hunter
@brief Simple state mahcine for driver and agent classes.
"""

__author__ = 'Edward Hunter'


from gevent.coros import RLock

class FSMError(Exception):
    pass


class FSMStateError(FSMError):
    pass


class FSMCommandUnknownError(FSMError):
    pass

class FSMLockedError(FSMError):
    pass

class InstrumentFSM(object):
    """
    Simple state mahcine for driver and agent classes.
    """

    def __init__(self, states, events, enter_event, exit_event):
        """
        Initialize states, events, handlers.
        @param states The list of states that the FSM handles
        @param events The list of events that the FSM handles
        @param enter_event The event that indicates a state is being entered
        @param exit_event The event that indicates a state is being exited
        """
        self.states = states
        self.events = events
        self.state_handlers = {}
        self.current_state = None
        self.previous_state = None
        self.enter_event = enter_event
        self.exit_event = exit_event

    def get_current_state(self):
        """
        Return current state.
        """
        return self.current_state

    def add_handler(self, state, event, handler):
        """
        Add an event handler.
        @param state the state to handler the event in.
        @param event the event to handle.
        @retval True if successful, False otherwise.
        """
        if not self.states.has(state):
            return False

        if not self.events.has(event):
            return False

        self.state_handlers[(state, event)] = handler
        return True

    def start(self, state, *args, **kwargs):
        """
        Start the state machine. Initializes current state and fires the
        EVENT_ENTER event.
        @param state The state to start in.
        @param args positional arguments to pass to the handler.
        @param kwargs keyword arguments to pass to the handler.
        @retval True if successful, False otherwise.
        @raises Any exception raised by the enter handler.
        """
        if not self.states.has(state):
            return False

        self.current_state = state
        handler = self.state_handlers.get((state, self.enter_event), None)
        if handler:
            handler(*args, **kwargs)
        return True

    def on_event(self, event, *args, **kwargs):
        """
        Handle an event. Call the current state handler passing the event
        and paramters.
        @param event A string indicating the event that has occurred.
        @param args positional arguments to pass to the handler.
        @param kwargs keyword arguments to pass to the handler.
        @retval result from the handler executed by the current state/event pair.
        @raises InstrumentStateException if no handler for the event exists in current state.
        @raises Any exception raised by the handlers.
        """
        next_state = None
        result = None
        if self.events.has(event):
            handler = self.state_handlers.get((self.current_state, event), None)
            if handler:
                (next_state, result) = handler(*args, **kwargs)
            else:
                raise FSMStateError('Command %s not handled in state %s' % (event, self.current_state))
        else:
            raise FSMCommandUnknownError('Unknown command: %s' % event)

        #if next_state in self.states:
        if self.states.has(next_state):
            self._on_transition(next_state, *args, **kwargs)

        return result

    def _on_transition(self, next_state, *args, **kwargs):
        """
        Call the sequence of events to cause a state transition. Called from
        on_event if the handler causes a transition.
        @param next_state The state to transition to.
        @param args positional arguments to pass to the handler.
        @param kwargs keyword arguments to pass to the handler.
        @raises Any exception raised by the handlers.
        """

        handler = self.state_handlers.get((self.current_state, self.exit_event), None)
        if handler:
            handler(*args, **kwargs)
        self.previous_state = self.current_state
        self.current_state = next_state
        handler = self.state_handlers.get((self.current_state, self.enter_event), None)
        if handler:
            handler(*args, **kwargs)

    def get_events(self, current_state=True):
        """
        Return a list of events handled.
        @param current_state if true, return events handled in the current state only.
        @retval list of events handled.
        """
        events = []
        for (key, handler) in self.state_handlers.iteritems():
            state = key[0]
            event = key[1]
            if not ((event == self.enter_event) or (event == self.exit_event)):
                if current_state:
                    if self.current_state == state:
                        if event not in events:
                            events.append(event)
                else:
                    if event not in events:
                        events.append(event)
        return events

class ThreadSafeFSM(InstrumentFSM):
    def __init__(self, states, events, enter_event, exit_event):
        self._lock = RLock()
        super(ThreadSafeFSM, self).__init__(states, events, enter_event, exit_event)
    def on_event(self, event, *args, **kwargs):
        with self._lock:
            return super(ThreadSafeFSM, self).on_event(event, *args, **kwargs)
    def on_event_if_free(self, event, *args, **kwargs):
        if not self._lock.acquire(blocking=False):
            raise FSMLockedError
        try:
            retval = super(ThreadSafeFSM, self).on_event(event, *args, **kwargs)
        finally:
            self._lock.release()
        return retval


"""
import gevent
from gevent.coros import RLock

r = RLock()


def gfunc(name):

    lock = r.acquire(blocking=False)
    if not lock:
        while not lock:
            gevent.sleep(1)
            lock = r.acquire(blocking=False)
    print 'worker %s returned retval %s' % (name, str(lock))
    x = 0
    while x < 5:
        gevent.sleep(1)
        print 'worker %s count %i' % (name, x)
        x += 1
    r.release()


gl1 = gevent.spawn(gfunc,'one')
gl2 = gevent.spawn(gfunc,'two')
gevent.joinall([gl1, gl2])
"""