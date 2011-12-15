""" Testing out various ways to do composite objects in yaml. """

#from pyon.core.object import IonObjectRegistry
import yaml
from yaml.scanner import Scanner
from yaml.reader import Reader
from yaml.parser import Parser
from yaml.composer import Composer
from yaml.constructor import Constructor
from yaml.resolver import Resolver


yaml_def_raw = '''
Foo:
  name: '<default>'
  age: 22
'''

yaml_raw = '''
things:
  #foo: !Foo "{ name: bob, age: 22 }"
  foo: !Foo
    name: bob
    age: 22

  foo2: !Foo
'''


yaml_comment = '''
  # Before Foo
Foo:
  # Before name
  name: some
  age: 22 # After age
  addr:
    some: more

# Before Bar
Bar:
  # Inside Bar
  name: hi
  dict:
    one: a # Inline one
    # Comment two
    two: b
# End comment
'''


#obj_reg = IonObjectRegistry()
#obj_def = obj_reg.register_yaml(yaml_def_raw)[0]
#print obj_def

class PyonYamlScanner(Scanner):

    def fetch_more_tokens(self):
        comment_in, comment = self.scan_to_next_token()
        if comment_in or comment:
            print "COMMENT", comment_in, "/", comment

        res = super(PyonYamlScanner, self).fetch_more_tokens()
        print "TOKEN", self.tokens, self.indent

        if comment_in and getattr(self, "_attach_token", None):
            # Add comment to first token that came before
            print " Adding inline comment to", self._attach_token
            self._attach_token._comment = comment_in

        if comment and len(self.tokens) >= 1:
            # Add comment to first token detected after comment
            print " Adding comment to", self.tokens[0]
            self.tokens[0]._comment = comment

        for i, token in enumerate(self.tokens):
            if token.__class__.__name__.endswith("KeyToken"):
                self._attach_token = self.tokens[i+1]

        return res

    def scan_to_next_token(self):
        # Original scanner function with additional comment extraction
        cmt_buf = []
        cmt_buf_inline = None
        inline_comment = True

        if self.index == 0 and self.peek() == u'\uFEFF':
            self.forward()
        found = False
        while not found:
            while self.peek() == u' ':
                self.forward()
            if self.peek() == u'#':
                while self.peek() not in u'\0\r\n\x85\u2028\u2029':
                    cmt_buf.append(self.peek())
                    self.forward()
            if self.scan_line_break():
                if inline_comment:
                    cmt_buf_inline = cmt_buf
                    cmt_buf = []
                    inline_comment = False
                if not self.flow_level:
                    self.allow_simple_key = True
            else:
                found = True

        cmt_inline = "".join(cmt_buf_inline) if cmt_buf_inline else None
        cmt_inline = cmt_inline if str(cmt_inline).startswith('#') else None

        cmt = "".join(cmt_buf)
        cmt = cmt if str(cmt).startswith('#') else None

        return (cmt_inline, cmt)

class PyonYamlLoader(Reader, PyonYamlScanner, Parser, Composer, Constructor, Resolver):
    def __init__(self, stream):
        Reader.__init__(self, stream)
        PyonYamlScanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        Constructor.__init__(self)
        Resolver.__init__(self)

def foo_constructor(loader, node):
    if isinstance(node, yaml.MappingNode):
        value = loader.construct_mapping(node)
    else:
        value = {}
    return obj_reg.new(obj_def, value)

#tag = u'!%s' % (obj_def.type.name)
#yaml.add_constructor(tag, foo_constructor, Loader=PyonYamlLoader)
#yaml.add_constructor(tag, foo_constructor, Loader=PyonYamlLoader)
#obj = yaml.load_all(yaml_raw, Loader=PyonYamlLoader)
#print list(obj)

obj = yaml.load_all(yaml_comment, Loader=PyonYamlLoader)
print list(obj)
