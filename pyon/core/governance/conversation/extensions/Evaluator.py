import sys
import ast 

test = "x + 3 and 7 > x"

class AssertionParser(object):
    def parse(annotation):
        return str(annotation)

class Assertion(object):
    def __init__(self, expressin):
        parser = AnnotationParser() 
        self.expression = parser.parse(expression)

class AssertionChecker():
    def check(self, assertion, context):
        assertion = assertion.strip()
        return eval(assertion, context)
    
def checkMessages(fsm):
    #print "Message is checked: \%s" \%(fsm.input_symbol)
    #plugin.check(dsm) for plugin in fsm.plugins
    pass
def main(args):
     my_dict = {}
     context = {1: ('x', 'int')}
     state = 1
     val = 5
     #print ast.literal_eval(test)
     my_dict.setdefault('x', -5)
     my_dict.setdefault('y', 1)
     checker = AssertionChecker()
     s = checker.check(test, my_dict)
     types = {'int': int , 'string':str}
     (_, type) = context.get(state)
     print test1
     print types[type](val)
"""
cont
"""    

if __name__ =="__main__":
    sys.exit(main(sys.argv))
