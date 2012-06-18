#!/usr/bin/env python
# Ion utility for generating interfaces from object definitions (and vice versa).
__author__ = 'Adam R. Smith, Thomas Lennan, Stephen Henrie, Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

import fnmatch
import os
import sys
import argparse
from pyon.core.interfaces.object_model_generator import ObjectModelGenerator
from pyon.core.interfaces.message_object_generator import MessageObjectGenerator
from pyon.core.interfaces.service_object_generator import ServiceObjectGenerator


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
    parser.add_argument('-n', '--sysname', action='store', help='System name')
    parser.add_argument('-ry', '--read_from_yaml_file', action='store_true',
                        help='Read configuration from YAML files instead of datastore - Default')
    parser.add_argument('-rd', '--read_from_datastore', action='store_true',
                        help='Read configuration from datastore.')
    opts = parser.parse_args()
    opts.system_name = 'ion_%s' % os.uname()[1].replace('.', '_').lower() \
                        if not opts.sysname else opts.sysname

    opts.force = True
    if not opts.read_from_datastore and not opts.read_from_yaml_file:
        opts.read_from_yaml_file = True
    elif opts.read_from_datastore:
        opts.read_from_yaml_file = False
    print "Forcing --force, we keep changing generate_interfaces!"

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
    model_object.generate(opts)
    message_object.generate(opts)
    exitcode = service_object.generate(opts)
    sys.exit(exitcode)

if __name__ == '__main__':
    main()
