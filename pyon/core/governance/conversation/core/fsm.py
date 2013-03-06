from collections import deque
from pydoc import deque
from pyon.core.governance.conversation.core.transition import DefaultTransition
from transition import Transition, AssertionTransition
from ooi.logging import log

class ExceptionFSM(Exception):
    """This is the FSM Exception class."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return `self.value`

class ExceptionFailAssertion(Exception):
    """This is the FSM Exception class."""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return `self.value`

type_converter = {'int':int, 'string':str}

class FSM:

    """This is a Finite State Machine (FSM).
    """
    ERROR_TRANSITION = 'ERROR'
    EMPTY_TRANSITION = 'EMPTY'
    REC_TRANSITION = 'REC'
    END_PAR_TRANSITION = 'END_PAR'

    def __init__(self, initial_state, memory=None):

        self.generics = ['request']
        # Map (input_symbol, current_state) --> (action, next_state).
        self.state_transitions = {}
        # Map (current_state) --> (action, next_state).
        self.state_transitions_any = {}
        self.default_transition = None
        self.error_transition = self.ERROR_TRANSITION
        self.empty_transition = self.EMPTY_TRANSITION
        self.input_symbol = None
        self.initial_state = initial_state
        self.current_state = self.initial_state
        self.next_state = None
        self.action = None
        # TODO: Delete the memory from the interface of the fsm.
        if memory is None: self.memory = dict() 
        else: self.memory = {}
        self.context = {}
        self.current_payload = None
        self.check_assertions = False
        self.has_reach_end_state = False
        
        self.interrupt_transition = None
        self.interrupt_start_state = None
        self.final_state = -1
        self.end_states = set()

    def set_assertion_check_on(self):
        self.check_assertions = True 

    def set_assertion_check_off(self):
        self.check_assertions = False

    def instantiate_generics(self, op_mapping):
        state_transitions = self.state_transitions.copy()
        for (transition, state) in state_transitions:
            for input in op_mapping:
                op = '_%s_'%(input)
                if op in transition:
                    val = self.state_transitions.pop((transition, state))
                    old_transition = DefaultTransition.create_from_string(transition)
                    new_transition = DefaultTransition(old_transition.lt_type, op_mapping[input], old_transition.role)
                    self.state_transitions[(new_transition.get_trigger(), state)] = val
                    break


    def reset (self):

        """This sets the current_state to the initial_state and sets
        input_symbol to None. The initial state was set by the constructor
        __init__(). """

        self.current_state = self.initial_state
        self.input_symbol = None

    def copy_transitions(self, from_state, to_state):
        for (input_symbol, state) in self.state_transitions.keys():
            if (state==from_state):
                (transition_context, action, next_state) = self.state_transitions[((input_symbol, state))]
                self.add_transition(input_symbol, to_state, next_state, action, transition_context)
                
    def add_transition (self, input_symbol, state, next_state=None, action=None, transition_context = None):

        """This adds a transition that associates:

                (input_symbol, current_state) --> (action, next_state)

        The action may be set to None in which case the process() method will
        ignore the action and only set the next_state. The next_state may be
        set to None in which case the current state will be unchanged.

        You can also set transitions for a list of symbols by using
        add_transition_list(). """

        if next_state is None:
            next_state = state

        if state in self.end_states:
            self.end_states.remove(state)

        self.end_states.add(next_state)

        self.state_transitions[(input_symbol, state)] = (transition_context, action, next_state)

    def add_transition_list (self, list_input_symbols, state, next_state=None, 
                             action=None, transition_context=None):

        """This adds the same transition for a list of input symbols.
        You can pass a list or a string. Note that it is handy to use
        string.digits, string.whitespace, string.letters, etc. to add
        transitions that match character classes.

        The action may be set to None in which case the process() method will
        ignore the action and only set the next_state. The next_state may be
        set to None in which case the current state will be unchanged. """

        if next_state is None:
            next_state = state
        for input_symbol in list_input_symbols:
            self.add_transition (input_symbol, state, next_state, action, transition_context)

    def add_transition_any (self, state, action=None, next_state=None):

        """This adds a transition that associates:

                (current_state) --> (action, next_state)

        That is, any input symbol will match the current state.
        The process() method checks the "any" state associations after it first
        checks for an exact match of (input_symbol, current_state).

        The action may be set to None in which case the process() method will
        ignore the action and only set the next_state. The next_state may be
        set to None in which case the current state will be unchanged. """

        if next_state is None:
            next_state = state
        self.state_transitions_any [state] = (None, action, next_state)

    # This is used whenever we want to represent state that represent parallel construct 
    def add_transition_to_memory_old(self, input_symbol, state, startNewTransitionQueue, action):
        """ We use startNewTransitionQueue when we have finished with pushing all the actions.
            Then we start new parallel branch. Thus we create a new FSA for that branch and put it in the list of FSAs
            for the state """
        if (state not in self.memory):
            startNewTransitionQueue = True
            
        cur_memory_state = self.memory.setdefault(state, []) 
        if startNewTransitionQueue: 
            cur_memory_state.append(deque([input_symbol])) 
        else: 
            cur_memory_state[-1].append(input_symbol)
            
    """ Used for parallel constructs
    FSM parameter is given only when we want to start new parallel branch. 
    When we just add_transitions to an existing parallel branch we know the current fsm so we do not pass it.
    Thus, in that case the fsm parameter will be None  
    (not that starting a parallel construct also means starting a new parallel branch)"""
    def add_fsm_to_memory(self, state, fsm):
        cur_memory_state = self.memory.setdefault(state, [])
        cur_memory_state.append(fsm)
    
    """ Used for parallel constructs """
    def add_nested_transition(self, input_symbol, state, 
                                 nested_state, 
                                 next_nested_state, 
                                 action, 
                                 transition_context):
        """ We use startNewTransitionQueue when we have finished with pushing all the actions.
            Then we start new parallel branch. Thus we create a new FSA for that branch and put it in the list of FSAs
            for the state """
        if (state not in self.memory):
            raise ExceptionFSM("""The given state is not in the list of states that are allowed to have nested transitions.
            Please check that you have called the add_fsm_to_memory function. It adds the state to the list.""")
        
        # get the list of FSM associated with the given state
        cur_memory_state = self.memory.get(state)     
        
        # add_transition to the last FSM. Note that cur_memory_state[-1] returns the last inserted FSM 
        cur_memory_state[-1].add_transition(input_symbol, nested_state, next_nested_state, action, transition_context)
            
    def set_default_transition (self, action, next_state):

        """This sets the default transition. This defines an action and
        next_state if the FSM cannot find the input symbol and the current
        state in the transition list and if the FSM cannot find the
        current_state in the transition_any list. This is useful as a final
        fall-through state for catching errors and undefined states.

        The default transition can be removed by setting the attribute
        default_transition to None. """

        self.default_transition = (None, action, next_state)
      
    #-------------------------------------------Methods for handling global interrupt-------------------------
    def add_interrupt_transition(self, transition, next_state):
        self.interrupt_transition = transition
        self.interrupt_start_state = next_state 
        
    def get_interrupt_transition(self, input_transition):
        if ((self.interrupt_transition is not None) and (str(input_transition) == str(self.interrupt_transition))):
            return self.interrupt_start_state
        else: return None
    #-------------------------------------------End of Methods for handling global interrupt-------------------

    def set_error_transition (self, action, next_state):
        self.error_transition = (None, action, next_state)
            
    def get_transition_from_memory(self, input_symbol, state):
        (local_context, action, next_state) = (None, None, None)
        fsmList = self.memory[state]
        fired_fsm = None
        for cur_fsm in fsmList:
            (local_context, action, next_state) = cur_fsm.get_transition(input_symbol, 
                                                                         cur_fsm.current_state, 
                                                                         (None, None, None))
            if (next_state is not None):
                fired_fsm = cur_fsm
                cur_fsm.current_state  = next_state 
                break 

        # Important: here we assume that recursion has a control message that is send in order to end the reccursion
        if fired_fsm is not None:
            if ((next_state == state) or (cur_fsm.has_transition(self.END_PAR_TRANSITION, next_state))):
                self.memory[state].remove(cur_fsm)
            return (local_context, action, state)
        else:
            raise ExceptionFSM ('Transition is undefined: (%s, %s).' %
                                (str(input_symbol), str(state)) )

    def has_transition (self, input_symbol, state):
        (_, _, next_state) = self.get_transition(input_symbol, state, (None, None, None))
        
        if next_state is None:
            return False
        else: 
            return True 
    
    def get_transition (self, input_symbol, state, default = None):
    
            """This returns (action, next state) given an input_symbol and state.
            This does not modify the FSM state, so calling this method has no side
            effects. Normally you do not call this method directly. It is called by
            process().
    
            The sequence of steps to check for a defined transition goes from the
            most specific to the least specific.
    
            0. First, check whether the transitions in the state_memory. 
            If there is not transitions in the memory go to the next step 
            
            1. Check state_transitions[] that match exactly the tuple,
                (input_symbol, state)
    
            2. Check state_transitions_any[] that match (state)
                In other words, match a specific state and ANY input_symbol.
    
            3. Check if the default_transition is defined.
                This catches any input_symbol and any state.
                This is a handler for errors, undefined states, or defaults.
    
            4. No transition was defined. If we get here then raise an exception.
            """
            
            has_memory = self.memory.get(state, None)
            # TODO: Change to fsm to work without empty state 
            while (((self.empty_transition, state) in self.state_transitions) and
                    (state not in self.memory or not has_memory)):
                    (self.current_context, self.action, self.current_state) = self.state_transitions[(self.EMPTY_TRANSITION, state)]
            
            
                    state = self.current_state
            if ((input_symbol is not self.EMPTY_TRANSITION) and has_memory):
                return self.get_transition_from_memory(input_symbol, state)
            if self.state_transitions.has_key((input_symbol, state)):
                return self.state_transitions[(input_symbol, state)]
            elif self.state_transitions_any.has_key (state):
                return self.state_transitions_any[state]
            elif self.default_transition is not None:
                return self.default_transition
            elif (default is not None): 
                return default
            else:
                raise ExceptionFSM ('Transition is undefined: (%s, %s).' %
                                    (str(input_symbol), str(state)) )

    def test_for_end_state(self, state):
        while  (((self.empty_transition, state) in self.state_transitions) and \
                state not in self.end_states):
                (current_context, action, state) = self.state_transitions[(self.EMPTY_TRANSITION, state)]
        return state in self.end_states

    def process_list (self, inputs, payloads = None):
        if payloads is not None:
            if (len(inputs)!=len(payloads)):
                raise ExceptionFSM('The payload values does not match the number of messages.')
            for input_transition, payload in zip(inputs, payloads):
                self.process (input_transition, payload)
        else:
            for input_transition in inputs:
                self.process (input_transition)
            
    def process (self, input_transition, payload = None):

        """This is the main method that you call to process input. This may
        cause the FSM to change state and call an action. This method calls
        get_transition() to find the action and next_state associated with the
        input_symbol and current_state. If the action is None then the action
        is not called and only the current state is changed. This method
        processes one complete input symbol. You can process a list of symbols
        (or a string) by calling process_list(). """

        if (self.current_state == self.final_state):
            raise ExceptionFSM('What are you sending?The communication has finished.')
        
        #First, check for global interrupt
        start_interrupt_state = self.get_interrupt_transition(input_transition)
        if (start_interrupt_state is not None):
            self.current_state = start_interrupt_state
            
        self.input_symbol = input_transition
        self.current_payload = payload
        
            
        (self.current_context, self.action, self.next_state) = self.get_transition(self.input_symbol,
                                                                                    self.current_state)
        
        if (self.check_assertions):
            if (self.current_context is not None):
                self.add_to_context(self.current_context)
            
            if self.action is not None:
                self.execute_transition_action (self.action, self.context)
           
        self.current_state = self.next_state
        self.next_state = None
    
    def __update_context(self, key, value):
        self.context[key] = value
        
    def add_to_context(self, local_context):
        if len(local_context) >0:
            if self.current_payload is None: 
                raise ExceptionFSM('Payload is required when the assertion_ckech is enabled')
            if len(local_context) != len(self.current_payload):
                raise ExceptionFSM('Wrong number of payloads for the current message')
            [self.__update_context(value, type_converter[type_sig](payload))
             for (value, type_sig), payload in zip(local_context, self.current_payload)]
            
    def execute_transition_action(self, assertion, context):
        log.debug('context is %s', context)
        result =  assertion.check(context)
        if not result: raise ExceptionFailAssertion('Assertion fail for input transition:%s , context: %s and assertion:%s' 
                                                    %(self.input_symbol, context, assertion.statement))
        else: log.debug('Message %s is checked', self.input_symbol)
            
    def __eq__(self, other) : 
        return self.__dict__ == other.__dict__
    
    def __str__(self):
        return "<transition_table:%s;memory: %s>" %(self.state_transitions, self.memory.__repr__())
    def __repr__(self):
        return "<transition_table:%s;memory: %s>" %(self.state_transitions, self.memory.__repr__())
