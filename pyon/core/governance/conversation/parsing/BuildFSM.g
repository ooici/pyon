tree grammar BuildFSM;

options
{ 
 tokenVocab = Monitor;
 ASTLabelType = CommonTree;
 language= Python;
}

@header{
from core.fsm import FSM
from core.fsm import ExceptionFSM
from core.transition import TransitionFactory
from core.LocalType import LocalType
from extensions.SimpleLogic import *

def checkMessages(fsm):
	print "Message is checked: \%s" \%(fsm.input_symbol)
	

def nothing(fsm):
	print "I am invoked for empty transition"
def generate_ints():
	x = 1
    	while True:
        	yield x
        	x += 1

def format_state_name(state, parent_state = None):
	if parent_state is not None:
		return "\%s_\%s" \%(parent_state, state)
	else: return state


class FSMBuilderState(object):
	def __init__(self, parent= None):
	      
	    self.state_gen = generate_ints()
	    if (parent is not None): 
	    	self.fsm = FSM(format_state_name(self.state_gen.next(), self.parent.get_current_state()))
	    	self.set_interrupt_transition = parent.set_interrupt_transition
	    	self.top_parent = parent.top_parent
	    else: 
	    	self.fsm = FSM(self.state_gen.next())
	    	self.top_parent = self
	    	self.set_interrupt_transition = False
	    self.start_new_par_branch = False
	    # Choice States
	    self.choice_start_state = []
	    self.choice_end_state = []
	    # Recursion states
	    self.recursions_states = {}
	    self.parent = parent
        
	def move_current_state(self, value = None):
		if value is None:
			self.fsm.current_state = self.state_gen.next()
		else: 
			self.fsm.current_state = value
		return self.fsm.current_state
	def get_current_state(self):
		return self.fsm.current_state
		
	def add_transition(self, transition, assertion = None, transition_context  = None):	        
	       
	        if assertion is not None: preprocess_assertion = Assertion.create(assertion) 
	        else: preprocess_assertion = assertion
	        
		if self.parent is not None: 
			suffix = self.parent.get_current_state()
			self.parent.fsm.add_nested_transition(transition, 
								self.parent.get_current_state(),
								format_state_name(self.get_current_state(), suffix), 
								format_state_name(self.move_current_state(), suffix),
								preprocess_assertion, 
								transition_context)
		else:
			self.fsm.add_transition(transition, 
						self.get_current_state(), 
						self.move_current_state(), 
						preprocess_assertion, 
						transition_context)
		
		# We are in interrup block and want to set the first transition that occur as interrupt_transition
	        # This is a global try catch. We assume that do wraps the whole program 
	        if self.set_interrupt_transition: 
	        	self.set_interrupt_transition = False
	        	self.fsm.add_interrupt_transition(transition, self.interrupt_start_state)
	        
}

@init {
# memory here is used only for logging and debugging purposes. 
# We append bebugging information to memory so we can print it later. 
self.memory = []
self.main_fsm = FSMBuilderState()
self.current_fsm = self.main_fsm
}

