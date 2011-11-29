#!/usr/bin/env python

# Ion utility for generating interfaces from object definitions (and vice versa).

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import datetime
import fnmatch
import inspect
import os
import re
import sys

import yaml
import hashlib
import argparse

from pyon.service.service import BaseService
from pyon.util.containers import named_any

# Adam Smith: Do not remove any of the imports below this comment!!!!!!
from pyon.core.object import IonYamlLoader, service_name_from_file_name
from pyon.util import yaml_ordered_dict #ijk5: pyflakes complains about this line...

class IonServiceDefinitionError(Exception):
    pass

class IonServiceDefinitionGenerator(object):

    INPUT_DIR     = 'obj'
    IN_SERVICES   = os.path.join(INPUT_DIR, 'services')
    IN_DATA       = os.path.join(INPUT_DIR, 'data')

    LOCAL_OVERRIDE_INPUT_DIR = 'obj-local'

    OUTPUT_DIR    = 'interface'
    OUT_SERVICES  = os.path.join(OUTPUT_DIR, 'services')


    SIGFILE     = os.path.join(OUTPUT_DIR, '.svc_signatures.yml')
    REPORTFILE  = os.path.join(OUTPUT_DIR, 'validation_report.txt')

    YAML_FILE_RE = re.compile('(' + INPUT_DIR + ')/(.*)[.](yml)')

    TEMPLATE = {
        'file':
'''#!/usr/bin/env python
#
# File generated on {when_generated}
#

from zope.interface import Interface, implements

from collections import OrderedDict, defaultdict

from pyon.service.service import BaseService

{classes}
''', 
        'class':
'''class I{name}(Interface):
{classdocstring}
{methods}
'''
'''class Base{name}(BaseService):
    implements(I{name})
{classdocstring}
{servicename}
{dependencies}
{classmethods}
''', 
        'clssdocstr':
'    """\n\
    {classdocstr}\n\
    """', 
        'svcname':
'    name = \'{name}\'', 
        'depends':
'    dependencies = {namelist}'
    , 
        'method':
'''
    def {name}({args}):
        {methoddocstring}
        # Return Value
        # ------------
        # {outargs}
        pass
''', 
        'arg': '{name}={val}', 
      'methdocstr':
'"""\n\
        {methoddocstr}\n\
        """'
        }

    def __init__(self, command_line_opts):
        self.opts = command_line_opts


    # build the argument list for a function based on a yaml defintion
    def build_args_str(self, _def, include_self=True):
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
            args.append(self.TEMPLATE['arg'].format(name=key, val=val))

        args_str = ', '.join(args)
        return args_str

    
    # place __init__.py files in parent directories of a path as appropriate
    def init_py_parent_dirs(self, path):
        #if the end case isn't in the path, abort
        endcase = os.path.abspath(self.OUTPUT_DIR)
        assert endcase in os.path.abspath(path)
        
        parent_dir = os.path.dirname(path)

        if not os.path.exists(parent_dir):
            os.makedirs(parent_dir)
            parent = parent_dir
            while True:
                # Add __init__.py files to parent dirs as necessary
                pkg_file = os.path.join(parent, '__init__.py')
                self.touch(pkg_file)

                if parent == endcase:
                    break
                
                parent = os.path.split(os.path.abspath(parent))[0]



    # for a given interface, generate the relevant file.
    def generate_service_definition(self, yaml_file, interface_name, interface_file):
        
        self.init_py_parent_dirs(interface_file)

        with open(yaml_file, 'r') as f:
            yaml_text = f.read()
            m = hashlib.md5()
            m.update(yaml_text)
            cur_md5 = m.hexdigest()

            if yaml_file in self.svc_signatures and not self.opts.force:
                if cur_md5 == self.svc_signatures[yaml_file]:
                    print "%10s %40s (md5 signature match)" % ("Skipping", interface_name)
                    return

            if self.opts.dryrun:
                self.service_definition_count += 1
                print "%10s %40s (needs update)" % ("Changed", interface_name)
                return

            # update signature set
            self.svc_signatures[yaml_file] = cur_md5
            print 'Generating %40s -> %s' % (interface_name, interface_file)

        defs = yaml.load_all(yaml_text)
        for def_set in defs:
            # Handle object definitions first; make dummy constructors so tags will parse
            if 'obj' in def_set:
                for obj_name in def_set['obj']:
                    tag = u'!%s' % (obj_name)
                    self.yaml_add_constructor(tag)
                continue

            service_name     = def_set.get('name', None)
            class_docstring  = def_set.get('docstring', "class docstring")
            dependencies     = def_set.get('dependencies', None)
            methods          = []
            class_methods    = []

            # It seems that despite the get with default arg, there still can be None resulting (YAML?)
            meth_list = def_set.get('methods', {}) or {}
            for op_name, op_def in meth_list.iteritems():
                if not op_def: continue
                def_docstring   = op_def.get('docstring', "method docstring")
                def_in          = op_def.get('in', None)
                def_out         = op_def.get('out', None)
                args_str        = self.build_args_str(def_in, False)
                class_args_str  = self.build_args_str(def_in, True)
                docstring_str   = self.TEMPLATE['methdocstr'].format(methoddocstr=def_docstring)
                outargs_str     = '\n        # '.join(yaml.dump(def_out).split('\n'))

                methods.append(self.TEMPLATE['method'].format(name=op_name, 
                                                              args=args_str, 
                                                              methoddocstring=docstring_str, 
                                                              outargs=outargs_str))

                class_methods.append(self.TEMPLATE['method'].format(name=op_name, 
                                                                    args=class_args_str, 
                                                                    methoddocstring=docstring_str, 
                                                                    outargs=outargs_str))

            if service_name is None:
                raise IonServiceDefinitionError("Service definition file %s does not define name attribute" % yaml_file)

            #generate text
            class_name           = service_name_from_file_name(interface_name)
            service_name_str     = self.TEMPLATE['svcname'].format(name=service_name)
            class_docstring_str  = self.TEMPLATE['clssdocstr'].format(classdocstr=class_docstring)
            dependencies_str     = self.TEMPLATE['depends'].format(namelist=dependencies)
            methods_str          = ''.join(methods) or '    pass\n'
            classmethods_str     = ''.join(class_methods)

            _class               = self.TEMPLATE['class'].format(name=class_name, 
                                                             classdocstring=class_docstring_str, 
                                                             servicename=service_name_str, 
                                                             dependencies=dependencies_str,
                                                             methods=methods_str, 
                                                             classmethods=classmethods_str)

            interface_contents   = self.TEMPLATE['file'].format(classes=_class, when_generated=self.currtime)

            open(interface_file, 'w').write(interface_contents)

            self.service_definition_count += 1


    #initialize service signatures from cache file
    def sigfile_read(self):
        if os.path.exists(self.SIGFILE):
            with open(self.SIGFILE, 'r') as f:
                cnts = f.read()
                self.svc_signatures = yaml.load(cnts)

    #save the cache of signatures
    def sigfile_write(self):
        print "Writing signature file to ", self.SIGFILE
        with open(self.SIGFILE, 'w') as f:
            f.write(yaml.dump(self.svc_signatures))


    # Clear old generated files
    def clean_interface_dir(self, interface_dir):
        files = os.listdir(interface_dir)
        for file in fnmatch.filter(files, '*.pyc'):
        #for file in fnmatch.filter(files, '*.py') + fnmatch.filter(files, '*.pyc'):
            os.unlink(os.path.join(interface_dir, file))

    #copy of unix "touch" command
    def touch(self, path):
        if not os.path.exists(path):
            open(path, 'w').close()


    #add a dummy constructor to aid parsing
    def yaml_add_constructor(self, tag):
        yaml.add_constructor(tag, lambda loader, node: {})


    #walk a directory and execute a function on yaml files
    def yml_dir_walk(self, some_dir, work_fn):
        for root, dirs, files in os.walk(some_dir):
            for filename in fnmatch.filter(files, '*.yml'):
                yaml_file = os.path.join(root, filename)
                #get the relative path with a regexp
                file_match = self.YAML_FILE_RE.match(yaml_file)
                if file_match:
                    rel_path = file_match.group(2)
                    
                    #FIXME
                    #look for matching file in the local override 
                    #local_rel_path  = os.path.join(self.LOCAL_OVERRIDE_INPUT_DIR, rel_path)
                    #local_yaml_file = local_rel_path + ".yml"

                    #if os.path.exists(local_yaml_file):
                    # FIXME: work_fn(local_yaml_file, SOMEHOW
                    #ELSE:

                    work_fn(yaml_file, rel_path)
        

    # prepare to generate interfaces -- initialize any necessary stuff
    def getready(self):
        self.svc_signatures = {}
        self.service_definition_count = 0
        self.currtime = str(datetime.datetime.today())


    # main function of this file
    def go(self):

        #work function for making an object definition in a directory walk
        def process_data_object(yaml_file, _):
            yaml_text = open(yaml_file, 'r').read()
            defs = yaml.load_all(yaml_text, Loader=IonYamlLoader)
            for def_set in defs:
                for name,_def in def_set.iteritems():
                    tag  = u'!%s' % (name)
                    xtag = u'!Extends_%s' % (name)
                    self.yaml_add_constructor(tag)
                    self.yaml_add_constructor(xtag)

        #work function for making a service definition in a directory walk
        def process_service(yaml_file, file_path):
            interface_base  = os.path.dirname(file_path)
            interface_name  = os.path.basename(file_path)
            interface_file  = os.path.join(self.OUTPUT_DIR, interface_base, 'i%s.py' % interface_name)

            self.generate_service_definition(yaml_file, interface_name, interface_file)

        
        #initialize output directory
        if not os.path.exists(self.OUTPUT_DIR):
            os.makedirs(self.OUTPUT_DIR)
        self.clean_interface_dir(self.OUTPUT_DIR)

        # Load data yaml files in case services define interfaces
        # in terms of common data objects
        entag = u'!enum'
        self.yaml_add_constructor(entag)
        self.yml_dir_walk(self.IN_DATA, process_data_object)


        # Generate the new definitions, for now giving each
        # yaml file its own python service
        self.sigfile_read()
        self.yml_dir_walk(self.IN_SERVICES, process_service)

        #things to do if its not a dry run (and we actually have material)
        if self.service_definition_count > 0 and not self.opts.dryrun:
            self.sigfile_write()

            # Load interface base classes
            self.load_mods(self.OUT_SERVICES, True)
            self.find_subtypes(BaseService) #ijk5: does this even need to be here?
            # Load impl classes
            self.load_mods("ion", False)


        self.generate_validation_report()

        exitcode = 0
        if self.service_definition_count > 0:
            exitcode = 1

        sys.exit(exitcode)


    def generate_validation_report(self):
        validation_results = self.generate_validation_report_str()

        try:
            os.unlink(self.REPORTFILE)
        except:
            pass
        print "Writing validation report to '" + self.REPORTFILE + "'"
        with open(self.REPORTFILE, 'w') as f:
            f.write(validation_results)


    def generate_validation_report_str(self):

        # Generate validation report
        validation_results = "Report generated on " + self.currtime + "\n"
        self.load_mods(self.OUT_SERVICES, True)
        base_subtypes = self.find_subtypes(BaseService)
        self.load_mods("ion", False)
        self.load_mods("examples", False)
        for base_subtype in base_subtypes:
            base_subtype_name = base_subtype.__module__ + "." + base_subtype.__name__
            compare_methods = {}
            for method_tuple in inspect.getmembers(base_subtype, inspect.ismethod):
                method_name = method_tuple[0]
                method = method_tuple[1]
                # Ignore private methods
                if method_name.startswith("_"):
                    continue
                # Ignore methods not implemented in the class
                if method_name not in base_subtype.__dict__:
                    continue
                compare_methods[method_name] = method

            # Find implementing subtypes of each base interface
            impl_subtypes = self.find_subtypes(base_subtype)
            if len(impl_subtypes) == 0:
                validation_results += "\nBase service: %s \n" % base_subtype_name
                validation_results += "  No impl subtypes found\n"
            for impl_subtype in self.find_subtypes(base_subtype):
                impl_subtype_name = impl_subtype.__module__ + "." + impl_subtype.__name__

                # Compare parameters
                added_class_names = False
                found_error = False
                for key in compare_methods:
                    if key not in impl_subtype.__dict__:
                        if not added_class_names:
                            added_class_names = True
                            validation_results += "\nBase service: %s\n" % base_subtype_name
                            validation_results += "Impl subtype: %s\n" % impl_subtype_name
                        validation_results += "  Method '%s' not implemented" % key
                    else:
                        base_params = inspect.getargspec(compare_methods[key])
                        impl_params = inspect.getargspec(impl_subtype.__dict__[key])

                        if base_params != impl_params:
                            if not added_class_names:
                                added_class_names = True
                                validation_results += "\nBase service: %s\n" % base_subtype_name
                                validation_results += "Impl subtype: %s\n" % impl_subtype_name
                            validation_results +=  "  Method '%s' implementation is out of sync\n" % key
                            validation_results +=  "    Base: %s\n" % str(base_params)
                            validation_results +=  "    Impl: %s\n" % str(impl_params)

                if found_error == False:
                    validation_results += "\nBase service: %s\n" % base_subtype_name
                    validation_results += "Impl subtype: %s\n" % impl_subtype_name
                    validation_results += "  OK\n"

        return validation_results


    #load modules in a given path
    def load_mods(self, path, interfaces):
        import pkgutil
        import string
        mod_prefix = string.replace(path, os.path.sep, ".")

        for mod_imp, mod_name, is_pkg in pkgutil.iter_modules([path]):
            if is_pkg:
                self.load_mods(os.path.join(path, mod_name), interfaces)
            else:
                mod_qual = "%s.%s" % (mod_prefix, mod_name)
                try:
                    named_any(mod_qual)
                except Exception, ex:
                    print "Import module '%s' failed: %s" % (mod_qual, ex)
                    if not interfaces:
                        print "Make sure that you have defined an __init__.py in your directory and that you have imported the correct base type"

    def find_subtypes(self, clz):
        res = []
        for cls in clz.__subclasses__():
            assert hasattr(cls,'name'), 'Service class must define name value. Service class in error: %s' % cls
            res.append(cls)
        return res





def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true', help='Do not do MD5 comparisons, always generate new files')
    parser.add_argument('-d', '--dryrun', action='store_true', help='Do not generate new files, just print status and exit with 1 if changes need to be made')

    #FIXME: we can do better than this
    if os.getcwd().endswith('scripts'):
        sys.exit('This script needs to be run from the pyon root.')

    isdg = IonServiceDefinitionGenerator(parser.parse_args())
    isdg.getready()
    isdg.go()
    isdg.print_report()


if __name__ == '__main__':
    main()
