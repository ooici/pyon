#!/usr/bin/env python

"""Utility for generating Python interfaces from object and services definitions"""

__author__ = 'Adam R. Smith, Thomas Lennan, Stephen Henrie, Dave Foster <dfoster@asascience.com>'

import fnmatch
import os
import sys
import argparse

from pyon.core.interfaces.object_model_generator import ObjectModelGenerator
from pyon.core.interfaces.message_object_generator import MessageObjectGenerator
from pyon.core.interfaces.service_object_generator import ServiceObjectGenerator
from pyon.util.containers import get_default_sysname

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true',
                        help='Do not do MD5 comparisons, always generate new files')
    parser.add_argument('-d', '--dryrun', action='store_true',
                        help='Do not generate new files, just print status and'
                             ' exit with 1 if changes need to be made')
    parser.add_argument('-sd', '--servicedoc', action='store_true',
                        help='Generate HTML service doc inclusion files')
    parser.add_argument('-od', '--objectdoc', action='store_true',
                        help='Generate HTML object doc files')
    parser.add_argument('-s', '--sysname', action='store', help='System name')
    parser.add_argument('-ry', '--read_from_yaml_file', action='store_true',
                        help='Read configuration from YAML files instead of datastore - Default')
    parser.add_argument('-rd', '--read_from_datastore', action='store_true',
                        help='Read configuration from datastore.')
    opts = parser.parse_args()

    print "generate_interfaces: ION interface generator with options:" , str(opts)

    print "generate_interfaces: Create directories and cleaning up..."
    opts.system_name = opts.sysname or get_default_sysname()

    from pyon.core import bootstrap
    bootstrap.testing = False

    opts.force = True
    if not opts.read_from_datastore and not opts.read_from_yaml_file:
        opts.read_from_yaml_file = True
    elif opts.read_from_datastore:
        opts.read_from_yaml_file = False
    #print "Forcing --force, we keep changing generate_interfaces!"

    model_object = ObjectModelGenerator(system_name=opts.system_name,
                        read_from_yaml_file=opts.read_from_yaml_file)

    message_object = MessageObjectGenerator(system_name=opts.system_name,
                        read_from_yaml_file=opts.read_from_yaml_file)

    service_object = ServiceObjectGenerator(system_name=opts.system_name,
                        read_from_yaml_file=opts.read_from_yaml_file)

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
    print "generate_interfaces: Generating object interfaces from object definitions..."
    model_object.generate(opts)

    print "generate_interfaces: Generating message interfaces from service definitions..."
    message_object.generate(opts)

    print "generate_interfaces: Generating service interfaces from service definitions..."
    exitcode = service_object.generate(opts)

    print "generate_interfaces: Completed with exit code:" , exitcode
    sys.exit(exitcode)

if __name__ == '__main__':
    main()
