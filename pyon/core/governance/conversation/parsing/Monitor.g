grammar Monitor;

options {
        language=Python;
	output=AST;
	backtrack=true;
}

tokens {
	INTERACTION = 'interaction';
	INT = 'int';
	STRING = 'string';
	PLUS 	= '+' ;
	MINUS	= '-' ;
	MULT	= '*' ;
	DIV	= '/' ;
	FULLSTOP = '.' ;
	RESV = 'RESV';
	SEND = 'SEND';
	TYPE = 'TYPE';
	VALUE = 'VALUE';
	BRANCH = 'BRANCH';
	UNORDERED = 'UNORDERED';
	RECLABEL = 'RECLABEL';
	PARALLEL = 'PARALLEL';
	PROTOCOL = 'PROTOCOL';
	ASSERT = 'ASSERT';
	INT = 'int';
	STRING = 'string';
	GLOBAL_ESCAPE = 'GLOBAL_ESCAPE';
	EMPTY = 'EMPTY';
	ROLES = 'ROLES';
}

/*------------------------------------------------------------------
 * PARSER RULES
*------------------------------------------------------------------*/

description: ( ( ANNOTATION )* ( importProtocolStatement | importTypeStatement ) )* ( ANNOTATION )* protocolDef -> protocolDef;

importProtocolStatement: 'import' 'protocol' importProtocolDef ( ','! importProtocolDef )* ';'! ;

importProtocolDef: ID 'from'! StringLiteral;
						
importTypeStatement: 'import' ( simpleName )? importTypeDef ( ','! importTypeDef )* ( 'from'! StringLiteral )? ';'! ;

importTypeDef: ( dataTypeDef 'as'! )? ID ;

dataTypeDef: StringLiteral ;

simpleName: ID ;

protocolDef: 'protocol' protocolName ( 'at' roleName )? ( parameterDefs )? '{' protocolBlockDef ( ( ANNOTATION )* protocolDef )* '}'
	     -> ^(PROTOCOL roleName  parameterDefs* protocolBlockDef+);

protocolName: ID ;

parameterDefs: '(' roleparameDef ( ',' roleparameDef )* ')' -> ^(ROLES roleparameDef+);

roleparameDef: 'role' simpleName -> simpleName;

protocolBlockDef: activityListDef -> activityListDef;

blockDef: '{' activityListDef '}' -> ^(BRANCH activityListDef);
	 	  
assertDef : (ASSERTION)? -> ^(ASSERT ASSERTION?);

activityListDef: ( ( ANNOTATION )* activityDef )* -> activityDef+;

primitivetype :(INT -> INT|STRING-> STRING);

activityDef: ( introducesDef | interactionDef | inlineDef | runDef | recursionDef | endDef | RECLABEL ) ';'! | 
			choiceDef | directedChoiceDef | parallelDef | repeatDef | unorderedDef |
			recBlockDef | globalEscapeDef ;

introducesDef: roleDef 'introduces' roleDef ( ',' roleDef )* ;

roleDef: ID -> ID;

roleName: ID -> ID;

typeReferenceDef: ID ->ID;
interactionSignatureDef: ((typeReferenceDef ('(' valueDecl (',' valueDecl)* ')')? -> typeReferenceDef ^(VALUE valueDecl*))
			 | (('(' valueDecl (',' valueDecl)* ')') -> ^(VALUE valueDecl*)));

valueDecl : ID (':'! primitivetype)?;	 
firstValueDecl	: valueDecl;

// TODO: add the to roleNames
interactionDef: 
	     interactionSignatureDef (
		'from' role= roleName  (assertDef)-> ^(RESV interactionSignatureDef $role assertDef)
	      | 'to' roleName  (assertDef) -> ^(SEND interactionSignatureDef roleName assertDef));

choiceDef: 'choice' ( 'at' roleName )? blockDef ( 'or' blockDef )* -> ^('choice' blockDef+);

directedChoiceDef: ( 'from' roleName )? ( 'to' roleName ( ','! roleName )* )? '{' ( onMessageDef )+ '}';

onMessageDef: interactionSignatureDef ':' activityList ; 

activityList: ( ( ANNOTATION )* activityDef )*;

repeatDef: 'repeat' ( 'at' roleName ( ',' roleName )* )? blockDef  -> ^('repeat' blockDef);

recBlockDef: 'rec' labelName blockDef -> ^('rec' labelName blockDef);

labelName: ID -> ID ;

recursionDef: labelName -> ^(RECLABEL labelName);

// TODO: check end
endDef: 'end'^ ;

// TODO: run
runDef: 'run'^ protocolRefDef ( '('! parameter ( ','! parameter )* ')'! )? 'from' roleName ;

protocolRefDef: ID ( 'at' roleName )? ;

declarationName: ID ;

parameter: declarationName ;

// TODO: inline
inlineDef: 'inline'^ protocolRefDef ( '('! parameter ( ','! parameter )* ')'! )? ;

parallelDef: 'parallel' blockDef ( 'and' blockDef )* -> ^(PARALLEL blockDef+);

// TODO: interruptDef
doBlockDef: 'do' '{' activityListDef  '}' -> ^('do' activityListDef);	  

interruptDef: 'interrupt' 'by' roleName '{' activityListDef '}' -> ^('interrupt' roleName activityListDef);

globalEscapeDef:  doBlockDef  interruptDef -> ^(GLOBAL_ESCAPE doBlockDef interruptDef);

unorderedDef: 'unordered' '{' ( ( ANNOTATION )* activityDef )* '}' -> ^(PARALLEL ^(BRANCH activityDef)+);


/*-----------------------------------------------
TO DO:
Declaration (variables) possibly - but that may need
lookahead to avoid conflict with interactions.
-------------------------------------------------*/

expr	: term ( ( PLUS | MINUS )  term )* ;

term	: factor ( ( MULT | DIV ) factor )* ;

factor	: NUMBER ;


/*------------------------------------------------------------------
 * LEXER RULES
 *------------------------------------------------------------------*/
	 

ID : ('a'..'z'|'A'..'Z'|'_')('a'..'z'|'A'..'Z'|'0'..'9'|'_')* ;

NUMBER	: (DIGIT)+ ;

WHITESPACE : ( '\t' | ' ' | '\r' | '\n'| '\u000C' )+ 	{ $channel = HIDDEN; } ;

fragment DIGIT	: '0'..'9' ;

ASSERTION : '@{' (options {greedy=false;} : .)* '}' ;

ANNOTATION : '[[' (options {greedy=false;} : .)* ']]' ;

ML_COMMENT
    :   '/*' (options {greedy=false;} : .)* '*/' {$channel=HIDDEN;}
    ;

LINE_COMMENT : '//' (options {greedy=false;} : .)* '\n' {$channel=HIDDEN;} ;

StringLiteral: '"' ( ~('\\'|'"') )* '"' ;
