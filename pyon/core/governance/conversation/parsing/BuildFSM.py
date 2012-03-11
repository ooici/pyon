# $ANTLR 3.1.3 Mar 18, 2009 10:09:25 src/SavedFSM/BuildFSM.g 2012-02-23 18:26:58

import sys
from antlr3 import *
from antlr3.tree import *
from antlr3.compat import set, frozenset

from ..core.fsm import FSM
from ..core.fsm import ExceptionFSM
from ..core.transition import TransitionFactory
from ..core.LocalType import LocalType
from ..extensions.SimpleLogic import *

def checkMessages(fsm):
	print "Message is checked: %s" %(fsm.input_symbol)
	

def nothing(fsm):
	print "I am invoked for empty transition"
def generate_ints():
	x = 1
    	while True:
        	yield x
        	x += 1

def format_state_name(state, parent_state = None):
	if parent_state is not None:
		return "%s_%s" %(parent_state, state)
	else: return state


class FSMBuilderState(object):
	def __init__(self, parent= None):
	    self.state_gen = generate_ints()
	    self.current_state = self.state_gen.next()
	    if (parent is not None): 
	    	self.parent = parent  
	    	self.fsm = FSM(format_state_name(self.current_state, self.parent.get_current_state()))
	    	self.set_interrupt_transition = self.parent.set_interrupt_transition
	    	self.top_parent = parent.top_parent
	    else: 
	    	self.fsm = FSM(self.current_state)
	    	self.top_parent = self
	    	self.set_interrupt_transition = False
	    self.start_new_par_branch = False
	    # Choice States
	    self.choice_start_state = []
	    self.choice_end_state = []
	    # Recursion states
	    self.recursions_states = {}
	    self.parent = parent  
       

	def format_state_name(self, state):
		if self.parent is not None:
			return "%s_%s" %(self.parent.get_current_state(), state)
		else: return state
	 
	def move_current_state(self, value = None):
		if value is None:
			self.current_state = self.state_gen.next()
		else: 
			self.current_state = value
		return self.current_state
	def get_current_state(self):
		return self.current_state
		
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
	        



# for convenience in actions
HIDDEN = BaseRecognizer.HIDDEN

# token types
RESV=12
ANNOTATION=24
ASSERTION=27
PARALLEL=19
ID=25
T__60=60
EOF=-1
PROTOCOL=20
TYPE=14
T__55=55
INTERACTION=4
T__56=56
ML_COMMENT=31
T__57=57
T__58=58
T__51=51
T__52=52
T__53=53
T__54=54
T__59=59
FULLSTOP=11
PLUS=7
SEND=13
DIGIT=29
T__50=50
T__42=42
T__43=43
T__40=40
T__41=41
T__46=46
T__47=47
T__44=44
T__45=45
LINE_COMMENT=32
T__48=48
T__49=49
RECLABEL=18
NUMBER=28
WHITESPACE=30
INT=5
VALUE=15
MULT=9
MINUS=8
ASSERT=21
UNORDERED=17
EMPTY=23
StringLiteral=26
T__33=33
T__34=34
GLOBAL_ESCAPE=22
T__35=35
T__36=36
T__37=37
T__38=38
T__39=39
BRANCH=16
DIV=10
STRING=6

# token names
tokenNames = [
    "<invalid>", "<EOR>", "<DOWN>", "<UP>", 
    "INTERACTION", "INT", "STRING", "PLUS", "MINUS", "MULT", "DIV", "FULLSTOP", 
    "RESV", "SEND", "TYPE", "VALUE", "BRANCH", "UNORDERED", "RECLABEL", 
    "PARALLEL", "PROTOCOL", "ASSERT", "GLOBAL_ESCAPE", "EMPTY", "ANNOTATION", 
    "ID", "StringLiteral", "ASSERTION", "NUMBER", "DIGIT", "WHITESPACE", 
    "ML_COMMENT", "LINE_COMMENT", "'import'", "'protocol'", "','", "';'", 
    "'from'", "'as'", "'at'", "'{'", "'}'", "'('", "')'", "'role'", "'introduces'", 
    "':'", "'to'", "'choice'", "'or'", "'repeat'", "'rec'", "'end'", "'run'", 
    "'inline'", "'parallel'", "'and'", "'do'", "'interrupt'", "'by'", "'unordered'"
]




