class AssertionParser(object):
    START_TOCKEN = '@{'
    END_TOCKEN = '}' 
    def parse(self, assertion):
        assertion = str(assertion)
        assertion = assertion.replace(self.START_TOCKEN, '')
        assertion = assertion.replace(self.END_TOCKEN, '')
        return  assertion.strip()

class Assertion(object):
    def __init__(self, assertion_statement):
        self.statement = assertion_statement
    @classmethod
    def create(cls, assertion_statement):
        parser = AssertionParser()
        parsed_statement = parser.parse(assertion_statement)
        return Assertion(parsed_statement)
        
    def check(self, context):
        print "Logic is checkeeeeeeeeeeeeed@@@@@@@@@@@________________________________@@@@@@@@@@@@@@@@@@@@@@@@"
        return eval(self.statement, context)
 
 
 
    
test = '@{s=="Hello"}'
context = {'x': 3, 'y':5, 's':"Hello"}
def main():
    print 'Ihu'
    assertion = Assertion.create(test)
    print assertion.statement
    p = assertion.check(context) 
    if p: print ' It Is True'
    else: print 'It Is False'
     
if __name__=="__main__":
    main()
     
