#!/usr/bin/env python
    
# Ion utility for generating interfaces from object definitions (and vice versa).
    
__author__ = 'Adam R. Smith, Thomas Lennan, Stephen Henrie, Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'
  

import ast, datetime, fnmatch, inspect, pkgutil, os, re, sys, string, yaml, hashlib, argparse

from collections import OrderedDict
from collections import OrderedDict
from pyon.core.path import list_files_recursive
from pyon.service.service import BaseService
from pyon.util.containers import named_any

# Do not remove any of the imports below this comment!!!!!!
from pyon.util import yaml_ordered_dict


from pyon.util.object_model_generator import ObjectModelGenerator
from pyon.util.message_object_generator import MessageObjectGenerator
from pyon.util.service_object_generator import ServiceObjectGenerator



#
#
#
def main():

    model_object   = ObjectModelGenerator ()
    message_object = MessageObjectGenerator ()
    service_object = ServiceObjectGenerator ()


    print "Forcing --force, we keep changing generate_interfaces, sorry!"
    if os.getcwd().endswith('scripts'):
        sys.exit('This script needs to be run from the pyon root.')


    # Create dir
    service_dir, interface_dir = 'obj/services', 'interface'
    if not os.path.exists(interface_dir):
        os.makedirs(interface_dir)


    # Clear old generated files
    files = os.listdir(interface_dir)
    for file in fnmatch.filter(files, '*.pyc'):
        os.unlink(os.path.join(interface_dir, file))

    for file in fnmatch.filter(files, '*.html'):
        os.unlink(os.path.join(interface_dir, file))
        
    open(os.path.join(interface_dir, '__init__.py'), 'w').close()


    # Generate objects
    model_object.generate ()
    message_object.generate ()
    service_object.generate ()




if __name__ == '__main__':
      main()


