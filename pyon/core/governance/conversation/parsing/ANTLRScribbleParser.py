import sys
import antlr3
from antlr3.tree import CommonTreeAdaptor
from antlr3.tree import CommonTree
from antlr3.tree import Tree
from antlr3.tree import CommonTreeNodeStream
from antlr3.tree import *
from MonitorLexer import MonitorLexer
from MonitorParser import MonitorParser
from baseParser import BaseParser 
from BuildFSM import BuildFSM
class ANTLRScribbleParser(BaseParser):
    # TODO: add exception handling for wrong file extension
    def parse(self, filename):
        input = antlr3.FileStream (filename)
        lexer = MonitorLexer (input)
        tokens = antlr3.CommonTokenStream (lexer)
        parser = MonitorParser (tokens)
        adaptor = CommonTreeAdaptor()
        parser.setTreeAdaptor(adaptor)
        res = parser.description ()
        return res
    def walk(self, parsedResult):
        ast = parsedResult.tree;
        nodes = CommonTreeNodeStream(ast);
        fsmBuilder =  BuildFSM(nodes);
        fsmBuilder.description()
        return fsmBuilder

def main(args):
     pass
        
if __name__ == "__main__":
    sys.exit (main (sys.argv))