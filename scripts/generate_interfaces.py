#!/usr/bin/env python

# Ion utility for generating interfaces from object definitions (and vice versa).

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import datetime
import fnmatch
import os
import re
import sys

import yaml

# Do not remove any of the imports below this comment!!!!!!
from pyon.core.object import IonYamlLoader, service_name_from_file_name
from pyon.util import yaml_ordered_dict

class IonServiceDefinitionError(Exception):
    pass

templates = {
      'file':
'''#!/usr/bin/env python

from zope.interface import Interface, implements

from collections import OrderedDict, defaultdict

from pyon.service.service import BaseService

{classes}
'''
    , 'class':
'''class I{name}(Interface):
{methods}
'''
'''class Base{name}(BaseService):
    implements(I{name})

{servicename}
{dependencies}
{classmethods}
'''
    , 'svcname':
'    name = \'{name}\''
    , 'depends':
'    dependencies = {namelist}'
    , 'method':
'''
    def {name}({args}):
        # Return Value
        # ------------
        # {outargs}
        pass
'''
    , 'arg': '{name}={val}'
}

def build_args_str(_def, include_self=True):
    # Handle case where method has no parameters
    args = []
    if include_self: args.append('self')
        
    for key,val in (_def or {}).iteritems():
        if isinstance(val, basestring):
            val = "'%s'" % (val)
        elif isinstance(val, datetime.datetime):
            # TODO: generate the datetime code
            val = "'%s'" % (val)
        # For collections, default to an empty collection of the same base type
        elif isinstance(val, list):
            val = []
        elif isinstance(val, dict):
            val = {}
        args.append(templates['arg'].format(name=key, val=val))
        
    args_str = ', '.join(args)
    return args_str

def main():
    if os.getcwd().endswith('scripts'):
        sys.exit('This script needs to be run from the pyon root.')

    service_dir, interface_dir = 'obj/services', 'interface'
    if not os.path.exists(interface_dir):
        os.makedirs(interface_dir)

    # Clear old generated files
    files = os.listdir(interface_dir)
    for file in fnmatch.filter(files, '*.py') + fnmatch.filter(files, '*.pyc'):
        os.unlink(os.path.join(interface_dir, file))

    open(os.path.join(interface_dir, '__init__.py'), 'w').close()

    # Load data yaml files in case services define interfaces
    # in terms of common data objects
    file_re = re.compile('(obj)/(.*)[.](yml)')
    data_dir = 'obj/data'
    for root, dirs, files in os.walk(data_dir):
        for filename in fnmatch.filter(files, '*.yml'):
            yaml_file = os.path.join(root, filename)
            file_match = file_re.match(yaml_file)
            if file_match is None: continue

            yaml_text = open(yaml_file, 'r').read()
            defs = yaml.load_all(yaml_text, Loader=IonYamlLoader)
            for def_set in defs:
                for name,_def in def_set.iteritems():
                    tag = u'!%s' % (name)
                    yaml.add_constructor(tag, lambda loader, node: {})

# Generate the new definitions, for now giving each
# yaml file its own python service
    for root, dirs, files in os.walk(service_dir):
        for filename in fnmatch.filter(files, '*.yml'):
            yaml_file = os.path.join(root, filename)
            file_match = file_re.match(yaml_file)
            if file_match is None: continue

            file_path = file_match.group(2)
            interface_base, interface_name = os.path.dirname(file_path), os.path.basename(file_path)
            print 'Generating "%s"...' % (interface_name)
            interface_file = os.path.join('interface', interface_base, 'i%s.py' % interface_name)

            parent_dir = os.path.dirname(interface_file)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            pkg_file = os.path.join(parent_dir, '__init__.py')
            if not os.path.exists(pkg_file):
                open(pkg_file, 'w').close()

            yaml_text = open(yaml_file, 'r').read()
            defs = yaml.load_all(yaml_text)
            for def_set in defs:
                # Handle object definitions first; make dummy constructors so tags will parse
                if 'obj' in def_set:
                    for obj_name in def_set['obj']:
                        tag = u'!%s' % (obj_name)
                        yaml.add_constructor(tag, lambda loader, node: {})
                    continue

                service_name = def_set.get('name', None)
                dependencies = def_set.get('dependencies', None)
                methods, class_methods = [], []

                for op_name,op_def in def_set.get('methods', {}).iteritems():
                    if not op_def: continue
                    def_in, def_out = op_def.get('in', None), op_def.get('out', None)

                    args_str, class_args_str = build_args_str(def_in, False), build_args_str(def_in, True)
                    outargs_str = '\n        # '.join(yaml.dump(def_out).split('\n'))

                    methods.append(templates['method'].format(name=op_name, args=args_str, outargs=outargs_str))
                    class_methods.append(templates['method'].format(name=op_name, args=class_args_str, outargs=outargs_str))

                if service_name is None:
                    raise IonServiceDefinitionError("Service definition file %s does not define name attribute" % yaml_file)
                service_name_str = templates['svcname'].format(name=service_name)
                dependencies_str = templates['depends'].format(namelist=dependencies)
                methods_str = ''.join(methods) or '    pass\n'
                classmethods_str = ''.join(class_methods)
                class_name = service_name_from_file_name(interface_name)
                _class = templates['class'].format(name=class_name, servicename=service_name_str, dependencies=dependencies_str,
                                                       methods=methods_str, classmethods=classmethods_str)

                interface_contents = templates['file'].format(classes=_class)
                open(interface_file, 'w').write(interface_contents)

if __name__ == '__main__':
    main()
