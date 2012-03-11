# $ANTLR 3.1.3 Mar 18, 2009 10:09:25 src/SavedFSM/Monitor.g 2012-02-23 17:37:18

import sys
from antlr3 import *
from antlr3.compat import set, frozenset

from antlr3.tree import *



# for convenience in actions
HIDDEN = BaseRecognizer.HIDDEN

# token types
RESV=12
ANNOTATION=24
ASSERTION=27
PARALLEL=19
ID=25
EOF=-1
T__60=60
PROTOCOL=20
TYPE=14
T__55=55
ML_COMMENT=31
T__56=56
INTERACTION=4
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
MINUS=8
MULT=9
VALUE=15
ASSERT=21
UNORDERED=17
EMPTY=23
StringLiteral=26
T__33=33
GLOBAL_ESCAPE=22
T__34=34
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




class MonitorParser(Parser):
    grammarFileName = "src/SavedFSM/Monitor.g"
    antlr_version = version_str_to_tuple("3.1.3 Mar 18, 2009 10:09:25")
    antlr_version_str = "3.1.3 Mar 18, 2009 10:09:25"
    tokenNames = tokenNames

    def __init__(self, input, state=None, *args, **kwargs):
        if state is None:
            state = RecognizerSharedState()

        super(MonitorParser, self).__init__(input, state, *args, **kwargs)

        self.dfa3 = self.DFA3(
            self, 3,
            eot = self.DFA3_eot,
            eof = self.DFA3_eof,
            min = self.DFA3_min,
            max = self.DFA3_max,
            accept = self.DFA3_accept,
            special = self.DFA3_special,
            transition = self.DFA3_transition
            )

        self.dfa18 = self.DFA18(
            self, 18,
            eot = self.DFA18_eot,
            eof = self.DFA18_eof,
            min = self.DFA18_min,
            max = self.DFA18_max,
            accept = self.DFA18_accept,
            special = self.DFA18_special,
            transition = self.DFA18_transition
            )

        self.dfa36 = self.DFA36(
            self, 36,
            eot = self.DFA36_eot,
            eof = self.DFA36_eof,
            min = self.DFA36_min,
            max = self.DFA36_max,
            accept = self.DFA36_accept,
            special = self.DFA36_special,
            transition = self.DFA36_transition
            )






        self._adaptor = None
        self.adaptor = CommonTreeAdaptor()
                


        
    def getTreeAdaptor(self):
        return self._adaptor

    def setTreeAdaptor(self, adaptor):
        self._adaptor = adaptor

    adaptor = property(getTreeAdaptor, setTreeAdaptor)


    class description_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.description_return, self).__init__()

            self.tree = None




    # $ANTLR start "description"
    # src/SavedFSM/Monitor.g:39:1: description : ( ( ANNOTATION )* ( importProtocolStatement | importTypeStatement ) )* ( ANNOTATION )* protocolDef -> protocolDef ;
    def description(self, ):

        retval = self.description_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ANNOTATION1 = None
        ANNOTATION4 = None
        importProtocolStatement2 = None

        importTypeStatement3 = None

        protocolDef5 = None


        ANNOTATION1_tree = None
        ANNOTATION4_tree = None
        stream_ANNOTATION = RewriteRuleTokenStream(self._adaptor, "token ANNOTATION")
        stream_importTypeStatement = RewriteRuleSubtreeStream(self._adaptor, "rule importTypeStatement")
        stream_protocolDef = RewriteRuleSubtreeStream(self._adaptor, "rule protocolDef")
        stream_importProtocolStatement = RewriteRuleSubtreeStream(self._adaptor, "rule importProtocolStatement")
        try:
            try:
                # src/SavedFSM/Monitor.g:39:12: ( ( ( ANNOTATION )* ( importProtocolStatement | importTypeStatement ) )* ( ANNOTATION )* protocolDef -> protocolDef )
                # src/SavedFSM/Monitor.g:39:14: ( ( ANNOTATION )* ( importProtocolStatement | importTypeStatement ) )* ( ANNOTATION )* protocolDef
                pass 
                # src/SavedFSM/Monitor.g:39:14: ( ( ANNOTATION )* ( importProtocolStatement | importTypeStatement ) )*
                while True: #loop3
                    alt3 = 2
                    alt3 = self.dfa3.predict(self.input)
                    if alt3 == 1:
                        # src/SavedFSM/Monitor.g:39:16: ( ANNOTATION )* ( importProtocolStatement | importTypeStatement )
                        pass 
                        # src/SavedFSM/Monitor.g:39:16: ( ANNOTATION )*
                        while True: #loop1
                            alt1 = 2
                            LA1_0 = self.input.LA(1)

                            if (LA1_0 == ANNOTATION) :
                                alt1 = 1


                            if alt1 == 1:
                                # src/SavedFSM/Monitor.g:39:18: ANNOTATION
                                pass 
                                ANNOTATION1=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_description234) 
                                if self._state.backtracking == 0:
                                    stream_ANNOTATION.add(ANNOTATION1)


                            else:
                                break #loop1
                        # src/SavedFSM/Monitor.g:39:32: ( importProtocolStatement | importTypeStatement )
                        alt2 = 2
                        LA2_0 = self.input.LA(1)

                        if (LA2_0 == 33) :
                            LA2_1 = self.input.LA(2)

                            if (LA2_1 == 34) :
                                alt2 = 1
                            elif ((ID <= LA2_1 <= StringLiteral)) :
                                alt2 = 2
                            else:
                                if self._state.backtracking > 0:
                                    raise BacktrackingFailed

                                nvae = NoViableAltException("", 2, 1, self.input)

                                raise nvae

                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed

                            nvae = NoViableAltException("", 2, 0, self.input)

                            raise nvae

                        if alt2 == 1:
                            # src/SavedFSM/Monitor.g:39:34: importProtocolStatement
                            pass 
                            self._state.following.append(self.FOLLOW_importProtocolStatement_in_description241)
                            importProtocolStatement2 = self.importProtocolStatement()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                stream_importProtocolStatement.add(importProtocolStatement2.tree)


                        elif alt2 == 2:
                            # src/SavedFSM/Monitor.g:39:60: importTypeStatement
                            pass 
                            self._state.following.append(self.FOLLOW_importTypeStatement_in_description245)
                            importTypeStatement3 = self.importTypeStatement()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                stream_importTypeStatement.add(importTypeStatement3.tree)





                    else:
                        break #loop3
                # src/SavedFSM/Monitor.g:39:85: ( ANNOTATION )*
                while True: #loop4
                    alt4 = 2
                    LA4_0 = self.input.LA(1)

                    if (LA4_0 == ANNOTATION) :
                        alt4 = 1


                    if alt4 == 1:
                        # src/SavedFSM/Monitor.g:39:87: ANNOTATION
                        pass 
                        ANNOTATION4=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_description254) 
                        if self._state.backtracking == 0:
                            stream_ANNOTATION.add(ANNOTATION4)


                    else:
                        break #loop4
                self._state.following.append(self.FOLLOW_protocolDef_in_description259)
                protocolDef5 = self.protocolDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_protocolDef.add(protocolDef5.tree)

                # AST Rewrite
                # elements: protocolDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 39:113: -> protocolDef
                    self._adaptor.addChild(root_0, stream_protocolDef.nextTree())



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "description"

    class importProtocolStatement_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.importProtocolStatement_return, self).__init__()

            self.tree = None




    # $ANTLR start "importProtocolStatement"
    # src/SavedFSM/Monitor.g:41:1: importProtocolStatement : 'import' 'protocol' importProtocolDef ( ',' importProtocolDef )* ';' ;
    def importProtocolStatement(self, ):

        retval = self.importProtocolStatement_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal6 = None
        string_literal7 = None
        char_literal9 = None
        char_literal11 = None
        importProtocolDef8 = None

        importProtocolDef10 = None


        string_literal6_tree = None
        string_literal7_tree = None
        char_literal9_tree = None
        char_literal11_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:41:24: ( 'import' 'protocol' importProtocolDef ( ',' importProtocolDef )* ';' )
                # src/SavedFSM/Monitor.g:41:26: 'import' 'protocol' importProtocolDef ( ',' importProtocolDef )* ';'
                pass 
                root_0 = self._adaptor.nil()

                string_literal6=self.match(self.input, 33, self.FOLLOW_33_in_importProtocolStatement270)
                if self._state.backtracking == 0:

                    string_literal6_tree = self._adaptor.createWithPayload(string_literal6)
                    self._adaptor.addChild(root_0, string_literal6_tree)

                string_literal7=self.match(self.input, 34, self.FOLLOW_34_in_importProtocolStatement272)
                if self._state.backtracking == 0:

                    string_literal7_tree = self._adaptor.createWithPayload(string_literal7)
                    self._adaptor.addChild(root_0, string_literal7_tree)

                self._state.following.append(self.FOLLOW_importProtocolDef_in_importProtocolStatement274)
                importProtocolDef8 = self.importProtocolDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, importProtocolDef8.tree)
                # src/SavedFSM/Monitor.g:41:64: ( ',' importProtocolDef )*
                while True: #loop5
                    alt5 = 2
                    LA5_0 = self.input.LA(1)

                    if (LA5_0 == 35) :
                        alt5 = 1


                    if alt5 == 1:
                        # src/SavedFSM/Monitor.g:41:66: ',' importProtocolDef
                        pass 
                        char_literal9=self.match(self.input, 35, self.FOLLOW_35_in_importProtocolStatement278)
                        self._state.following.append(self.FOLLOW_importProtocolDef_in_importProtocolStatement281)
                        importProtocolDef10 = self.importProtocolDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, importProtocolDef10.tree)


                    else:
                        break #loop5
                char_literal11=self.match(self.input, 36, self.FOLLOW_36_in_importProtocolStatement286)



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "importProtocolStatement"

    class importProtocolDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.importProtocolDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "importProtocolDef"
    # src/SavedFSM/Monitor.g:43:1: importProtocolDef : ID 'from' StringLiteral ;
    def importProtocolDef(self, ):

        retval = self.importProtocolDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ID12 = None
        string_literal13 = None
        StringLiteral14 = None

        ID12_tree = None
        string_literal13_tree = None
        StringLiteral14_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:43:18: ( ID 'from' StringLiteral )
                # src/SavedFSM/Monitor.g:43:20: ID 'from' StringLiteral
                pass 
                root_0 = self._adaptor.nil()

                ID12=self.match(self.input, ID, self.FOLLOW_ID_in_importProtocolDef295)
                if self._state.backtracking == 0:

                    ID12_tree = self._adaptor.createWithPayload(ID12)
                    self._adaptor.addChild(root_0, ID12_tree)

                string_literal13=self.match(self.input, 37, self.FOLLOW_37_in_importProtocolDef297)
                StringLiteral14=self.match(self.input, StringLiteral, self.FOLLOW_StringLiteral_in_importProtocolDef300)
                if self._state.backtracking == 0:

                    StringLiteral14_tree = self._adaptor.createWithPayload(StringLiteral14)
                    self._adaptor.addChild(root_0, StringLiteral14_tree)




                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "importProtocolDef"

    class importTypeStatement_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.importTypeStatement_return, self).__init__()

            self.tree = None




    # $ANTLR start "importTypeStatement"
    # src/SavedFSM/Monitor.g:45:1: importTypeStatement : 'import' ( simpleName )? importTypeDef ( ',' importTypeDef )* ( 'from' StringLiteral )? ';' ;
    def importTypeStatement(self, ):

        retval = self.importTypeStatement_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal15 = None
        char_literal18 = None
        string_literal20 = None
        StringLiteral21 = None
        char_literal22 = None
        simpleName16 = None

        importTypeDef17 = None

        importTypeDef19 = None


        string_literal15_tree = None
        char_literal18_tree = None
        string_literal20_tree = None
        StringLiteral21_tree = None
        char_literal22_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:45:20: ( 'import' ( simpleName )? importTypeDef ( ',' importTypeDef )* ( 'from' StringLiteral )? ';' )
                # src/SavedFSM/Monitor.g:45:22: 'import' ( simpleName )? importTypeDef ( ',' importTypeDef )* ( 'from' StringLiteral )? ';'
                pass 
                root_0 = self._adaptor.nil()

                string_literal15=self.match(self.input, 33, self.FOLLOW_33_in_importTypeStatement313)
                if self._state.backtracking == 0:

                    string_literal15_tree = self._adaptor.createWithPayload(string_literal15)
                    self._adaptor.addChild(root_0, string_literal15_tree)

                # src/SavedFSM/Monitor.g:45:31: ( simpleName )?
                alt6 = 2
                LA6_0 = self.input.LA(1)

                if (LA6_0 == ID) :
                    LA6_1 = self.input.LA(2)

                    if ((ID <= LA6_1 <= StringLiteral)) :
                        alt6 = 1
                if alt6 == 1:
                    # src/SavedFSM/Monitor.g:45:33: simpleName
                    pass 
                    self._state.following.append(self.FOLLOW_simpleName_in_importTypeStatement317)
                    simpleName16 = self.simpleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, simpleName16.tree)



                self._state.following.append(self.FOLLOW_importTypeDef_in_importTypeStatement322)
                importTypeDef17 = self.importTypeDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, importTypeDef17.tree)
                # src/SavedFSM/Monitor.g:45:61: ( ',' importTypeDef )*
                while True: #loop7
                    alt7 = 2
                    LA7_0 = self.input.LA(1)

                    if (LA7_0 == 35) :
                        alt7 = 1


                    if alt7 == 1:
                        # src/SavedFSM/Monitor.g:45:63: ',' importTypeDef
                        pass 
                        char_literal18=self.match(self.input, 35, self.FOLLOW_35_in_importTypeStatement326)
                        self._state.following.append(self.FOLLOW_importTypeDef_in_importTypeStatement329)
                        importTypeDef19 = self.importTypeDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, importTypeDef19.tree)


                    else:
                        break #loop7
                # src/SavedFSM/Monitor.g:45:85: ( 'from' StringLiteral )?
                alt8 = 2
                LA8_0 = self.input.LA(1)

                if (LA8_0 == 37) :
                    alt8 = 1
                if alt8 == 1:
                    # src/SavedFSM/Monitor.g:45:87: 'from' StringLiteral
                    pass 
                    string_literal20=self.match(self.input, 37, self.FOLLOW_37_in_importTypeStatement336)
                    StringLiteral21=self.match(self.input, StringLiteral, self.FOLLOW_StringLiteral_in_importTypeStatement339)
                    if self._state.backtracking == 0:

                        StringLiteral21_tree = self._adaptor.createWithPayload(StringLiteral21)
                        self._adaptor.addChild(root_0, StringLiteral21_tree)




                char_literal22=self.match(self.input, 36, self.FOLLOW_36_in_importTypeStatement344)



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "importTypeStatement"

    class importTypeDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.importTypeDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "importTypeDef"
    # src/SavedFSM/Monitor.g:47:1: importTypeDef : ( dataTypeDef 'as' )? ID ;
    def importTypeDef(self, ):

        retval = self.importTypeDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal24 = None
        ID25 = None
        dataTypeDef23 = None


        string_literal24_tree = None
        ID25_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:47:14: ( ( dataTypeDef 'as' )? ID )
                # src/SavedFSM/Monitor.g:47:16: ( dataTypeDef 'as' )? ID
                pass 
                root_0 = self._adaptor.nil()

                # src/SavedFSM/Monitor.g:47:16: ( dataTypeDef 'as' )?
                alt9 = 2
                LA9_0 = self.input.LA(1)

                if (LA9_0 == StringLiteral) :
                    alt9 = 1
                if alt9 == 1:
                    # src/SavedFSM/Monitor.g:47:18: dataTypeDef 'as'
                    pass 
                    self._state.following.append(self.FOLLOW_dataTypeDef_in_importTypeDef355)
                    dataTypeDef23 = self.dataTypeDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, dataTypeDef23.tree)
                    string_literal24=self.match(self.input, 38, self.FOLLOW_38_in_importTypeDef357)



                ID25=self.match(self.input, ID, self.FOLLOW_ID_in_importTypeDef363)
                if self._state.backtracking == 0:

                    ID25_tree = self._adaptor.createWithPayload(ID25)
                    self._adaptor.addChild(root_0, ID25_tree)




                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "importTypeDef"

    class dataTypeDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.dataTypeDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "dataTypeDef"
    # src/SavedFSM/Monitor.g:49:1: dataTypeDef : StringLiteral ;
    def dataTypeDef(self, ):

        retval = self.dataTypeDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        StringLiteral26 = None

        StringLiteral26_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:49:12: ( StringLiteral )
                # src/SavedFSM/Monitor.g:49:14: StringLiteral
                pass 
                root_0 = self._adaptor.nil()

                StringLiteral26=self.match(self.input, StringLiteral, self.FOLLOW_StringLiteral_in_dataTypeDef371)
                if self._state.backtracking == 0:

                    StringLiteral26_tree = self._adaptor.createWithPayload(StringLiteral26)
                    self._adaptor.addChild(root_0, StringLiteral26_tree)




                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "dataTypeDef"

    class simpleName_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.simpleName_return, self).__init__()

            self.tree = None




    # $ANTLR start "simpleName"
    # src/SavedFSM/Monitor.g:51:1: simpleName : ID ;
    def simpleName(self, ):

        retval = self.simpleName_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ID27 = None

        ID27_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:51:11: ( ID )
                # src/SavedFSM/Monitor.g:51:13: ID
                pass 
                root_0 = self._adaptor.nil()

                ID27=self.match(self.input, ID, self.FOLLOW_ID_in_simpleName379)
                if self._state.backtracking == 0:

                    ID27_tree = self._adaptor.createWithPayload(ID27)
                    self._adaptor.addChild(root_0, ID27_tree)




                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "simpleName"

    class protocolDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.protocolDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "protocolDef"
    # src/SavedFSM/Monitor.g:53:1: protocolDef : 'protocol' protocolName ( 'at' roleName )? ( parameterDefs )? '{' protocolBlockDef ( ( ANNOTATION )* protocolDef )* '}' -> ^( PROTOCOL ( protocolBlockDef )+ ) ;
    def protocolDef(self, ):

        retval = self.protocolDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal28 = None
        string_literal30 = None
        char_literal33 = None
        ANNOTATION35 = None
        char_literal37 = None
        protocolName29 = None

        roleName31 = None

        parameterDefs32 = None

        protocolBlockDef34 = None

        protocolDef36 = None


        string_literal28_tree = None
        string_literal30_tree = None
        char_literal33_tree = None
        ANNOTATION35_tree = None
        char_literal37_tree = None
        stream_41 = RewriteRuleTokenStream(self._adaptor, "token 41")
        stream_40 = RewriteRuleTokenStream(self._adaptor, "token 40")
        stream_34 = RewriteRuleTokenStream(self._adaptor, "token 34")
        stream_ANNOTATION = RewriteRuleTokenStream(self._adaptor, "token ANNOTATION")
        stream_39 = RewriteRuleTokenStream(self._adaptor, "token 39")
        stream_parameterDefs = RewriteRuleSubtreeStream(self._adaptor, "rule parameterDefs")
        stream_protocolDef = RewriteRuleSubtreeStream(self._adaptor, "rule protocolDef")
        stream_protocolName = RewriteRuleSubtreeStream(self._adaptor, "rule protocolName")
        stream_protocolBlockDef = RewriteRuleSubtreeStream(self._adaptor, "rule protocolBlockDef")
        stream_roleName = RewriteRuleSubtreeStream(self._adaptor, "rule roleName")
        try:
            try:
                # src/SavedFSM/Monitor.g:53:12: ( 'protocol' protocolName ( 'at' roleName )? ( parameterDefs )? '{' protocolBlockDef ( ( ANNOTATION )* protocolDef )* '}' -> ^( PROTOCOL ( protocolBlockDef )+ ) )
                # src/SavedFSM/Monitor.g:53:14: 'protocol' protocolName ( 'at' roleName )? ( parameterDefs )? '{' protocolBlockDef ( ( ANNOTATION )* protocolDef )* '}'
                pass 
                string_literal28=self.match(self.input, 34, self.FOLLOW_34_in_protocolDef387) 
                if self._state.backtracking == 0:
                    stream_34.add(string_literal28)
                self._state.following.append(self.FOLLOW_protocolName_in_protocolDef389)
                protocolName29 = self.protocolName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_protocolName.add(protocolName29.tree)
                # src/SavedFSM/Monitor.g:53:38: ( 'at' roleName )?
                alt10 = 2
                LA10_0 = self.input.LA(1)

                if (LA10_0 == 39) :
                    alt10 = 1
                if alt10 == 1:
                    # src/SavedFSM/Monitor.g:53:40: 'at' roleName
                    pass 
                    string_literal30=self.match(self.input, 39, self.FOLLOW_39_in_protocolDef393) 
                    if self._state.backtracking == 0:
                        stream_39.add(string_literal30)
                    self._state.following.append(self.FOLLOW_roleName_in_protocolDef395)
                    roleName31 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_roleName.add(roleName31.tree)



                # src/SavedFSM/Monitor.g:53:57: ( parameterDefs )?
                alt11 = 2
                LA11_0 = self.input.LA(1)

                if (LA11_0 == 42) :
                    alt11 = 1
                if alt11 == 1:
                    # src/SavedFSM/Monitor.g:53:59: parameterDefs
                    pass 
                    self._state.following.append(self.FOLLOW_parameterDefs_in_protocolDef402)
                    parameterDefs32 = self.parameterDefs()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_parameterDefs.add(parameterDefs32.tree)



                char_literal33=self.match(self.input, 40, self.FOLLOW_40_in_protocolDef407) 
                if self._state.backtracking == 0:
                    stream_40.add(char_literal33)
                self._state.following.append(self.FOLLOW_protocolBlockDef_in_protocolDef409)
                protocolBlockDef34 = self.protocolBlockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_protocolBlockDef.add(protocolBlockDef34.tree)
                # src/SavedFSM/Monitor.g:53:97: ( ( ANNOTATION )* protocolDef )*
                while True: #loop13
                    alt13 = 2
                    LA13_0 = self.input.LA(1)

                    if (LA13_0 == ANNOTATION or LA13_0 == 34) :
                        alt13 = 1


                    if alt13 == 1:
                        # src/SavedFSM/Monitor.g:53:99: ( ANNOTATION )* protocolDef
                        pass 
                        # src/SavedFSM/Monitor.g:53:99: ( ANNOTATION )*
                        while True: #loop12
                            alt12 = 2
                            LA12_0 = self.input.LA(1)

                            if (LA12_0 == ANNOTATION) :
                                alt12 = 1


                            if alt12 == 1:
                                # src/SavedFSM/Monitor.g:53:101: ANNOTATION
                                pass 
                                ANNOTATION35=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_protocolDef415) 
                                if self._state.backtracking == 0:
                                    stream_ANNOTATION.add(ANNOTATION35)


                            else:
                                break #loop12
                        self._state.following.append(self.FOLLOW_protocolDef_in_protocolDef420)
                        protocolDef36 = self.protocolDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_protocolDef.add(protocolDef36.tree)


                    else:
                        break #loop13
                char_literal37=self.match(self.input, 41, self.FOLLOW_41_in_protocolDef425) 
                if self._state.backtracking == 0:
                    stream_41.add(char_literal37)

                # AST Rewrite
                # elements: protocolBlockDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 54:7: -> ^( PROTOCOL ( protocolBlockDef )+ )
                    # src/SavedFSM/Monitor.g:54:10: ^( PROTOCOL ( protocolBlockDef )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(PROTOCOL, "PROTOCOL"), root_1)

                    # src/SavedFSM/Monitor.g:54:21: ( protocolBlockDef )+
                    if not (stream_protocolBlockDef.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_protocolBlockDef.hasNext():
                        self._adaptor.addChild(root_1, stream_protocolBlockDef.nextTree())


                    stream_protocolBlockDef.reset()

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "protocolDef"

    class protocolName_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.protocolName_return, self).__init__()

            self.tree = None




    # $ANTLR start "protocolName"
    # src/SavedFSM/Monitor.g:56:1: protocolName : ID ;
    def protocolName(self, ):

        retval = self.protocolName_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ID38 = None

        ID38_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:56:13: ( ID )
                # src/SavedFSM/Monitor.g:56:15: ID
                pass 
                root_0 = self._adaptor.nil()

                ID38=self.match(self.input, ID, self.FOLLOW_ID_in_protocolName447)
                if self._state.backtracking == 0:

                    ID38_tree = self._adaptor.createWithPayload(ID38)
                    self._adaptor.addChild(root_0, ID38_tree)




                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "protocolName"

    class parameterDefs_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.parameterDefs_return, self).__init__()

            self.tree = None




    # $ANTLR start "parameterDefs"
    # src/SavedFSM/Monitor.g:58:1: parameterDefs : '(' parameterDef ( ',' parameterDef )* ')' ;
    def parameterDefs(self, ):

        retval = self.parameterDefs_return()
        retval.start = self.input.LT(1)

        root_0 = None

        char_literal39 = None
        char_literal41 = None
        char_literal43 = None
        parameterDef40 = None

        parameterDef42 = None


        char_literal39_tree = None
        char_literal41_tree = None
        char_literal43_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:58:14: ( '(' parameterDef ( ',' parameterDef )* ')' )
                # src/SavedFSM/Monitor.g:58:16: '(' parameterDef ( ',' parameterDef )* ')'
                pass 
                root_0 = self._adaptor.nil()

                char_literal39=self.match(self.input, 42, self.FOLLOW_42_in_parameterDefs455)
                self._state.following.append(self.FOLLOW_parameterDef_in_parameterDefs458)
                parameterDef40 = self.parameterDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, parameterDef40.tree)
                # src/SavedFSM/Monitor.g:58:34: ( ',' parameterDef )*
                while True: #loop14
                    alt14 = 2
                    LA14_0 = self.input.LA(1)

                    if (LA14_0 == 35) :
                        alt14 = 1


                    if alt14 == 1:
                        # src/SavedFSM/Monitor.g:58:36: ',' parameterDef
                        pass 
                        char_literal41=self.match(self.input, 35, self.FOLLOW_35_in_parameterDefs462)
                        self._state.following.append(self.FOLLOW_parameterDef_in_parameterDefs465)
                        parameterDef42 = self.parameterDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, parameterDef42.tree)


                    else:
                        break #loop14
                char_literal43=self.match(self.input, 43, self.FOLLOW_43_in_parameterDefs470)



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "parameterDefs"

    class parameterDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.parameterDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "parameterDef"
    # src/SavedFSM/Monitor.g:60:1: parameterDef : ( typeReferenceDef | 'role' ) simpleName ;
    def parameterDef(self, ):

        retval = self.parameterDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal45 = None
        typeReferenceDef44 = None

        simpleName46 = None


        string_literal45_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:60:13: ( ( typeReferenceDef | 'role' ) simpleName )
                # src/SavedFSM/Monitor.g:60:15: ( typeReferenceDef | 'role' ) simpleName
                pass 
                root_0 = self._adaptor.nil()

                # src/SavedFSM/Monitor.g:60:15: ( typeReferenceDef | 'role' )
                alt15 = 2
                LA15_0 = self.input.LA(1)

                if (LA15_0 == ID) :
                    alt15 = 1
                elif (LA15_0 == 44) :
                    alt15 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed

                    nvae = NoViableAltException("", 15, 0, self.input)

                    raise nvae

                if alt15 == 1:
                    # src/SavedFSM/Monitor.g:60:17: typeReferenceDef
                    pass 
                    self._state.following.append(self.FOLLOW_typeReferenceDef_in_parameterDef481)
                    typeReferenceDef44 = self.typeReferenceDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, typeReferenceDef44.tree)


                elif alt15 == 2:
                    # src/SavedFSM/Monitor.g:60:36: 'role'
                    pass 
                    string_literal45=self.match(self.input, 44, self.FOLLOW_44_in_parameterDef485)
                    if self._state.backtracking == 0:

                        string_literal45_tree = self._adaptor.createWithPayload(string_literal45)
                        self._adaptor.addChild(root_0, string_literal45_tree)




                self._state.following.append(self.FOLLOW_simpleName_in_parameterDef489)
                simpleName46 = self.simpleName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, simpleName46.tree)



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "parameterDef"

    class protocolBlockDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.protocolBlockDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "protocolBlockDef"
    # src/SavedFSM/Monitor.g:62:1: protocolBlockDef : activityListDef -> activityListDef ;
    def protocolBlockDef(self, ):

        retval = self.protocolBlockDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        activityListDef47 = None


        stream_activityListDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityListDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:62:17: ( activityListDef -> activityListDef )
                # src/SavedFSM/Monitor.g:62:19: activityListDef
                pass 
                self._state.following.append(self.FOLLOW_activityListDef_in_protocolBlockDef497)
                activityListDef47 = self.activityListDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_activityListDef.add(activityListDef47.tree)

                # AST Rewrite
                # elements: activityListDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 62:35: -> activityListDef
                    self._adaptor.addChild(root_0, stream_activityListDef.nextTree())



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "protocolBlockDef"

    class blockDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.blockDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "blockDef"
    # src/SavedFSM/Monitor.g:64:1: blockDef : '{' activityListDef '}' -> ^( BRANCH activityListDef ) ;
    def blockDef(self, ):

        retval = self.blockDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        char_literal48 = None
        char_literal50 = None
        activityListDef49 = None


        char_literal48_tree = None
        char_literal50_tree = None
        stream_41 = RewriteRuleTokenStream(self._adaptor, "token 41")
        stream_40 = RewriteRuleTokenStream(self._adaptor, "token 40")
        stream_activityListDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityListDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:64:9: ( '{' activityListDef '}' -> ^( BRANCH activityListDef ) )
                # src/SavedFSM/Monitor.g:64:11: '{' activityListDef '}'
                pass 
                char_literal48=self.match(self.input, 40, self.FOLLOW_40_in_blockDef508) 
                if self._state.backtracking == 0:
                    stream_40.add(char_literal48)
                self._state.following.append(self.FOLLOW_activityListDef_in_blockDef510)
                activityListDef49 = self.activityListDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_activityListDef.add(activityListDef49.tree)
                char_literal50=self.match(self.input, 41, self.FOLLOW_41_in_blockDef512) 
                if self._state.backtracking == 0:
                    stream_41.add(char_literal50)

                # AST Rewrite
                # elements: activityListDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 64:35: -> ^( BRANCH activityListDef )
                    # src/SavedFSM/Monitor.g:64:38: ^( BRANCH activityListDef )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(BRANCH, "BRANCH"), root_1)

                    self._adaptor.addChild(root_1, stream_activityListDef.nextTree())

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "blockDef"

    class assertDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.assertDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "assertDef"
    # src/SavedFSM/Monitor.g:66:1: assertDef : ( ASSERTION )? -> ^( ASSERT ( ASSERTION )? ) ;
    def assertDef(self, ):

        retval = self.assertDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ASSERTION51 = None

        ASSERTION51_tree = None
        stream_ASSERTION = RewriteRuleTokenStream(self._adaptor, "token ASSERTION")

        try:
            try:
                # src/SavedFSM/Monitor.g:66:11: ( ( ASSERTION )? -> ^( ASSERT ( ASSERTION )? ) )
                # src/SavedFSM/Monitor.g:66:13: ( ASSERTION )?
                pass 
                # src/SavedFSM/Monitor.g:66:13: ( ASSERTION )?
                alt16 = 2
                LA16_0 = self.input.LA(1)

                if (LA16_0 == ASSERTION) :
                    alt16 = 1
                if alt16 == 1:
                    # src/SavedFSM/Monitor.g:66:14: ASSERTION
                    pass 
                    ASSERTION51=self.match(self.input, ASSERTION, self.FOLLOW_ASSERTION_in_assertDef534) 
                    if self._state.backtracking == 0:
                        stream_ASSERTION.add(ASSERTION51)




                # AST Rewrite
                # elements: ASSERTION
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 66:26: -> ^( ASSERT ( ASSERTION )? )
                    # src/SavedFSM/Monitor.g:66:29: ^( ASSERT ( ASSERTION )? )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(ASSERT, "ASSERT"), root_1)

                    # src/SavedFSM/Monitor.g:66:38: ( ASSERTION )?
                    if stream_ASSERTION.hasNext():
                        self._adaptor.addChild(root_1, stream_ASSERTION.nextNode())


                    stream_ASSERTION.reset();

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "assertDef"

    class activityListDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.activityListDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "activityListDef"
    # src/SavedFSM/Monitor.g:68:1: activityListDef : ( ( ANNOTATION )* activityDef )* -> ( activityDef )+ ;
    def activityListDef(self, ):

        retval = self.activityListDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ANNOTATION52 = None
        activityDef53 = None


        ANNOTATION52_tree = None
        stream_ANNOTATION = RewriteRuleTokenStream(self._adaptor, "token ANNOTATION")
        stream_activityDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:68:16: ( ( ( ANNOTATION )* activityDef )* -> ( activityDef )+ )
                # src/SavedFSM/Monitor.g:68:18: ( ( ANNOTATION )* activityDef )*
                pass 
                # src/SavedFSM/Monitor.g:68:18: ( ( ANNOTATION )* activityDef )*
                while True: #loop18
                    alt18 = 2
                    alt18 = self.dfa18.predict(self.input)
                    if alt18 == 1:
                        # src/SavedFSM/Monitor.g:68:20: ( ANNOTATION )* activityDef
                        pass 
                        # src/SavedFSM/Monitor.g:68:20: ( ANNOTATION )*
                        while True: #loop17
                            alt17 = 2
                            LA17_0 = self.input.LA(1)

                            if (LA17_0 == ANNOTATION) :
                                alt17 = 1


                            if alt17 == 1:
                                # src/SavedFSM/Monitor.g:68:22: ANNOTATION
                                pass 
                                ANNOTATION52=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_activityListDef556) 
                                if self._state.backtracking == 0:
                                    stream_ANNOTATION.add(ANNOTATION52)


                            else:
                                break #loop17
                        self._state.following.append(self.FOLLOW_activityDef_in_activityListDef561)
                        activityDef53 = self.activityDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_activityDef.add(activityDef53.tree)


                    else:
                        break #loop18

                # AST Rewrite
                # elements: activityDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 68:51: -> ( activityDef )+
                    # src/SavedFSM/Monitor.g:68:54: ( activityDef )+
                    if not (stream_activityDef.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_activityDef.hasNext():
                        self._adaptor.addChild(root_0, stream_activityDef.nextTree())


                    stream_activityDef.reset()



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "activityListDef"

    class primitivetype_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.primitivetype_return, self).__init__()

            self.tree = None




    # $ANTLR start "primitivetype"
    # src/SavedFSM/Monitor.g:70:1: primitivetype : ( INT -> INT | STRING -> STRING ) ;
    def primitivetype(self, ):

        retval = self.primitivetype_return()
        retval.start = self.input.LT(1)

        root_0 = None

        INT54 = None
        STRING55 = None

        INT54_tree = None
        STRING55_tree = None
        stream_INT = RewriteRuleTokenStream(self._adaptor, "token INT")
        stream_STRING = RewriteRuleTokenStream(self._adaptor, "token STRING")

        try:
            try:
                # src/SavedFSM/Monitor.g:70:15: ( ( INT -> INT | STRING -> STRING ) )
                # src/SavedFSM/Monitor.g:70:16: ( INT -> INT | STRING -> STRING )
                pass 
                # src/SavedFSM/Monitor.g:70:16: ( INT -> INT | STRING -> STRING )
                alt19 = 2
                LA19_0 = self.input.LA(1)

                if (LA19_0 == INT) :
                    alt19 = 1
                elif (LA19_0 == STRING) :
                    alt19 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed

                    nvae = NoViableAltException("", 19, 0, self.input)

                    raise nvae

                if alt19 == 1:
                    # src/SavedFSM/Monitor.g:70:17: INT
                    pass 
                    INT54=self.match(self.input, INT, self.FOLLOW_INT_in_primitivetype577) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT54)

                    # AST Rewrite
                    # elements: INT
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:

                        retval.tree = root_0

                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 70:21: -> INT
                        self._adaptor.addChild(root_0, stream_INT.nextNode())



                        retval.tree = root_0


                elif alt19 == 2:
                    # src/SavedFSM/Monitor.g:70:28: STRING
                    pass 
                    STRING55=self.match(self.input, STRING, self.FOLLOW_STRING_in_primitivetype583) 
                    if self._state.backtracking == 0:
                        stream_STRING.add(STRING55)

                    # AST Rewrite
                    # elements: STRING
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:

                        retval.tree = root_0

                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 70:34: -> STRING
                        self._adaptor.addChild(root_0, stream_STRING.nextNode())



                        retval.tree = root_0






                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "primitivetype"

    class activityDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.activityDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "activityDef"
    # src/SavedFSM/Monitor.g:72:1: activityDef : ( ( introducesDef | interactionDef | inlineDef | runDef | recursionDef | endDef | RECLABEL ) ';' | choiceDef | directedChoiceDef | parallelDef | repeatDef | unorderedDef | recBlockDef | globalEscapeDef );
    def activityDef(self, ):

        retval = self.activityDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        RECLABEL62 = None
        char_literal63 = None
        introducesDef56 = None

        interactionDef57 = None

        inlineDef58 = None

        runDef59 = None

        recursionDef60 = None

        endDef61 = None

        choiceDef64 = None

        directedChoiceDef65 = None

        parallelDef66 = None

        repeatDef67 = None

        unorderedDef68 = None

        recBlockDef69 = None

        globalEscapeDef70 = None


        RECLABEL62_tree = None
        char_literal63_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:72:12: ( ( introducesDef | interactionDef | inlineDef | runDef | recursionDef | endDef | RECLABEL ) ';' | choiceDef | directedChoiceDef | parallelDef | repeatDef | unorderedDef | recBlockDef | globalEscapeDef )
                alt21 = 8
                LA21 = self.input.LA(1)
                if LA21 == RECLABEL or LA21 == ID or LA21 == 42 or LA21 == 52 or LA21 == 53 or LA21 == 54:
                    alt21 = 1
                elif LA21 == 48:
                    alt21 = 2
                elif LA21 == 37 or LA21 == 40 or LA21 == 47:
                    alt21 = 3
                elif LA21 == 55:
                    alt21 = 4
                elif LA21 == 50:
                    alt21 = 5
                elif LA21 == 60:
                    alt21 = 6
                elif LA21 == 51:
                    alt21 = 7
                elif LA21 == 57:
                    alt21 = 8
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed

                    nvae = NoViableAltException("", 21, 0, self.input)

                    raise nvae

                if alt21 == 1:
                    # src/SavedFSM/Monitor.g:72:14: ( introducesDef | interactionDef | inlineDef | runDef | recursionDef | endDef | RECLABEL ) ';'
                    pass 
                    root_0 = self._adaptor.nil()

                    # src/SavedFSM/Monitor.g:72:14: ( introducesDef | interactionDef | inlineDef | runDef | recursionDef | endDef | RECLABEL )
                    alt20 = 7
                    LA20 = self.input.LA(1)
                    if LA20 == ID:
                        LA20 = self.input.LA(2)
                        if LA20 == 36:
                            alt20 = 5
                        elif LA20 == 37 or LA20 == 42 or LA20 == 47:
                            alt20 = 2
                        elif LA20 == 45:
                            alt20 = 1
                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed

                            nvae = NoViableAltException("", 20, 1, self.input)

                            raise nvae

                    elif LA20 == 42:
                        alt20 = 2
                    elif LA20 == 54:
                        alt20 = 3
                    elif LA20 == 53:
                        alt20 = 4
                    elif LA20 == 52:
                        alt20 = 6
                    elif LA20 == RECLABEL:
                        alt20 = 7
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed

                        nvae = NoViableAltException("", 20, 0, self.input)

                        raise nvae

                    if alt20 == 1:
                        # src/SavedFSM/Monitor.g:72:16: introducesDef
                        pass 
                        self._state.following.append(self.FOLLOW_introducesDef_in_activityDef596)
                        introducesDef56 = self.introducesDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, introducesDef56.tree)


                    elif alt20 == 2:
                        # src/SavedFSM/Monitor.g:72:32: interactionDef
                        pass 
                        self._state.following.append(self.FOLLOW_interactionDef_in_activityDef600)
                        interactionDef57 = self.interactionDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, interactionDef57.tree)


                    elif alt20 == 3:
                        # src/SavedFSM/Monitor.g:72:49: inlineDef
                        pass 
                        self._state.following.append(self.FOLLOW_inlineDef_in_activityDef604)
                        inlineDef58 = self.inlineDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, inlineDef58.tree)


                    elif alt20 == 4:
                        # src/SavedFSM/Monitor.g:72:61: runDef
                        pass 
                        self._state.following.append(self.FOLLOW_runDef_in_activityDef608)
                        runDef59 = self.runDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, runDef59.tree)


                    elif alt20 == 5:
                        # src/SavedFSM/Monitor.g:72:70: recursionDef
                        pass 
                        self._state.following.append(self.FOLLOW_recursionDef_in_activityDef612)
                        recursionDef60 = self.recursionDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, recursionDef60.tree)


                    elif alt20 == 6:
                        # src/SavedFSM/Monitor.g:72:85: endDef
                        pass 
                        self._state.following.append(self.FOLLOW_endDef_in_activityDef616)
                        endDef61 = self.endDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, endDef61.tree)


                    elif alt20 == 7:
                        # src/SavedFSM/Monitor.g:72:94: RECLABEL
                        pass 
                        RECLABEL62=self.match(self.input, RECLABEL, self.FOLLOW_RECLABEL_in_activityDef620)
                        if self._state.backtracking == 0:

                            RECLABEL62_tree = self._adaptor.createWithPayload(RECLABEL62)
                            self._adaptor.addChild(root_0, RECLABEL62_tree)




                    char_literal63=self.match(self.input, 36, self.FOLLOW_36_in_activityDef624)


                elif alt21 == 2:
                    # src/SavedFSM/Monitor.g:73:4: choiceDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_choiceDef_in_activityDef633)
                    choiceDef64 = self.choiceDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, choiceDef64.tree)


                elif alt21 == 3:
                    # src/SavedFSM/Monitor.g:73:16: directedChoiceDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_directedChoiceDef_in_activityDef637)
                    directedChoiceDef65 = self.directedChoiceDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, directedChoiceDef65.tree)


                elif alt21 == 4:
                    # src/SavedFSM/Monitor.g:73:36: parallelDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_parallelDef_in_activityDef641)
                    parallelDef66 = self.parallelDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, parallelDef66.tree)


                elif alt21 == 5:
                    # src/SavedFSM/Monitor.g:73:50: repeatDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_repeatDef_in_activityDef645)
                    repeatDef67 = self.repeatDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, repeatDef67.tree)


                elif alt21 == 6:
                    # src/SavedFSM/Monitor.g:73:62: unorderedDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_unorderedDef_in_activityDef649)
                    unorderedDef68 = self.unorderedDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, unorderedDef68.tree)


                elif alt21 == 7:
                    # src/SavedFSM/Monitor.g:74:4: recBlockDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_recBlockDef_in_activityDef656)
                    recBlockDef69 = self.recBlockDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, recBlockDef69.tree)


                elif alt21 == 8:
                    # src/SavedFSM/Monitor.g:74:18: globalEscapeDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_globalEscapeDef_in_activityDef660)
                    globalEscapeDef70 = self.globalEscapeDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, globalEscapeDef70.tree)


                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "activityDef"

    class introducesDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.introducesDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "introducesDef"
    # src/SavedFSM/Monitor.g:76:1: introducesDef : roleDef 'introduces' roleDef ( ',' roleDef )* ;
    def introducesDef(self, ):

        retval = self.introducesDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal72 = None
        char_literal74 = None
        roleDef71 = None

        roleDef73 = None

        roleDef75 = None


        string_literal72_tree = None
        char_literal74_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:76:14: ( roleDef 'introduces' roleDef ( ',' roleDef )* )
                # src/SavedFSM/Monitor.g:76:16: roleDef 'introduces' roleDef ( ',' roleDef )*
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_roleDef_in_introducesDef668)
                roleDef71 = self.roleDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, roleDef71.tree)
                string_literal72=self.match(self.input, 45, self.FOLLOW_45_in_introducesDef670)
                if self._state.backtracking == 0:

                    string_literal72_tree = self._adaptor.createWithPayload(string_literal72)
                    self._adaptor.addChild(root_0, string_literal72_tree)

                self._state.following.append(self.FOLLOW_roleDef_in_introducesDef672)
                roleDef73 = self.roleDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, roleDef73.tree)
                # src/SavedFSM/Monitor.g:76:45: ( ',' roleDef )*
                while True: #loop22
                    alt22 = 2
                    LA22_0 = self.input.LA(1)

                    if (LA22_0 == 35) :
                        alt22 = 1


                    if alt22 == 1:
                        # src/SavedFSM/Monitor.g:76:47: ',' roleDef
                        pass 
                        char_literal74=self.match(self.input, 35, self.FOLLOW_35_in_introducesDef676)
                        if self._state.backtracking == 0:

                            char_literal74_tree = self._adaptor.createWithPayload(char_literal74)
                            self._adaptor.addChild(root_0, char_literal74_tree)

                        self._state.following.append(self.FOLLOW_roleDef_in_introducesDef678)
                        roleDef75 = self.roleDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, roleDef75.tree)


                    else:
                        break #loop22



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "introducesDef"

    class roleDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.roleDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "roleDef"
    # src/SavedFSM/Monitor.g:78:1: roleDef : ID -> ID ;
    def roleDef(self, ):

        retval = self.roleDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ID76 = None

        ID76_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")

        try:
            try:
                # src/SavedFSM/Monitor.g:78:8: ( ID -> ID )
                # src/SavedFSM/Monitor.g:78:10: ID
                pass 
                ID76=self.match(self.input, ID, self.FOLLOW_ID_in_roleDef689) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID76)

                # AST Rewrite
                # elements: ID
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 78:13: -> ID
                    self._adaptor.addChild(root_0, stream_ID.nextNode())



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "roleDef"

    class roleName_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.roleName_return, self).__init__()

            self.tree = None




    # $ANTLR start "roleName"
    # src/SavedFSM/Monitor.g:80:1: roleName : ID -> ID ;
    def roleName(self, ):

        retval = self.roleName_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ID77 = None

        ID77_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")

        try:
            try:
                # src/SavedFSM/Monitor.g:80:9: ( ID -> ID )
                # src/SavedFSM/Monitor.g:80:11: ID
                pass 
                ID77=self.match(self.input, ID, self.FOLLOW_ID_in_roleName700) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID77)

                # AST Rewrite
                # elements: ID
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 80:14: -> ID
                    self._adaptor.addChild(root_0, stream_ID.nextNode())



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "roleName"

    class typeReferenceDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.typeReferenceDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "typeReferenceDef"
    # src/SavedFSM/Monitor.g:82:1: typeReferenceDef : ID -> ID ;
    def typeReferenceDef(self, ):

        retval = self.typeReferenceDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ID78 = None

        ID78_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")

        try:
            try:
                # src/SavedFSM/Monitor.g:82:17: ( ID -> ID )
                # src/SavedFSM/Monitor.g:82:19: ID
                pass 
                ID78=self.match(self.input, ID, self.FOLLOW_ID_in_typeReferenceDef711) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID78)

                # AST Rewrite
                # elements: ID
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 82:22: -> ID
                    self._adaptor.addChild(root_0, stream_ID.nextNode())



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "typeReferenceDef"

    class interactionSignatureDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.interactionSignatureDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "interactionSignatureDef"
    # src/SavedFSM/Monitor.g:83:1: interactionSignatureDef : ( ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) ) | ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) ) ) ;
    def interactionSignatureDef(self, ):

        retval = self.interactionSignatureDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        char_literal80 = None
        char_literal82 = None
        char_literal84 = None
        char_literal85 = None
        char_literal87 = None
        char_literal89 = None
        typeReferenceDef79 = None

        valueDecl81 = None

        valueDecl83 = None

        valueDecl86 = None

        valueDecl88 = None


        char_literal80_tree = None
        char_literal82_tree = None
        char_literal84_tree = None
        char_literal85_tree = None
        char_literal87_tree = None
        char_literal89_tree = None
        stream_43 = RewriteRuleTokenStream(self._adaptor, "token 43")
        stream_42 = RewriteRuleTokenStream(self._adaptor, "token 42")
        stream_35 = RewriteRuleTokenStream(self._adaptor, "token 35")
        stream_typeReferenceDef = RewriteRuleSubtreeStream(self._adaptor, "rule typeReferenceDef")
        stream_valueDecl = RewriteRuleSubtreeStream(self._adaptor, "rule valueDecl")
        try:
            try:
                # src/SavedFSM/Monitor.g:83:24: ( ( ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) ) | ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) ) ) )
                # src/SavedFSM/Monitor.g:83:26: ( ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) ) | ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) ) )
                pass 
                # src/SavedFSM/Monitor.g:83:26: ( ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) ) | ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) ) )
                alt26 = 2
                LA26_0 = self.input.LA(1)

                if (LA26_0 == ID) :
                    alt26 = 1
                elif (LA26_0 == 42) :
                    alt26 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed

                    nvae = NoViableAltException("", 26, 0, self.input)

                    raise nvae

                if alt26 == 1:
                    # src/SavedFSM/Monitor.g:83:27: ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) )
                    pass 
                    # src/SavedFSM/Monitor.g:83:27: ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) )
                    # src/SavedFSM/Monitor.g:83:28: typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )?
                    pass 
                    self._state.following.append(self.FOLLOW_typeReferenceDef_in_interactionSignatureDef722)
                    typeReferenceDef79 = self.typeReferenceDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_typeReferenceDef.add(typeReferenceDef79.tree)
                    # src/SavedFSM/Monitor.g:83:45: ( '(' valueDecl ( ',' valueDecl )* ')' )?
                    alt24 = 2
                    LA24_0 = self.input.LA(1)

                    if (LA24_0 == 42) :
                        alt24 = 1
                    if alt24 == 1:
                        # src/SavedFSM/Monitor.g:83:46: '(' valueDecl ( ',' valueDecl )* ')'
                        pass 
                        char_literal80=self.match(self.input, 42, self.FOLLOW_42_in_interactionSignatureDef725) 
                        if self._state.backtracking == 0:
                            stream_42.add(char_literal80)
                        self._state.following.append(self.FOLLOW_valueDecl_in_interactionSignatureDef727)
                        valueDecl81 = self.valueDecl()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_valueDecl.add(valueDecl81.tree)
                        # src/SavedFSM/Monitor.g:83:60: ( ',' valueDecl )*
                        while True: #loop23
                            alt23 = 2
                            LA23_0 = self.input.LA(1)

                            if (LA23_0 == 35) :
                                alt23 = 1


                            if alt23 == 1:
                                # src/SavedFSM/Monitor.g:83:61: ',' valueDecl
                                pass 
                                char_literal82=self.match(self.input, 35, self.FOLLOW_35_in_interactionSignatureDef730) 
                                if self._state.backtracking == 0:
                                    stream_35.add(char_literal82)
                                self._state.following.append(self.FOLLOW_valueDecl_in_interactionSignatureDef732)
                                valueDecl83 = self.valueDecl()

                                self._state.following.pop()
                                if self._state.backtracking == 0:
                                    stream_valueDecl.add(valueDecl83.tree)


                            else:
                                break #loop23
                        char_literal84=self.match(self.input, 43, self.FOLLOW_43_in_interactionSignatureDef736) 
                        if self._state.backtracking == 0:
                            stream_43.add(char_literal84)




                    # AST Rewrite
                    # elements: valueDecl, typeReferenceDef
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:

                        retval.tree = root_0

                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 83:83: -> typeReferenceDef ^( VALUE ( valueDecl )* )
                        self._adaptor.addChild(root_0, stream_typeReferenceDef.nextTree())
                        # src/SavedFSM/Monitor.g:83:103: ^( VALUE ( valueDecl )* )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(VALUE, "VALUE"), root_1)

                        # src/SavedFSM/Monitor.g:83:111: ( valueDecl )*
                        while stream_valueDecl.hasNext():
                            self._adaptor.addChild(root_1, stream_valueDecl.nextTree())


                        stream_valueDecl.reset();

                        self._adaptor.addChild(root_0, root_1)



                        retval.tree = root_0





                elif alt26 == 2:
                    # src/SavedFSM/Monitor.g:84:7: ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) )
                    pass 
                    # src/SavedFSM/Monitor.g:84:7: ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) )
                    # src/SavedFSM/Monitor.g:84:8: ( '(' valueDecl ( ',' valueDecl )* ')' )
                    pass 
                    # src/SavedFSM/Monitor.g:84:8: ( '(' valueDecl ( ',' valueDecl )* ')' )
                    # src/SavedFSM/Monitor.g:84:9: '(' valueDecl ( ',' valueDecl )* ')'
                    pass 
                    char_literal85=self.match(self.input, 42, self.FOLLOW_42_in_interactionSignatureDef760) 
                    if self._state.backtracking == 0:
                        stream_42.add(char_literal85)
                    self._state.following.append(self.FOLLOW_valueDecl_in_interactionSignatureDef762)
                    valueDecl86 = self.valueDecl()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_valueDecl.add(valueDecl86.tree)
                    # src/SavedFSM/Monitor.g:84:23: ( ',' valueDecl )*
                    while True: #loop25
                        alt25 = 2
                        LA25_0 = self.input.LA(1)

                        if (LA25_0 == 35) :
                            alt25 = 1


                        if alt25 == 1:
                            # src/SavedFSM/Monitor.g:84:24: ',' valueDecl
                            pass 
                            char_literal87=self.match(self.input, 35, self.FOLLOW_35_in_interactionSignatureDef765) 
                            if self._state.backtracking == 0:
                                stream_35.add(char_literal87)
                            self._state.following.append(self.FOLLOW_valueDecl_in_interactionSignatureDef767)
                            valueDecl88 = self.valueDecl()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                stream_valueDecl.add(valueDecl88.tree)


                        else:
                            break #loop25
                    char_literal89=self.match(self.input, 43, self.FOLLOW_43_in_interactionSignatureDef771) 
                    if self._state.backtracking == 0:
                        stream_43.add(char_literal89)




                    # AST Rewrite
                    # elements: valueDecl
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:

                        retval.tree = root_0

                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 84:45: -> ^( VALUE ( valueDecl )* )
                        # src/SavedFSM/Monitor.g:84:48: ^( VALUE ( valueDecl )* )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(VALUE, "VALUE"), root_1)

                        # src/SavedFSM/Monitor.g:84:56: ( valueDecl )*
                        while stream_valueDecl.hasNext():
                            self._adaptor.addChild(root_1, stream_valueDecl.nextTree())


                        stream_valueDecl.reset();

                        self._adaptor.addChild(root_0, root_1)



                        retval.tree = root_0









                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "interactionSignatureDef"

    class valueDecl_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.valueDecl_return, self).__init__()

            self.tree = None




    # $ANTLR start "valueDecl"
    # src/SavedFSM/Monitor.g:86:1: valueDecl : ID ( ':' primitivetype )? ;
    def valueDecl(self, ):

        retval = self.valueDecl_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ID90 = None
        char_literal91 = None
        primitivetype92 = None


        ID90_tree = None
        char_literal91_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:86:11: ( ID ( ':' primitivetype )? )
                # src/SavedFSM/Monitor.g:86:13: ID ( ':' primitivetype )?
                pass 
                root_0 = self._adaptor.nil()

                ID90=self.match(self.input, ID, self.FOLLOW_ID_in_valueDecl791)
                if self._state.backtracking == 0:

                    ID90_tree = self._adaptor.createWithPayload(ID90)
                    self._adaptor.addChild(root_0, ID90_tree)

                # src/SavedFSM/Monitor.g:86:16: ( ':' primitivetype )?
                alt27 = 2
                LA27_0 = self.input.LA(1)

                if (LA27_0 == 46) :
                    alt27 = 1
                if alt27 == 1:
                    # src/SavedFSM/Monitor.g:86:17: ':' primitivetype
                    pass 
                    char_literal91=self.match(self.input, 46, self.FOLLOW_46_in_valueDecl794)
                    self._state.following.append(self.FOLLOW_primitivetype_in_valueDecl797)
                    primitivetype92 = self.primitivetype()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, primitivetype92.tree)






                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "valueDecl"

    class firstValueDecl_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.firstValueDecl_return, self).__init__()

            self.tree = None




    # $ANTLR start "firstValueDecl"
    # src/SavedFSM/Monitor.g:87:1: firstValueDecl : valueDecl ;
    def firstValueDecl(self, ):

        retval = self.firstValueDecl_return()
        retval.start = self.input.LT(1)

        root_0 = None

        valueDecl93 = None



        try:
            try:
                # src/SavedFSM/Monitor.g:87:16: ( valueDecl )
                # src/SavedFSM/Monitor.g:87:18: valueDecl
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_valueDecl_in_firstValueDecl808)
                valueDecl93 = self.valueDecl()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, valueDecl93.tree)



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "firstValueDecl"

    class interactionDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.interactionDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "interactionDef"
    # src/SavedFSM/Monitor.g:90:1: interactionDef : interactionSignatureDef ( 'from' role= roleName ( assertDef ) -> ^( RESV interactionSignatureDef $role assertDef ) | 'to' roleName ( assertDef ) -> ^( SEND interactionSignatureDef roleName assertDef ) ) ;
    def interactionDef(self, ):

        retval = self.interactionDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal95 = None
        string_literal97 = None
        role = None

        interactionSignatureDef94 = None

        assertDef96 = None

        roleName98 = None

        assertDef99 = None


        string_literal95_tree = None
        string_literal97_tree = None
        stream_47 = RewriteRuleTokenStream(self._adaptor, "token 47")
        stream_37 = RewriteRuleTokenStream(self._adaptor, "token 37")
        stream_assertDef = RewriteRuleSubtreeStream(self._adaptor, "rule assertDef")
        stream_roleName = RewriteRuleSubtreeStream(self._adaptor, "rule roleName")
        stream_interactionSignatureDef = RewriteRuleSubtreeStream(self._adaptor, "rule interactionSignatureDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:90:15: ( interactionSignatureDef ( 'from' role= roleName ( assertDef ) -> ^( RESV interactionSignatureDef $role assertDef ) | 'to' roleName ( assertDef ) -> ^( SEND interactionSignatureDef roleName assertDef ) ) )
                # src/SavedFSM/Monitor.g:91:7: interactionSignatureDef ( 'from' role= roleName ( assertDef ) -> ^( RESV interactionSignatureDef $role assertDef ) | 'to' roleName ( assertDef ) -> ^( SEND interactionSignatureDef roleName assertDef ) )
                pass 
                self._state.following.append(self.FOLLOW_interactionSignatureDef_in_interactionDef823)
                interactionSignatureDef94 = self.interactionSignatureDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_interactionSignatureDef.add(interactionSignatureDef94.tree)
                # src/SavedFSM/Monitor.g:91:31: ( 'from' role= roleName ( assertDef ) -> ^( RESV interactionSignatureDef $role assertDef ) | 'to' roleName ( assertDef ) -> ^( SEND interactionSignatureDef roleName assertDef ) )
                alt28 = 2
                LA28_0 = self.input.LA(1)

                if (LA28_0 == 37) :
                    alt28 = 1
                elif (LA28_0 == 47) :
                    alt28 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed

                    nvae = NoViableAltException("", 28, 0, self.input)

                    raise nvae

                if alt28 == 1:
                    # src/SavedFSM/Monitor.g:92:3: 'from' role= roleName ( assertDef )
                    pass 
                    string_literal95=self.match(self.input, 37, self.FOLLOW_37_in_interactionDef829) 
                    if self._state.backtracking == 0:
                        stream_37.add(string_literal95)
                    self._state.following.append(self.FOLLOW_roleName_in_interactionDef834)
                    role = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_roleName.add(role.tree)
                    # src/SavedFSM/Monitor.g:92:26: ( assertDef )
                    # src/SavedFSM/Monitor.g:92:27: assertDef
                    pass 
                    self._state.following.append(self.FOLLOW_assertDef_in_interactionDef838)
                    assertDef96 = self.assertDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_assertDef.add(assertDef96.tree)




                    # AST Rewrite
                    # elements: interactionSignatureDef, role, assertDef
                    # token labels: 
                    # rule labels: retval, role
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:

                        retval.tree = root_0

                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        if role is not None:
                            stream_role = RewriteRuleSubtreeStream(self._adaptor, "rule role", role.tree)
                        else:
                            stream_role = RewriteRuleSubtreeStream(self._adaptor, "token role", None)


                        root_0 = self._adaptor.nil()
                        # 92:37: -> ^( RESV interactionSignatureDef $role assertDef )
                        # src/SavedFSM/Monitor.g:92:40: ^( RESV interactionSignatureDef $role assertDef )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(RESV, "RESV"), root_1)

                        self._adaptor.addChild(root_1, stream_interactionSignatureDef.nextTree())
                        self._adaptor.addChild(root_1, stream_role.nextTree())
                        self._adaptor.addChild(root_1, stream_assertDef.nextTree())

                        self._adaptor.addChild(root_0, root_1)



                        retval.tree = root_0


                elif alt28 == 2:
                    # src/SavedFSM/Monitor.g:93:10: 'to' roleName ( assertDef )
                    pass 
                    string_literal97=self.match(self.input, 47, self.FOLLOW_47_in_interactionDef862) 
                    if self._state.backtracking == 0:
                        stream_47.add(string_literal97)
                    self._state.following.append(self.FOLLOW_roleName_in_interactionDef864)
                    roleName98 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_roleName.add(roleName98.tree)
                    # src/SavedFSM/Monitor.g:93:25: ( assertDef )
                    # src/SavedFSM/Monitor.g:93:26: assertDef
                    pass 
                    self._state.following.append(self.FOLLOW_assertDef_in_interactionDef868)
                    assertDef99 = self.assertDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_assertDef.add(assertDef99.tree)




                    # AST Rewrite
                    # elements: roleName, interactionSignatureDef, assertDef
                    # token labels: 
                    # rule labels: retval
                    # token list labels: 
                    # rule list labels: 
                    # wildcard labels: 
                    if self._state.backtracking == 0:

                        retval.tree = root_0

                        if retval is not None:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                        else:
                            stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                        root_0 = self._adaptor.nil()
                        # 93:37: -> ^( SEND interactionSignatureDef roleName assertDef )
                        # src/SavedFSM/Monitor.g:93:40: ^( SEND interactionSignatureDef roleName assertDef )
                        root_1 = self._adaptor.nil()
                        root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(SEND, "SEND"), root_1)

                        self._adaptor.addChild(root_1, stream_interactionSignatureDef.nextTree())
                        self._adaptor.addChild(root_1, stream_roleName.nextTree())
                        self._adaptor.addChild(root_1, stream_assertDef.nextTree())

                        self._adaptor.addChild(root_0, root_1)



                        retval.tree = root_0






                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "interactionDef"

    class choiceDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.choiceDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "choiceDef"
    # src/SavedFSM/Monitor.g:95:1: choiceDef : 'choice' ( 'at' roleName )? blockDef ( 'or' blockDef )* -> ^( 'choice' ( blockDef )+ ) ;
    def choiceDef(self, ):

        retval = self.choiceDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal100 = None
        string_literal101 = None
        string_literal104 = None
        roleName102 = None

        blockDef103 = None

        blockDef105 = None


        string_literal100_tree = None
        string_literal101_tree = None
        string_literal104_tree = None
        stream_49 = RewriteRuleTokenStream(self._adaptor, "token 49")
        stream_48 = RewriteRuleTokenStream(self._adaptor, "token 48")
        stream_39 = RewriteRuleTokenStream(self._adaptor, "token 39")
        stream_roleName = RewriteRuleSubtreeStream(self._adaptor, "rule roleName")
        stream_blockDef = RewriteRuleSubtreeStream(self._adaptor, "rule blockDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:95:10: ( 'choice' ( 'at' roleName )? blockDef ( 'or' blockDef )* -> ^( 'choice' ( blockDef )+ ) )
                # src/SavedFSM/Monitor.g:95:12: 'choice' ( 'at' roleName )? blockDef ( 'or' blockDef )*
                pass 
                string_literal100=self.match(self.input, 48, self.FOLLOW_48_in_choiceDef889) 
                if self._state.backtracking == 0:
                    stream_48.add(string_literal100)
                # src/SavedFSM/Monitor.g:95:21: ( 'at' roleName )?
                alt29 = 2
                LA29_0 = self.input.LA(1)

                if (LA29_0 == 39) :
                    alt29 = 1
                if alt29 == 1:
                    # src/SavedFSM/Monitor.g:95:23: 'at' roleName
                    pass 
                    string_literal101=self.match(self.input, 39, self.FOLLOW_39_in_choiceDef893) 
                    if self._state.backtracking == 0:
                        stream_39.add(string_literal101)
                    self._state.following.append(self.FOLLOW_roleName_in_choiceDef895)
                    roleName102 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_roleName.add(roleName102.tree)



                self._state.following.append(self.FOLLOW_blockDef_in_choiceDef900)
                blockDef103 = self.blockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_blockDef.add(blockDef103.tree)
                # src/SavedFSM/Monitor.g:95:49: ( 'or' blockDef )*
                while True: #loop30
                    alt30 = 2
                    LA30_0 = self.input.LA(1)

                    if (LA30_0 == 49) :
                        alt30 = 1


                    if alt30 == 1:
                        # src/SavedFSM/Monitor.g:95:51: 'or' blockDef
                        pass 
                        string_literal104=self.match(self.input, 49, self.FOLLOW_49_in_choiceDef904) 
                        if self._state.backtracking == 0:
                            stream_49.add(string_literal104)
                        self._state.following.append(self.FOLLOW_blockDef_in_choiceDef906)
                        blockDef105 = self.blockDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_blockDef.add(blockDef105.tree)


                    else:
                        break #loop30

                # AST Rewrite
                # elements: 48, blockDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 95:68: -> ^( 'choice' ( blockDef )+ )
                    # src/SavedFSM/Monitor.g:95:71: ^( 'choice' ( blockDef )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(stream_48.nextNode(), root_1)

                    # src/SavedFSM/Monitor.g:95:82: ( blockDef )+
                    if not (stream_blockDef.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_blockDef.hasNext():
                        self._adaptor.addChild(root_1, stream_blockDef.nextTree())


                    stream_blockDef.reset()

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "choiceDef"

    class directedChoiceDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.directedChoiceDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "directedChoiceDef"
    # src/SavedFSM/Monitor.g:97:1: directedChoiceDef : ( 'from' roleName )? ( 'to' roleName ( ',' roleName )* )? '{' ( onMessageDef )+ '}' ;
    def directedChoiceDef(self, ):

        retval = self.directedChoiceDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal106 = None
        string_literal108 = None
        char_literal110 = None
        char_literal112 = None
        char_literal114 = None
        roleName107 = None

        roleName109 = None

        roleName111 = None

        onMessageDef113 = None


        string_literal106_tree = None
        string_literal108_tree = None
        char_literal110_tree = None
        char_literal112_tree = None
        char_literal114_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:97:18: ( ( 'from' roleName )? ( 'to' roleName ( ',' roleName )* )? '{' ( onMessageDef )+ '}' )
                # src/SavedFSM/Monitor.g:97:20: ( 'from' roleName )? ( 'to' roleName ( ',' roleName )* )? '{' ( onMessageDef )+ '}'
                pass 
                root_0 = self._adaptor.nil()

                # src/SavedFSM/Monitor.g:97:20: ( 'from' roleName )?
                alt31 = 2
                LA31_0 = self.input.LA(1)

                if (LA31_0 == 37) :
                    alt31 = 1
                if alt31 == 1:
                    # src/SavedFSM/Monitor.g:97:22: 'from' roleName
                    pass 
                    string_literal106=self.match(self.input, 37, self.FOLLOW_37_in_directedChoiceDef927)
                    if self._state.backtracking == 0:

                        string_literal106_tree = self._adaptor.createWithPayload(string_literal106)
                        self._adaptor.addChild(root_0, string_literal106_tree)

                    self._state.following.append(self.FOLLOW_roleName_in_directedChoiceDef929)
                    roleName107 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, roleName107.tree)



                # src/SavedFSM/Monitor.g:97:41: ( 'to' roleName ( ',' roleName )* )?
                alt33 = 2
                LA33_0 = self.input.LA(1)

                if (LA33_0 == 47) :
                    alt33 = 1
                if alt33 == 1:
                    # src/SavedFSM/Monitor.g:97:43: 'to' roleName ( ',' roleName )*
                    pass 
                    string_literal108=self.match(self.input, 47, self.FOLLOW_47_in_directedChoiceDef936)
                    if self._state.backtracking == 0:

                        string_literal108_tree = self._adaptor.createWithPayload(string_literal108)
                        self._adaptor.addChild(root_0, string_literal108_tree)

                    self._state.following.append(self.FOLLOW_roleName_in_directedChoiceDef938)
                    roleName109 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, roleName109.tree)
                    # src/SavedFSM/Monitor.g:97:57: ( ',' roleName )*
                    while True: #loop32
                        alt32 = 2
                        LA32_0 = self.input.LA(1)

                        if (LA32_0 == 35) :
                            alt32 = 1


                        if alt32 == 1:
                            # src/SavedFSM/Monitor.g:97:59: ',' roleName
                            pass 
                            char_literal110=self.match(self.input, 35, self.FOLLOW_35_in_directedChoiceDef942)
                            self._state.following.append(self.FOLLOW_roleName_in_directedChoiceDef945)
                            roleName111 = self.roleName()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, roleName111.tree)


                        else:
                            break #loop32



                char_literal112=self.match(self.input, 40, self.FOLLOW_40_in_directedChoiceDef953)
                if self._state.backtracking == 0:

                    char_literal112_tree = self._adaptor.createWithPayload(char_literal112)
                    self._adaptor.addChild(root_0, char_literal112_tree)

                # src/SavedFSM/Monitor.g:97:83: ( onMessageDef )+
                cnt34 = 0
                while True: #loop34
                    alt34 = 2
                    LA34_0 = self.input.LA(1)

                    if (LA34_0 == ID or LA34_0 == 42) :
                        alt34 = 1


                    if alt34 == 1:
                        # src/SavedFSM/Monitor.g:97:85: onMessageDef
                        pass 
                        self._state.following.append(self.FOLLOW_onMessageDef_in_directedChoiceDef957)
                        onMessageDef113 = self.onMessageDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, onMessageDef113.tree)


                    else:
                        if cnt34 >= 1:
                            break #loop34

                        if self._state.backtracking > 0:
                            raise BacktrackingFailed

                        eee = EarlyExitException(34, self.input)
                        raise eee

                    cnt34 += 1
                char_literal114=self.match(self.input, 41, self.FOLLOW_41_in_directedChoiceDef962)
                if self._state.backtracking == 0:

                    char_literal114_tree = self._adaptor.createWithPayload(char_literal114)
                    self._adaptor.addChild(root_0, char_literal114_tree)




                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "directedChoiceDef"

    class onMessageDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.onMessageDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "onMessageDef"
    # src/SavedFSM/Monitor.g:99:1: onMessageDef : interactionSignatureDef ':' activityList ;
    def onMessageDef(self, ):

        retval = self.onMessageDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        char_literal116 = None
        interactionSignatureDef115 = None

        activityList117 = None


        char_literal116_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:99:13: ( interactionSignatureDef ':' activityList )
                # src/SavedFSM/Monitor.g:99:15: interactionSignatureDef ':' activityList
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_interactionSignatureDef_in_onMessageDef969)
                interactionSignatureDef115 = self.interactionSignatureDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, interactionSignatureDef115.tree)
                char_literal116=self.match(self.input, 46, self.FOLLOW_46_in_onMessageDef971)
                if self._state.backtracking == 0:

                    char_literal116_tree = self._adaptor.createWithPayload(char_literal116)
                    self._adaptor.addChild(root_0, char_literal116_tree)

                self._state.following.append(self.FOLLOW_activityList_in_onMessageDef973)
                activityList117 = self.activityList()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, activityList117.tree)



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "onMessageDef"

    class activityList_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.activityList_return, self).__init__()

            self.tree = None




    # $ANTLR start "activityList"
    # src/SavedFSM/Monitor.g:101:1: activityList : ( ( ANNOTATION )* activityDef )* ;
    def activityList(self, ):

        retval = self.activityList_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ANNOTATION118 = None
        activityDef119 = None


        ANNOTATION118_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:101:13: ( ( ( ANNOTATION )* activityDef )* )
                # src/SavedFSM/Monitor.g:101:15: ( ( ANNOTATION )* activityDef )*
                pass 
                root_0 = self._adaptor.nil()

                # src/SavedFSM/Monitor.g:101:15: ( ( ANNOTATION )* activityDef )*
                while True: #loop36
                    alt36 = 2
                    alt36 = self.dfa36.predict(self.input)
                    if alt36 == 1:
                        # src/SavedFSM/Monitor.g:101:17: ( ANNOTATION )* activityDef
                        pass 
                        # src/SavedFSM/Monitor.g:101:17: ( ANNOTATION )*
                        while True: #loop35
                            alt35 = 2
                            LA35_0 = self.input.LA(1)

                            if (LA35_0 == ANNOTATION) :
                                alt35 = 1


                            if alt35 == 1:
                                # src/SavedFSM/Monitor.g:101:19: ANNOTATION
                                pass 
                                ANNOTATION118=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_activityList986)
                                if self._state.backtracking == 0:

                                    ANNOTATION118_tree = self._adaptor.createWithPayload(ANNOTATION118)
                                    self._adaptor.addChild(root_0, ANNOTATION118_tree)



                            else:
                                break #loop35
                        self._state.following.append(self.FOLLOW_activityDef_in_activityList991)
                        activityDef119 = self.activityDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, activityDef119.tree)


                    else:
                        break #loop36



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "activityList"

    class repeatDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.repeatDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "repeatDef"
    # src/SavedFSM/Monitor.g:103:1: repeatDef : 'repeat' ( 'at' roleName ( ',' roleName )* )? blockDef -> ^( 'repeat' blockDef ) ;
    def repeatDef(self, ):

        retval = self.repeatDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal120 = None
        string_literal121 = None
        char_literal123 = None
        roleName122 = None

        roleName124 = None

        blockDef125 = None


        string_literal120_tree = None
        string_literal121_tree = None
        char_literal123_tree = None
        stream_35 = RewriteRuleTokenStream(self._adaptor, "token 35")
        stream_39 = RewriteRuleTokenStream(self._adaptor, "token 39")
        stream_50 = RewriteRuleTokenStream(self._adaptor, "token 50")
        stream_roleName = RewriteRuleSubtreeStream(self._adaptor, "rule roleName")
        stream_blockDef = RewriteRuleSubtreeStream(self._adaptor, "rule blockDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:103:10: ( 'repeat' ( 'at' roleName ( ',' roleName )* )? blockDef -> ^( 'repeat' blockDef ) )
                # src/SavedFSM/Monitor.g:103:12: 'repeat' ( 'at' roleName ( ',' roleName )* )? blockDef
                pass 
                string_literal120=self.match(self.input, 50, self.FOLLOW_50_in_repeatDef1001) 
                if self._state.backtracking == 0:
                    stream_50.add(string_literal120)
                # src/SavedFSM/Monitor.g:103:21: ( 'at' roleName ( ',' roleName )* )?
                alt38 = 2
                LA38_0 = self.input.LA(1)

                if (LA38_0 == 39) :
                    alt38 = 1
                if alt38 == 1:
                    # src/SavedFSM/Monitor.g:103:23: 'at' roleName ( ',' roleName )*
                    pass 
                    string_literal121=self.match(self.input, 39, self.FOLLOW_39_in_repeatDef1005) 
                    if self._state.backtracking == 0:
                        stream_39.add(string_literal121)
                    self._state.following.append(self.FOLLOW_roleName_in_repeatDef1007)
                    roleName122 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_roleName.add(roleName122.tree)
                    # src/SavedFSM/Monitor.g:103:37: ( ',' roleName )*
                    while True: #loop37
                        alt37 = 2
                        LA37_0 = self.input.LA(1)

                        if (LA37_0 == 35) :
                            alt37 = 1


                        if alt37 == 1:
                            # src/SavedFSM/Monitor.g:103:39: ',' roleName
                            pass 
                            char_literal123=self.match(self.input, 35, self.FOLLOW_35_in_repeatDef1011) 
                            if self._state.backtracking == 0:
                                stream_35.add(char_literal123)
                            self._state.following.append(self.FOLLOW_roleName_in_repeatDef1013)
                            roleName124 = self.roleName()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                stream_roleName.add(roleName124.tree)


                        else:
                            break #loop37



                self._state.following.append(self.FOLLOW_blockDef_in_repeatDef1021)
                blockDef125 = self.blockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_blockDef.add(blockDef125.tree)

                # AST Rewrite
                # elements: 50, blockDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 103:68: -> ^( 'repeat' blockDef )
                    # src/SavedFSM/Monitor.g:103:71: ^( 'repeat' blockDef )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(stream_50.nextNode(), root_1)

                    self._adaptor.addChild(root_1, stream_blockDef.nextTree())

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "repeatDef"

    class recBlockDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.recBlockDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "recBlockDef"
    # src/SavedFSM/Monitor.g:105:1: recBlockDef : 'rec' labelName blockDef -> ^( 'rec' labelName blockDef ) ;
    def recBlockDef(self, ):

        retval = self.recBlockDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal126 = None
        labelName127 = None

        blockDef128 = None


        string_literal126_tree = None
        stream_51 = RewriteRuleTokenStream(self._adaptor, "token 51")
        stream_labelName = RewriteRuleSubtreeStream(self._adaptor, "rule labelName")
        stream_blockDef = RewriteRuleSubtreeStream(self._adaptor, "rule blockDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:105:12: ( 'rec' labelName blockDef -> ^( 'rec' labelName blockDef ) )
                # src/SavedFSM/Monitor.g:105:14: 'rec' labelName blockDef
                pass 
                string_literal126=self.match(self.input, 51, self.FOLLOW_51_in_recBlockDef1037) 
                if self._state.backtracking == 0:
                    stream_51.add(string_literal126)
                self._state.following.append(self.FOLLOW_labelName_in_recBlockDef1039)
                labelName127 = self.labelName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_labelName.add(labelName127.tree)
                self._state.following.append(self.FOLLOW_blockDef_in_recBlockDef1041)
                blockDef128 = self.blockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_blockDef.add(blockDef128.tree)

                # AST Rewrite
                # elements: labelName, 51, blockDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 105:39: -> ^( 'rec' labelName blockDef )
                    # src/SavedFSM/Monitor.g:105:42: ^( 'rec' labelName blockDef )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(stream_51.nextNode(), root_1)

                    self._adaptor.addChild(root_1, stream_labelName.nextTree())
                    self._adaptor.addChild(root_1, stream_blockDef.nextTree())

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "recBlockDef"

    class labelName_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.labelName_return, self).__init__()

            self.tree = None




    # $ANTLR start "labelName"
    # src/SavedFSM/Monitor.g:107:1: labelName : ID -> ID ;
    def labelName(self, ):

        retval = self.labelName_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ID129 = None

        ID129_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")

        try:
            try:
                # src/SavedFSM/Monitor.g:107:10: ( ID -> ID )
                # src/SavedFSM/Monitor.g:107:12: ID
                pass 
                ID129=self.match(self.input, ID, self.FOLLOW_ID_in_labelName1058) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID129)

                # AST Rewrite
                # elements: ID
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 107:15: -> ID
                    self._adaptor.addChild(root_0, stream_ID.nextNode())



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "labelName"

    class recursionDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.recursionDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "recursionDef"
    # src/SavedFSM/Monitor.g:109:1: recursionDef : labelName -> ^( RECLABEL labelName ) ;
    def recursionDef(self, ):

        retval = self.recursionDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        labelName130 = None


        stream_labelName = RewriteRuleSubtreeStream(self._adaptor, "rule labelName")
        try:
            try:
                # src/SavedFSM/Monitor.g:109:13: ( labelName -> ^( RECLABEL labelName ) )
                # src/SavedFSM/Monitor.g:109:15: labelName
                pass 
                self._state.following.append(self.FOLLOW_labelName_in_recursionDef1070)
                labelName130 = self.labelName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_labelName.add(labelName130.tree)

                # AST Rewrite
                # elements: labelName
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 109:25: -> ^( RECLABEL labelName )
                    # src/SavedFSM/Monitor.g:109:28: ^( RECLABEL labelName )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(RECLABEL, "RECLABEL"), root_1)

                    self._adaptor.addChild(root_1, stream_labelName.nextTree())

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "recursionDef"

    class endDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.endDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "endDef"
    # src/SavedFSM/Monitor.g:112:1: endDef : 'end' ;
    def endDef(self, ):

        retval = self.endDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal131 = None

        string_literal131_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:112:7: ( 'end' )
                # src/SavedFSM/Monitor.g:112:9: 'end'
                pass 
                root_0 = self._adaptor.nil()

                string_literal131=self.match(self.input, 52, self.FOLLOW_52_in_endDef1086)
                if self._state.backtracking == 0:

                    string_literal131_tree = self._adaptor.createWithPayload(string_literal131)
                    root_0 = self._adaptor.becomeRoot(string_literal131_tree, root_0)




                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "endDef"

    class runDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.runDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "runDef"
    # src/SavedFSM/Monitor.g:115:1: runDef : 'run' protocolRefDef ( '(' parameter ( ',' parameter )* ')' )? 'from' roleName ;
    def runDef(self, ):

        retval = self.runDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal132 = None
        char_literal134 = None
        char_literal136 = None
        char_literal138 = None
        string_literal139 = None
        protocolRefDef133 = None

        parameter135 = None

        parameter137 = None

        roleName140 = None


        string_literal132_tree = None
        char_literal134_tree = None
        char_literal136_tree = None
        char_literal138_tree = None
        string_literal139_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:115:7: ( 'run' protocolRefDef ( '(' parameter ( ',' parameter )* ')' )? 'from' roleName )
                # src/SavedFSM/Monitor.g:115:9: 'run' protocolRefDef ( '(' parameter ( ',' parameter )* ')' )? 'from' roleName
                pass 
                root_0 = self._adaptor.nil()

                string_literal132=self.match(self.input, 53, self.FOLLOW_53_in_runDef1096)
                if self._state.backtracking == 0:

                    string_literal132_tree = self._adaptor.createWithPayload(string_literal132)
                    root_0 = self._adaptor.becomeRoot(string_literal132_tree, root_0)

                self._state.following.append(self.FOLLOW_protocolRefDef_in_runDef1099)
                protocolRefDef133 = self.protocolRefDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, protocolRefDef133.tree)
                # src/SavedFSM/Monitor.g:115:31: ( '(' parameter ( ',' parameter )* ')' )?
                alt40 = 2
                LA40_0 = self.input.LA(1)

                if (LA40_0 == 42) :
                    alt40 = 1
                if alt40 == 1:
                    # src/SavedFSM/Monitor.g:115:33: '(' parameter ( ',' parameter )* ')'
                    pass 
                    char_literal134=self.match(self.input, 42, self.FOLLOW_42_in_runDef1103)
                    self._state.following.append(self.FOLLOW_parameter_in_runDef1106)
                    parameter135 = self.parameter()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, parameter135.tree)
                    # src/SavedFSM/Monitor.g:115:48: ( ',' parameter )*
                    while True: #loop39
                        alt39 = 2
                        LA39_0 = self.input.LA(1)

                        if (LA39_0 == 35) :
                            alt39 = 1


                        if alt39 == 1:
                            # src/SavedFSM/Monitor.g:115:50: ',' parameter
                            pass 
                            char_literal136=self.match(self.input, 35, self.FOLLOW_35_in_runDef1110)
                            self._state.following.append(self.FOLLOW_parameter_in_runDef1113)
                            parameter137 = self.parameter()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, parameter137.tree)


                        else:
                            break #loop39
                    char_literal138=self.match(self.input, 43, self.FOLLOW_43_in_runDef1118)



                string_literal139=self.match(self.input, 37, self.FOLLOW_37_in_runDef1124)
                if self._state.backtracking == 0:

                    string_literal139_tree = self._adaptor.createWithPayload(string_literal139)
                    self._adaptor.addChild(root_0, string_literal139_tree)

                self._state.following.append(self.FOLLOW_roleName_in_runDef1126)
                roleName140 = self.roleName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, roleName140.tree)



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "runDef"

    class protocolRefDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.protocolRefDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "protocolRefDef"
    # src/SavedFSM/Monitor.g:117:1: protocolRefDef : ID ( 'at' roleName )? ;
    def protocolRefDef(self, ):

        retval = self.protocolRefDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ID141 = None
        string_literal142 = None
        roleName143 = None


        ID141_tree = None
        string_literal142_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:117:15: ( ID ( 'at' roleName )? )
                # src/SavedFSM/Monitor.g:117:17: ID ( 'at' roleName )?
                pass 
                root_0 = self._adaptor.nil()

                ID141=self.match(self.input, ID, self.FOLLOW_ID_in_protocolRefDef1134)
                if self._state.backtracking == 0:

                    ID141_tree = self._adaptor.createWithPayload(ID141)
                    self._adaptor.addChild(root_0, ID141_tree)

                # src/SavedFSM/Monitor.g:117:20: ( 'at' roleName )?
                alt41 = 2
                LA41_0 = self.input.LA(1)

                if (LA41_0 == 39) :
                    alt41 = 1
                if alt41 == 1:
                    # src/SavedFSM/Monitor.g:117:22: 'at' roleName
                    pass 
                    string_literal142=self.match(self.input, 39, self.FOLLOW_39_in_protocolRefDef1138)
                    if self._state.backtracking == 0:

                        string_literal142_tree = self._adaptor.createWithPayload(string_literal142)
                        self._adaptor.addChild(root_0, string_literal142_tree)

                    self._state.following.append(self.FOLLOW_roleName_in_protocolRefDef1140)
                    roleName143 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, roleName143.tree)






                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "protocolRefDef"

    class declarationName_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.declarationName_return, self).__init__()

            self.tree = None




    # $ANTLR start "declarationName"
    # src/SavedFSM/Monitor.g:119:1: declarationName : ID ;
    def declarationName(self, ):

        retval = self.declarationName_return()
        retval.start = self.input.LT(1)

        root_0 = None

        ID144 = None

        ID144_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:119:16: ( ID )
                # src/SavedFSM/Monitor.g:119:18: ID
                pass 
                root_0 = self._adaptor.nil()

                ID144=self.match(self.input, ID, self.FOLLOW_ID_in_declarationName1151)
                if self._state.backtracking == 0:

                    ID144_tree = self._adaptor.createWithPayload(ID144)
                    self._adaptor.addChild(root_0, ID144_tree)




                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "declarationName"

    class parameter_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.parameter_return, self).__init__()

            self.tree = None




    # $ANTLR start "parameter"
    # src/SavedFSM/Monitor.g:121:1: parameter : declarationName ;
    def parameter(self, ):

        retval = self.parameter_return()
        retval.start = self.input.LT(1)

        root_0 = None

        declarationName145 = None



        try:
            try:
                # src/SavedFSM/Monitor.g:121:10: ( declarationName )
                # src/SavedFSM/Monitor.g:121:12: declarationName
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_declarationName_in_parameter1159)
                declarationName145 = self.declarationName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, declarationName145.tree)



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "parameter"

    class inlineDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.inlineDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "inlineDef"
    # src/SavedFSM/Monitor.g:124:1: inlineDef : 'inline' protocolRefDef ( '(' parameter ( ',' parameter )* ')' )? ;
    def inlineDef(self, ):

        retval = self.inlineDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal146 = None
        char_literal148 = None
        char_literal150 = None
        char_literal152 = None
        protocolRefDef147 = None

        parameter149 = None

        parameter151 = None


        string_literal146_tree = None
        char_literal148_tree = None
        char_literal150_tree = None
        char_literal152_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:124:10: ( 'inline' protocolRefDef ( '(' parameter ( ',' parameter )* ')' )? )
                # src/SavedFSM/Monitor.g:124:12: 'inline' protocolRefDef ( '(' parameter ( ',' parameter )* ')' )?
                pass 
                root_0 = self._adaptor.nil()

                string_literal146=self.match(self.input, 54, self.FOLLOW_54_in_inlineDef1168)
                if self._state.backtracking == 0:

                    string_literal146_tree = self._adaptor.createWithPayload(string_literal146)
                    root_0 = self._adaptor.becomeRoot(string_literal146_tree, root_0)

                self._state.following.append(self.FOLLOW_protocolRefDef_in_inlineDef1171)
                protocolRefDef147 = self.protocolRefDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, protocolRefDef147.tree)
                # src/SavedFSM/Monitor.g:124:37: ( '(' parameter ( ',' parameter )* ')' )?
                alt43 = 2
                LA43_0 = self.input.LA(1)

                if (LA43_0 == 42) :
                    alt43 = 1
                if alt43 == 1:
                    # src/SavedFSM/Monitor.g:124:39: '(' parameter ( ',' parameter )* ')'
                    pass 
                    char_literal148=self.match(self.input, 42, self.FOLLOW_42_in_inlineDef1175)
                    self._state.following.append(self.FOLLOW_parameter_in_inlineDef1178)
                    parameter149 = self.parameter()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, parameter149.tree)
                    # src/SavedFSM/Monitor.g:124:54: ( ',' parameter )*
                    while True: #loop42
                        alt42 = 2
                        LA42_0 = self.input.LA(1)

                        if (LA42_0 == 35) :
                            alt42 = 1


                        if alt42 == 1:
                            # src/SavedFSM/Monitor.g:124:56: ',' parameter
                            pass 
                            char_literal150=self.match(self.input, 35, self.FOLLOW_35_in_inlineDef1182)
                            self._state.following.append(self.FOLLOW_parameter_in_inlineDef1185)
                            parameter151 = self.parameter()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, parameter151.tree)


                        else:
                            break #loop42
                    char_literal152=self.match(self.input, 43, self.FOLLOW_43_in_inlineDef1190)






                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "inlineDef"

    class parallelDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.parallelDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "parallelDef"
    # src/SavedFSM/Monitor.g:126:1: parallelDef : 'parallel' blockDef ( 'and' blockDef )* -> ^( PARALLEL ( blockDef )+ ) ;
    def parallelDef(self, ):

        retval = self.parallelDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal153 = None
        string_literal155 = None
        blockDef154 = None

        blockDef156 = None


        string_literal153_tree = None
        string_literal155_tree = None
        stream_56 = RewriteRuleTokenStream(self._adaptor, "token 56")
        stream_55 = RewriteRuleTokenStream(self._adaptor, "token 55")
        stream_blockDef = RewriteRuleSubtreeStream(self._adaptor, "rule blockDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:126:12: ( 'parallel' blockDef ( 'and' blockDef )* -> ^( PARALLEL ( blockDef )+ ) )
                # src/SavedFSM/Monitor.g:126:14: 'parallel' blockDef ( 'and' blockDef )*
                pass 
                string_literal153=self.match(self.input, 55, self.FOLLOW_55_in_parallelDef1202) 
                if self._state.backtracking == 0:
                    stream_55.add(string_literal153)
                self._state.following.append(self.FOLLOW_blockDef_in_parallelDef1204)
                blockDef154 = self.blockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_blockDef.add(blockDef154.tree)
                # src/SavedFSM/Monitor.g:126:34: ( 'and' blockDef )*
                while True: #loop44
                    alt44 = 2
                    LA44_0 = self.input.LA(1)

                    if (LA44_0 == 56) :
                        alt44 = 1


                    if alt44 == 1:
                        # src/SavedFSM/Monitor.g:126:36: 'and' blockDef
                        pass 
                        string_literal155=self.match(self.input, 56, self.FOLLOW_56_in_parallelDef1208) 
                        if self._state.backtracking == 0:
                            stream_56.add(string_literal155)
                        self._state.following.append(self.FOLLOW_blockDef_in_parallelDef1210)
                        blockDef156 = self.blockDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_blockDef.add(blockDef156.tree)


                    else:
                        break #loop44

                # AST Rewrite
                # elements: blockDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 126:54: -> ^( PARALLEL ( blockDef )+ )
                    # src/SavedFSM/Monitor.g:126:57: ^( PARALLEL ( blockDef )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(PARALLEL, "PARALLEL"), root_1)

                    # src/SavedFSM/Monitor.g:126:68: ( blockDef )+
                    if not (stream_blockDef.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_blockDef.hasNext():
                        self._adaptor.addChild(root_1, stream_blockDef.nextTree())


                    stream_blockDef.reset()

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "parallelDef"

    class doBlockDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.doBlockDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "doBlockDef"
    # src/SavedFSM/Monitor.g:129:1: doBlockDef : 'do' '{' activityListDef '}' -> ^( 'do' activityListDef ) ;
    def doBlockDef(self, ):

        retval = self.doBlockDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal157 = None
        char_literal158 = None
        char_literal160 = None
        activityListDef159 = None


        string_literal157_tree = None
        char_literal158_tree = None
        char_literal160_tree = None
        stream_57 = RewriteRuleTokenStream(self._adaptor, "token 57")
        stream_41 = RewriteRuleTokenStream(self._adaptor, "token 41")
        stream_40 = RewriteRuleTokenStream(self._adaptor, "token 40")
        stream_activityListDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityListDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:129:11: ( 'do' '{' activityListDef '}' -> ^( 'do' activityListDef ) )
                # src/SavedFSM/Monitor.g:129:13: 'do' '{' activityListDef '}'
                pass 
                string_literal157=self.match(self.input, 57, self.FOLLOW_57_in_doBlockDef1230) 
                if self._state.backtracking == 0:
                    stream_57.add(string_literal157)
                char_literal158=self.match(self.input, 40, self.FOLLOW_40_in_doBlockDef1232) 
                if self._state.backtracking == 0:
                    stream_40.add(char_literal158)
                self._state.following.append(self.FOLLOW_activityListDef_in_doBlockDef1234)
                activityListDef159 = self.activityListDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_activityListDef.add(activityListDef159.tree)
                char_literal160=self.match(self.input, 41, self.FOLLOW_41_in_doBlockDef1237) 
                if self._state.backtracking == 0:
                    stream_41.add(char_literal160)

                # AST Rewrite
                # elements: 57, activityListDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 129:43: -> ^( 'do' activityListDef )
                    # src/SavedFSM/Monitor.g:129:46: ^( 'do' activityListDef )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(stream_57.nextNode(), root_1)

                    self._adaptor.addChild(root_1, stream_activityListDef.nextTree())

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "doBlockDef"

    class interruptDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.interruptDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "interruptDef"
    # src/SavedFSM/Monitor.g:131:1: interruptDef : 'interrupt' 'by' roleName '{' activityListDef '}' -> ^( 'interrupt' roleName activityListDef ) ;
    def interruptDef(self, ):

        retval = self.interruptDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal161 = None
        string_literal162 = None
        char_literal164 = None
        char_literal166 = None
        roleName163 = None

        activityListDef165 = None


        string_literal161_tree = None
        string_literal162_tree = None
        char_literal164_tree = None
        char_literal166_tree = None
        stream_59 = RewriteRuleTokenStream(self._adaptor, "token 59")
        stream_58 = RewriteRuleTokenStream(self._adaptor, "token 58")
        stream_41 = RewriteRuleTokenStream(self._adaptor, "token 41")
        stream_40 = RewriteRuleTokenStream(self._adaptor, "token 40")
        stream_activityListDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityListDef")
        stream_roleName = RewriteRuleSubtreeStream(self._adaptor, "rule roleName")
        try:
            try:
                # src/SavedFSM/Monitor.g:131:13: ( 'interrupt' 'by' roleName '{' activityListDef '}' -> ^( 'interrupt' roleName activityListDef ) )
                # src/SavedFSM/Monitor.g:131:15: 'interrupt' 'by' roleName '{' activityListDef '}'
                pass 
                string_literal161=self.match(self.input, 58, self.FOLLOW_58_in_interruptDef1255) 
                if self._state.backtracking == 0:
                    stream_58.add(string_literal161)
                string_literal162=self.match(self.input, 59, self.FOLLOW_59_in_interruptDef1257) 
                if self._state.backtracking == 0:
                    stream_59.add(string_literal162)
                self._state.following.append(self.FOLLOW_roleName_in_interruptDef1259)
                roleName163 = self.roleName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_roleName.add(roleName163.tree)
                char_literal164=self.match(self.input, 40, self.FOLLOW_40_in_interruptDef1261) 
                if self._state.backtracking == 0:
                    stream_40.add(char_literal164)
                self._state.following.append(self.FOLLOW_activityListDef_in_interruptDef1263)
                activityListDef165 = self.activityListDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_activityListDef.add(activityListDef165.tree)
                char_literal166=self.match(self.input, 41, self.FOLLOW_41_in_interruptDef1265) 
                if self._state.backtracking == 0:
                    stream_41.add(char_literal166)

                # AST Rewrite
                # elements: 58, activityListDef, roleName
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 131:65: -> ^( 'interrupt' roleName activityListDef )
                    # src/SavedFSM/Monitor.g:131:68: ^( 'interrupt' roleName activityListDef )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(stream_58.nextNode(), root_1)

                    self._adaptor.addChild(root_1, stream_roleName.nextTree())
                    self._adaptor.addChild(root_1, stream_activityListDef.nextTree())

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "interruptDef"

    class globalEscapeDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.globalEscapeDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "globalEscapeDef"
    # src/SavedFSM/Monitor.g:133:1: globalEscapeDef : doBlockDef interruptDef -> ^( GLOBAL_ESCAPE doBlockDef interruptDef ) ;
    def globalEscapeDef(self, ):

        retval = self.globalEscapeDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        doBlockDef167 = None

        interruptDef168 = None


        stream_interruptDef = RewriteRuleSubtreeStream(self._adaptor, "rule interruptDef")
        stream_doBlockDef = RewriteRuleSubtreeStream(self._adaptor, "rule doBlockDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:133:16: ( doBlockDef interruptDef -> ^( GLOBAL_ESCAPE doBlockDef interruptDef ) )
                # src/SavedFSM/Monitor.g:133:19: doBlockDef interruptDef
                pass 
                self._state.following.append(self.FOLLOW_doBlockDef_in_globalEscapeDef1283)
                doBlockDef167 = self.doBlockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_doBlockDef.add(doBlockDef167.tree)
                self._state.following.append(self.FOLLOW_interruptDef_in_globalEscapeDef1286)
                interruptDef168 = self.interruptDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_interruptDef.add(interruptDef168.tree)

                # AST Rewrite
                # elements: doBlockDef, interruptDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 133:44: -> ^( GLOBAL_ESCAPE doBlockDef interruptDef )
                    # src/SavedFSM/Monitor.g:133:47: ^( GLOBAL_ESCAPE doBlockDef interruptDef )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(GLOBAL_ESCAPE, "GLOBAL_ESCAPE"), root_1)

                    self._adaptor.addChild(root_1, stream_doBlockDef.nextTree())
                    self._adaptor.addChild(root_1, stream_interruptDef.nextTree())

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "globalEscapeDef"

    class unorderedDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.unorderedDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "unorderedDef"
    # src/SavedFSM/Monitor.g:135:1: unorderedDef : 'unordered' '{' ( ( ANNOTATION )* activityDef )* '}' -> ^( PARALLEL ( ^( BRANCH activityDef ) )+ ) ;
    def unorderedDef(self, ):

        retval = self.unorderedDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal169 = None
        char_literal170 = None
        ANNOTATION171 = None
        char_literal173 = None
        activityDef172 = None


        string_literal169_tree = None
        char_literal170_tree = None
        ANNOTATION171_tree = None
        char_literal173_tree = None
        stream_41 = RewriteRuleTokenStream(self._adaptor, "token 41")
        stream_40 = RewriteRuleTokenStream(self._adaptor, "token 40")
        stream_ANNOTATION = RewriteRuleTokenStream(self._adaptor, "token ANNOTATION")
        stream_60 = RewriteRuleTokenStream(self._adaptor, "token 60")
        stream_activityDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:135:13: ( 'unordered' '{' ( ( ANNOTATION )* activityDef )* '}' -> ^( PARALLEL ( ^( BRANCH activityDef ) )+ ) )
                # src/SavedFSM/Monitor.g:135:15: 'unordered' '{' ( ( ANNOTATION )* activityDef )* '}'
                pass 
                string_literal169=self.match(self.input, 60, self.FOLLOW_60_in_unorderedDef1303) 
                if self._state.backtracking == 0:
                    stream_60.add(string_literal169)
                char_literal170=self.match(self.input, 40, self.FOLLOW_40_in_unorderedDef1305) 
                if self._state.backtracking == 0:
                    stream_40.add(char_literal170)
                # src/SavedFSM/Monitor.g:135:31: ( ( ANNOTATION )* activityDef )*
                while True: #loop46
                    alt46 = 2
                    LA46_0 = self.input.LA(1)

                    if (LA46_0 == RECLABEL or (ANNOTATION <= LA46_0 <= ID) or LA46_0 == 37 or LA46_0 == 40 or LA46_0 == 42 or (47 <= LA46_0 <= 48) or (50 <= LA46_0 <= 55) or LA46_0 == 57 or LA46_0 == 60) :
                        alt46 = 1


                    if alt46 == 1:
                        # src/SavedFSM/Monitor.g:135:33: ( ANNOTATION )* activityDef
                        pass 
                        # src/SavedFSM/Monitor.g:135:33: ( ANNOTATION )*
                        while True: #loop45
                            alt45 = 2
                            LA45_0 = self.input.LA(1)

                            if (LA45_0 == ANNOTATION) :
                                alt45 = 1


                            if alt45 == 1:
                                # src/SavedFSM/Monitor.g:135:35: ANNOTATION
                                pass 
                                ANNOTATION171=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_unorderedDef1311) 
                                if self._state.backtracking == 0:
                                    stream_ANNOTATION.add(ANNOTATION171)


                            else:
                                break #loop45
                        self._state.following.append(self.FOLLOW_activityDef_in_unorderedDef1316)
                        activityDef172 = self.activityDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_activityDef.add(activityDef172.tree)


                    else:
                        break #loop46
                char_literal173=self.match(self.input, 41, self.FOLLOW_41_in_unorderedDef1321) 
                if self._state.backtracking == 0:
                    stream_41.add(char_literal173)

                # AST Rewrite
                # elements: activityDef
                # token labels: 
                # rule labels: retval
                # token list labels: 
                # rule list labels: 
                # wildcard labels: 
                if self._state.backtracking == 0:

                    retval.tree = root_0

                    if retval is not None:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "rule retval", retval.tree)
                    else:
                        stream_retval = RewriteRuleSubtreeStream(self._adaptor, "token retval", None)


                    root_0 = self._adaptor.nil()
                    # 135:68: -> ^( PARALLEL ( ^( BRANCH activityDef ) )+ )
                    # src/SavedFSM/Monitor.g:135:71: ^( PARALLEL ( ^( BRANCH activityDef ) )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(PARALLEL, "PARALLEL"), root_1)

                    # src/SavedFSM/Monitor.g:135:82: ( ^( BRANCH activityDef ) )+
                    if not (stream_activityDef.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_activityDef.hasNext():
                        # src/SavedFSM/Monitor.g:135:82: ^( BRANCH activityDef )
                        root_2 = self._adaptor.nil()
                        root_2 = self._adaptor.becomeRoot(self._adaptor.createFromType(BRANCH, "BRANCH"), root_2)

                        self._adaptor.addChild(root_2, stream_activityDef.nextTree())

                        self._adaptor.addChild(root_1, root_2)


                    stream_activityDef.reset()

                    self._adaptor.addChild(root_0, root_1)



                    retval.tree = root_0



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "unorderedDef"

    class expr_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.expr_return, self).__init__()

            self.tree = None




    # $ANTLR start "expr"
    # src/SavedFSM/Monitor.g:144:1: expr : term ( ( PLUS | MINUS ) term )* ;
    def expr(self, ):

        retval = self.expr_return()
        retval.start = self.input.LT(1)

        root_0 = None

        set175 = None
        term174 = None

        term176 = None


        set175_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:144:6: ( term ( ( PLUS | MINUS ) term )* )
                # src/SavedFSM/Monitor.g:144:8: term ( ( PLUS | MINUS ) term )*
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_term_in_expr1346)
                term174 = self.term()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, term174.tree)
                # src/SavedFSM/Monitor.g:144:13: ( ( PLUS | MINUS ) term )*
                while True: #loop47
                    alt47 = 2
                    LA47_0 = self.input.LA(1)

                    if ((PLUS <= LA47_0 <= MINUS)) :
                        alt47 = 1


                    if alt47 == 1:
                        # src/SavedFSM/Monitor.g:144:15: ( PLUS | MINUS ) term
                        pass 
                        set175 = self.input.LT(1)
                        if (PLUS <= self.input.LA(1) <= MINUS):
                            self.input.consume()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set175))
                            self._state.errorRecovery = False

                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed

                            mse = MismatchedSetException(None, self.input)
                            raise mse


                        self._state.following.append(self.FOLLOW_term_in_expr1361)
                        term176 = self.term()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, term176.tree)


                    else:
                        break #loop47



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "expr"

    class term_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.term_return, self).__init__()

            self.tree = None




    # $ANTLR start "term"
    # src/SavedFSM/Monitor.g:146:1: term : factor ( ( MULT | DIV ) factor )* ;
    def term(self, ):

        retval = self.term_return()
        retval.start = self.input.LT(1)

        root_0 = None

        set178 = None
        factor177 = None

        factor179 = None


        set178_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:146:6: ( factor ( ( MULT | DIV ) factor )* )
                # src/SavedFSM/Monitor.g:146:8: factor ( ( MULT | DIV ) factor )*
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_factor_in_term1373)
                factor177 = self.factor()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, factor177.tree)
                # src/SavedFSM/Monitor.g:146:15: ( ( MULT | DIV ) factor )*
                while True: #loop48
                    alt48 = 2
                    LA48_0 = self.input.LA(1)

                    if ((MULT <= LA48_0 <= DIV)) :
                        alt48 = 1


                    if alt48 == 1:
                        # src/SavedFSM/Monitor.g:146:17: ( MULT | DIV ) factor
                        pass 
                        set178 = self.input.LT(1)
                        if (MULT <= self.input.LA(1) <= DIV):
                            self.input.consume()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set178))
                            self._state.errorRecovery = False

                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed

                            mse = MismatchedSetException(None, self.input)
                            raise mse


                        self._state.following.append(self.FOLLOW_factor_in_term1387)
                        factor179 = self.factor()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, factor179.tree)


                    else:
                        break #loop48



                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "term"

    class factor_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.factor_return, self).__init__()

            self.tree = None




    # $ANTLR start "factor"
    # src/SavedFSM/Monitor.g:148:1: factor : NUMBER ;
    def factor(self, ):

        retval = self.factor_return()
        retval.start = self.input.LT(1)

        root_0 = None

        NUMBER180 = None

        NUMBER180_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:148:8: ( NUMBER )
                # src/SavedFSM/Monitor.g:148:10: NUMBER
                pass 
                root_0 = self._adaptor.nil()

                NUMBER180=self.match(self.input, NUMBER, self.FOLLOW_NUMBER_in_factor1399)
                if self._state.backtracking == 0:

                    NUMBER180_tree = self._adaptor.createWithPayload(NUMBER180)
                    self._adaptor.addChild(root_0, NUMBER180_tree)




                retval.stop = self.input.LT(-1)

                if self._state.backtracking == 0:

                    retval.tree = self._adaptor.rulePostProcessing(root_0)
                    self._adaptor.setTokenBoundaries(retval.tree, retval.start, retval.stop)


            except RecognitionException, re:
                self.reportError(re)
                self.recover(self.input, re)
                retval.tree = self._adaptor.errorNode(self.input, retval.start, self.input.LT(-1), re)
        finally:

            pass
        return retval

    # $ANTLR end "factor"


    # Delegated rules


    # lookup tables for DFA #3

    DFA3_eot = DFA.unpack(
        u"\4\uffff"
        )

    DFA3_eof = DFA.unpack(
        u"\4\uffff"
        )

    DFA3_min = DFA.unpack(
        u"\2\30\2\uffff"
        )

    DFA3_max = DFA.unpack(
        u"\2\42\2\uffff"
        )

    DFA3_accept = DFA.unpack(
        u"\2\uffff\1\2\1\1"
        )

    DFA3_special = DFA.unpack(
        u"\4\uffff"
        )

            
    DFA3_transition = [
        DFA.unpack(u"\1\1\10\uffff\1\3\1\2"),
        DFA.unpack(u"\1\1\10\uffff\1\3\1\2"),
        DFA.unpack(u""),
        DFA.unpack(u"")
    ]

    # class definition for DFA #3

    class DFA3(DFA):
        pass


    # lookup tables for DFA #18

    DFA18_eot = DFA.unpack(
        u"\4\uffff"
        )

    DFA18_eof = DFA.unpack(
        u"\4\uffff"
        )

    DFA18_min = DFA.unpack(
        u"\2\22\2\uffff"
        )

    DFA18_max = DFA.unpack(
        u"\2\74\2\uffff"
        )

    DFA18_accept = DFA.unpack(
        u"\2\uffff\1\2\1\1"
        )

    DFA18_special = DFA.unpack(
        u"\4\uffff"
        )

            
    DFA18_transition = [
        DFA.unpack(u"\1\3\5\uffff\1\1\1\3\10\uffff\1\2\2\uffff\1\3\2\uffff"
        u"\1\3\1\2\1\3\4\uffff\2\3\1\uffff\6\3\1\uffff\1\3\2\uffff\1\3"),
        DFA.unpack(u"\1\3\5\uffff\1\1\1\3\10\uffff\1\2\2\uffff\1\3\2\uffff"
        u"\1\3\1\uffff\1\3\4\uffff\2\3\1\uffff\6\3\1\uffff\1\3\2\uffff\1"
        u"\3"),
        DFA.unpack(u""),
        DFA.unpack(u"")
    ]

    # class definition for DFA #18

    class DFA18(DFA):
        pass


    # lookup tables for DFA #36

    DFA36_eot = DFA.unpack(
        u"\32\uffff"
        )

    DFA36_eof = DFA.unpack(
        u"\1\1\31\uffff"
        )

    DFA36_min = DFA.unpack(
        u"\1\22\1\uffff\1\44\1\31\1\uffff\1\31\2\43\1\5\1\31\1\45\1\5\1\31"
        u"\1\45\6\43\2\5\4\43"
        )

    DFA36_max = DFA.unpack(
        u"\1\74\1\uffff\1\57\1\31\1\uffff\1\31\2\56\1\6\1\31\1\57\1\6\1\31"
        u"\1\57\2\53\1\56\2\53\1\56\2\6\4\53"
        )

    DFA36_accept = DFA.unpack(
        u"\1\uffff\1\2\2\uffff\1\1\25\uffff"
        )

    DFA36_special = DFA.unpack(
        u"\32\uffff"
        )

            
    DFA36_transition = [
        DFA.unpack(u"\1\4\5\uffff\1\4\1\2\13\uffff\1\4\2\uffff\1\4\1\1\1"
        u"\3\4\uffff\2\4\1\uffff\6\4\1\uffff\1\4\2\uffff\1\4"),
        DFA.unpack(u""),
        DFA.unpack(u"\2\4\4\uffff\1\5\2\uffff\1\4\1\1\1\4"),
        DFA.unpack(u"\1\6"),
        DFA.unpack(u""),
        DFA.unpack(u"\1\7"),
        DFA.unpack(u"\1\11\7\uffff\1\12\2\uffff\1\10"),
        DFA.unpack(u"\1\14\7\uffff\1\15\2\uffff\1\13"),
        DFA.unpack(u"\1\16\1\17"),
        DFA.unpack(u"\1\20"),
        DFA.unpack(u"\1\4\10\uffff\1\1\1\4"),
        DFA.unpack(u"\1\21\1\22"),
        DFA.unpack(u"\1\23"),
        DFA.unpack(u"\1\4\10\uffff\1\1\1\4"),
        DFA.unpack(u"\1\11\7\uffff\1\12"),
        DFA.unpack(u"\1\11\7\uffff\1\12"),
        DFA.unpack(u"\1\11\7\uffff\1\12\2\uffff\1\24"),
        DFA.unpack(u"\1\14\7\uffff\1\15"),
        DFA.unpack(u"\1\14\7\uffff\1\15"),
        DFA.unpack(u"\1\14\7\uffff\1\15\2\uffff\1\25"),
        DFA.unpack(u"\1\26\1\27"),
        DFA.unpack(u"\1\30\1\31"),
        DFA.unpack(u"\1\11\7\uffff\1\12"),
        DFA.unpack(u"\1\11\7\uffff\1\12"),
        DFA.unpack(u"\1\14\7\uffff\1\15"),
        DFA.unpack(u"\1\14\7\uffff\1\15")
    ]

    # class definition for DFA #36

    class DFA36(DFA):
        pass


 

    FOLLOW_ANNOTATION_in_description234 = frozenset([24, 33])
    FOLLOW_importProtocolStatement_in_description241 = frozenset([24, 33, 34])
    FOLLOW_importTypeStatement_in_description245 = frozenset([24, 33, 34])
    FOLLOW_ANNOTATION_in_description254 = frozenset([24, 34])
    FOLLOW_protocolDef_in_description259 = frozenset([1])
    FOLLOW_33_in_importProtocolStatement270 = frozenset([34])
    FOLLOW_34_in_importProtocolStatement272 = frozenset([25])
    FOLLOW_importProtocolDef_in_importProtocolStatement274 = frozenset([35, 36])
    FOLLOW_35_in_importProtocolStatement278 = frozenset([25])
    FOLLOW_importProtocolDef_in_importProtocolStatement281 = frozenset([35, 36])
    FOLLOW_36_in_importProtocolStatement286 = frozenset([1])
    FOLLOW_ID_in_importProtocolDef295 = frozenset([37])
    FOLLOW_37_in_importProtocolDef297 = frozenset([26])
    FOLLOW_StringLiteral_in_importProtocolDef300 = frozenset([1])
    FOLLOW_33_in_importTypeStatement313 = frozenset([25, 26])
    FOLLOW_simpleName_in_importTypeStatement317 = frozenset([25, 26])
    FOLLOW_importTypeDef_in_importTypeStatement322 = frozenset([35, 36, 37])
    FOLLOW_35_in_importTypeStatement326 = frozenset([25, 26])
    FOLLOW_importTypeDef_in_importTypeStatement329 = frozenset([35, 36, 37])
    FOLLOW_37_in_importTypeStatement336 = frozenset([26])
    FOLLOW_StringLiteral_in_importTypeStatement339 = frozenset([36])
    FOLLOW_36_in_importTypeStatement344 = frozenset([1])
    FOLLOW_dataTypeDef_in_importTypeDef355 = frozenset([38])
    FOLLOW_38_in_importTypeDef357 = frozenset([25])
    FOLLOW_ID_in_importTypeDef363 = frozenset([1])
    FOLLOW_StringLiteral_in_dataTypeDef371 = frozenset([1])
    FOLLOW_ID_in_simpleName379 = frozenset([1])
    FOLLOW_34_in_protocolDef387 = frozenset([25])
    FOLLOW_protocolName_in_protocolDef389 = frozenset([39, 40, 42])
    FOLLOW_39_in_protocolDef393 = frozenset([25])
    FOLLOW_roleName_in_protocolDef395 = frozenset([40, 42])
    FOLLOW_parameterDefs_in_protocolDef402 = frozenset([40])
    FOLLOW_40_in_protocolDef407 = frozenset([18, 24, 25, 37, 40, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_protocolBlockDef_in_protocolDef409 = frozenset([24, 34, 41])
    FOLLOW_ANNOTATION_in_protocolDef415 = frozenset([24, 34])
    FOLLOW_protocolDef_in_protocolDef420 = frozenset([24, 34, 41])
    FOLLOW_41_in_protocolDef425 = frozenset([1])
    FOLLOW_ID_in_protocolName447 = frozenset([1])
    FOLLOW_42_in_parameterDefs455 = frozenset([25, 44])
    FOLLOW_parameterDef_in_parameterDefs458 = frozenset([35, 43])
    FOLLOW_35_in_parameterDefs462 = frozenset([25, 44])
    FOLLOW_parameterDef_in_parameterDefs465 = frozenset([35, 43])
    FOLLOW_43_in_parameterDefs470 = frozenset([1])
    FOLLOW_typeReferenceDef_in_parameterDef481 = frozenset([25])
    FOLLOW_44_in_parameterDef485 = frozenset([25])
    FOLLOW_simpleName_in_parameterDef489 = frozenset([1])
    FOLLOW_activityListDef_in_protocolBlockDef497 = frozenset([1])
    FOLLOW_40_in_blockDef508 = frozenset([18, 24, 25, 37, 40, 41, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_activityListDef_in_blockDef510 = frozenset([41])
    FOLLOW_41_in_blockDef512 = frozenset([1])
    FOLLOW_ASSERTION_in_assertDef534 = frozenset([1])
    FOLLOW_ANNOTATION_in_activityListDef556 = frozenset([18, 24, 25, 37, 40, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_activityDef_in_activityListDef561 = frozenset([1, 18, 24, 25, 37, 40, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_INT_in_primitivetype577 = frozenset([1])
    FOLLOW_STRING_in_primitivetype583 = frozenset([1])
    FOLLOW_introducesDef_in_activityDef596 = frozenset([36])
    FOLLOW_interactionDef_in_activityDef600 = frozenset([36])
    FOLLOW_inlineDef_in_activityDef604 = frozenset([36])
    FOLLOW_runDef_in_activityDef608 = frozenset([36])
    FOLLOW_recursionDef_in_activityDef612 = frozenset([36])
    FOLLOW_endDef_in_activityDef616 = frozenset([36])
    FOLLOW_RECLABEL_in_activityDef620 = frozenset([36])
    FOLLOW_36_in_activityDef624 = frozenset([1])
    FOLLOW_choiceDef_in_activityDef633 = frozenset([1])
    FOLLOW_directedChoiceDef_in_activityDef637 = frozenset([1])
    FOLLOW_parallelDef_in_activityDef641 = frozenset([1])
    FOLLOW_repeatDef_in_activityDef645 = frozenset([1])
    FOLLOW_unorderedDef_in_activityDef649 = frozenset([1])
    FOLLOW_recBlockDef_in_activityDef656 = frozenset([1])
    FOLLOW_globalEscapeDef_in_activityDef660 = frozenset([1])
    FOLLOW_roleDef_in_introducesDef668 = frozenset([45])
    FOLLOW_45_in_introducesDef670 = frozenset([25])
    FOLLOW_roleDef_in_introducesDef672 = frozenset([1, 35])
    FOLLOW_35_in_introducesDef676 = frozenset([25])
    FOLLOW_roleDef_in_introducesDef678 = frozenset([1, 35])
    FOLLOW_ID_in_roleDef689 = frozenset([1])
    FOLLOW_ID_in_roleName700 = frozenset([1])
    FOLLOW_ID_in_typeReferenceDef711 = frozenset([1])
    FOLLOW_typeReferenceDef_in_interactionSignatureDef722 = frozenset([1, 42])
    FOLLOW_42_in_interactionSignatureDef725 = frozenset([25])
    FOLLOW_valueDecl_in_interactionSignatureDef727 = frozenset([35, 43])
    FOLLOW_35_in_interactionSignatureDef730 = frozenset([25])
    FOLLOW_valueDecl_in_interactionSignatureDef732 = frozenset([35, 43])
    FOLLOW_43_in_interactionSignatureDef736 = frozenset([1])
    FOLLOW_42_in_interactionSignatureDef760 = frozenset([25])
    FOLLOW_valueDecl_in_interactionSignatureDef762 = frozenset([35, 43])
    FOLLOW_35_in_interactionSignatureDef765 = frozenset([25])
    FOLLOW_valueDecl_in_interactionSignatureDef767 = frozenset([35, 43])
    FOLLOW_43_in_interactionSignatureDef771 = frozenset([1])
    FOLLOW_ID_in_valueDecl791 = frozenset([1, 46])
    FOLLOW_46_in_valueDecl794 = frozenset([5, 6])
    FOLLOW_primitivetype_in_valueDecl797 = frozenset([1])
    FOLLOW_valueDecl_in_firstValueDecl808 = frozenset([1])
    FOLLOW_interactionSignatureDef_in_interactionDef823 = frozenset([37, 47])
    FOLLOW_37_in_interactionDef829 = frozenset([25])
    FOLLOW_roleName_in_interactionDef834 = frozenset([27])
    FOLLOW_assertDef_in_interactionDef838 = frozenset([1])
    FOLLOW_47_in_interactionDef862 = frozenset([25])
    FOLLOW_roleName_in_interactionDef864 = frozenset([27])
    FOLLOW_assertDef_in_interactionDef868 = frozenset([1])
    FOLLOW_48_in_choiceDef889 = frozenset([39, 40])
    FOLLOW_39_in_choiceDef893 = frozenset([25])
    FOLLOW_roleName_in_choiceDef895 = frozenset([39, 40])
    FOLLOW_blockDef_in_choiceDef900 = frozenset([1, 49])
    FOLLOW_49_in_choiceDef904 = frozenset([39, 40])
    FOLLOW_blockDef_in_choiceDef906 = frozenset([1, 49])
    FOLLOW_37_in_directedChoiceDef927 = frozenset([25])
    FOLLOW_roleName_in_directedChoiceDef929 = frozenset([40, 47])
    FOLLOW_47_in_directedChoiceDef936 = frozenset([25])
    FOLLOW_roleName_in_directedChoiceDef938 = frozenset([35, 40])
    FOLLOW_35_in_directedChoiceDef942 = frozenset([25])
    FOLLOW_roleName_in_directedChoiceDef945 = frozenset([35, 40])
    FOLLOW_40_in_directedChoiceDef953 = frozenset([25, 42])
    FOLLOW_onMessageDef_in_directedChoiceDef957 = frozenset([25, 41, 42])
    FOLLOW_41_in_directedChoiceDef962 = frozenset([1])
    FOLLOW_interactionSignatureDef_in_onMessageDef969 = frozenset([46])
    FOLLOW_46_in_onMessageDef971 = frozenset([18, 24, 25, 37, 40, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_activityList_in_onMessageDef973 = frozenset([1])
    FOLLOW_ANNOTATION_in_activityList986 = frozenset([18, 24, 25, 37, 40, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_activityDef_in_activityList991 = frozenset([1, 18, 24, 25, 37, 40, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_50_in_repeatDef1001 = frozenset([39, 40])
    FOLLOW_39_in_repeatDef1005 = frozenset([25])
    FOLLOW_roleName_in_repeatDef1007 = frozenset([35, 39, 40])
    FOLLOW_35_in_repeatDef1011 = frozenset([25])
    FOLLOW_roleName_in_repeatDef1013 = frozenset([35, 39, 40])
    FOLLOW_blockDef_in_repeatDef1021 = frozenset([1])
    FOLLOW_51_in_recBlockDef1037 = frozenset([25])
    FOLLOW_labelName_in_recBlockDef1039 = frozenset([39, 40])
    FOLLOW_blockDef_in_recBlockDef1041 = frozenset([1])
    FOLLOW_ID_in_labelName1058 = frozenset([1])
    FOLLOW_labelName_in_recursionDef1070 = frozenset([1])
    FOLLOW_52_in_endDef1086 = frozenset([1])
    FOLLOW_53_in_runDef1096 = frozenset([25])
    FOLLOW_protocolRefDef_in_runDef1099 = frozenset([37, 42])
    FOLLOW_42_in_runDef1103 = frozenset([25])
    FOLLOW_parameter_in_runDef1106 = frozenset([35, 43])
    FOLLOW_35_in_runDef1110 = frozenset([25])
    FOLLOW_parameter_in_runDef1113 = frozenset([35, 43])
    FOLLOW_43_in_runDef1118 = frozenset([37])
    FOLLOW_37_in_runDef1124 = frozenset([25])
    FOLLOW_roleName_in_runDef1126 = frozenset([1])
    FOLLOW_ID_in_protocolRefDef1134 = frozenset([1, 39])
    FOLLOW_39_in_protocolRefDef1138 = frozenset([25])
    FOLLOW_roleName_in_protocolRefDef1140 = frozenset([1])
    FOLLOW_ID_in_declarationName1151 = frozenset([1])
    FOLLOW_declarationName_in_parameter1159 = frozenset([1])
    FOLLOW_54_in_inlineDef1168 = frozenset([25])
    FOLLOW_protocolRefDef_in_inlineDef1171 = frozenset([1, 42])
    FOLLOW_42_in_inlineDef1175 = frozenset([25])
    FOLLOW_parameter_in_inlineDef1178 = frozenset([35, 43])
    FOLLOW_35_in_inlineDef1182 = frozenset([25])
    FOLLOW_parameter_in_inlineDef1185 = frozenset([35, 43])
    FOLLOW_43_in_inlineDef1190 = frozenset([1])
    FOLLOW_55_in_parallelDef1202 = frozenset([39, 40])
    FOLLOW_blockDef_in_parallelDef1204 = frozenset([1, 56])
    FOLLOW_56_in_parallelDef1208 = frozenset([39, 40])
    FOLLOW_blockDef_in_parallelDef1210 = frozenset([1, 56])
    FOLLOW_57_in_doBlockDef1230 = frozenset([40])
    FOLLOW_40_in_doBlockDef1232 = frozenset([18, 24, 25, 37, 40, 41, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_activityListDef_in_doBlockDef1234 = frozenset([41])
    FOLLOW_41_in_doBlockDef1237 = frozenset([1])
    FOLLOW_58_in_interruptDef1255 = frozenset([59])
    FOLLOW_59_in_interruptDef1257 = frozenset([25])
    FOLLOW_roleName_in_interruptDef1259 = frozenset([40])
    FOLLOW_40_in_interruptDef1261 = frozenset([18, 24, 25, 37, 40, 41, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_activityListDef_in_interruptDef1263 = frozenset([41])
    FOLLOW_41_in_interruptDef1265 = frozenset([1])
    FOLLOW_doBlockDef_in_globalEscapeDef1283 = frozenset([58])
    FOLLOW_interruptDef_in_globalEscapeDef1286 = frozenset([1])
    FOLLOW_60_in_unorderedDef1303 = frozenset([40])
    FOLLOW_40_in_unorderedDef1305 = frozenset([18, 24, 25, 37, 40, 41, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_ANNOTATION_in_unorderedDef1311 = frozenset([18, 24, 25, 37, 40, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_activityDef_in_unorderedDef1316 = frozenset([18, 24, 25, 37, 40, 41, 42, 47, 48, 50, 51, 52, 53, 54, 55, 57, 60])
    FOLLOW_41_in_unorderedDef1321 = frozenset([1])
    FOLLOW_term_in_expr1346 = frozenset([1, 7, 8])
    FOLLOW_set_in_expr1350 = frozenset([28])
    FOLLOW_term_in_expr1361 = frozenset([1, 7, 8])
    FOLLOW_factor_in_term1373 = frozenset([1, 9, 10])
    FOLLOW_set_in_term1377 = frozenset([28])
    FOLLOW_factor_in_term1387 = frozenset([1, 9, 10])
    FOLLOW_NUMBER_in_factor1399 = frozenset([1])



def main(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    from antlr3.main import ParserMain
    main = ParserMain("MonitorLexer", MonitorParser)
    main.stdin = stdin
    main.stdout = stdout
    main.stderr = stderr
    main.execute(argv)


if __name__ == '__main__':
    main(sys.argv)