description: ^(PROTOCOL activityDef+) {print "ProtocolDefinition"};
activityDef:
	^(RESV {local_context = []}
	   (^(VALUE ((val=ID vtype=(INT|STRING)){if (($val is not None) and ($vtype is not None)): local_context.append(($val.text, $vtype.text))})*)) 
	   rlabel = ID {#INFO: This is the way to write comments in actions self.memory.append('resv' + $rlabel.text)} 
	   (rtype = ID {self.memory.append($rtype.text)})* role = ID
	   (^(ASSERT (assertion=ASSERTION)?)))
	{
	 
	 self.current_fsm.add_transition(TransitionFactory.create(LocalType.RESV,$rlabel, $role), $assertion, local_context)
	}
	    
	|^(SEND {local_context = []}
       	   (^(VALUE ((val=ID vtype= (INT|STRING)){if (($val is not None) and ($vtype is not None)): local_context.append(($val.text, $vtype.text))})*)) 
	   slabel = ID {self.memory.append('send' + $slabel.text)} ( stype = ID {self.memory.append($stype.text)})* role = ID
	   (^(ASSERT (assertion=ASSERTION)?)))	  {self.memory.append('In SEND assertion')}
	{
	 self.current_fsm.add_transition(TransitionFactory.create(LocalType.SEND,$slabel, $role), $assertion, local_context)
	} 

	|^('choice' 
	{self.memory.append('enter choice state')
	 self.current_fsm.choice_start_state.append(self.current_fsm.get_current_state())
	 self.current_fsm.choice_end_state.append(self.current_fsm.state_gen.next())
	} 
	(^(BRANCH 
	{
	self.memory.append('enter choice branch and save the current state')
	
	self.current_fsm.move_current_state(self.current_fsm.choice_start_state[-1])
	} activityDef+)
	{
	self.memory.append('exit choice branch and set the current state to the end state for the choice')
	self.current_fsm.fsm.add_transition(self.current_fsm.fsm.EMPTY_TRANSITION, self.current_fsm.get_current_state(), self.current_fsm.choice_end_state[-1])
	})+) 
	{
	self.memory.append('set the current state to be equal to the end state for the choice')
	self.current_fsm.move_current_state(self.current_fsm.choice_end_state[-1])
	self.current_fsm.choice_end_state.pop()
	self.current_fsm.choice_start_state.pop()
	}

	| ^(PARALLEL 
        {
        self.memory.append('enter parallel state')
        self.parallel_root = self.current_fsm
        } 
	(^(BRANCH 
	{
	self.memory.append('enter parallel branch')
	nested_fsm = FSMBuilderState(self.parallel_root)
	self.parallel_root.fsm.add_fsm_to_memory(self.parallel_root.get_current_state(), nested_fsm.fsm)
	self.current_fsm = nested_fsm	
	} 
	(activityDef) +) 
	{
	self.memory.append('exit parallel branch')
	self.current_fsm.add_transition(self.current_fsm.fsm.END_PAR_TRANSITION)
	})+) 
	{self.memory.append('exit parallel state')
	 self.current_fsm = self.current_fsm.parent
	 self.current_fsm.fsm.add_transition(self.current_fsm.fsm.EMPTY_TRANSITION, self.current_fsm.get_current_state(), self.current_fsm.move_current_state())
	}

	|^('repeat'
	{self.memory.append('enter repeat state')} 
	(^(BRANCH (activityDef {self.memory.append('repeat statement')})+))) 
	{self.memory.append('exit repeat state')}

        |^('rec' label = ID
        {self.memory.append('enter rec state ' + $label.text + str(self.current_fsm.get_current_state()))
         self.current_fsm.recursions_states.setdefault($label.text, (self.current_fsm.get_current_state(), True))
        } 
	(^(BRANCH (activityDef {self.memory.append('rec statement')})+))) 
	{
	 (start_state, isActive) = self.current_fsm.recursions_states.get($label.text)
	 self.memory.append('exit rec state ' + $label.text + 'start_state' + str(start_state))
	 self.current_fsm.recursions_states[$label.text] = (start_state, False)	 
	}
	
	|^('RECLABEL'  labelID = ID 
	{
	
	(start_rec_state, isActive) = self.current_fsm.recursions_states.get($labelID.text)
	self.memory.append('rec label:' + $labelID.text + 'starts from state:' + str(start_rec_state))
	if isActive:
		self.current_fsm.fsm.add_transition(self.current_fsm.fsm.EMPTY_TRANSITION, 
						    self.current_fsm.get_current_state(), 
						    start_rec_state)
		# Generate unreachable state for the choice construct						    
		self.current_fsm.move_current_state()	
	else: raise ExceptionFSM('Calling a recusrion label from a recursion that is not valid')
	}) 
	{
	# Do not need it for no
        #self.current_fsm.fsm.copy_transitions(self.current_fsm.recursions_states[$labelID.text], self.current_fsm.get_current_state())
	}
	|^(GLOBAL_ESCAPE 
	   (^('do' (activityDef+){self.current_fsm.fsm.final_state = self.current_fsm.get_current_state()}))
	   (^('interrupt' roleName
	   {self.memory.append('before setting interrupt_transition to True')
	    self.current_fsm.interrupt_start_state = self.current_fsm.move_current_state()
	    self.current_fsm.set_interrupt_transition = True} (activityDef+))))
	;
roleName: ID;
labelName: ID;
roleDef: ID;
primitivetype :INT;



