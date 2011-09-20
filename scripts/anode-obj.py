#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from collections import OrderedDict
import datetime
import fnmatch
import os
import re
import sys
import argparse

import yaml
# Do not remove the
import anode.util.yaml_ordered_dict

class AnodeServiceDefinitionError(Exception):
    pass

templates = {
      'file':
'''#!/usr/bin/env python

from zope.interface import Interface, implements

from collections import OrderedDict, defaultdict

from anode.service.service import BaseService

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
'''
    , 'svcname':
'    name = \'{name}\''
    , 'depends':
'    dependencies = {namelist}'
    , 'method':
'''
    def {name}({args}):
        pass
'''
    , 'arg': '{name}={val}'
}

description = 'Anode utility for generating interfaces from object definitions (and vice versa).'
parser = argparse.ArgumentParser(description=description)
parser.add_argument('action', type=str, default='generate', choices=['generate'], help='Which action to perform.')
args = parser.parse_args()

if os.getcwd().endswith('scripts'):
    sys.exit('This script needs to be run from the anode root.')

if args.action == 'generate':
    service_dir, interface_dir = 'obj/services', 'interface'
    if not os.path.exists(interface_dir):
        os.makedirs(interface_dir)

    # Clear old generated files
    files = os.listdir(interface_dir)
    for file in fnmatch.filter(files, '*.py') + fnmatch.filter(files, '*.pyc'):
        os.unlink(os.path.join(interface_dir, file))

    open(os.path.join(interface_dir, '__init__.py'), 'w').close()

    # Generate the new definitions, for now giving each yaml file its own python service
    file_re = re.compile('(obj)/(.*)[.](yml)')
    for root, dirs, files in os.walk(service_dir):
        for filename in fnmatch.filter(files, '*.yml'):
            yaml_file = os.path.join(root, filename)
            file_match = file_re.match(yaml_file)
            if file_match is None: continue

            file_path = file_match.group(2)
            interface_base, interface_name = os.path.dirname(file_path), os.path.basename(file_path)
            interface_file = os.path.join('interface', interface_base, 'i%s.py' % interface_name)

            parent_dir = os.path.dirname(interface_file)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
            pkg_file = os.path.join(parent_dir, '__init__.py')
            if not os.path.exists(pkg_file):
                open(pkg_file, 'w').close()

            service_name = None
            dependencies = []
            methods = []
            yaml_text = open(yaml_file, 'r').read()
            defs = yaml.load_all(yaml_text)
            for def_set in defs:
                for name,_def in def_set.iteritems():
                    # Handle name declaration
                    if name == '_name':
                        service_name = _def

                    # Jandle dependency declaration
                    elif name == '_dependencies':
                        dependencies = _def

                    # Handle service operations
                    else:
                        # TODO: Handle more than one definition version for the same object type

                        # If the service specifies "in" and "out" blocks
                        if isinstance(_def, dict) and 'in' in _def:
                            _def = _def['in']

                        # Handle case where method has no parameters
                        if _def is None:
                            args_str = ''
                        else:
                            args = []
                            for key,val in _def.iteritems():
                                if isinstance(val, basestring):
                                    val = "'%s'" % (val)
                                elif isinstance(val, datetime.datetime):
                                    # TODO: generate the datetime code
                                    val = "'%s'" % (val)
                                elif isinstance(val, OrderedDict):
                                    val = dict(val)
                                args.append(templates['arg'].format(name=key, val=val))
                            args_str = ', '.join(args)

                        methods.append(templates['method'].format(name=name, args=args_str))

            if service_name is None:
                raise AnodeServiceDefinitionError("Service definition file %s does not define _name attribute" % yaml_file)
            service_name_str = templates['svcname'].format(name=service_name)
            dependencies_str = templates['depends'].format(namelist=dependencies)
            methods_str = ''.join(methods)
            class_name = interface_name.title().replace('_', '').replace('-', '')
            _class = templates['class'].format(name=class_name, servicename=service_name_str, dependencies=dependencies_str, methods=methods_str)

            interface_contents = templates['file'].format(classes=_class)
            open(interface_file, 'w').write(interface_contents)


