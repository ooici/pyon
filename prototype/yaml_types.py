""" Testing out various ways to do composite objects in yaml. """

import yaml

yaml_raw = '''
%TAG ! tag:oceanobservatories.org,2011:
---
#!Foo
#  name: ''
#  age: 0
  
things:
  foo: !Foo "{ name: bob, age: 22 }"
  #  name: bob
  #  age: 22
'''

obj = yaml.load_all(yaml_raw)
print list(obj)
