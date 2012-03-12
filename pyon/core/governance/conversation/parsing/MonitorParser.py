# $ANTLR 3.1.3 Mar 18, 2009 10:09:25 src/SavedFSM/Monitor.g 2012-03-12 22:09:37

import sys
from antlr3 import *
from antlr3.compat import set, frozenset

from antlr3.tree import *



# for convenience in actions
HIDDEN = BaseRecognizer.HIDDEN

# token types
RESV=12
ANNOTATION=25
ASSERTION=28
PARALLEL=19
ID=26
T__61=61
EOF=-1
T__60=60
PROTOCOL=20
TYPE=14
T__55=55
ML_COMMENT=32
T__56=56
INTERACTION=4
T__57=57
ROLES=24
T__58=58
T__51=51
T__52=52
T__53=53
T__54=54
T__59=59
FULLSTOP=11
PLUS=7
SEND=13
DIGIT=30
T__50=50
T__42=42
T__43=43
T__40=40
T__41=41
T__46=46
T__47=47
T__44=44
T__45=45
LINE_COMMENT=33
T__48=48
T__49=49
RECLABEL=18
NUMBER=29
WHITESPACE=31
INT=5
MINUS=8
MULT=9
VALUE=15
ASSERT=21
UNORDERED=17
EMPTY=23
StringLiteral=27
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
    "PARALLEL", "PROTOCOL", "ASSERT", "GLOBAL_ESCAPE", "EMPTY", "ROLES", 
    "ANNOTATION", "ID", "StringLiteral", "ASSERTION", "NUMBER", "DIGIT", 
    "WHITESPACE", "ML_COMMENT", "LINE_COMMENT", "'import'", "'protocol'", 
    "','", "';'", "'from'", "'as'", "'at'", "'{'", "'}'", "'('", "')'", 
    "'role'", "'introduces'", "':'", "'to'", "'choice'", "'or'", "'repeat'", 
    "'rec'", "'end'", "'run'", "'inline'", "'parallel'", "'and'", "'do'", 
    "'interrupt'", "'by'", "'unordered'"
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

        self.dfa17 = self.DFA17(
            self, 17,
            eot = self.DFA17_eot,
            eof = self.DFA17_eof,
            min = self.DFA17_min,
            max = self.DFA17_max,
            accept = self.DFA17_accept,
            special = self.DFA17_special,
            transition = self.DFA17_transition
            )

        self.dfa35 = self.DFA35(
            self, 35,
            eot = self.DFA35_eot,
            eof = self.DFA35_eof,
            min = self.DFA35_min,
            max = self.DFA35_max,
            accept = self.DFA35_accept,
            special = self.DFA35_special,
            transition = self.DFA35_transition
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
                                ANNOTATION1=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_description241) 
                                if self._state.backtracking == 0:
                                    stream_ANNOTATION.add(ANNOTATION1)


                            else:
                                break #loop1
                        # src/SavedFSM/Monitor.g:39:32: ( importProtocolStatement | importTypeStatement )
                        alt2 = 2
                        LA2_0 = self.input.LA(1)

                        if (LA2_0 == 34) :
                            LA2_1 = self.input.LA(2)

                            if (LA2_1 == 35) :
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
                            self._state.following.append(self.FOLLOW_importProtocolStatement_in_description248)
                            importProtocolStatement2 = self.importProtocolStatement()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                stream_importProtocolStatement.add(importProtocolStatement2.tree)


                        elif alt2 == 2:
                            # src/SavedFSM/Monitor.g:39:60: importTypeStatement
                            pass 
                            self._state.following.append(self.FOLLOW_importTypeStatement_in_description252)
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
                        ANNOTATION4=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_description261) 
                        if self._state.backtracking == 0:
                            stream_ANNOTATION.add(ANNOTATION4)


                    else:
                        break #loop4
                self._state.following.append(self.FOLLOW_protocolDef_in_description266)
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

                string_literal6=self.match(self.input, 34, self.FOLLOW_34_in_importProtocolStatement277)
                if self._state.backtracking == 0:

                    string_literal6_tree = self._adaptor.createWithPayload(string_literal6)
                    self._adaptor.addChild(root_0, string_literal6_tree)

                string_literal7=self.match(self.input, 35, self.FOLLOW_35_in_importProtocolStatement279)
                if self._state.backtracking == 0:

                    string_literal7_tree = self._adaptor.createWithPayload(string_literal7)
                    self._adaptor.addChild(root_0, string_literal7_tree)

                self._state.following.append(self.FOLLOW_importProtocolDef_in_importProtocolStatement281)
                importProtocolDef8 = self.importProtocolDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, importProtocolDef8.tree)
                # src/SavedFSM/Monitor.g:41:64: ( ',' importProtocolDef )*
                while True: #loop5
                    alt5 = 2
                    LA5_0 = self.input.LA(1)

                    if (LA5_0 == 36) :
                        alt5 = 1


                    if alt5 == 1:
                        # src/SavedFSM/Monitor.g:41:66: ',' importProtocolDef
                        pass 
                        char_literal9=self.match(self.input, 36, self.FOLLOW_36_in_importProtocolStatement285)
                        self._state.following.append(self.FOLLOW_importProtocolDef_in_importProtocolStatement288)
                        importProtocolDef10 = self.importProtocolDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, importProtocolDef10.tree)


                    else:
                        break #loop5
                char_literal11=self.match(self.input, 37, self.FOLLOW_37_in_importProtocolStatement293)



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

                ID12=self.match(self.input, ID, self.FOLLOW_ID_in_importProtocolDef302)
                if self._state.backtracking == 0:

                    ID12_tree = self._adaptor.createWithPayload(ID12)
                    self._adaptor.addChild(root_0, ID12_tree)

                string_literal13=self.match(self.input, 38, self.FOLLOW_38_in_importProtocolDef304)
                StringLiteral14=self.match(self.input, StringLiteral, self.FOLLOW_StringLiteral_in_importProtocolDef307)
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

                string_literal15=self.match(self.input, 34, self.FOLLOW_34_in_importTypeStatement320)
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
                    self._state.following.append(self.FOLLOW_simpleName_in_importTypeStatement324)
                    simpleName16 = self.simpleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, simpleName16.tree)



                self._state.following.append(self.FOLLOW_importTypeDef_in_importTypeStatement329)
                importTypeDef17 = self.importTypeDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, importTypeDef17.tree)
                # src/SavedFSM/Monitor.g:45:61: ( ',' importTypeDef )*
                while True: #loop7
                    alt7 = 2
                    LA7_0 = self.input.LA(1)

                    if (LA7_0 == 36) :
                        alt7 = 1


                    if alt7 == 1:
                        # src/SavedFSM/Monitor.g:45:63: ',' importTypeDef
                        pass 
                        char_literal18=self.match(self.input, 36, self.FOLLOW_36_in_importTypeStatement333)
                        self._state.following.append(self.FOLLOW_importTypeDef_in_importTypeStatement336)
                        importTypeDef19 = self.importTypeDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, importTypeDef19.tree)


                    else:
                        break #loop7
                # src/SavedFSM/Monitor.g:45:85: ( 'from' StringLiteral )?
                alt8 = 2
                LA8_0 = self.input.LA(1)

                if (LA8_0 == 38) :
                    alt8 = 1
                if alt8 == 1:
                    # src/SavedFSM/Monitor.g:45:87: 'from' StringLiteral
                    pass 
                    string_literal20=self.match(self.input, 38, self.FOLLOW_38_in_importTypeStatement343)
                    StringLiteral21=self.match(self.input, StringLiteral, self.FOLLOW_StringLiteral_in_importTypeStatement346)
                    if self._state.backtracking == 0:

                        StringLiteral21_tree = self._adaptor.createWithPayload(StringLiteral21)
                        self._adaptor.addChild(root_0, StringLiteral21_tree)




                char_literal22=self.match(self.input, 37, self.FOLLOW_37_in_importTypeStatement351)



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
                    self._state.following.append(self.FOLLOW_dataTypeDef_in_importTypeDef362)
                    dataTypeDef23 = self.dataTypeDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, dataTypeDef23.tree)
                    string_literal24=self.match(self.input, 39, self.FOLLOW_39_in_importTypeDef364)



                ID25=self.match(self.input, ID, self.FOLLOW_ID_in_importTypeDef370)
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

                StringLiteral26=self.match(self.input, StringLiteral, self.FOLLOW_StringLiteral_in_dataTypeDef378)
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

                ID27=self.match(self.input, ID, self.FOLLOW_ID_in_simpleName386)
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
    # src/SavedFSM/Monitor.g:53:1: protocolDef : 'protocol' protocolName ( 'at' roleName )? ( parameterDefs )? '{' protocolBlockDef ( ( ANNOTATION )* protocolDef )* '}' -> ^( PROTOCOL roleName ( parameterDefs )* ( protocolBlockDef )+ ) ;
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
        stream_42 = RewriteRuleTokenStream(self._adaptor, "token 42")
        stream_41 = RewriteRuleTokenStream(self._adaptor, "token 41")
        stream_40 = RewriteRuleTokenStream(self._adaptor, "token 40")
        stream_35 = RewriteRuleTokenStream(self._adaptor, "token 35")
        stream_ANNOTATION = RewriteRuleTokenStream(self._adaptor, "token ANNOTATION")
        stream_parameterDefs = RewriteRuleSubtreeStream(self._adaptor, "rule parameterDefs")
        stream_protocolDef = RewriteRuleSubtreeStream(self._adaptor, "rule protocolDef")
        stream_protocolName = RewriteRuleSubtreeStream(self._adaptor, "rule protocolName")
        stream_protocolBlockDef = RewriteRuleSubtreeStream(self._adaptor, "rule protocolBlockDef")
        stream_roleName = RewriteRuleSubtreeStream(self._adaptor, "rule roleName")
        try:
            try:
                # src/SavedFSM/Monitor.g:53:12: ( 'protocol' protocolName ( 'at' roleName )? ( parameterDefs )? '{' protocolBlockDef ( ( ANNOTATION )* protocolDef )* '}' -> ^( PROTOCOL roleName ( parameterDefs )* ( protocolBlockDef )+ ) )
                # src/SavedFSM/Monitor.g:53:14: 'protocol' protocolName ( 'at' roleName )? ( parameterDefs )? '{' protocolBlockDef ( ( ANNOTATION )* protocolDef )* '}'
                pass 
                string_literal28=self.match(self.input, 35, self.FOLLOW_35_in_protocolDef394) 
                if self._state.backtracking == 0:
                    stream_35.add(string_literal28)
                self._state.following.append(self.FOLLOW_protocolName_in_protocolDef396)
                protocolName29 = self.protocolName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_protocolName.add(protocolName29.tree)
                # src/SavedFSM/Monitor.g:53:38: ( 'at' roleName )?
                alt10 = 2
                LA10_0 = self.input.LA(1)

                if (LA10_0 == 40) :
                    alt10 = 1
                if alt10 == 1:
                    # src/SavedFSM/Monitor.g:53:40: 'at' roleName
                    pass 
                    string_literal30=self.match(self.input, 40, self.FOLLOW_40_in_protocolDef400) 
                    if self._state.backtracking == 0:
                        stream_40.add(string_literal30)
                    self._state.following.append(self.FOLLOW_roleName_in_protocolDef402)
                    roleName31 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_roleName.add(roleName31.tree)



                # src/SavedFSM/Monitor.g:53:57: ( parameterDefs )?
                alt11 = 2
                LA11_0 = self.input.LA(1)

                if (LA11_0 == 43) :
                    alt11 = 1
                if alt11 == 1:
                    # src/SavedFSM/Monitor.g:53:59: parameterDefs
                    pass 
                    self._state.following.append(self.FOLLOW_parameterDefs_in_protocolDef409)
                    parameterDefs32 = self.parameterDefs()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_parameterDefs.add(parameterDefs32.tree)



                char_literal33=self.match(self.input, 41, self.FOLLOW_41_in_protocolDef414) 
                if self._state.backtracking == 0:
                    stream_41.add(char_literal33)
                self._state.following.append(self.FOLLOW_protocolBlockDef_in_protocolDef416)
                protocolBlockDef34 = self.protocolBlockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_protocolBlockDef.add(protocolBlockDef34.tree)
                # src/SavedFSM/Monitor.g:53:97: ( ( ANNOTATION )* protocolDef )*
                while True: #loop13
                    alt13 = 2
                    LA13_0 = self.input.LA(1)

                    if (LA13_0 == ANNOTATION or LA13_0 == 35) :
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
                                ANNOTATION35=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_protocolDef422) 
                                if self._state.backtracking == 0:
                                    stream_ANNOTATION.add(ANNOTATION35)


                            else:
                                break #loop12
                        self._state.following.append(self.FOLLOW_protocolDef_in_protocolDef427)
                        protocolDef36 = self.protocolDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_protocolDef.add(protocolDef36.tree)


                    else:
                        break #loop13
                char_literal37=self.match(self.input, 42, self.FOLLOW_42_in_protocolDef432) 
                if self._state.backtracking == 0:
                    stream_42.add(char_literal37)

                # AST Rewrite
                # elements: parameterDefs, roleName, protocolBlockDef
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
                    # 54:7: -> ^( PROTOCOL roleName ( parameterDefs )* ( protocolBlockDef )+ )
                    # src/SavedFSM/Monitor.g:54:10: ^( PROTOCOL roleName ( parameterDefs )* ( protocolBlockDef )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(PROTOCOL, "PROTOCOL"), root_1)

                    self._adaptor.addChild(root_1, stream_roleName.nextTree())
                    # src/SavedFSM/Monitor.g:54:31: ( parameterDefs )*
                    while stream_parameterDefs.hasNext():
                        self._adaptor.addChild(root_1, stream_parameterDefs.nextTree())


                    stream_parameterDefs.reset();
                    # src/SavedFSM/Monitor.g:54:46: ( protocolBlockDef )+
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

                ID38=self.match(self.input, ID, self.FOLLOW_ID_in_protocolName460)
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
    # src/SavedFSM/Monitor.g:58:1: parameterDefs : '(' roleparameDef ( ',' roleparameDef )* ')' -> ^( ROLES ( roleparameDef )+ ) ;
    def parameterDefs(self, ):

        retval = self.parameterDefs_return()
        retval.start = self.input.LT(1)

        root_0 = None

        char_literal39 = None
        char_literal41 = None
        char_literal43 = None
        roleparameDef40 = None

        roleparameDef42 = None


        char_literal39_tree = None
        char_literal41_tree = None
        char_literal43_tree = None
        stream_43 = RewriteRuleTokenStream(self._adaptor, "token 43")
        stream_44 = RewriteRuleTokenStream(self._adaptor, "token 44")
        stream_36 = RewriteRuleTokenStream(self._adaptor, "token 36")
        stream_roleparameDef = RewriteRuleSubtreeStream(self._adaptor, "rule roleparameDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:58:14: ( '(' roleparameDef ( ',' roleparameDef )* ')' -> ^( ROLES ( roleparameDef )+ ) )
                # src/SavedFSM/Monitor.g:58:16: '(' roleparameDef ( ',' roleparameDef )* ')'
                pass 
                char_literal39=self.match(self.input, 43, self.FOLLOW_43_in_parameterDefs468) 
                if self._state.backtracking == 0:
                    stream_43.add(char_literal39)
                self._state.following.append(self.FOLLOW_roleparameDef_in_parameterDefs470)
                roleparameDef40 = self.roleparameDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_roleparameDef.add(roleparameDef40.tree)
                # src/SavedFSM/Monitor.g:58:34: ( ',' roleparameDef )*
                while True: #loop14
                    alt14 = 2
                    LA14_0 = self.input.LA(1)

                    if (LA14_0 == 36) :
                        alt14 = 1


                    if alt14 == 1:
                        # src/SavedFSM/Monitor.g:58:36: ',' roleparameDef
                        pass 
                        char_literal41=self.match(self.input, 36, self.FOLLOW_36_in_parameterDefs474) 
                        if self._state.backtracking == 0:
                            stream_36.add(char_literal41)
                        self._state.following.append(self.FOLLOW_roleparameDef_in_parameterDefs476)
                        roleparameDef42 = self.roleparameDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_roleparameDef.add(roleparameDef42.tree)


                    else:
                        break #loop14
                char_literal43=self.match(self.input, 44, self.FOLLOW_44_in_parameterDefs481) 
                if self._state.backtracking == 0:
                    stream_44.add(char_literal43)

                # AST Rewrite
                # elements: roleparameDef
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
                    # 58:61: -> ^( ROLES ( roleparameDef )+ )
                    # src/SavedFSM/Monitor.g:58:64: ^( ROLES ( roleparameDef )+ )
                    root_1 = self._adaptor.nil()
                    root_1 = self._adaptor.becomeRoot(self._adaptor.createFromType(ROLES, "ROLES"), root_1)

                    # src/SavedFSM/Monitor.g:58:72: ( roleparameDef )+
                    if not (stream_roleparameDef.hasNext()):
                        raise RewriteEarlyExitException()

                    while stream_roleparameDef.hasNext():
                        self._adaptor.addChild(root_1, stream_roleparameDef.nextTree())


                    stream_roleparameDef.reset()

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

    # $ANTLR end "parameterDefs"

    class roleparameDef_return(ParserRuleReturnScope):
        def __init__(self):
            super(MonitorParser.roleparameDef_return, self).__init__()

            self.tree = None




    # $ANTLR start "roleparameDef"
    # src/SavedFSM/Monitor.g:60:1: roleparameDef : 'role' simpleName -> simpleName ;
    def roleparameDef(self, ):

        retval = self.roleparameDef_return()
        retval.start = self.input.LT(1)

        root_0 = None

        string_literal44 = None
        simpleName45 = None


        string_literal44_tree = None
        stream_45 = RewriteRuleTokenStream(self._adaptor, "token 45")
        stream_simpleName = RewriteRuleSubtreeStream(self._adaptor, "rule simpleName")
        try:
            try:
                # src/SavedFSM/Monitor.g:60:14: ( 'role' simpleName -> simpleName )
                # src/SavedFSM/Monitor.g:60:16: 'role' simpleName
                pass 
                string_literal44=self.match(self.input, 45, self.FOLLOW_45_in_roleparameDef497) 
                if self._state.backtracking == 0:
                    stream_45.add(string_literal44)
                self._state.following.append(self.FOLLOW_simpleName_in_roleparameDef499)
                simpleName45 = self.simpleName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_simpleName.add(simpleName45.tree)

                # AST Rewrite
                # elements: simpleName
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
                    # 60:34: -> simpleName
                    self._adaptor.addChild(root_0, stream_simpleName.nextTree())



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

    # $ANTLR end "roleparameDef"

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

        activityListDef46 = None


        stream_activityListDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityListDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:62:17: ( activityListDef -> activityListDef )
                # src/SavedFSM/Monitor.g:62:19: activityListDef
                pass 
                self._state.following.append(self.FOLLOW_activityListDef_in_protocolBlockDef510)
                activityListDef46 = self.activityListDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_activityListDef.add(activityListDef46.tree)

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

        char_literal47 = None
        char_literal49 = None
        activityListDef48 = None


        char_literal47_tree = None
        char_literal49_tree = None
        stream_42 = RewriteRuleTokenStream(self._adaptor, "token 42")
        stream_41 = RewriteRuleTokenStream(self._adaptor, "token 41")
        stream_activityListDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityListDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:64:9: ( '{' activityListDef '}' -> ^( BRANCH activityListDef ) )
                # src/SavedFSM/Monitor.g:64:11: '{' activityListDef '}'
                pass 
                char_literal47=self.match(self.input, 41, self.FOLLOW_41_in_blockDef521) 
                if self._state.backtracking == 0:
                    stream_41.add(char_literal47)
                self._state.following.append(self.FOLLOW_activityListDef_in_blockDef523)
                activityListDef48 = self.activityListDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_activityListDef.add(activityListDef48.tree)
                char_literal49=self.match(self.input, 42, self.FOLLOW_42_in_blockDef525) 
                if self._state.backtracking == 0:
                    stream_42.add(char_literal49)

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

        ASSERTION50 = None

        ASSERTION50_tree = None
        stream_ASSERTION = RewriteRuleTokenStream(self._adaptor, "token ASSERTION")

        try:
            try:
                # src/SavedFSM/Monitor.g:66:11: ( ( ASSERTION )? -> ^( ASSERT ( ASSERTION )? ) )
                # src/SavedFSM/Monitor.g:66:13: ( ASSERTION )?
                pass 
                # src/SavedFSM/Monitor.g:66:13: ( ASSERTION )?
                alt15 = 2
                LA15_0 = self.input.LA(1)

                if (LA15_0 == ASSERTION) :
                    alt15 = 1
                if alt15 == 1:
                    # src/SavedFSM/Monitor.g:66:14: ASSERTION
                    pass 
                    ASSERTION50=self.match(self.input, ASSERTION, self.FOLLOW_ASSERTION_in_assertDef547) 
                    if self._state.backtracking == 0:
                        stream_ASSERTION.add(ASSERTION50)




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

        ANNOTATION51 = None
        activityDef52 = None


        ANNOTATION51_tree = None
        stream_ANNOTATION = RewriteRuleTokenStream(self._adaptor, "token ANNOTATION")
        stream_activityDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:68:16: ( ( ( ANNOTATION )* activityDef )* -> ( activityDef )+ )
                # src/SavedFSM/Monitor.g:68:18: ( ( ANNOTATION )* activityDef )*
                pass 
                # src/SavedFSM/Monitor.g:68:18: ( ( ANNOTATION )* activityDef )*
                while True: #loop17
                    alt17 = 2
                    alt17 = self.dfa17.predict(self.input)
                    if alt17 == 1:
                        # src/SavedFSM/Monitor.g:68:20: ( ANNOTATION )* activityDef
                        pass 
                        # src/SavedFSM/Monitor.g:68:20: ( ANNOTATION )*
                        while True: #loop16
                            alt16 = 2
                            LA16_0 = self.input.LA(1)

                            if (LA16_0 == ANNOTATION) :
                                alt16 = 1


                            if alt16 == 1:
                                # src/SavedFSM/Monitor.g:68:22: ANNOTATION
                                pass 
                                ANNOTATION51=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_activityListDef569) 
                                if self._state.backtracking == 0:
                                    stream_ANNOTATION.add(ANNOTATION51)


                            else:
                                break #loop16
                        self._state.following.append(self.FOLLOW_activityDef_in_activityListDef574)
                        activityDef52 = self.activityDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_activityDef.add(activityDef52.tree)


                    else:
                        break #loop17

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

        INT53 = None
        STRING54 = None

        INT53_tree = None
        STRING54_tree = None
        stream_INT = RewriteRuleTokenStream(self._adaptor, "token INT")
        stream_STRING = RewriteRuleTokenStream(self._adaptor, "token STRING")

        try:
            try:
                # src/SavedFSM/Monitor.g:70:15: ( ( INT -> INT | STRING -> STRING ) )
                # src/SavedFSM/Monitor.g:70:16: ( INT -> INT | STRING -> STRING )
                pass 
                # src/SavedFSM/Monitor.g:70:16: ( INT -> INT | STRING -> STRING )
                alt18 = 2
                LA18_0 = self.input.LA(1)

                if (LA18_0 == INT) :
                    alt18 = 1
                elif (LA18_0 == STRING) :
                    alt18 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed

                    nvae = NoViableAltException("", 18, 0, self.input)

                    raise nvae

                if alt18 == 1:
                    # src/SavedFSM/Monitor.g:70:17: INT
                    pass 
                    INT53=self.match(self.input, INT, self.FOLLOW_INT_in_primitivetype590) 
                    if self._state.backtracking == 0:
                        stream_INT.add(INT53)

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


                elif alt18 == 2:
                    # src/SavedFSM/Monitor.g:70:28: STRING
                    pass 
                    STRING54=self.match(self.input, STRING, self.FOLLOW_STRING_in_primitivetype596) 
                    if self._state.backtracking == 0:
                        stream_STRING.add(STRING54)

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

        RECLABEL61 = None
        char_literal62 = None
        introducesDef55 = None

        interactionDef56 = None

        inlineDef57 = None

        runDef58 = None

        recursionDef59 = None

        endDef60 = None

        choiceDef63 = None

        directedChoiceDef64 = None

        parallelDef65 = None

        repeatDef66 = None

        unorderedDef67 = None

        recBlockDef68 = None

        globalEscapeDef69 = None


        RECLABEL61_tree = None
        char_literal62_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:72:12: ( ( introducesDef | interactionDef | inlineDef | runDef | recursionDef | endDef | RECLABEL ) ';' | choiceDef | directedChoiceDef | parallelDef | repeatDef | unorderedDef | recBlockDef | globalEscapeDef )
                alt20 = 8
                LA20 = self.input.LA(1)
                if LA20 == RECLABEL or LA20 == ID or LA20 == 43 or LA20 == 53 or LA20 == 54 or LA20 == 55:
                    alt20 = 1
                elif LA20 == 49:
                    alt20 = 2
                elif LA20 == 38 or LA20 == 41 or LA20 == 48:
                    alt20 = 3
                elif LA20 == 56:
                    alt20 = 4
                elif LA20 == 51:
                    alt20 = 5
                elif LA20 == 61:
                    alt20 = 6
                elif LA20 == 52:
                    alt20 = 7
                elif LA20 == 58:
                    alt20 = 8
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed

                    nvae = NoViableAltException("", 20, 0, self.input)

                    raise nvae

                if alt20 == 1:
                    # src/SavedFSM/Monitor.g:72:14: ( introducesDef | interactionDef | inlineDef | runDef | recursionDef | endDef | RECLABEL ) ';'
                    pass 
                    root_0 = self._adaptor.nil()

                    # src/SavedFSM/Monitor.g:72:14: ( introducesDef | interactionDef | inlineDef | runDef | recursionDef | endDef | RECLABEL )
                    alt19 = 7
                    LA19 = self.input.LA(1)
                    if LA19 == ID:
                        LA19 = self.input.LA(2)
                        if LA19 == 37:
                            alt19 = 5
                        elif LA19 == 46:
                            alt19 = 1
                        elif LA19 == 38 or LA19 == 43 or LA19 == 48:
                            alt19 = 2
                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed

                            nvae = NoViableAltException("", 19, 1, self.input)

                            raise nvae

                    elif LA19 == 43:
                        alt19 = 2
                    elif LA19 == 55:
                        alt19 = 3
                    elif LA19 == 54:
                        alt19 = 4
                    elif LA19 == 53:
                        alt19 = 6
                    elif LA19 == RECLABEL:
                        alt19 = 7
                    else:
                        if self._state.backtracking > 0:
                            raise BacktrackingFailed

                        nvae = NoViableAltException("", 19, 0, self.input)

                        raise nvae

                    if alt19 == 1:
                        # src/SavedFSM/Monitor.g:72:16: introducesDef
                        pass 
                        self._state.following.append(self.FOLLOW_introducesDef_in_activityDef609)
                        introducesDef55 = self.introducesDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, introducesDef55.tree)


                    elif alt19 == 2:
                        # src/SavedFSM/Monitor.g:72:32: interactionDef
                        pass 
                        self._state.following.append(self.FOLLOW_interactionDef_in_activityDef613)
                        interactionDef56 = self.interactionDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, interactionDef56.tree)


                    elif alt19 == 3:
                        # src/SavedFSM/Monitor.g:72:49: inlineDef
                        pass 
                        self._state.following.append(self.FOLLOW_inlineDef_in_activityDef617)
                        inlineDef57 = self.inlineDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, inlineDef57.tree)


                    elif alt19 == 4:
                        # src/SavedFSM/Monitor.g:72:61: runDef
                        pass 
                        self._state.following.append(self.FOLLOW_runDef_in_activityDef621)
                        runDef58 = self.runDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, runDef58.tree)


                    elif alt19 == 5:
                        # src/SavedFSM/Monitor.g:72:70: recursionDef
                        pass 
                        self._state.following.append(self.FOLLOW_recursionDef_in_activityDef625)
                        recursionDef59 = self.recursionDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, recursionDef59.tree)


                    elif alt19 == 6:
                        # src/SavedFSM/Monitor.g:72:85: endDef
                        pass 
                        self._state.following.append(self.FOLLOW_endDef_in_activityDef629)
                        endDef60 = self.endDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, endDef60.tree)


                    elif alt19 == 7:
                        # src/SavedFSM/Monitor.g:72:94: RECLABEL
                        pass 
                        RECLABEL61=self.match(self.input, RECLABEL, self.FOLLOW_RECLABEL_in_activityDef633)
                        if self._state.backtracking == 0:

                            RECLABEL61_tree = self._adaptor.createWithPayload(RECLABEL61)
                            self._adaptor.addChild(root_0, RECLABEL61_tree)




                    char_literal62=self.match(self.input, 37, self.FOLLOW_37_in_activityDef637)


                elif alt20 == 2:
                    # src/SavedFSM/Monitor.g:73:4: choiceDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_choiceDef_in_activityDef646)
                    choiceDef63 = self.choiceDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, choiceDef63.tree)


                elif alt20 == 3:
                    # src/SavedFSM/Monitor.g:73:16: directedChoiceDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_directedChoiceDef_in_activityDef650)
                    directedChoiceDef64 = self.directedChoiceDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, directedChoiceDef64.tree)


                elif alt20 == 4:
                    # src/SavedFSM/Monitor.g:73:36: parallelDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_parallelDef_in_activityDef654)
                    parallelDef65 = self.parallelDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, parallelDef65.tree)


                elif alt20 == 5:
                    # src/SavedFSM/Monitor.g:73:50: repeatDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_repeatDef_in_activityDef658)
                    repeatDef66 = self.repeatDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, repeatDef66.tree)


                elif alt20 == 6:
                    # src/SavedFSM/Monitor.g:73:62: unorderedDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_unorderedDef_in_activityDef662)
                    unorderedDef67 = self.unorderedDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, unorderedDef67.tree)


                elif alt20 == 7:
                    # src/SavedFSM/Monitor.g:74:4: recBlockDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_recBlockDef_in_activityDef669)
                    recBlockDef68 = self.recBlockDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, recBlockDef68.tree)


                elif alt20 == 8:
                    # src/SavedFSM/Monitor.g:74:18: globalEscapeDef
                    pass 
                    root_0 = self._adaptor.nil()

                    self._state.following.append(self.FOLLOW_globalEscapeDef_in_activityDef673)
                    globalEscapeDef69 = self.globalEscapeDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, globalEscapeDef69.tree)


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

        string_literal71 = None
        char_literal73 = None
        roleDef70 = None

        roleDef72 = None

        roleDef74 = None


        string_literal71_tree = None
        char_literal73_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:76:14: ( roleDef 'introduces' roleDef ( ',' roleDef )* )
                # src/SavedFSM/Monitor.g:76:16: roleDef 'introduces' roleDef ( ',' roleDef )*
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_roleDef_in_introducesDef681)
                roleDef70 = self.roleDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, roleDef70.tree)
                string_literal71=self.match(self.input, 46, self.FOLLOW_46_in_introducesDef683)
                if self._state.backtracking == 0:

                    string_literal71_tree = self._adaptor.createWithPayload(string_literal71)
                    self._adaptor.addChild(root_0, string_literal71_tree)

                self._state.following.append(self.FOLLOW_roleDef_in_introducesDef685)
                roleDef72 = self.roleDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, roleDef72.tree)
                # src/SavedFSM/Monitor.g:76:45: ( ',' roleDef )*
                while True: #loop21
                    alt21 = 2
                    LA21_0 = self.input.LA(1)

                    if (LA21_0 == 36) :
                        alt21 = 1


                    if alt21 == 1:
                        # src/SavedFSM/Monitor.g:76:47: ',' roleDef
                        pass 
                        char_literal73=self.match(self.input, 36, self.FOLLOW_36_in_introducesDef689)
                        if self._state.backtracking == 0:

                            char_literal73_tree = self._adaptor.createWithPayload(char_literal73)
                            self._adaptor.addChild(root_0, char_literal73_tree)

                        self._state.following.append(self.FOLLOW_roleDef_in_introducesDef691)
                        roleDef74 = self.roleDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, roleDef74.tree)


                    else:
                        break #loop21



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

        ID75 = None

        ID75_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")

        try:
            try:
                # src/SavedFSM/Monitor.g:78:8: ( ID -> ID )
                # src/SavedFSM/Monitor.g:78:10: ID
                pass 
                ID75=self.match(self.input, ID, self.FOLLOW_ID_in_roleDef702) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID75)

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

        ID76 = None

        ID76_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")

        try:
            try:
                # src/SavedFSM/Monitor.g:80:9: ( ID -> ID )
                # src/SavedFSM/Monitor.g:80:11: ID
                pass 
                ID76=self.match(self.input, ID, self.FOLLOW_ID_in_roleName713) 
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

        ID77 = None

        ID77_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")

        try:
            try:
                # src/SavedFSM/Monitor.g:82:17: ( ID -> ID )
                # src/SavedFSM/Monitor.g:82:19: ID
                pass 
                ID77=self.match(self.input, ID, self.FOLLOW_ID_in_typeReferenceDef724) 
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

        char_literal79 = None
        char_literal81 = None
        char_literal83 = None
        char_literal84 = None
        char_literal86 = None
        char_literal88 = None
        typeReferenceDef78 = None

        valueDecl80 = None

        valueDecl82 = None

        valueDecl85 = None

        valueDecl87 = None


        char_literal79_tree = None
        char_literal81_tree = None
        char_literal83_tree = None
        char_literal84_tree = None
        char_literal86_tree = None
        char_literal88_tree = None
        stream_43 = RewriteRuleTokenStream(self._adaptor, "token 43")
        stream_44 = RewriteRuleTokenStream(self._adaptor, "token 44")
        stream_36 = RewriteRuleTokenStream(self._adaptor, "token 36")
        stream_typeReferenceDef = RewriteRuleSubtreeStream(self._adaptor, "rule typeReferenceDef")
        stream_valueDecl = RewriteRuleSubtreeStream(self._adaptor, "rule valueDecl")
        try:
            try:
                # src/SavedFSM/Monitor.g:83:24: ( ( ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) ) | ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) ) ) )
                # src/SavedFSM/Monitor.g:83:26: ( ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) ) | ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) ) )
                pass 
                # src/SavedFSM/Monitor.g:83:26: ( ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) ) | ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) ) )
                alt25 = 2
                LA25_0 = self.input.LA(1)

                if (LA25_0 == ID) :
                    alt25 = 1
                elif (LA25_0 == 43) :
                    alt25 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed

                    nvae = NoViableAltException("", 25, 0, self.input)

                    raise nvae

                if alt25 == 1:
                    # src/SavedFSM/Monitor.g:83:27: ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) )
                    pass 
                    # src/SavedFSM/Monitor.g:83:27: ( typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )? -> typeReferenceDef ^( VALUE ( valueDecl )* ) )
                    # src/SavedFSM/Monitor.g:83:28: typeReferenceDef ( '(' valueDecl ( ',' valueDecl )* ')' )?
                    pass 
                    self._state.following.append(self.FOLLOW_typeReferenceDef_in_interactionSignatureDef735)
                    typeReferenceDef78 = self.typeReferenceDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_typeReferenceDef.add(typeReferenceDef78.tree)
                    # src/SavedFSM/Monitor.g:83:45: ( '(' valueDecl ( ',' valueDecl )* ')' )?
                    alt23 = 2
                    LA23_0 = self.input.LA(1)

                    if (LA23_0 == 43) :
                        alt23 = 1
                    if alt23 == 1:
                        # src/SavedFSM/Monitor.g:83:46: '(' valueDecl ( ',' valueDecl )* ')'
                        pass 
                        char_literal79=self.match(self.input, 43, self.FOLLOW_43_in_interactionSignatureDef738) 
                        if self._state.backtracking == 0:
                            stream_43.add(char_literal79)
                        self._state.following.append(self.FOLLOW_valueDecl_in_interactionSignatureDef740)
                        valueDecl80 = self.valueDecl()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_valueDecl.add(valueDecl80.tree)
                        # src/SavedFSM/Monitor.g:83:60: ( ',' valueDecl )*
                        while True: #loop22
                            alt22 = 2
                            LA22_0 = self.input.LA(1)

                            if (LA22_0 == 36) :
                                alt22 = 1


                            if alt22 == 1:
                                # src/SavedFSM/Monitor.g:83:61: ',' valueDecl
                                pass 
                                char_literal81=self.match(self.input, 36, self.FOLLOW_36_in_interactionSignatureDef743) 
                                if self._state.backtracking == 0:
                                    stream_36.add(char_literal81)
                                self._state.following.append(self.FOLLOW_valueDecl_in_interactionSignatureDef745)
                                valueDecl82 = self.valueDecl()

                                self._state.following.pop()
                                if self._state.backtracking == 0:
                                    stream_valueDecl.add(valueDecl82.tree)


                            else:
                                break #loop22
                        char_literal83=self.match(self.input, 44, self.FOLLOW_44_in_interactionSignatureDef749) 
                        if self._state.backtracking == 0:
                            stream_44.add(char_literal83)




                    # AST Rewrite
                    # elements: typeReferenceDef, valueDecl
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





                elif alt25 == 2:
                    # src/SavedFSM/Monitor.g:84:7: ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) )
                    pass 
                    # src/SavedFSM/Monitor.g:84:7: ( ( '(' valueDecl ( ',' valueDecl )* ')' ) -> ^( VALUE ( valueDecl )* ) )
                    # src/SavedFSM/Monitor.g:84:8: ( '(' valueDecl ( ',' valueDecl )* ')' )
                    pass 
                    # src/SavedFSM/Monitor.g:84:8: ( '(' valueDecl ( ',' valueDecl )* ')' )
                    # src/SavedFSM/Monitor.g:84:9: '(' valueDecl ( ',' valueDecl )* ')'
                    pass 
                    char_literal84=self.match(self.input, 43, self.FOLLOW_43_in_interactionSignatureDef773) 
                    if self._state.backtracking == 0:
                        stream_43.add(char_literal84)
                    self._state.following.append(self.FOLLOW_valueDecl_in_interactionSignatureDef775)
                    valueDecl85 = self.valueDecl()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_valueDecl.add(valueDecl85.tree)
                    # src/SavedFSM/Monitor.g:84:23: ( ',' valueDecl )*
                    while True: #loop24
                        alt24 = 2
                        LA24_0 = self.input.LA(1)

                        if (LA24_0 == 36) :
                            alt24 = 1


                        if alt24 == 1:
                            # src/SavedFSM/Monitor.g:84:24: ',' valueDecl
                            pass 
                            char_literal86=self.match(self.input, 36, self.FOLLOW_36_in_interactionSignatureDef778) 
                            if self._state.backtracking == 0:
                                stream_36.add(char_literal86)
                            self._state.following.append(self.FOLLOW_valueDecl_in_interactionSignatureDef780)
                            valueDecl87 = self.valueDecl()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                stream_valueDecl.add(valueDecl87.tree)


                        else:
                            break #loop24
                    char_literal88=self.match(self.input, 44, self.FOLLOW_44_in_interactionSignatureDef784) 
                    if self._state.backtracking == 0:
                        stream_44.add(char_literal88)




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

        ID89 = None
        char_literal90 = None
        primitivetype91 = None


        ID89_tree = None
        char_literal90_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:86:11: ( ID ( ':' primitivetype )? )
                # src/SavedFSM/Monitor.g:86:13: ID ( ':' primitivetype )?
                pass 
                root_0 = self._adaptor.nil()

                ID89=self.match(self.input, ID, self.FOLLOW_ID_in_valueDecl804)
                if self._state.backtracking == 0:

                    ID89_tree = self._adaptor.createWithPayload(ID89)
                    self._adaptor.addChild(root_0, ID89_tree)

                # src/SavedFSM/Monitor.g:86:16: ( ':' primitivetype )?
                alt26 = 2
                LA26_0 = self.input.LA(1)

                if (LA26_0 == 47) :
                    alt26 = 1
                if alt26 == 1:
                    # src/SavedFSM/Monitor.g:86:17: ':' primitivetype
                    pass 
                    char_literal90=self.match(self.input, 47, self.FOLLOW_47_in_valueDecl807)
                    self._state.following.append(self.FOLLOW_primitivetype_in_valueDecl810)
                    primitivetype91 = self.primitivetype()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, primitivetype91.tree)






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

        valueDecl92 = None



        try:
            try:
                # src/SavedFSM/Monitor.g:87:16: ( valueDecl )
                # src/SavedFSM/Monitor.g:87:18: valueDecl
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_valueDecl_in_firstValueDecl821)
                valueDecl92 = self.valueDecl()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, valueDecl92.tree)



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

        string_literal94 = None
        string_literal96 = None
        role = None

        interactionSignatureDef93 = None

        assertDef95 = None

        roleName97 = None

        assertDef98 = None


        string_literal94_tree = None
        string_literal96_tree = None
        stream_48 = RewriteRuleTokenStream(self._adaptor, "token 48")
        stream_38 = RewriteRuleTokenStream(self._adaptor, "token 38")
        stream_assertDef = RewriteRuleSubtreeStream(self._adaptor, "rule assertDef")
        stream_roleName = RewriteRuleSubtreeStream(self._adaptor, "rule roleName")
        stream_interactionSignatureDef = RewriteRuleSubtreeStream(self._adaptor, "rule interactionSignatureDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:90:15: ( interactionSignatureDef ( 'from' role= roleName ( assertDef ) -> ^( RESV interactionSignatureDef $role assertDef ) | 'to' roleName ( assertDef ) -> ^( SEND interactionSignatureDef roleName assertDef ) ) )
                # src/SavedFSM/Monitor.g:91:7: interactionSignatureDef ( 'from' role= roleName ( assertDef ) -> ^( RESV interactionSignatureDef $role assertDef ) | 'to' roleName ( assertDef ) -> ^( SEND interactionSignatureDef roleName assertDef ) )
                pass 
                self._state.following.append(self.FOLLOW_interactionSignatureDef_in_interactionDef836)
                interactionSignatureDef93 = self.interactionSignatureDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_interactionSignatureDef.add(interactionSignatureDef93.tree)
                # src/SavedFSM/Monitor.g:91:31: ( 'from' role= roleName ( assertDef ) -> ^( RESV interactionSignatureDef $role assertDef ) | 'to' roleName ( assertDef ) -> ^( SEND interactionSignatureDef roleName assertDef ) )
                alt27 = 2
                LA27_0 = self.input.LA(1)

                if (LA27_0 == 38) :
                    alt27 = 1
                elif (LA27_0 == 48) :
                    alt27 = 2
                else:
                    if self._state.backtracking > 0:
                        raise BacktrackingFailed

                    nvae = NoViableAltException("", 27, 0, self.input)

                    raise nvae

                if alt27 == 1:
                    # src/SavedFSM/Monitor.g:92:3: 'from' role= roleName ( assertDef )
                    pass 
                    string_literal94=self.match(self.input, 38, self.FOLLOW_38_in_interactionDef842) 
                    if self._state.backtracking == 0:
                        stream_38.add(string_literal94)
                    self._state.following.append(self.FOLLOW_roleName_in_interactionDef847)
                    role = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_roleName.add(role.tree)
                    # src/SavedFSM/Monitor.g:92:26: ( assertDef )
                    # src/SavedFSM/Monitor.g:92:27: assertDef
                    pass 
                    self._state.following.append(self.FOLLOW_assertDef_in_interactionDef851)
                    assertDef95 = self.assertDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_assertDef.add(assertDef95.tree)




                    # AST Rewrite
                    # elements: assertDef, role, interactionSignatureDef
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


                elif alt27 == 2:
                    # src/SavedFSM/Monitor.g:93:10: 'to' roleName ( assertDef )
                    pass 
                    string_literal96=self.match(self.input, 48, self.FOLLOW_48_in_interactionDef875) 
                    if self._state.backtracking == 0:
                        stream_48.add(string_literal96)
                    self._state.following.append(self.FOLLOW_roleName_in_interactionDef877)
                    roleName97 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_roleName.add(roleName97.tree)
                    # src/SavedFSM/Monitor.g:93:25: ( assertDef )
                    # src/SavedFSM/Monitor.g:93:26: assertDef
                    pass 
                    self._state.following.append(self.FOLLOW_assertDef_in_interactionDef881)
                    assertDef98 = self.assertDef()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_assertDef.add(assertDef98.tree)




                    # AST Rewrite
                    # elements: roleName, assertDef, interactionSignatureDef
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

        string_literal99 = None
        string_literal100 = None
        string_literal103 = None
        roleName101 = None

        blockDef102 = None

        blockDef104 = None


        string_literal99_tree = None
        string_literal100_tree = None
        string_literal103_tree = None
        stream_49 = RewriteRuleTokenStream(self._adaptor, "token 49")
        stream_40 = RewriteRuleTokenStream(self._adaptor, "token 40")
        stream_50 = RewriteRuleTokenStream(self._adaptor, "token 50")
        stream_roleName = RewriteRuleSubtreeStream(self._adaptor, "rule roleName")
        stream_blockDef = RewriteRuleSubtreeStream(self._adaptor, "rule blockDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:95:10: ( 'choice' ( 'at' roleName )? blockDef ( 'or' blockDef )* -> ^( 'choice' ( blockDef )+ ) )
                # src/SavedFSM/Monitor.g:95:12: 'choice' ( 'at' roleName )? blockDef ( 'or' blockDef )*
                pass 
                string_literal99=self.match(self.input, 49, self.FOLLOW_49_in_choiceDef902) 
                if self._state.backtracking == 0:
                    stream_49.add(string_literal99)
                # src/SavedFSM/Monitor.g:95:21: ( 'at' roleName )?
                alt28 = 2
                LA28_0 = self.input.LA(1)

                if (LA28_0 == 40) :
                    alt28 = 1
                if alt28 == 1:
                    # src/SavedFSM/Monitor.g:95:23: 'at' roleName
                    pass 
                    string_literal100=self.match(self.input, 40, self.FOLLOW_40_in_choiceDef906) 
                    if self._state.backtracking == 0:
                        stream_40.add(string_literal100)
                    self._state.following.append(self.FOLLOW_roleName_in_choiceDef908)
                    roleName101 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_roleName.add(roleName101.tree)



                self._state.following.append(self.FOLLOW_blockDef_in_choiceDef913)
                blockDef102 = self.blockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_blockDef.add(blockDef102.tree)
                # src/SavedFSM/Monitor.g:95:49: ( 'or' blockDef )*
                while True: #loop29
                    alt29 = 2
                    LA29_0 = self.input.LA(1)

                    if (LA29_0 == 50) :
                        alt29 = 1


                    if alt29 == 1:
                        # src/SavedFSM/Monitor.g:95:51: 'or' blockDef
                        pass 
                        string_literal103=self.match(self.input, 50, self.FOLLOW_50_in_choiceDef917) 
                        if self._state.backtracking == 0:
                            stream_50.add(string_literal103)
                        self._state.following.append(self.FOLLOW_blockDef_in_choiceDef919)
                        blockDef104 = self.blockDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_blockDef.add(blockDef104.tree)


                    else:
                        break #loop29

                # AST Rewrite
                # elements: 49, blockDef
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
                    root_1 = self._adaptor.becomeRoot(stream_49.nextNode(), root_1)

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

        string_literal105 = None
        string_literal107 = None
        char_literal109 = None
        char_literal111 = None
        char_literal113 = None
        roleName106 = None

        roleName108 = None

        roleName110 = None

        onMessageDef112 = None


        string_literal105_tree = None
        string_literal107_tree = None
        char_literal109_tree = None
        char_literal111_tree = None
        char_literal113_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:97:18: ( ( 'from' roleName )? ( 'to' roleName ( ',' roleName )* )? '{' ( onMessageDef )+ '}' )
                # src/SavedFSM/Monitor.g:97:20: ( 'from' roleName )? ( 'to' roleName ( ',' roleName )* )? '{' ( onMessageDef )+ '}'
                pass 
                root_0 = self._adaptor.nil()

                # src/SavedFSM/Monitor.g:97:20: ( 'from' roleName )?
                alt30 = 2
                LA30_0 = self.input.LA(1)

                if (LA30_0 == 38) :
                    alt30 = 1
                if alt30 == 1:
                    # src/SavedFSM/Monitor.g:97:22: 'from' roleName
                    pass 
                    string_literal105=self.match(self.input, 38, self.FOLLOW_38_in_directedChoiceDef940)
                    if self._state.backtracking == 0:

                        string_literal105_tree = self._adaptor.createWithPayload(string_literal105)
                        self._adaptor.addChild(root_0, string_literal105_tree)

                    self._state.following.append(self.FOLLOW_roleName_in_directedChoiceDef942)
                    roleName106 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, roleName106.tree)



                # src/SavedFSM/Monitor.g:97:41: ( 'to' roleName ( ',' roleName )* )?
                alt32 = 2
                LA32_0 = self.input.LA(1)

                if (LA32_0 == 48) :
                    alt32 = 1
                if alt32 == 1:
                    # src/SavedFSM/Monitor.g:97:43: 'to' roleName ( ',' roleName )*
                    pass 
                    string_literal107=self.match(self.input, 48, self.FOLLOW_48_in_directedChoiceDef949)
                    if self._state.backtracking == 0:

                        string_literal107_tree = self._adaptor.createWithPayload(string_literal107)
                        self._adaptor.addChild(root_0, string_literal107_tree)

                    self._state.following.append(self.FOLLOW_roleName_in_directedChoiceDef951)
                    roleName108 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, roleName108.tree)
                    # src/SavedFSM/Monitor.g:97:57: ( ',' roleName )*
                    while True: #loop31
                        alt31 = 2
                        LA31_0 = self.input.LA(1)

                        if (LA31_0 == 36) :
                            alt31 = 1


                        if alt31 == 1:
                            # src/SavedFSM/Monitor.g:97:59: ',' roleName
                            pass 
                            char_literal109=self.match(self.input, 36, self.FOLLOW_36_in_directedChoiceDef955)
                            self._state.following.append(self.FOLLOW_roleName_in_directedChoiceDef958)
                            roleName110 = self.roleName()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, roleName110.tree)


                        else:
                            break #loop31



                char_literal111=self.match(self.input, 41, self.FOLLOW_41_in_directedChoiceDef966)
                if self._state.backtracking == 0:

                    char_literal111_tree = self._adaptor.createWithPayload(char_literal111)
                    self._adaptor.addChild(root_0, char_literal111_tree)

                # src/SavedFSM/Monitor.g:97:83: ( onMessageDef )+
                cnt33 = 0
                while True: #loop33
                    alt33 = 2
                    LA33_0 = self.input.LA(1)

                    if (LA33_0 == ID or LA33_0 == 43) :
                        alt33 = 1


                    if alt33 == 1:
                        # src/SavedFSM/Monitor.g:97:85: onMessageDef
                        pass 
                        self._state.following.append(self.FOLLOW_onMessageDef_in_directedChoiceDef970)
                        onMessageDef112 = self.onMessageDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, onMessageDef112.tree)


                    else:
                        if cnt33 >= 1:
                            break #loop33

                        if self._state.backtracking > 0:
                            raise BacktrackingFailed

                        eee = EarlyExitException(33, self.input)
                        raise eee

                    cnt33 += 1
                char_literal113=self.match(self.input, 42, self.FOLLOW_42_in_directedChoiceDef975)
                if self._state.backtracking == 0:

                    char_literal113_tree = self._adaptor.createWithPayload(char_literal113)
                    self._adaptor.addChild(root_0, char_literal113_tree)




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

        char_literal115 = None
        interactionSignatureDef114 = None

        activityList116 = None


        char_literal115_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:99:13: ( interactionSignatureDef ':' activityList )
                # src/SavedFSM/Monitor.g:99:15: interactionSignatureDef ':' activityList
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_interactionSignatureDef_in_onMessageDef982)
                interactionSignatureDef114 = self.interactionSignatureDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, interactionSignatureDef114.tree)
                char_literal115=self.match(self.input, 47, self.FOLLOW_47_in_onMessageDef984)
                if self._state.backtracking == 0:

                    char_literal115_tree = self._adaptor.createWithPayload(char_literal115)
                    self._adaptor.addChild(root_0, char_literal115_tree)

                self._state.following.append(self.FOLLOW_activityList_in_onMessageDef986)
                activityList116 = self.activityList()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, activityList116.tree)



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

        ANNOTATION117 = None
        activityDef118 = None


        ANNOTATION117_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:101:13: ( ( ( ANNOTATION )* activityDef )* )
                # src/SavedFSM/Monitor.g:101:15: ( ( ANNOTATION )* activityDef )*
                pass 
                root_0 = self._adaptor.nil()

                # src/SavedFSM/Monitor.g:101:15: ( ( ANNOTATION )* activityDef )*
                while True: #loop35
                    alt35 = 2
                    alt35 = self.dfa35.predict(self.input)
                    if alt35 == 1:
                        # src/SavedFSM/Monitor.g:101:17: ( ANNOTATION )* activityDef
                        pass 
                        # src/SavedFSM/Monitor.g:101:17: ( ANNOTATION )*
                        while True: #loop34
                            alt34 = 2
                            LA34_0 = self.input.LA(1)

                            if (LA34_0 == ANNOTATION) :
                                alt34 = 1


                            if alt34 == 1:
                                # src/SavedFSM/Monitor.g:101:19: ANNOTATION
                                pass 
                                ANNOTATION117=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_activityList999)
                                if self._state.backtracking == 0:

                                    ANNOTATION117_tree = self._adaptor.createWithPayload(ANNOTATION117)
                                    self._adaptor.addChild(root_0, ANNOTATION117_tree)



                            else:
                                break #loop34
                        self._state.following.append(self.FOLLOW_activityDef_in_activityList1004)
                        activityDef118 = self.activityDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, activityDef118.tree)


                    else:
                        break #loop35



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

        string_literal119 = None
        string_literal120 = None
        char_literal122 = None
        roleName121 = None

        roleName123 = None

        blockDef124 = None


        string_literal119_tree = None
        string_literal120_tree = None
        char_literal122_tree = None
        stream_40 = RewriteRuleTokenStream(self._adaptor, "token 40")
        stream_51 = RewriteRuleTokenStream(self._adaptor, "token 51")
        stream_36 = RewriteRuleTokenStream(self._adaptor, "token 36")
        stream_roleName = RewriteRuleSubtreeStream(self._adaptor, "rule roleName")
        stream_blockDef = RewriteRuleSubtreeStream(self._adaptor, "rule blockDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:103:10: ( 'repeat' ( 'at' roleName ( ',' roleName )* )? blockDef -> ^( 'repeat' blockDef ) )
                # src/SavedFSM/Monitor.g:103:12: 'repeat' ( 'at' roleName ( ',' roleName )* )? blockDef
                pass 
                string_literal119=self.match(self.input, 51, self.FOLLOW_51_in_repeatDef1014) 
                if self._state.backtracking == 0:
                    stream_51.add(string_literal119)
                # src/SavedFSM/Monitor.g:103:21: ( 'at' roleName ( ',' roleName )* )?
                alt37 = 2
                LA37_0 = self.input.LA(1)

                if (LA37_0 == 40) :
                    alt37 = 1
                if alt37 == 1:
                    # src/SavedFSM/Monitor.g:103:23: 'at' roleName ( ',' roleName )*
                    pass 
                    string_literal120=self.match(self.input, 40, self.FOLLOW_40_in_repeatDef1018) 
                    if self._state.backtracking == 0:
                        stream_40.add(string_literal120)
                    self._state.following.append(self.FOLLOW_roleName_in_repeatDef1020)
                    roleName121 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        stream_roleName.add(roleName121.tree)
                    # src/SavedFSM/Monitor.g:103:37: ( ',' roleName )*
                    while True: #loop36
                        alt36 = 2
                        LA36_0 = self.input.LA(1)

                        if (LA36_0 == 36) :
                            alt36 = 1


                        if alt36 == 1:
                            # src/SavedFSM/Monitor.g:103:39: ',' roleName
                            pass 
                            char_literal122=self.match(self.input, 36, self.FOLLOW_36_in_repeatDef1024) 
                            if self._state.backtracking == 0:
                                stream_36.add(char_literal122)
                            self._state.following.append(self.FOLLOW_roleName_in_repeatDef1026)
                            roleName123 = self.roleName()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                stream_roleName.add(roleName123.tree)


                        else:
                            break #loop36



                self._state.following.append(self.FOLLOW_blockDef_in_repeatDef1034)
                blockDef124 = self.blockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_blockDef.add(blockDef124.tree)

                # AST Rewrite
                # elements: 51, blockDef
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
                    root_1 = self._adaptor.becomeRoot(stream_51.nextNode(), root_1)

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

        string_literal125 = None
        labelName126 = None

        blockDef127 = None


        string_literal125_tree = None
        stream_52 = RewriteRuleTokenStream(self._adaptor, "token 52")
        stream_labelName = RewriteRuleSubtreeStream(self._adaptor, "rule labelName")
        stream_blockDef = RewriteRuleSubtreeStream(self._adaptor, "rule blockDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:105:12: ( 'rec' labelName blockDef -> ^( 'rec' labelName blockDef ) )
                # src/SavedFSM/Monitor.g:105:14: 'rec' labelName blockDef
                pass 
                string_literal125=self.match(self.input, 52, self.FOLLOW_52_in_recBlockDef1050) 
                if self._state.backtracking == 0:
                    stream_52.add(string_literal125)
                self._state.following.append(self.FOLLOW_labelName_in_recBlockDef1052)
                labelName126 = self.labelName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_labelName.add(labelName126.tree)
                self._state.following.append(self.FOLLOW_blockDef_in_recBlockDef1054)
                blockDef127 = self.blockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_blockDef.add(blockDef127.tree)

                # AST Rewrite
                # elements: labelName, blockDef, 52
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
                    root_1 = self._adaptor.becomeRoot(stream_52.nextNode(), root_1)

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

        ID128 = None

        ID128_tree = None
        stream_ID = RewriteRuleTokenStream(self._adaptor, "token ID")

        try:
            try:
                # src/SavedFSM/Monitor.g:107:10: ( ID -> ID )
                # src/SavedFSM/Monitor.g:107:12: ID
                pass 
                ID128=self.match(self.input, ID, self.FOLLOW_ID_in_labelName1071) 
                if self._state.backtracking == 0:
                    stream_ID.add(ID128)

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

        labelName129 = None


        stream_labelName = RewriteRuleSubtreeStream(self._adaptor, "rule labelName")
        try:
            try:
                # src/SavedFSM/Monitor.g:109:13: ( labelName -> ^( RECLABEL labelName ) )
                # src/SavedFSM/Monitor.g:109:15: labelName
                pass 
                self._state.following.append(self.FOLLOW_labelName_in_recursionDef1083)
                labelName129 = self.labelName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_labelName.add(labelName129.tree)

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

        string_literal130 = None

        string_literal130_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:112:7: ( 'end' )
                # src/SavedFSM/Monitor.g:112:9: 'end'
                pass 
                root_0 = self._adaptor.nil()

                string_literal130=self.match(self.input, 53, self.FOLLOW_53_in_endDef1099)
                if self._state.backtracking == 0:

                    string_literal130_tree = self._adaptor.createWithPayload(string_literal130)
                    root_0 = self._adaptor.becomeRoot(string_literal130_tree, root_0)




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

        string_literal131 = None
        char_literal133 = None
        char_literal135 = None
        char_literal137 = None
        string_literal138 = None
        protocolRefDef132 = None

        parameter134 = None

        parameter136 = None

        roleName139 = None


        string_literal131_tree = None
        char_literal133_tree = None
        char_literal135_tree = None
        char_literal137_tree = None
        string_literal138_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:115:7: ( 'run' protocolRefDef ( '(' parameter ( ',' parameter )* ')' )? 'from' roleName )
                # src/SavedFSM/Monitor.g:115:9: 'run' protocolRefDef ( '(' parameter ( ',' parameter )* ')' )? 'from' roleName
                pass 
                root_0 = self._adaptor.nil()

                string_literal131=self.match(self.input, 54, self.FOLLOW_54_in_runDef1109)
                if self._state.backtracking == 0:

                    string_literal131_tree = self._adaptor.createWithPayload(string_literal131)
                    root_0 = self._adaptor.becomeRoot(string_literal131_tree, root_0)

                self._state.following.append(self.FOLLOW_protocolRefDef_in_runDef1112)
                protocolRefDef132 = self.protocolRefDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, protocolRefDef132.tree)
                # src/SavedFSM/Monitor.g:115:31: ( '(' parameter ( ',' parameter )* ')' )?
                alt39 = 2
                LA39_0 = self.input.LA(1)

                if (LA39_0 == 43) :
                    alt39 = 1
                if alt39 == 1:
                    # src/SavedFSM/Monitor.g:115:33: '(' parameter ( ',' parameter )* ')'
                    pass 
                    char_literal133=self.match(self.input, 43, self.FOLLOW_43_in_runDef1116)
                    self._state.following.append(self.FOLLOW_parameter_in_runDef1119)
                    parameter134 = self.parameter()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, parameter134.tree)
                    # src/SavedFSM/Monitor.g:115:48: ( ',' parameter )*
                    while True: #loop38
                        alt38 = 2
                        LA38_0 = self.input.LA(1)

                        if (LA38_0 == 36) :
                            alt38 = 1


                        if alt38 == 1:
                            # src/SavedFSM/Monitor.g:115:50: ',' parameter
                            pass 
                            char_literal135=self.match(self.input, 36, self.FOLLOW_36_in_runDef1123)
                            self._state.following.append(self.FOLLOW_parameter_in_runDef1126)
                            parameter136 = self.parameter()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, parameter136.tree)


                        else:
                            break #loop38
                    char_literal137=self.match(self.input, 44, self.FOLLOW_44_in_runDef1131)



                string_literal138=self.match(self.input, 38, self.FOLLOW_38_in_runDef1137)
                if self._state.backtracking == 0:

                    string_literal138_tree = self._adaptor.createWithPayload(string_literal138)
                    self._adaptor.addChild(root_0, string_literal138_tree)

                self._state.following.append(self.FOLLOW_roleName_in_runDef1139)
                roleName139 = self.roleName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, roleName139.tree)



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

        ID140 = None
        string_literal141 = None
        roleName142 = None


        ID140_tree = None
        string_literal141_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:117:15: ( ID ( 'at' roleName )? )
                # src/SavedFSM/Monitor.g:117:17: ID ( 'at' roleName )?
                pass 
                root_0 = self._adaptor.nil()

                ID140=self.match(self.input, ID, self.FOLLOW_ID_in_protocolRefDef1147)
                if self._state.backtracking == 0:

                    ID140_tree = self._adaptor.createWithPayload(ID140)
                    self._adaptor.addChild(root_0, ID140_tree)

                # src/SavedFSM/Monitor.g:117:20: ( 'at' roleName )?
                alt40 = 2
                LA40_0 = self.input.LA(1)

                if (LA40_0 == 40) :
                    alt40 = 1
                if alt40 == 1:
                    # src/SavedFSM/Monitor.g:117:22: 'at' roleName
                    pass 
                    string_literal141=self.match(self.input, 40, self.FOLLOW_40_in_protocolRefDef1151)
                    if self._state.backtracking == 0:

                        string_literal141_tree = self._adaptor.createWithPayload(string_literal141)
                        self._adaptor.addChild(root_0, string_literal141_tree)

                    self._state.following.append(self.FOLLOW_roleName_in_protocolRefDef1153)
                    roleName142 = self.roleName()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, roleName142.tree)






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

        ID143 = None

        ID143_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:119:16: ( ID )
                # src/SavedFSM/Monitor.g:119:18: ID
                pass 
                root_0 = self._adaptor.nil()

                ID143=self.match(self.input, ID, self.FOLLOW_ID_in_declarationName1164)
                if self._state.backtracking == 0:

                    ID143_tree = self._adaptor.createWithPayload(ID143)
                    self._adaptor.addChild(root_0, ID143_tree)




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

        declarationName144 = None



        try:
            try:
                # src/SavedFSM/Monitor.g:121:10: ( declarationName )
                # src/SavedFSM/Monitor.g:121:12: declarationName
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_declarationName_in_parameter1172)
                declarationName144 = self.declarationName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, declarationName144.tree)



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

        string_literal145 = None
        char_literal147 = None
        char_literal149 = None
        char_literal151 = None
        protocolRefDef146 = None

        parameter148 = None

        parameter150 = None


        string_literal145_tree = None
        char_literal147_tree = None
        char_literal149_tree = None
        char_literal151_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:124:10: ( 'inline' protocolRefDef ( '(' parameter ( ',' parameter )* ')' )? )
                # src/SavedFSM/Monitor.g:124:12: 'inline' protocolRefDef ( '(' parameter ( ',' parameter )* ')' )?
                pass 
                root_0 = self._adaptor.nil()

                string_literal145=self.match(self.input, 55, self.FOLLOW_55_in_inlineDef1181)
                if self._state.backtracking == 0:

                    string_literal145_tree = self._adaptor.createWithPayload(string_literal145)
                    root_0 = self._adaptor.becomeRoot(string_literal145_tree, root_0)

                self._state.following.append(self.FOLLOW_protocolRefDef_in_inlineDef1184)
                protocolRefDef146 = self.protocolRefDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, protocolRefDef146.tree)
                # src/SavedFSM/Monitor.g:124:37: ( '(' parameter ( ',' parameter )* ')' )?
                alt42 = 2
                LA42_0 = self.input.LA(1)

                if (LA42_0 == 43) :
                    alt42 = 1
                if alt42 == 1:
                    # src/SavedFSM/Monitor.g:124:39: '(' parameter ( ',' parameter )* ')'
                    pass 
                    char_literal147=self.match(self.input, 43, self.FOLLOW_43_in_inlineDef1188)
                    self._state.following.append(self.FOLLOW_parameter_in_inlineDef1191)
                    parameter148 = self.parameter()

                    self._state.following.pop()
                    if self._state.backtracking == 0:
                        self._adaptor.addChild(root_0, parameter148.tree)
                    # src/SavedFSM/Monitor.g:124:54: ( ',' parameter )*
                    while True: #loop41
                        alt41 = 2
                        LA41_0 = self.input.LA(1)

                        if (LA41_0 == 36) :
                            alt41 = 1


                        if alt41 == 1:
                            # src/SavedFSM/Monitor.g:124:56: ',' parameter
                            pass 
                            char_literal149=self.match(self.input, 36, self.FOLLOW_36_in_inlineDef1195)
                            self._state.following.append(self.FOLLOW_parameter_in_inlineDef1198)
                            parameter150 = self.parameter()

                            self._state.following.pop()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, parameter150.tree)


                        else:
                            break #loop41
                    char_literal151=self.match(self.input, 44, self.FOLLOW_44_in_inlineDef1203)






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

        string_literal152 = None
        string_literal154 = None
        blockDef153 = None

        blockDef155 = None


        string_literal152_tree = None
        string_literal154_tree = None
        stream_57 = RewriteRuleTokenStream(self._adaptor, "token 57")
        stream_56 = RewriteRuleTokenStream(self._adaptor, "token 56")
        stream_blockDef = RewriteRuleSubtreeStream(self._adaptor, "rule blockDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:126:12: ( 'parallel' blockDef ( 'and' blockDef )* -> ^( PARALLEL ( blockDef )+ ) )
                # src/SavedFSM/Monitor.g:126:14: 'parallel' blockDef ( 'and' blockDef )*
                pass 
                string_literal152=self.match(self.input, 56, self.FOLLOW_56_in_parallelDef1215) 
                if self._state.backtracking == 0:
                    stream_56.add(string_literal152)
                self._state.following.append(self.FOLLOW_blockDef_in_parallelDef1217)
                blockDef153 = self.blockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_blockDef.add(blockDef153.tree)
                # src/SavedFSM/Monitor.g:126:34: ( 'and' blockDef )*
                while True: #loop43
                    alt43 = 2
                    LA43_0 = self.input.LA(1)

                    if (LA43_0 == 57) :
                        alt43 = 1


                    if alt43 == 1:
                        # src/SavedFSM/Monitor.g:126:36: 'and' blockDef
                        pass 
                        string_literal154=self.match(self.input, 57, self.FOLLOW_57_in_parallelDef1221) 
                        if self._state.backtracking == 0:
                            stream_57.add(string_literal154)
                        self._state.following.append(self.FOLLOW_blockDef_in_parallelDef1223)
                        blockDef155 = self.blockDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_blockDef.add(blockDef155.tree)


                    else:
                        break #loop43

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

        string_literal156 = None
        char_literal157 = None
        char_literal159 = None
        activityListDef158 = None


        string_literal156_tree = None
        char_literal157_tree = None
        char_literal159_tree = None
        stream_58 = RewriteRuleTokenStream(self._adaptor, "token 58")
        stream_42 = RewriteRuleTokenStream(self._adaptor, "token 42")
        stream_41 = RewriteRuleTokenStream(self._adaptor, "token 41")
        stream_activityListDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityListDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:129:11: ( 'do' '{' activityListDef '}' -> ^( 'do' activityListDef ) )
                # src/SavedFSM/Monitor.g:129:13: 'do' '{' activityListDef '}'
                pass 
                string_literal156=self.match(self.input, 58, self.FOLLOW_58_in_doBlockDef1243) 
                if self._state.backtracking == 0:
                    stream_58.add(string_literal156)
                char_literal157=self.match(self.input, 41, self.FOLLOW_41_in_doBlockDef1245) 
                if self._state.backtracking == 0:
                    stream_41.add(char_literal157)
                self._state.following.append(self.FOLLOW_activityListDef_in_doBlockDef1247)
                activityListDef158 = self.activityListDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_activityListDef.add(activityListDef158.tree)
                char_literal159=self.match(self.input, 42, self.FOLLOW_42_in_doBlockDef1250) 
                if self._state.backtracking == 0:
                    stream_42.add(char_literal159)

                # AST Rewrite
                # elements: activityListDef, 58
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
                    root_1 = self._adaptor.becomeRoot(stream_58.nextNode(), root_1)

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

        string_literal160 = None
        string_literal161 = None
        char_literal163 = None
        char_literal165 = None
        roleName162 = None

        activityListDef164 = None


        string_literal160_tree = None
        string_literal161_tree = None
        char_literal163_tree = None
        char_literal165_tree = None
        stream_59 = RewriteRuleTokenStream(self._adaptor, "token 59")
        stream_42 = RewriteRuleTokenStream(self._adaptor, "token 42")
        stream_41 = RewriteRuleTokenStream(self._adaptor, "token 41")
        stream_60 = RewriteRuleTokenStream(self._adaptor, "token 60")
        stream_activityListDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityListDef")
        stream_roleName = RewriteRuleSubtreeStream(self._adaptor, "rule roleName")
        try:
            try:
                # src/SavedFSM/Monitor.g:131:13: ( 'interrupt' 'by' roleName '{' activityListDef '}' -> ^( 'interrupt' roleName activityListDef ) )
                # src/SavedFSM/Monitor.g:131:15: 'interrupt' 'by' roleName '{' activityListDef '}'
                pass 
                string_literal160=self.match(self.input, 59, self.FOLLOW_59_in_interruptDef1268) 
                if self._state.backtracking == 0:
                    stream_59.add(string_literal160)
                string_literal161=self.match(self.input, 60, self.FOLLOW_60_in_interruptDef1270) 
                if self._state.backtracking == 0:
                    stream_60.add(string_literal161)
                self._state.following.append(self.FOLLOW_roleName_in_interruptDef1272)
                roleName162 = self.roleName()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_roleName.add(roleName162.tree)
                char_literal163=self.match(self.input, 41, self.FOLLOW_41_in_interruptDef1274) 
                if self._state.backtracking == 0:
                    stream_41.add(char_literal163)
                self._state.following.append(self.FOLLOW_activityListDef_in_interruptDef1276)
                activityListDef164 = self.activityListDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_activityListDef.add(activityListDef164.tree)
                char_literal165=self.match(self.input, 42, self.FOLLOW_42_in_interruptDef1278) 
                if self._state.backtracking == 0:
                    stream_42.add(char_literal165)

                # AST Rewrite
                # elements: activityListDef, 59, roleName
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
                    root_1 = self._adaptor.becomeRoot(stream_59.nextNode(), root_1)

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

        doBlockDef166 = None

        interruptDef167 = None


        stream_interruptDef = RewriteRuleSubtreeStream(self._adaptor, "rule interruptDef")
        stream_doBlockDef = RewriteRuleSubtreeStream(self._adaptor, "rule doBlockDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:133:16: ( doBlockDef interruptDef -> ^( GLOBAL_ESCAPE doBlockDef interruptDef ) )
                # src/SavedFSM/Monitor.g:133:19: doBlockDef interruptDef
                pass 
                self._state.following.append(self.FOLLOW_doBlockDef_in_globalEscapeDef1296)
                doBlockDef166 = self.doBlockDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_doBlockDef.add(doBlockDef166.tree)
                self._state.following.append(self.FOLLOW_interruptDef_in_globalEscapeDef1299)
                interruptDef167 = self.interruptDef()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    stream_interruptDef.add(interruptDef167.tree)

                # AST Rewrite
                # elements: interruptDef, doBlockDef
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

        string_literal168 = None
        char_literal169 = None
        ANNOTATION170 = None
        char_literal172 = None
        activityDef171 = None


        string_literal168_tree = None
        char_literal169_tree = None
        ANNOTATION170_tree = None
        char_literal172_tree = None
        stream_42 = RewriteRuleTokenStream(self._adaptor, "token 42")
        stream_41 = RewriteRuleTokenStream(self._adaptor, "token 41")
        stream_ANNOTATION = RewriteRuleTokenStream(self._adaptor, "token ANNOTATION")
        stream_61 = RewriteRuleTokenStream(self._adaptor, "token 61")
        stream_activityDef = RewriteRuleSubtreeStream(self._adaptor, "rule activityDef")
        try:
            try:
                # src/SavedFSM/Monitor.g:135:13: ( 'unordered' '{' ( ( ANNOTATION )* activityDef )* '}' -> ^( PARALLEL ( ^( BRANCH activityDef ) )+ ) )
                # src/SavedFSM/Monitor.g:135:15: 'unordered' '{' ( ( ANNOTATION )* activityDef )* '}'
                pass 
                string_literal168=self.match(self.input, 61, self.FOLLOW_61_in_unorderedDef1316) 
                if self._state.backtracking == 0:
                    stream_61.add(string_literal168)
                char_literal169=self.match(self.input, 41, self.FOLLOW_41_in_unorderedDef1318) 
                if self._state.backtracking == 0:
                    stream_41.add(char_literal169)
                # src/SavedFSM/Monitor.g:135:31: ( ( ANNOTATION )* activityDef )*
                while True: #loop45
                    alt45 = 2
                    LA45_0 = self.input.LA(1)

                    if (LA45_0 == RECLABEL or (ANNOTATION <= LA45_0 <= ID) or LA45_0 == 38 or LA45_0 == 41 or LA45_0 == 43 or (48 <= LA45_0 <= 49) or (51 <= LA45_0 <= 56) or LA45_0 == 58 or LA45_0 == 61) :
                        alt45 = 1


                    if alt45 == 1:
                        # src/SavedFSM/Monitor.g:135:33: ( ANNOTATION )* activityDef
                        pass 
                        # src/SavedFSM/Monitor.g:135:33: ( ANNOTATION )*
                        while True: #loop44
                            alt44 = 2
                            LA44_0 = self.input.LA(1)

                            if (LA44_0 == ANNOTATION) :
                                alt44 = 1


                            if alt44 == 1:
                                # src/SavedFSM/Monitor.g:135:35: ANNOTATION
                                pass 
                                ANNOTATION170=self.match(self.input, ANNOTATION, self.FOLLOW_ANNOTATION_in_unorderedDef1324) 
                                if self._state.backtracking == 0:
                                    stream_ANNOTATION.add(ANNOTATION170)


                            else:
                                break #loop44
                        self._state.following.append(self.FOLLOW_activityDef_in_unorderedDef1329)
                        activityDef171 = self.activityDef()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            stream_activityDef.add(activityDef171.tree)


                    else:
                        break #loop45
                char_literal172=self.match(self.input, 42, self.FOLLOW_42_in_unorderedDef1334) 
                if self._state.backtracking == 0:
                    stream_42.add(char_literal172)

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

        set174 = None
        term173 = None

        term175 = None


        set174_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:144:6: ( term ( ( PLUS | MINUS ) term )* )
                # src/SavedFSM/Monitor.g:144:8: term ( ( PLUS | MINUS ) term )*
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_term_in_expr1359)
                term173 = self.term()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, term173.tree)
                # src/SavedFSM/Monitor.g:144:13: ( ( PLUS | MINUS ) term )*
                while True: #loop46
                    alt46 = 2
                    LA46_0 = self.input.LA(1)

                    if ((PLUS <= LA46_0 <= MINUS)) :
                        alt46 = 1


                    if alt46 == 1:
                        # src/SavedFSM/Monitor.g:144:15: ( PLUS | MINUS ) term
                        pass 
                        set174 = self.input.LT(1)
                        if (PLUS <= self.input.LA(1) <= MINUS):
                            self.input.consume()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set174))
                            self._state.errorRecovery = False

                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed

                            mse = MismatchedSetException(None, self.input)
                            raise mse


                        self._state.following.append(self.FOLLOW_term_in_expr1374)
                        term175 = self.term()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, term175.tree)


                    else:
                        break #loop46



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

        set177 = None
        factor176 = None

        factor178 = None


        set177_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:146:6: ( factor ( ( MULT | DIV ) factor )* )
                # src/SavedFSM/Monitor.g:146:8: factor ( ( MULT | DIV ) factor )*
                pass 
                root_0 = self._adaptor.nil()

                self._state.following.append(self.FOLLOW_factor_in_term1386)
                factor176 = self.factor()

                self._state.following.pop()
                if self._state.backtracking == 0:
                    self._adaptor.addChild(root_0, factor176.tree)
                # src/SavedFSM/Monitor.g:146:15: ( ( MULT | DIV ) factor )*
                while True: #loop47
                    alt47 = 2
                    LA47_0 = self.input.LA(1)

                    if ((MULT <= LA47_0 <= DIV)) :
                        alt47 = 1


                    if alt47 == 1:
                        # src/SavedFSM/Monitor.g:146:17: ( MULT | DIV ) factor
                        pass 
                        set177 = self.input.LT(1)
                        if (MULT <= self.input.LA(1) <= DIV):
                            self.input.consume()
                            if self._state.backtracking == 0:
                                self._adaptor.addChild(root_0, self._adaptor.createWithPayload(set177))
                            self._state.errorRecovery = False

                        else:
                            if self._state.backtracking > 0:
                                raise BacktrackingFailed

                            mse = MismatchedSetException(None, self.input)
                            raise mse


                        self._state.following.append(self.FOLLOW_factor_in_term1400)
                        factor178 = self.factor()

                        self._state.following.pop()
                        if self._state.backtracking == 0:
                            self._adaptor.addChild(root_0, factor178.tree)


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

        NUMBER179 = None

        NUMBER179_tree = None

        try:
            try:
                # src/SavedFSM/Monitor.g:148:8: ( NUMBER )
                # src/SavedFSM/Monitor.g:148:10: NUMBER
                pass 
                root_0 = self._adaptor.nil()

                NUMBER179=self.match(self.input, NUMBER, self.FOLLOW_NUMBER_in_factor1412)
                if self._state.backtracking == 0:

                    NUMBER179_tree = self._adaptor.createWithPayload(NUMBER179)
                    self._adaptor.addChild(root_0, NUMBER179_tree)




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
        u"\2\31\2\uffff"
        )

    DFA3_max = DFA.unpack(
        u"\2\43\2\uffff"
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


    # lookup tables for DFA #17

    DFA17_eot = DFA.unpack(
        u"\4\uffff"
        )

    DFA17_eof = DFA.unpack(
        u"\4\uffff"
        )

    DFA17_min = DFA.unpack(
        u"\2\22\2\uffff"
        )

    DFA17_max = DFA.unpack(
        u"\2\75\2\uffff"
        )

    DFA17_accept = DFA.unpack(
        u"\2\uffff\1\2\1\1"
        )

    DFA17_special = DFA.unpack(
        u"\4\uffff"
        )

            
    DFA17_transition = [
        DFA.unpack(u"\1\3\6\uffff\1\1\1\3\10\uffff\1\2\2\uffff\1\3\2\uffff"
        u"\1\3\1\2\1\3\4\uffff\2\3\1\uffff\6\3\1\uffff\1\3\2\uffff\1\3"),
        DFA.unpack(u"\1\3\6\uffff\1\1\1\3\10\uffff\1\2\2\uffff\1\3\2\uffff"
        u"\1\3\1\uffff\1\3\4\uffff\2\3\1\uffff\6\3\1\uffff\1\3\2\uffff\1"
        u"\3"),
        DFA.unpack(u""),
        DFA.unpack(u"")
    ]

    # class definition for DFA #17

    class DFA17(DFA):
        pass


    # lookup tables for DFA #35

    DFA35_eot = DFA.unpack(
        u"\32\uffff"
        )

    DFA35_eof = DFA.unpack(
        u"\1\1\31\uffff"
        )

    DFA35_min = DFA.unpack(
        u"\1\22\1\uffff\1\45\1\32\1\uffff\1\32\2\44\1\5\1\32\1\46\1\5\1\32"
        u"\1\46\6\44\2\5\4\44"
        )

    DFA35_max = DFA.unpack(
        u"\1\75\1\uffff\1\60\1\32\1\uffff\1\32\2\57\1\6\1\32\1\60\1\6\1\32"
        u"\1\60\2\54\1\57\2\54\1\57\2\6\4\54"
        )

    DFA35_accept = DFA.unpack(
        u"\1\uffff\1\2\2\uffff\1\1\25\uffff"
        )

    DFA35_special = DFA.unpack(
        u"\32\uffff"
        )

            
    DFA35_transition = [
        DFA.unpack(u"\1\4\6\uffff\1\4\1\2\13\uffff\1\4\2\uffff\1\4\1\1\1"
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

    # class definition for DFA #35

    class DFA35(DFA):
        pass


 

    FOLLOW_ANNOTATION_in_description241 = frozenset([25, 34])
    FOLLOW_importProtocolStatement_in_description248 = frozenset([25, 34, 35])
    FOLLOW_importTypeStatement_in_description252 = frozenset([25, 34, 35])
    FOLLOW_ANNOTATION_in_description261 = frozenset([25, 35])
    FOLLOW_protocolDef_in_description266 = frozenset([1])
    FOLLOW_34_in_importProtocolStatement277 = frozenset([35])
    FOLLOW_35_in_importProtocolStatement279 = frozenset([26])
    FOLLOW_importProtocolDef_in_importProtocolStatement281 = frozenset([36, 37])
    FOLLOW_36_in_importProtocolStatement285 = frozenset([26])
    FOLLOW_importProtocolDef_in_importProtocolStatement288 = frozenset([36, 37])
    FOLLOW_37_in_importProtocolStatement293 = frozenset([1])
    FOLLOW_ID_in_importProtocolDef302 = frozenset([38])
    FOLLOW_38_in_importProtocolDef304 = frozenset([27])
    FOLLOW_StringLiteral_in_importProtocolDef307 = frozenset([1])
    FOLLOW_34_in_importTypeStatement320 = frozenset([26, 27])
    FOLLOW_simpleName_in_importTypeStatement324 = frozenset([26, 27])
    FOLLOW_importTypeDef_in_importTypeStatement329 = frozenset([36, 37, 38])
    FOLLOW_36_in_importTypeStatement333 = frozenset([26, 27])
    FOLLOW_importTypeDef_in_importTypeStatement336 = frozenset([36, 37, 38])
    FOLLOW_38_in_importTypeStatement343 = frozenset([27])
    FOLLOW_StringLiteral_in_importTypeStatement346 = frozenset([37])
    FOLLOW_37_in_importTypeStatement351 = frozenset([1])
    FOLLOW_dataTypeDef_in_importTypeDef362 = frozenset([39])
    FOLLOW_39_in_importTypeDef364 = frozenset([26])
    FOLLOW_ID_in_importTypeDef370 = frozenset([1])
    FOLLOW_StringLiteral_in_dataTypeDef378 = frozenset([1])
    FOLLOW_ID_in_simpleName386 = frozenset([1])
    FOLLOW_35_in_protocolDef394 = frozenset([26])
    FOLLOW_protocolName_in_protocolDef396 = frozenset([40, 41, 43])
    FOLLOW_40_in_protocolDef400 = frozenset([26])
    FOLLOW_roleName_in_protocolDef402 = frozenset([41, 43])
    FOLLOW_parameterDefs_in_protocolDef409 = frozenset([41])
    FOLLOW_41_in_protocolDef414 = frozenset([18, 25, 26, 38, 41, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_protocolBlockDef_in_protocolDef416 = frozenset([25, 35, 42])
    FOLLOW_ANNOTATION_in_protocolDef422 = frozenset([25, 35])
    FOLLOW_protocolDef_in_protocolDef427 = frozenset([25, 35, 42])
    FOLLOW_42_in_protocolDef432 = frozenset([1])
    FOLLOW_ID_in_protocolName460 = frozenset([1])
    FOLLOW_43_in_parameterDefs468 = frozenset([45])
    FOLLOW_roleparameDef_in_parameterDefs470 = frozenset([36, 44])
    FOLLOW_36_in_parameterDefs474 = frozenset([45])
    FOLLOW_roleparameDef_in_parameterDefs476 = frozenset([36, 44])
    FOLLOW_44_in_parameterDefs481 = frozenset([1])
    FOLLOW_45_in_roleparameDef497 = frozenset([26])
    FOLLOW_simpleName_in_roleparameDef499 = frozenset([1])
    FOLLOW_activityListDef_in_protocolBlockDef510 = frozenset([1])
    FOLLOW_41_in_blockDef521 = frozenset([18, 25, 26, 38, 41, 42, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_activityListDef_in_blockDef523 = frozenset([42])
    FOLLOW_42_in_blockDef525 = frozenset([1])
    FOLLOW_ASSERTION_in_assertDef547 = frozenset([1])
    FOLLOW_ANNOTATION_in_activityListDef569 = frozenset([18, 25, 26, 38, 41, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_activityDef_in_activityListDef574 = frozenset([1, 18, 25, 26, 38, 41, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_INT_in_primitivetype590 = frozenset([1])
    FOLLOW_STRING_in_primitivetype596 = frozenset([1])
    FOLLOW_introducesDef_in_activityDef609 = frozenset([37])
    FOLLOW_interactionDef_in_activityDef613 = frozenset([37])
    FOLLOW_inlineDef_in_activityDef617 = frozenset([37])
    FOLLOW_runDef_in_activityDef621 = frozenset([37])
    FOLLOW_recursionDef_in_activityDef625 = frozenset([37])
    FOLLOW_endDef_in_activityDef629 = frozenset([37])
    FOLLOW_RECLABEL_in_activityDef633 = frozenset([37])
    FOLLOW_37_in_activityDef637 = frozenset([1])
    FOLLOW_choiceDef_in_activityDef646 = frozenset([1])
    FOLLOW_directedChoiceDef_in_activityDef650 = frozenset([1])
    FOLLOW_parallelDef_in_activityDef654 = frozenset([1])
    FOLLOW_repeatDef_in_activityDef658 = frozenset([1])
    FOLLOW_unorderedDef_in_activityDef662 = frozenset([1])
    FOLLOW_recBlockDef_in_activityDef669 = frozenset([1])
    FOLLOW_globalEscapeDef_in_activityDef673 = frozenset([1])
    FOLLOW_roleDef_in_introducesDef681 = frozenset([46])
    FOLLOW_46_in_introducesDef683 = frozenset([26])
    FOLLOW_roleDef_in_introducesDef685 = frozenset([1, 36])
    FOLLOW_36_in_introducesDef689 = frozenset([26])
    FOLLOW_roleDef_in_introducesDef691 = frozenset([1, 36])
    FOLLOW_ID_in_roleDef702 = frozenset([1])
    FOLLOW_ID_in_roleName713 = frozenset([1])
    FOLLOW_ID_in_typeReferenceDef724 = frozenset([1])
    FOLLOW_typeReferenceDef_in_interactionSignatureDef735 = frozenset([1, 43])
    FOLLOW_43_in_interactionSignatureDef738 = frozenset([26])
    FOLLOW_valueDecl_in_interactionSignatureDef740 = frozenset([36, 44])
    FOLLOW_36_in_interactionSignatureDef743 = frozenset([26])
    FOLLOW_valueDecl_in_interactionSignatureDef745 = frozenset([36, 44])
    FOLLOW_44_in_interactionSignatureDef749 = frozenset([1])
    FOLLOW_43_in_interactionSignatureDef773 = frozenset([26])
    FOLLOW_valueDecl_in_interactionSignatureDef775 = frozenset([36, 44])
    FOLLOW_36_in_interactionSignatureDef778 = frozenset([26])
    FOLLOW_valueDecl_in_interactionSignatureDef780 = frozenset([36, 44])
    FOLLOW_44_in_interactionSignatureDef784 = frozenset([1])
    FOLLOW_ID_in_valueDecl804 = frozenset([1, 47])
    FOLLOW_47_in_valueDecl807 = frozenset([5, 6])
    FOLLOW_primitivetype_in_valueDecl810 = frozenset([1])
    FOLLOW_valueDecl_in_firstValueDecl821 = frozenset([1])
    FOLLOW_interactionSignatureDef_in_interactionDef836 = frozenset([38, 48])
    FOLLOW_38_in_interactionDef842 = frozenset([26])
    FOLLOW_roleName_in_interactionDef847 = frozenset([28])
    FOLLOW_assertDef_in_interactionDef851 = frozenset([1])
    FOLLOW_48_in_interactionDef875 = frozenset([26])
    FOLLOW_roleName_in_interactionDef877 = frozenset([28])
    FOLLOW_assertDef_in_interactionDef881 = frozenset([1])
    FOLLOW_49_in_choiceDef902 = frozenset([40, 41])
    FOLLOW_40_in_choiceDef906 = frozenset([26])
    FOLLOW_roleName_in_choiceDef908 = frozenset([40, 41])
    FOLLOW_blockDef_in_choiceDef913 = frozenset([1, 50])
    FOLLOW_50_in_choiceDef917 = frozenset([40, 41])
    FOLLOW_blockDef_in_choiceDef919 = frozenset([1, 50])
    FOLLOW_38_in_directedChoiceDef940 = frozenset([26])
    FOLLOW_roleName_in_directedChoiceDef942 = frozenset([41, 48])
    FOLLOW_48_in_directedChoiceDef949 = frozenset([26])
    FOLLOW_roleName_in_directedChoiceDef951 = frozenset([36, 41])
    FOLLOW_36_in_directedChoiceDef955 = frozenset([26])
    FOLLOW_roleName_in_directedChoiceDef958 = frozenset([36, 41])
    FOLLOW_41_in_directedChoiceDef966 = frozenset([26, 43])
    FOLLOW_onMessageDef_in_directedChoiceDef970 = frozenset([26, 42, 43])
    FOLLOW_42_in_directedChoiceDef975 = frozenset([1])
    FOLLOW_interactionSignatureDef_in_onMessageDef982 = frozenset([47])
    FOLLOW_47_in_onMessageDef984 = frozenset([18, 25, 26, 38, 41, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_activityList_in_onMessageDef986 = frozenset([1])
    FOLLOW_ANNOTATION_in_activityList999 = frozenset([18, 25, 26, 38, 41, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_activityDef_in_activityList1004 = frozenset([1, 18, 25, 26, 38, 41, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_51_in_repeatDef1014 = frozenset([40, 41])
    FOLLOW_40_in_repeatDef1018 = frozenset([26])
    FOLLOW_roleName_in_repeatDef1020 = frozenset([36, 40, 41])
    FOLLOW_36_in_repeatDef1024 = frozenset([26])
    FOLLOW_roleName_in_repeatDef1026 = frozenset([36, 40, 41])
    FOLLOW_blockDef_in_repeatDef1034 = frozenset([1])
    FOLLOW_52_in_recBlockDef1050 = frozenset([26])
    FOLLOW_labelName_in_recBlockDef1052 = frozenset([40, 41])
    FOLLOW_blockDef_in_recBlockDef1054 = frozenset([1])
    FOLLOW_ID_in_labelName1071 = frozenset([1])
    FOLLOW_labelName_in_recursionDef1083 = frozenset([1])
    FOLLOW_53_in_endDef1099 = frozenset([1])
    FOLLOW_54_in_runDef1109 = frozenset([26])
    FOLLOW_protocolRefDef_in_runDef1112 = frozenset([38, 43])
    FOLLOW_43_in_runDef1116 = frozenset([26])
    FOLLOW_parameter_in_runDef1119 = frozenset([36, 44])
    FOLLOW_36_in_runDef1123 = frozenset([26])
    FOLLOW_parameter_in_runDef1126 = frozenset([36, 44])
    FOLLOW_44_in_runDef1131 = frozenset([38])
    FOLLOW_38_in_runDef1137 = frozenset([26])
    FOLLOW_roleName_in_runDef1139 = frozenset([1])
    FOLLOW_ID_in_protocolRefDef1147 = frozenset([1, 40])
    FOLLOW_40_in_protocolRefDef1151 = frozenset([26])
    FOLLOW_roleName_in_protocolRefDef1153 = frozenset([1])
    FOLLOW_ID_in_declarationName1164 = frozenset([1])
    FOLLOW_declarationName_in_parameter1172 = frozenset([1])
    FOLLOW_55_in_inlineDef1181 = frozenset([26])
    FOLLOW_protocolRefDef_in_inlineDef1184 = frozenset([1, 43])
    FOLLOW_43_in_inlineDef1188 = frozenset([26])
    FOLLOW_parameter_in_inlineDef1191 = frozenset([36, 44])
    FOLLOW_36_in_inlineDef1195 = frozenset([26])
    FOLLOW_parameter_in_inlineDef1198 = frozenset([36, 44])
    FOLLOW_44_in_inlineDef1203 = frozenset([1])
    FOLLOW_56_in_parallelDef1215 = frozenset([40, 41])
    FOLLOW_blockDef_in_parallelDef1217 = frozenset([1, 57])
    FOLLOW_57_in_parallelDef1221 = frozenset([40, 41])
    FOLLOW_blockDef_in_parallelDef1223 = frozenset([1, 57])
    FOLLOW_58_in_doBlockDef1243 = frozenset([41])
    FOLLOW_41_in_doBlockDef1245 = frozenset([18, 25, 26, 38, 41, 42, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_activityListDef_in_doBlockDef1247 = frozenset([42])
    FOLLOW_42_in_doBlockDef1250 = frozenset([1])
    FOLLOW_59_in_interruptDef1268 = frozenset([60])
    FOLLOW_60_in_interruptDef1270 = frozenset([26])
    FOLLOW_roleName_in_interruptDef1272 = frozenset([41])
    FOLLOW_41_in_interruptDef1274 = frozenset([18, 25, 26, 38, 41, 42, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_activityListDef_in_interruptDef1276 = frozenset([42])
    FOLLOW_42_in_interruptDef1278 = frozenset([1])
    FOLLOW_doBlockDef_in_globalEscapeDef1296 = frozenset([59])
    FOLLOW_interruptDef_in_globalEscapeDef1299 = frozenset([1])
    FOLLOW_61_in_unorderedDef1316 = frozenset([41])
    FOLLOW_41_in_unorderedDef1318 = frozenset([18, 25, 26, 38, 41, 42, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_ANNOTATION_in_unorderedDef1324 = frozenset([18, 25, 26, 38, 41, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_activityDef_in_unorderedDef1329 = frozenset([18, 25, 26, 38, 41, 42, 43, 48, 49, 51, 52, 53, 54, 55, 56, 58, 61])
    FOLLOW_42_in_unorderedDef1334 = frozenset([1])
    FOLLOW_term_in_expr1359 = frozenset([1, 7, 8])
    FOLLOW_set_in_expr1363 = frozenset([29])
    FOLLOW_term_in_expr1374 = frozenset([1, 7, 8])
    FOLLOW_factor_in_term1386 = frozenset([1, 9, 10])
    FOLLOW_set_in_term1390 = frozenset([29])
    FOLLOW_factor_in_term1400 = frozenset([1, 9, 10])
    FOLLOW_NUMBER_in_factor1412 = frozenset([1])



def main(argv, stdin=sys.stdin, stdout=sys.stdout, stderr=sys.stderr):
    from antlr3.main import ParserMain
    main = ParserMain("MonitorLexer", MonitorParser)
    main.stdin = stdin
    main.stdout = stdout
    main.stderr = stderr
    main.execute(argv)


if __name__ == '__main__':
    main(sys.argv)