class BuildFSM(TreeParser):
    grammarFileName = "src/SavedFSM/BuildFSM.g"
    antlr_version = version_str_to_tuple("3.1.3 Mar 18, 2009 10:09:25")
    antlr_version_str = "3.1.3 Mar 18, 2009 10:09:25"
    tokenNames = tokenNames

    def __init__(self, input, state=None, *args, **kwargs):
        if state is None:
            state = RecognizerSharedState()

        super(BuildFSM, self).__init__(input, state, *args, **kwargs)



               
        # memory here is used only for logging and debugging purposes. 
        # We append bebugging information to memory so we can print it later. 
        self.memory = []
        self.main_fsm = FSMBuilderState()
        self.current_fsm = self.main_fsm




                


        



    # $ANTLR start "description"
    # src/SavedFSM/BuildFSM.g:107:1: description : ^( PROTOCOL ( activityDef )+ ) ;
    def description(self, ):

        try:
            try:
                # src/SavedFSM/BuildFSM.g:107:12: ( ^( PROTOCOL ( activityDef )+ ) )
                # src/SavedFSM/BuildFSM.g:107:14: ^( PROTOCOL ( activityDef )+ )
                pass 
                self.match(self.input, PROTOCOL, self.FOLLOW_PROTOCOL_in_description52)

                self.match(self.input, DOWN, None)
                # src/SavedFSM/BuildFSM.g:107:25: ( activityDef )+
                cnt1 = 0
                while True: #loop1
                    alt1 = 2
                    LA1_0 = self.input.LA(1)

                    if ((RESV <= LA1_0 <= SEND) or (RECLABEL <= LA1_0 <= PARALLEL) or LA1_0 == GLOBAL_ESCAPE or LA1_0 == 48 or (50 <= LA1_0 <= 51)) :
                        alt1 = 1


                    if alt1 == 1:
                        # src/SavedFSM/BuildFSM.g:107:25: activityDef
                        pass 
                        self._state.following.append(self.FOLLOW_activityDef_in_description54)
                        self.activityDef()

                        self._state.following.pop()


                    else:
                        if cnt1 >= 1:
                            break #loop1

                        eee = EarlyExitException(1, self.input)
                        raise eee

                    cnt1 += 1

                self.match(self.input, UP, None)
                #action start
                print "ProtocolDefinition"
                #action end




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return 

    # $ANTLR end "description"


    # $ANTLR start "activityDef"
    # src/SavedFSM/BuildFSM.g:108:1: activityDef : ( ^( RESV (rlabel= ID )? ( ^( VALUE ( (val= ID (vtype= ( INT | STRING ) )? ) )* ) ) role= ID ( ^( ASSERT (assertion= ASSERTION )? ) ) ) | ^( SEND (slabel= ID )? ( ^( VALUE ( (val= ID (vtype= ( INT | STRING ) )? ) )* ) ) role= ID ( ^( ASSERT (assertion= ASSERTION )? ) ) ) | ^( 'choice' ( ^( BRANCH ( activityDef )+ ) )+ ) | ^( PARALLEL ( ^( BRANCH ( activityDef )+ ) )+ ) | ^( 'repeat' ( ^( BRANCH ( activityDef )+ ) ) ) | ^( 'rec' label= ID ( ^( BRANCH ( activityDef )+ ) ) ) | ^( 'RECLABEL' labelID= ID ) | ^( GLOBAL_ESCAPE ( ^( 'do' ( ( activityDef )+ ) ) ) ( ^( 'interrupt' roleName ( ( activityDef )+ ) ) ) ) );
    def activityDef(self, ):

        rlabel = None
        val = None
        vtype = None
        role = None
        assertion = None
        slabel = None
        label = None
        labelID = None

        try:
            try:
                # src/SavedFSM/BuildFSM.g:108:12: ( ^( RESV (rlabel= ID )? ( ^( VALUE ( (val= ID (vtype= ( INT | STRING ) )? ) )* ) ) role= ID ( ^( ASSERT (assertion= ASSERTION )? ) ) ) | ^( SEND (slabel= ID )? ( ^( VALUE ( (val= ID (vtype= ( INT | STRING ) )? ) )* ) ) role= ID ( ^( ASSERT (assertion= ASSERTION )? ) ) ) | ^( 'choice' ( ^( BRANCH ( activityDef )+ ) )+ ) | ^( PARALLEL ( ^( BRANCH ( activityDef )+ ) )+ ) | ^( 'repeat' ( ^( BRANCH ( activityDef )+ ) ) ) | ^( 'rec' label= ID ( ^( BRANCH ( activityDef )+ ) ) ) | ^( 'RECLABEL' labelID= ID ) | ^( GLOBAL_ESCAPE ( ^( 'do' ( ( activityDef )+ ) ) ) ( ^( 'interrupt' roleName ( ( activityDef )+ ) ) ) ) )
                alt18 = 8
                LA18 = self.input.LA(1)
                if LA18 == RESV:
                    alt18 = 1
                elif LA18 == SEND:
                    alt18 = 2
                elif LA18 == 48:
                    alt18 = 3
                elif LA18 == PARALLEL:
                    alt18 = 4
                elif LA18 == 50:
                    alt18 = 5
                elif LA18 == 51:
                    alt18 = 6
                elif LA18 == RECLABEL:
                    alt18 = 7
                elif LA18 == GLOBAL_ESCAPE:
                    alt18 = 8
                else:
                    nvae = NoViableAltException("", 18, 0, self.input)

                    raise nvae

                if alt18 == 1:
                    # src/SavedFSM/BuildFSM.g:109:2: ^( RESV (rlabel= ID )? ( ^( VALUE ( (val= ID (vtype= ( INT | STRING ) )? ) )* ) ) role= ID ( ^( ASSERT (assertion= ASSERTION )? ) ) )
                    pass 
                    self.match(self.input, RESV, self.FOLLOW_RESV_in_activityDef66)

                    #action start
                             
                    local_context = []
                    label = ''
                    #action end

                    self.match(self.input, DOWN, None)
                    # src/SavedFSM/BuildFSM.g:112:5: (rlabel= ID )?
                    alt2 = 2
                    LA2_0 = self.input.LA(1)

                    if (LA2_0 == ID) :
                        alt2 = 1
                    if alt2 == 1:
                        # src/SavedFSM/BuildFSM.g:112:6: rlabel= ID
                        pass 
                        rlabel=self.match(self.input, ID, self.FOLLOW_ID_in_activityDef79)
                        #action start
                                          
                        if (rlabel is not None): label = rlabel.text
                        self.memory.append('before setting the label:' +  label)
                        #action end



                    # src/SavedFSM/BuildFSM.g:115:5: ( ^( VALUE ( (val= ID (vtype= ( INT | STRING ) )? ) )* ) )
                    # src/SavedFSM/BuildFSM.g:115:6: ^( VALUE ( (val= ID (vtype= ( INT | STRING ) )? ) )* )
                    pass 
                    self.match(self.input, VALUE, self.FOLLOW_VALUE_in_activityDef91)

                    if self.input.LA(1) == DOWN:
                        self.match(self.input, DOWN, None)
                        # src/SavedFSM/BuildFSM.g:115:14: ( (val= ID (vtype= ( INT | STRING ) )? ) )*
                        while True: #loop4
                            alt4 = 2
                            LA4_0 = self.input.LA(1)

                            if (LA4_0 == ID) :
                                alt4 = 1


                            if alt4 == 1:
                                # src/SavedFSM/BuildFSM.g:115:15: (val= ID (vtype= ( INT | STRING ) )? )
                                pass 
                                # src/SavedFSM/BuildFSM.g:115:15: (val= ID (vtype= ( INT | STRING ) )? )
                                # src/SavedFSM/BuildFSM.g:115:16: val= ID (vtype= ( INT | STRING ) )?
                                pass 
                                val=self.match(self.input, ID, self.FOLLOW_ID_in_activityDef97)
                                # src/SavedFSM/BuildFSM.g:115:28: (vtype= ( INT | STRING ) )?
                                alt3 = 2
                                LA3_0 = self.input.LA(1)

                                if ((INT <= LA3_0 <= STRING)) :
                                    alt3 = 1
                                if alt3 == 1:
                                    # src/SavedFSM/BuildFSM.g:115:28: vtype= ( INT | STRING )
                                    pass 
                                    vtype = self.input.LT(1)
                                    if (INT <= self.input.LA(1) <= STRING):
                                        self.input.consume()
                                        self._state.errorRecovery = False

                                    else:
                                        mse = MismatchedSetException(None, self.input)
                                        raise mse








                                #action start
                                if ((val is not None) and (vtype is not None)): local_context.append((val.text, vtype.text))
                                #action end


                            else:
                                break #loop4

                        self.match(self.input, UP, None)




                    role=self.match(self.input, ID, self.FOLLOW_ID_in_activityDef122)
                    # src/SavedFSM/BuildFSM.g:117:5: ( ^( ASSERT (assertion= ASSERTION )? ) )
                    # src/SavedFSM/BuildFSM.g:117:6: ^( ASSERT (assertion= ASSERTION )? )
                    pass 
                    self.match(self.input, ASSERT, self.FOLLOW_ASSERT_in_activityDef130)

                    if self.input.LA(1) == DOWN:
                        self.match(self.input, DOWN, None)
                        # src/SavedFSM/BuildFSM.g:117:15: (assertion= ASSERTION )?
                        alt5 = 2
                        LA5_0 = self.input.LA(1)

                        if (LA5_0 == ASSERTION) :
                            alt5 = 1
                        if alt5 == 1:
                            # src/SavedFSM/BuildFSM.g:117:16: assertion= ASSERTION
                            pass 
                            assertion=self.match(self.input, ASSERTION, self.FOLLOW_ASSERTION_in_activityDef135)




                        self.match(self.input, UP, None)





                    self.match(self.input, UP, None)
                    #action start
                      
                    self.memory.append('label is:' +  label);
                    self.current_fsm.add_transition(TransitionFactory.create(LocalType.RESV, label, role), assertion, local_context)
                    	
                    #action end


                elif alt18 == 2:
                    # src/SavedFSM/BuildFSM.g:123:3: ^( SEND (slabel= ID )? ( ^( VALUE ( (val= ID (vtype= ( INT | STRING ) )? ) )* ) ) role= ID ( ^( ASSERT (assertion= ASSERTION )? ) ) )
                    pass 
                    self.match(self.input, SEND, self.FOLLOW_SEND_in_activityDef154)

                    #action start
                              
                    local_context = []
                    label = ''
                    #action end

                    self.match(self.input, DOWN, None)
                    # src/SavedFSM/BuildFSM.g:126:5: (slabel= ID )?
                    alt6 = 2
                    LA6_0 = self.input.LA(1)

                    if (LA6_0 == ID) :
                        alt6 = 1
                    if alt6 == 1:
                        # src/SavedFSM/BuildFSM.g:126:6: slabel= ID
                        pass 
                        slabel=self.match(self.input, ID, self.FOLLOW_ID_in_activityDef167)
                        #action start
                                          
                        self.memory.append('send' + slabel.text)
                        if (slabel is not None): label = slabel.text
                        #action end



                    # src/SavedFSM/BuildFSM.g:129:12: ( ^( VALUE ( (val= ID (vtype= ( INT | STRING ) )? ) )* ) )
                    # src/SavedFSM/BuildFSM.g:129:13: ^( VALUE ( (val= ID (vtype= ( INT | STRING ) )? ) )* )
                    pass 
                    self.match(self.input, VALUE, self.FOLLOW_VALUE_in_activityDef186)

                    if self.input.LA(1) == DOWN:
                        self.match(self.input, DOWN, None)
                        # src/SavedFSM/BuildFSM.g:129:21: ( (val= ID (vtype= ( INT | STRING ) )? ) )*
                        while True: #loop8
                            alt8 = 2
                            LA8_0 = self.input.LA(1)

                            if (LA8_0 == ID) :
                                alt8 = 1


                            if alt8 == 1:
                                # src/SavedFSM/BuildFSM.g:129:22: (val= ID (vtype= ( INT | STRING ) )? )
                                pass 
                                # src/SavedFSM/BuildFSM.g:129:22: (val= ID (vtype= ( INT | STRING ) )? )
                                # src/SavedFSM/BuildFSM.g:129:23: val= ID (vtype= ( INT | STRING ) )?
                                pass 
                                val=self.match(self.input, ID, self.FOLLOW_ID_in_activityDef192)
                                # src/SavedFSM/BuildFSM.g:129:35: (vtype= ( INT | STRING ) )?
                                alt7 = 2
                                LA7_0 = self.input.LA(1)

                                if ((INT <= LA7_0 <= STRING)) :
                                    alt7 = 1
                                if alt7 == 1:
                                    # src/SavedFSM/BuildFSM.g:129:35: vtype= ( INT | STRING )
                                    pass 
                                    vtype = self.input.LT(1)
                                    if (INT <= self.input.LA(1) <= STRING):
                                        self.input.consume()
                                        self._state.errorRecovery = False

                                    else:
                                        mse = MismatchedSetException(None, self.input)
                                        raise mse








                                #action start
                                if ((val is not None) and (vtype is not None)): local_context.append((val.text, vtype.text))
                                #action end


                            else:
                                break #loop8

                        self.match(self.input, UP, None)




                    role=self.match(self.input, ID, self.FOLLOW_ID_in_activityDef221)
                    # src/SavedFSM/BuildFSM.g:131:5: ( ^( ASSERT (assertion= ASSERTION )? ) )
                    # src/SavedFSM/BuildFSM.g:131:6: ^( ASSERT (assertion= ASSERTION )? )
                    pass 
                    self.match(self.input, ASSERT, self.FOLLOW_ASSERT_in_activityDef229)

                    if self.input.LA(1) == DOWN:
                        self.match(self.input, DOWN, None)
                        # src/SavedFSM/BuildFSM.g:131:15: (assertion= ASSERTION )?
                        alt9 = 2
                        LA9_0 = self.input.LA(1)

                        if (LA9_0 == ASSERTION) :
                            alt9 = 1
                        if alt9 == 1:
                            # src/SavedFSM/BuildFSM.g:131:16: assertion= ASSERTION
                            pass 
                            assertion=self.match(self.input, ASSERTION, self.FOLLOW_ASSERTION_in_activityDef234)




                        self.match(self.input, UP, None)





                    self.match(self.input, UP, None)
                    #action start
                    self.memory.append('In SEND assertion')
                    #action end
                    #action start
                      
                    self.current_fsm.add_transition(TransitionFactory.create(LocalType.SEND, label, role), assertion, local_context)
                    	
                    #action end


                elif alt18 == 3:
                    # src/SavedFSM/BuildFSM.g:136:3: ^( 'choice' ( ^( BRANCH ( activityDef )+ ) )+ )
                    pass 
                    self.match(self.input, 48, self.FOLLOW_48_in_activityDef253)

                    #action start
                    self.memory.append('enter choice state')
                    self.current_fsm.choice_start_state.append(self.current_fsm.get_current_state())
                    self.current_fsm.choice_end_state.append(self.current_fsm.state_gen.next())
                    	
                    #action end

                    self.match(self.input, DOWN, None)
                    # src/SavedFSM/BuildFSM.g:141:2: ( ^( BRANCH ( activityDef )+ ) )+
                    cnt11 = 0
                    while True: #loop11
                        alt11 = 2
                        LA11_0 = self.input.LA(1)

                        if (LA11_0 == BRANCH) :
                            alt11 = 1


                        if alt11 == 1:
                            # src/SavedFSM/BuildFSM.g:141:3: ^( BRANCH ( activityDef )+ )
                            pass 
                            self.match(self.input, BRANCH, self.FOLLOW_BRANCH_in_activityDef263)

                            #action start
                              
                            self.memory.append('enter choice branch and save the current state')

                            self.current_fsm.move_current_state(self.current_fsm.choice_start_state[-1])
                            	
                            #action end

                            self.match(self.input, DOWN, None)
                            # src/SavedFSM/BuildFSM.g:146:4: ( activityDef )+
                            cnt10 = 0
                            while True: #loop10
                                alt10 = 2
                                LA10_0 = self.input.LA(1)

                                if ((RESV <= LA10_0 <= SEND) or (RECLABEL <= LA10_0 <= PARALLEL) or LA10_0 == GLOBAL_ESCAPE or LA10_0 == 48 or (50 <= LA10_0 <= 51)) :
                                    alt10 = 1


                                if alt10 == 1:
                                    # src/SavedFSM/BuildFSM.g:146:4: activityDef
                                    pass 
                                    self._state.following.append(self.FOLLOW_activityDef_in_activityDef269)
                                    self.activityDef()

                                    self._state.following.pop()


                                else:
                                    if cnt10 >= 1:
                                        break #loop10

                                    eee = EarlyExitException(10, self.input)
                                    raise eee

                                cnt10 += 1

                            self.match(self.input, UP, None)
                            #action start
                              
                            self.memory.append('exit choice branch and set the current state to the end state for the choice')
                            self.current_fsm.fsm.add_transition(self.current_fsm.fsm.EMPTY_TRANSITION, self.current_fsm.get_current_state(), self.current_fsm.choice_end_state[-1])
                            	
                            #action end


                        else:
                            if cnt11 >= 1:
                                break #loop11

                            eee = EarlyExitException(11, self.input)
                            raise eee

                        cnt11 += 1

                    self.match(self.input, UP, None)
                    #action start
                      
                    self.memory.append('set the current state to be equal to the end state for the choice')
                    self.current_fsm.move_current_state(self.current_fsm.choice_end_state[-1])
                    self.current_fsm.choice_end_state.pop()
                    self.current_fsm.choice_start_state.pop()
                    	
                    #action end


                elif alt18 == 4:
                    # src/SavedFSM/BuildFSM.g:158:4: ^( PARALLEL ( ^( BRANCH ( activityDef )+ ) )+ )
                    pass 
                    self.match(self.input, PARALLEL, self.FOLLOW_PARALLEL_in_activityDef288)

                    #action start
                             
                    self.memory.append('enter parallel state')
                    self.parallel_root = self.current_fsm
                            
                    #action end

                    self.match(self.input, DOWN, None)
                    # src/SavedFSM/BuildFSM.g:163:2: ( ^( BRANCH ( activityDef )+ ) )+
                    cnt13 = 0
                    while True: #loop13
                        alt13 = 2
                        LA13_0 = self.input.LA(1)

                        if (LA13_0 == BRANCH) :
                            alt13 = 1


                        if alt13 == 1:
                            # src/SavedFSM/BuildFSM.g:163:3: ^( BRANCH ( activityDef )+ )
                            pass 
                            self.match(self.input, BRANCH, self.FOLLOW_BRANCH_in_activityDef305)

                            #action start
                              
                            self.memory.append('enter parallel branch')
                            nested_fsm = FSMBuilderState(self.parallel_root)
                            self.parallel_root.fsm.add_fsm_to_memory(self.parallel_root.get_current_state(), nested_fsm.fsm)
                            self.current_fsm = nested_fsm	
                            	
                            #action end

                            self.match(self.input, DOWN, None)
                            # src/SavedFSM/BuildFSM.g:170:2: ( activityDef )+
                            cnt12 = 0
                            while True: #loop12
                                alt12 = 2
                                LA12_0 = self.input.LA(1)

                                if ((RESV <= LA12_0 <= SEND) or (RECLABEL <= LA12_0 <= PARALLEL) or LA12_0 == GLOBAL_ESCAPE or LA12_0 == 48 or (50 <= LA12_0 <= 51)) :
                                    alt12 = 1


                                if alt12 == 1:
                                    # src/SavedFSM/BuildFSM.g:170:3: activityDef
                                    pass 
                                    self._state.following.append(self.FOLLOW_activityDef_in_activityDef314)
                                    self.activityDef()

                                    self._state.following.pop()


                                else:
                                    if cnt12 >= 1:
                                        break #loop12

                                    eee = EarlyExitException(12, self.input)
                                    raise eee

                                cnt12 += 1

                            self.match(self.input, UP, None)
                            #action start
                              
                            self.memory.append('exit parallel branch')
                            self.current_fsm.add_transition(self.current_fsm.fsm.END_PAR_TRANSITION)
                            	
                            #action end


                        else:
                            if cnt13 >= 1:
                                break #loop13

                            eee = EarlyExitException(13, self.input)
                            raise eee

                        cnt13 += 1

                    self.match(self.input, UP, None)
                    #action start
                    self.memory.append('exit parallel state')
                    self.current_fsm = self.current_fsm.parent
                    self.current_fsm.fsm.add_transition(self.current_fsm.fsm.EMPTY_TRANSITION, self.current_fsm.get_current_state(), self.current_fsm.move_current_state())
                    	
                    #action end


                elif alt18 == 5:
                    # src/SavedFSM/BuildFSM.g:180:3: ^( 'repeat' ( ^( BRANCH ( activityDef )+ ) ) )
                    pass 
                    self.match(self.input, 50, self.FOLLOW_50_in_activityDef335)

                    #action start
                    self.memory.append('enter repeat state')
                    #action end

                    self.match(self.input, DOWN, None)
                    # src/SavedFSM/BuildFSM.g:182:2: ( ^( BRANCH ( activityDef )+ ) )
                    # src/SavedFSM/BuildFSM.g:182:3: ^( BRANCH ( activityDef )+ )
                    pass 
                    self.match(self.input, BRANCH, self.FOLLOW_BRANCH_in_activityDef344)

                    self.match(self.input, DOWN, None)
                    # src/SavedFSM/BuildFSM.g:182:12: ( activityDef )+
                    cnt14 = 0
                    while True: #loop14
                        alt14 = 2
                        LA14_0 = self.input.LA(1)

                        if ((RESV <= LA14_0 <= SEND) or (RECLABEL <= LA14_0 <= PARALLEL) or LA14_0 == GLOBAL_ESCAPE or LA14_0 == 48 or (50 <= LA14_0 <= 51)) :
                            alt14 = 1


                        if alt14 == 1:
                            # src/SavedFSM/BuildFSM.g:182:13: activityDef
                            pass 
                            self._state.following.append(self.FOLLOW_activityDef_in_activityDef347)
                            self.activityDef()

                            self._state.following.pop()
                            #action start
                            self.memory.append('repeat statement')
                            #action end


                        else:
                            if cnt14 >= 1:
                                break #loop14

                            eee = EarlyExitException(14, self.input)
                            raise eee

                        cnt14 += 1

                    self.match(self.input, UP, None)




                    self.match(self.input, UP, None)
                    #action start
                    self.memory.append('exit repeat state')
                    #action end


                elif alt18 == 6:
                    # src/SavedFSM/BuildFSM.g:185:10: ^( 'rec' label= ID ( ^( BRANCH ( activityDef )+ ) ) )
                    pass 
                    self.match(self.input, 51, self.FOLLOW_51_in_activityDef371)

                    self.match(self.input, DOWN, None)
                    label=self.match(self.input, ID, self.FOLLOW_ID_in_activityDef377)
                    #action start
                    self.memory.append('enter rec state ' + label.text + str(self.current_fsm.get_current_state()))
                    self.current_fsm.recursions_states.setdefault(label.text, (self.current_fsm.format_state_name(self.current_fsm.get_current_state()), True))
                            
                    #action end
                    # src/SavedFSM/BuildFSM.g:189:2: ( ^( BRANCH ( activityDef )+ ) )
                    # src/SavedFSM/BuildFSM.g:189:3: ^( BRANCH ( activityDef )+ )
                    pass 
                    self.match(self.input, BRANCH, self.FOLLOW_BRANCH_in_activityDef393)

                    self.match(self.input, DOWN, None)
                    # src/SavedFSM/BuildFSM.g:189:12: ( activityDef )+
                    cnt15 = 0
                    while True: #loop15
                        alt15 = 2
                        LA15_0 = self.input.LA(1)

                        if ((RESV <= LA15_0 <= SEND) or (RECLABEL <= LA15_0 <= PARALLEL) or LA15_0 == GLOBAL_ESCAPE or LA15_0 == 48 or (50 <= LA15_0 <= 51)) :
                            alt15 = 1


                        if alt15 == 1:
                            # src/SavedFSM/BuildFSM.g:189:13: activityDef
                            pass 
                            self._state.following.append(self.FOLLOW_activityDef_in_activityDef396)
                            self.activityDef()

                            self._state.following.pop()
                            #action start
                            self.memory.append('rec statement')
                            #action end


                        else:
                            if cnt15 >= 1:
                                break #loop15

                            eee = EarlyExitException(15, self.input)
                            raise eee

                        cnt15 += 1

                    self.match(self.input, UP, None)




                    self.match(self.input, UP, None)
                    #action start
                      
                    (start_state, isActive) = self.current_fsm.recursions_states.get(label.text)
                    self.memory.append('exit rec state ' + label.text + 'start_state' + str(start_state))
                    self.current_fsm.recursions_states[label.text] = (start_state, False)	 
                    	
                    #action end


                elif alt18 == 7:
                    # src/SavedFSM/BuildFSM.g:196:3: ^( 'RECLABEL' labelID= ID )
                    pass 
                    self.match(self.input, RECLABEL, self.FOLLOW_RECLABEL_in_activityDef414)

                    self.match(self.input, DOWN, None)
                    labelID=self.match(self.input, ID, self.FOLLOW_ID_in_activityDef421)
                    #action start
                      
                    	
                    (start_rec_state, isActive) = self.current_fsm.recursions_states.get(labelID.text)
                    self.memory.append('rec label:' + labelID.text + 'starts from state:' + str(start_rec_state))
                    if isActive:
                    	self.current_fsm.fsm.add_transition(self.current_fsm.fsm.EMPTY_TRANSITION, 
                    					    self.current_fsm.format_state_name(self.current_fsm.get_current_state()), 
                    					    start_rec_state)
                    	# Generate unreachable state for the choice construct						    
                    	self.current_fsm.move_current_state()	
                    else: raise ExceptionFSM('Calling a recusrion label from a recursion that is not valid')
                    	
                    #action end

                    self.match(self.input, UP, None)
                    #action start
                      
                    # Do not need it for no
                           #self.current_fsm.fsm.copy_transitions(self.current_fsm.recursions_states[labelID.text], self.current_fsm.get_current_state())
                    	
                    #action end


                elif alt18 == 8:
                    # src/SavedFSM/BuildFSM.g:213:3: ^( GLOBAL_ESCAPE ( ^( 'do' ( ( activityDef )+ ) ) ) ( ^( 'interrupt' roleName ( ( activityDef )+ ) ) ) )
                    pass 
                    self.match(self.input, GLOBAL_ESCAPE, self.FOLLOW_GLOBAL_ESCAPE_in_activityDef435)

                    self.match(self.input, DOWN, None)
                    # src/SavedFSM/BuildFSM.g:214:5: ( ^( 'do' ( ( activityDef )+ ) ) )
                    # src/SavedFSM/BuildFSM.g:214:6: ^( 'do' ( ( activityDef )+ ) )
                    pass 
                    self.match(self.input, 57, self.FOLLOW_57_in_activityDef444)

                    self.match(self.input, DOWN, None)
                    # src/SavedFSM/BuildFSM.g:214:13: ( ( activityDef )+ )
                    # src/SavedFSM/BuildFSM.g:214:14: ( activityDef )+
                    pass 
                    # src/SavedFSM/BuildFSM.g:214:14: ( activityDef )+
                    cnt16 = 0
                    while True: #loop16
                        alt16 = 2
                        LA16_0 = self.input.LA(1)

                        if ((RESV <= LA16_0 <= SEND) or (RECLABEL <= LA16_0 <= PARALLEL) or LA16_0 == GLOBAL_ESCAPE or LA16_0 == 48 or (50 <= LA16_0 <= 51)) :
                            alt16 = 1


                        if alt16 == 1:
                            # src/SavedFSM/BuildFSM.g:214:14: activityDef
                            pass 
                            self._state.following.append(self.FOLLOW_activityDef_in_activityDef447)
                            self.activityDef()

                            self._state.following.pop()


                        else:
                            if cnt16 >= 1:
                                break #loop16

                            eee = EarlyExitException(16, self.input)
                            raise eee

                        cnt16 += 1



                    #action start
                    self.current_fsm.fsm.final_state = self.current_fsm.get_current_state()
                    #action end

                    self.match(self.input, UP, None)



                    # src/SavedFSM/BuildFSM.g:215:5: ( ^( 'interrupt' roleName ( ( activityDef )+ ) ) )
                    # src/SavedFSM/BuildFSM.g:215:6: ^( 'interrupt' roleName ( ( activityDef )+ ) )
                    pass 
                    self.match(self.input, 58, self.FOLLOW_58_in_activityDef460)

                    self.match(self.input, DOWN, None)
                    self._state.following.append(self.FOLLOW_roleName_in_activityDef462)
                    self.roleName()

                    self._state.following.pop()
                    #action start
                    self.memory.append('before setting interrupt_transition to True')
                    self.current_fsm.interrupt_start_state = self.current_fsm.move_current_state()
                    self.current_fsm.set_interrupt_transition = True
                    #action end
                    # src/SavedFSM/BuildFSM.g:218:56: ( ( activityDef )+ )
                    # src/SavedFSM/BuildFSM.g:218:57: ( activityDef )+
                    pass 
                    # src/SavedFSM/BuildFSM.g:218:57: ( activityDef )+
                    cnt17 = 0
                    while True: #loop17
                        alt17 = 2
                        LA17_0 = self.input.LA(1)

                        if ((RESV <= LA17_0 <= SEND) or (RECLABEL <= LA17_0 <= PARALLEL) or LA17_0 == GLOBAL_ESCAPE or LA17_0 == 48 or (50 <= LA17_0 <= 51)) :
                            alt17 = 1


                        if alt17 == 1:
                            # src/SavedFSM/BuildFSM.g:218:57: activityDef
                            pass 
                            self._state.following.append(self.FOLLOW_activityDef_in_activityDef471)
                            self.activityDef()

                            self._state.following.pop()


                        else:
                            if cnt17 >= 1:
                                break #loop17

                            eee = EarlyExitException(17, self.input)
                            raise eee

                        cnt17 += 1




                    self.match(self.input, UP, None)




                    self.match(self.input, UP, None)



            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return 

    # $ANTLR end "activityDef"


    # $ANTLR start "roleName"
    # src/SavedFSM/BuildFSM.g:220:1: roleName : ID ;
    def roleName(self, ):

        try:
            try:
                # src/SavedFSM/BuildFSM.g:220:9: ( ID )
                # src/SavedFSM/BuildFSM.g:220:11: ID
                pass 
                self.match(self.input, ID, self.FOLLOW_ID_in_roleName484)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return 

    # $ANTLR end "roleName"


    # $ANTLR start "labelName"
    # src/SavedFSM/BuildFSM.g:221:1: labelName : ID ;
    def labelName(self, ):

        try:
            try:
                # src/SavedFSM/BuildFSM.g:221:10: ( ID )
                # src/SavedFSM/BuildFSM.g:221:12: ID
                pass 
                self.match(self.input, ID, self.FOLLOW_ID_in_labelName490)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return 

    # $ANTLR end "labelName"


    # $ANTLR start "roleDef"
    # src/SavedFSM/BuildFSM.g:222:1: roleDef : ID ;
    def roleDef(self, ):

        try:
            try:
                # src/SavedFSM/BuildFSM.g:222:8: ( ID )
                # src/SavedFSM/BuildFSM.g:222:10: ID
                pass 
                self.match(self.input, ID, self.FOLLOW_ID_in_roleDef496)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return 

    # $ANTLR end "roleDef"


    # $ANTLR start "primitivetype"
    # src/SavedFSM/BuildFSM.g:223:1: primitivetype : INT ;
    def primitivetype(self, ):

        try:
            try:
                # src/SavedFSM/BuildFSM.g:223:15: ( INT )
                # src/SavedFSM/BuildFSM.g:223:16: INT
                pass 
                self.match(self.input, INT, self.FOLLOW_INT_in_primitivetype502)




            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
        finally:

            pass
        return 

    # $ANTLR end "primitivetype"


    # Delegated rules


 

    FOLLOW_PROTOCOL_in_description52 = frozenset([2])
    FOLLOW_activityDef_in_description54 = frozenset([3, 12, 13, 18, 19, 22, 48, 50, 51])
    FOLLOW_RESV_in_activityDef66 = frozenset([2])
    FOLLOW_ID_in_activityDef79 = frozenset([15])
    FOLLOW_VALUE_in_activityDef91 = frozenset([2])
    FOLLOW_ID_in_activityDef97 = frozenset([3, 5, 6, 25])
    FOLLOW_set_in_activityDef101 = frozenset([3, 25])
    FOLLOW_ID_in_activityDef122 = frozenset([21])
    FOLLOW_ASSERT_in_activityDef130 = frozenset([2])
    FOLLOW_ASSERTION_in_activityDef135 = frozenset([3])
    FOLLOW_SEND_in_activityDef154 = frozenset([2])
    FOLLOW_ID_in_activityDef167 = frozenset([15])
    FOLLOW_VALUE_in_activityDef186 = frozenset([2])
    FOLLOW_ID_in_activityDef192 = frozenset([3, 5, 6, 25])
    FOLLOW_set_in_activityDef197 = frozenset([3, 25])
    FOLLOW_ID_in_activityDef221 = frozenset([21])
    FOLLOW_ASSERT_in_activityDef229 = frozenset([2])
    FOLLOW_ASSERTION_in_activityDef234 = frozenset([3])
    FOLLOW_48_in_activityDef253 = frozenset([2])
    FOLLOW_BRANCH_in_activityDef263 = frozenset([2])
    FOLLOW_activityDef_in_activityDef269 = frozenset([3, 12, 13, 18, 19, 22, 48, 50, 51])
    FOLLOW_PARALLEL_in_activityDef288 = frozenset([2])
    FOLLOW_BRANCH_in_activityDef305 = frozenset([2])
    FOLLOW_activityDef_in_activityDef314 = frozenset([3, 12, 13, 18, 19, 22, 48, 50, 51])
    FOLLOW_50_in_activityDef335 = frozenset([2])
    FOLLOW_BRANCH_in_activityDef344 = frozenset([2])
    FOLLOW_activityDef_in_activityDef347 = frozenset([3, 12, 13, 18, 19, 22, 48, 50, 51])
    FOLLOW_51_in_activityDef371 = frozenset([2])
    FOLLOW_ID_in_activityDef377 = frozenset([16])
    FOLLOW_BRANCH_in_activityDef393 = frozenset([2])
    FOLLOW_activityDef_in_activityDef396 = frozenset([3, 12, 13, 18, 19, 22, 48, 50, 51])
    FOLLOW_RECLABEL_in_activityDef414 = frozenset([2])
    FOLLOW_ID_in_activityDef421 = frozenset([3])
    FOLLOW_GLOBAL_ESCAPE_in_activityDef435 = frozenset([2])
    FOLLOW_57_in_activityDef444 = frozenset([2])
    FOLLOW_activityDef_in_activityDef447 = frozenset([3, 12, 13, 18, 19, 22, 48, 50, 51])
    FOLLOW_58_in_activityDef460 = frozenset([2])
    FOLLOW_roleName_in_activityDef462 = frozenset([3, 12, 13, 18, 19, 22, 48, 50, 51])
    FOLLOW_activityDef_in_activityDef471 = frozenset([3, 12, 13, 18, 19, 22, 48, 50, 51])
    FOLLOW_ID_in_roleName484 = frozenset([1])
    FOLLOW_ID_in_labelName490 = frozenset([1])
    FOLLOW_ID_in_roleDef496 = frozenset([1])
    FOLLOW_INT_in_primitivetype502 = frozenset([1])



def main(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    from antlr3.main import WalkerMain
    main = WalkerMain(BuildFSM)
    main.stdin = stdin
    main.stdout = stdout
    main.stderr = stderr
    main.execute(argv)


if __name__ == '__main__':
    main(sys.argv)
