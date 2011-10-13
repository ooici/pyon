#!/usr/bin/env python

"""
This module implements a Finite State Machine (FSM). In addition to state
this FSM also maintains a user defined "memory". So this FSM can be used as a
Push-down Automata (PDA) since a PDA is a FSM + memory.

Documentation shortened. For full documentation, see original package.

Noah Spurrier 20020822
Extended by Michael Meisinger 2011
http://www.noah.org/python/FSM/
"""

class ExceptionFSM(Exception):
    """This is the FSM Exception class."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

class FSM(object):
    """This is a Finite State Machine (FSM).
    """

    def __init__(self, initial_state, memory=None, post_action=False):
        """
        This creates the FSM. You set the initial state here.
        The "memory" attribute is any object.
        """

        # Map (input_symbol, current_state) --> (action, next_state).
        self.state_transitions = {}
        # Map (input_symbol) --> (action, next_state).
        self.state_transitions_catch = {}
        # Map (current_state) --> (action, next_state).
        self.state_transitions_any = {}
        # (action, next_state).
        self.default_transition = None

        self.input_symbol = None
        self.initial_state = initial_state
        self.current_state = self.initial_state
        self.next_state = None
        self.action = None
        self.memory = memory
        # If True, the action will be executed after the state change
        self.post_action = post_action

    def reset(self):
        """
        This sets the current_state to the initial_state and sets
        input_symbol to None.
        """

        self.current_state = self.initial_state
        self.input_symbol = None

    def add_transition(self, input_symbol, state, action=None, next_state=None):
        """
        This adds a transition that associates:
            (input_symbol, current_state) --> (action, next_state)

        The action may be set to None in which case the process() method will
        ignore the action and only set the next_state. The next_state may be
        set to None in which case the current state will be unchanged.
        """
        if next_state is None:
            next_state = state
        self.state_transitions[(input_symbol, state)] = (action, next_state)

    def add_transition_list(self, list_input_symbols, state, action=None, next_state=None):
        """
        This adds the same transition for a list of input symbols.
        You can pass a list or a string. Note that it is handy to use
        string.digits, string.whitespace, string.letters, etc. to add
        transitions that match character classes.

        The action may be set to None in which case the process() method will
        ignore the action and only set the next_state. The next_state may be
        set to None in which case the current state will be unchanged.
        """
        if next_state is None:
            next_state = state
        for input_symbol in list_input_symbols:
            self.add_transition (input_symbol, state, action, next_state)

    def add_transition_catch(self, input_symbol, action=None, next_state=None):
        """
        This adds a transition that associates:
            (input_symbol, ANY state) --> (action, next_state)

        That is, the input symbol will match any current state.
        The process() method checks the "catch" event associations after it first
        checks for an exact match of (input_symbol, current_state) and before
        the "any" associations.

        The action may be set to None in which case the process() method will
        ignore the action and only set the next_state. The next_state may be
        set to None in which case the current state will be unchanged.
        """
        if next_state is None:
            return
        self.state_transitions_catch[input_symbol] = (action, next_state)

    def add_transition_any(self, state, action=None, next_state=None):
        """
        This adds a transition that associates:
            (current_state) --> (action, next_state)

        That is, any input symbol will match the current state.
        The process() method checks the "any" state associations after it first
        checks for an exact match of (input_symbol, current_state).

        The action may be set to None in which case the process() method will
        ignore the action and only set the next_state. The next_state may be
        set to None in which case the current state will be unchanged.
        """
        if next_state is None:
            next_state = state
        self.state_transitions_any[state] = (action, next_state)

    def set_default_transition(self, action, next_state):
        """
        This sets the default transition. This defines an action and
        next_state if the FSM cannot find the input symbol and the current
        state in the transition list and if the FSM cannot find the
        current_state in the transition_any list. This is useful as a final
        fall-through state for catching errors and undefined states.

        The default transition can be removed by setting the attribute
        default_transition to None.
        """
        self.default_transition = (action, next_state)

    def get_transition(self, input_symbol, state):
        """
        This returns (action, next state) given an input_symbol and state.
        This does not modify the FSM state, so calling this method has no side
        effects. Normally you do not call this method directly. It is called by
        process().

        The sequence of steps to check for a defined transition goes from the
        most specific to the least specific.

        1. Check state_transitions[] that match exactly the tuple,
        (input_symbol, state)

        2. Check state_transitions_catch[] that match (input_symbol)
        In other words, match ANY state and a specific input_symbol.

        3. Check state_transitions_any[] that match (state)
        In other words, match a specific state and ANY input_symbol.

        4. Check if the default_transition is defined.
        This catches any input_symbol and any state.
        This is a handler for errors, undefined states, or defaults.

        5. No transition was defined. If we get here then raise an exception.
        """
        if self.state_transitions.has_key((input_symbol, state)):
            return self.state_transitions[(input_symbol, state)]
        elif self.state_transitions_catch.has_key(input_symbol):
            return self.state_transitions_catch[input_symbol]
        elif self.state_transitions_any.has_key(state):
            return self.state_transitions_any[state]
        elif self.default_transition is not None:
            return self.default_transition
        else:
            raise ExceptionFSM('Transition is undefined: (%s, %s).' %
                (str(input_symbol), str(state)) )

    def process(self, input_symbol):
        """
        This is the main method that you call to process input. This may
        cause the FSM to change state and call an action. This method calls
        get_transition() to find the action and next_state associated with the
        input_symbol and current_state. If the action is None then the action
        is not called and only the current state is changed. This method
        processes one complete input symbol. You can process a list of symbols
        (or a string) by calling process_list().
        """
        self.input_symbol = input_symbol
        (self.action, self.next_state) = self.get_transition(self.input_symbol, self.current_state)

        res = None
        if self.post_action:
            self.current_state = self.next_state
            self.next_state = None

        if self.action is not None:
            res = self.action(self)

        if not self.post_action:
            self.current_state = self.next_state
            self.next_state = None

        return res

    def _transition(self):
        """
        Transitions the current state to the next state, as currently processed
        in an action function. Can be called by the action function to switch a
        pre-action handler into a post-action handler.
        @return True if transitioned, False otherwise
        """

        # daf 11 aug 2011
        # Calling _so_transition() which subsequently calls here would successfully transition the state during an action handler,
        # but would then set the state to None after the handler had finished.  The problem is the code in the method above which
        # sets the current state to the next state after the handler completes has no knowledge of the transition performed in
        # this method.  It now works by never changing what the next_state is, and allowing the method above to set current_state
        # to next_state, which is as if we just called this method.

        if self.next_state is not None and self.current_state != self.next_state:
            self.current_state = self.next_state
            #self.next_state = None
            return True
        else:
            return False

    def process_list(self, input_symbols):
        """
        This takes a list and sends each element to process().
        """
        res = []
        for s in input_symbols:
            pres = self.process(s)
            res.append(pres)
        return res
