""" Testing out various ways to do composite objects in yaml. """

from pyon.core.object import IonObjectRegistry
import yaml

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

obj_reg = IonObjectRegistry()
obj_def = obj_reg.register_yaml(yaml_def_raw)[0]
print obj_def

class PyonYamlLoader(yaml.Loader):
    #def construct_object(self, node, deep=False):
    #    yaml.Loader.construct_object(self, node, deep)
    pass

def foo_constructor(loader, node):
    if isinstance(node, yaml.MappingNode):
        value = loader.construct_mapping(node)
    else:
        value = {}
    return obj_reg.new(obj_def, value)

tag = u'!%s' % (obj_def.type.name)
yaml.add_constructor(tag, foo_constructor, Loader=PyonYamlLoader)
yaml.add_constructor(tag, foo_constructor, Loader=PyonYamlLoader)
obj = yaml.load_all(yaml_raw, Loader=PyonYamlLoader)
print list(obj)
