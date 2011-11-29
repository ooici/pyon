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
import string

import yaml
import hashlib
import argparse

from pyon.service.service import BaseService
from pyon.util.containers import named_any

# Do not remove any of the imports below this comment!!!!!!
from pyon.core.object import IonYamlLoader, service_name_from_file_name
from pyon.util import yaml_ordered_dict

class IonServiceDefinitionError(Exception):
    pass

currtime = str(datetime.datetime.today())

templates = {
      'file':
'''#!/usr/bin/env python
#
# File generated on ${when_generated}
#

from zope.interface import Interface, implements

from collections import OrderedDict, defaultdict

from pyon.service.service import BaseService, BaseClients
from pyon.net.endpoint import RPCClient, ProcessRPCClient
${dep_client_imports}

${clientsholder}

${classes}

${client}
'''
    , 'clientsholder':
'''class ${name}Clients(BaseClients):
    def __init__(self, process=None):
        BaseClients.__init__(self)
${dep_clients}
'''
    , 'client_file':
'''#!/usr/bin/env python
#
# File generated on ${when_generated}
#
${client_imports}
'''
    , 'class':
'''class I${name}(Interface):
${classdocstring}
${methods}
'''
'''class Base${name}(BaseService):
    implements(I${name})
${classdocstring}
${servicename}
${dependencies}

    def __init__(self, *args, **kwargs):
        BaseService.__init__(self, *args, **kwargs)
        self.clients = ${name}Clients(process=self)

${classmethods}
'''
    , 'dep_client':
'''        self.${svc} = ${clientclass}(process=process)'''
    , 'dep_client_imports':
'''from ${clientmodule} import ${clientclass}'''
    , 'clssdocstr':
'    """${classdocstr}\n\
    """'
    , 'svcname':
'    name = \'${name}\''
    , 'depends':
'    dependencies = ${namelist}'
    , 'method':
'''
    def ${name}(${args}):
        ${methoddocstring}
        # Return Value
        # ------------
        # ${outargs}
        pass
'''
    , 'arg': '${name}=${val}'
    , 'methdocstr':
'"""${methoddocstr}\n\
        """'
}

client_templates = {
    'full':
'''
${client}

${rpcclient}

${processrpcclient}
''',
    'class':
'''class ${name}ClientMixin(object):
    """
    ${clientdocstring}
    """
    implements(I${name})

${methods}
''',
    'method':
'''
    def ${name}(${args}):
        ${methoddocstring}
        # Return Value
        # ------------
        # ${outargs}
        return self.request({'method': '${name}', 'args': [${argssmall}]})
''',
    'rpcclient':
'''class ${name}Client(RPCClient, ${name}ClientMixin):
    def __init__(self, name=None, node=None, **kwargs):
        name = name or '${targetname}'
        RPCClient.__init__(self, name=name, node=node, **kwargs)
        ${name}ClientMixin.__init__(self)
''',
    'processrpcclient':
'''class ${name}ProcessClient(ProcessRPCClient, ${name}ClientMixin):
    def __init__(self, process=None, name=None, node=None, **kwargs):
        name = name or '${targetname}'
        ProcessRPCClient.__init__(self, process=process, name=name, node=node, **kwargs)
        ${name}ClientMixin.__init__(self)
'''
}

# convert both to string.Template
templates           = dict(((k, string.Template(v)) for k, v in templates.iteritems()))
client_templates    = dict(((k, string.Template(v)) for k, v in client_templates.iteritems()))

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
        args.append(templates['arg'].substitute(name=key, val=val))

    args_str = ', '.join(args)
    return args_str

def generate_service(interface_file, svc_def, client_defs):
    """
    Generates a single service/client/interface definition.

    @param  interface_file      The file on disk this def should be written to.
    @param  svc_def             Hash of info about service.
    @param  client_defs         Static mapping of service names to their defined clients.
    """
    service_name    = svc_def['name']
    class_docstring = svc_def['docstring']
    dependencies    = svc_def['dependencies']
    meth_list       = svc_def['methods']
    interface_name  = svc_def['interface_name']

    print 'Generating %40s -> %s' % (interface_name, interface_file)

    methods         = []
    class_methods   = []
    client_methods  = []

    for op_name, op_def in meth_list.iteritems():
        if not op_def: continue

        def_docstring, def_in, def_out  = op_def.get('docstring', "method docstring"), op_def.get('in', None), op_def.get('out', None)

        # multiline docstring for method
        docstring_lines = def_docstring.split('\n')

        # Annoyingly, we have to hand format the doc strings to introduce
        # the correct indentation on multi-line strings           
        first_time = True
        docstring_formatted = ""
        for i in range(len(docstring_lines)):
            docstring_line = docstring_lines[i]
            # Potentially remove excess blank line
            if docstring_line == "" and i == len(docstring_lines) - 1:
                break
            if first_time:
                first_time = False
            else:
                docstring_formatted += "\n        "
            docstring_formatted += docstring_line

        args_str, class_args_str        = build_args_str(def_in, False), build_args_str(def_in, True)
        docstring_str                   = templates['methdocstr'].substitute(methoddocstr=docstring_formatted)
        outargs_str                     = '\n        # '.join(yaml.dump(def_out).split('\n'))

        methods.append(templates['method'].substitute(name=op_name, args=args_str, methoddocstring=docstring_str, outargs=outargs_str))
        class_methods.append(templates['method'].substitute(name=op_name, args=class_args_str, methoddocstring=docstring_str, outargs=outargs_str))

        clientargspass = ''
        if def_in:
            clientargspass = ','.join((k for k in def_in))   # enumerates keys only, which are names, aka what we want here
        client_methods.append(client_templates['method'].substitute(name=op_name,
                                                                    args=class_args_str,
                                                                    methoddocstring=docstring_str,
                                                                    argssmall=clientargspass,
                                                                    outargs=outargs_str))

    if service_name is None:
        raise IonServiceDefinitionError("Service definition file %s does not define name attribute" % yaml_file)

    # dep client names
    dep_clients             = [(x, client_defs[x][1]) for x in dependencies]
    dep_clients_str         = "\n".join(map(lambda x2: templates['dep_client'].substitute(svc=x2[0], clientclass=x2[1]), dep_clients))
    dep_client_imports_str  = "\n".join([templates['dep_client_imports'].substitute(clientmodule=client_defs[x][0], clientclass=client_defs[x][1]) for x in dependencies])

    service_name_str    = templates['svcname'].substitute(name=service_name)
    class_docstring_str = templates['clssdocstr'].substitute(classdocstr=class_docstring)
    dependencies_str    = templates['depends'].substitute(namelist=dependencies)
    methods_str         = ''.join(methods) or '    pass\n'
    classmethods_str    = ''.join(class_methods)
    class_name          = service_name_from_file_name(interface_name)

    _class = templates['class'].substitute(name=class_name,
                                           classdocstring=class_docstring_str,
                                           servicename=service_name_str,
                                           dependencies=dependencies_str,
                                           methods=methods_str,
                                           classmethods=classmethods_str)

    # dependent clients generation
    clients_holder_str = templates['clientsholder'].substitute(name=class_name,
                                                               dep_clients=dep_clients_str)

    # this service's client generation
    _client_methods             = ''.join(client_methods)
    _client_class               = client_templates['class'].substitute(name=class_name,
                                                                       clientdocstring='#todo',
                                                                       methods=_client_methods)
    _client_rpcclient           = client_templates['rpcclient'].substitute(name=class_name,
                                                                           targetname=service_name)
    _client_processrpc_client   = client_templates['processrpcclient'].substitute(name=class_name,
                                                                                  targetname=service_name)

    _client                     = client_templates['full'].substitute(client=_client_class,
                                                                      rpcclient=_client_rpcclient,
                                                                      processrpcclient=_client_processrpc_client)

    interface_contents          = templates['file'].substitute(dep_client_imports=dep_client_imports_str,
                                                               clientsholder=clients_holder_str,
                                                               classes=_class,
                                                               when_generated=currtime,
                                                               client=_client)
    with open(interface_file, 'w') as f:
        f.write(interface_contents)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--force', action='store_true', help='Do not do MD5 comparisons, always generate new files')
    parser.add_argument('-d', '--dryrun', action='store_true', help='Do not generate new files, just print status and exit with 1 if changes need to be made')
    opts = parser.parse_args()

    if os.getcwd().endswith('scripts'):
        sys.exit('This script needs to be run from the pyon root.')

    service_dir, interface_dir = 'obj/services', 'interface'
    if not os.path.exists(interface_dir):
        os.makedirs(interface_dir)

    # Clear old generated files
    files = os.listdir(interface_dir)
    for file in fnmatch.filter(files, '*.pyc'):
    #for file in fnmatch.filter(files, '*.py') + fnmatch.filter(files, '*.pyc'):
        os.unlink(os.path.join(interface_dir, file))

    open(os.path.join(interface_dir, '__init__.py'), 'w').close()

    # Load data yaml files in case services define interfaces
    # in terms of common data objects
    yaml_file_re = re.compile('(obj)/(.*)[.](yml)')
    data_dir = 'obj/data'
    entag = u'!enum'
    yaml.add_constructor(entag, lambda loader, node: {})
    for root, dirs, files in os.walk(data_dir):
        for filename in fnmatch.filter(files, '*.yml'):
            yaml_file = os.path.join(root, filename)
            file_match = yaml_file_re.match(yaml_file)
            if file_match is None: continue

            yaml_text = open(yaml_file, 'r').read()
            defs = yaml.load_all(yaml_text, Loader=IonYamlLoader)
            for def_set in defs:
                for name,_def in def_set.iteritems():
                    tag = u'!%s' % (name)
                    yaml.add_constructor(tag, lambda loader, node: {})
                    xtag = u'!Extends_%s' % (name)
                    yaml.add_constructor(xtag, lambda loader, node: {})

    svc_signatures = {}
    sigfile = os.path.join('interface', '.svc_signatures.yml')
    if os.path.exists(sigfile):
        with open(sigfile, 'r') as f:
            cnts = f.read()
            svc_signatures = yaml.load(cnts)

    count = 0

    # mapping of service name -> { name, docstring, deps, methods }
    raw_services = {}

    # dependency graph, maps svcs -> deps by service name as a list
    service_dep_graph = {}

    # completed service client definitions, maps service name -> full module path to find module
    client_defs = {}

    # Generate the new definitions, for now giving each
    # yaml file its own python service
    for root, dirs, files in os.walk(service_dir):
        for filename in fnmatch.filter(files, '*.yml'):
            yaml_file = os.path.join(root, filename)
            file_match = yaml_file_re.match(yaml_file)
            if '.svc_signatures' in filename: continue
            if file_match is None: continue

            file_path = file_match.group(2)
            interface_base, interface_name = os.path.dirname(file_path), os.path.basename(file_path)
            interface_file = os.path.join('interface', interface_base, 'i%s.py' % interface_name)

            parent_dir = os.path.dirname(interface_file)
            if not os.path.exists(parent_dir):
                os.makedirs(parent_dir)
                parent = parent_dir
                while True:
                    # Add __init__.py files to parent dirs as necessary
                    curdir = os.path.split(os.path.abspath(parent))[1]
                    if curdir == 'services':
                        break
                    else:
                        parent = os.path.split(os.path.abspath(parent))[0]

                        pkg_file = os.path.join(parent, '__init__.py')
                        if not os.path.exists(pkg_file):
                            open(pkg_file, 'w').close()

            pkg_file = os.path.join(parent_dir, '__init__.py')
            if not os.path.exists(pkg_file):
                open(pkg_file, 'w').close()

            skip_file = False
            with open(yaml_file, 'r') as f:
                yaml_text = f.read()
                m = hashlib.md5()
                m.update(yaml_text)
                cur_md5 = m.hexdigest()

                if yaml_file in svc_signatures and not opts.force:
                    if cur_md5 == svc_signatures[yaml_file]:
                        print "Skipping   %40s (md5 signature match)" % interface_name
                        skip_file = True
                        # do not continue here, we want to read the service deps below

                if opts.dryrun:
                    count += 1
                    print "Changed    %40s (needs update)" % interface_name
                    skip_file = True
                    # do not continue here, we want to read the service deps below

                # update signature set
                if not skip_file:
                    svc_signatures[yaml_file] = cur_md5

            defs = yaml.load_all(yaml_text)
            for def_set in defs:
                # Handle object definitions first; make dummy constructors so tags will parse
                if 'obj' in def_set:
                    for obj_name in def_set['obj']:
                        tag = u'!%s' % (obj_name)
                        yaml.add_constructor(tag, lambda loader, node: {})
                    continue

                service_name    = def_set.get('name', None)
                class_docstring = def_set.get('docstring', "class docstring")
                dependencies    = def_set.get('dependencies', None)
                meth_list       = def_set.get('methods', {}) or {}
                client_path     = ('.'.join(['interface', interface_base.replace('/', '.'), 'i%s' % interface_name]), '%sProcessClient' % service_name_from_file_name(interface_name))

                # format multiline docstring
                class_docstring_lines = class_docstring.split('\n')

                # Annoyingly, we have to hand format the doc strings to introduce
                # the correct indentation on multi-line strings           
                first_time = True
                class_docstring_formatted = ""
                for i in range(len(class_docstring_lines)):
                    class_docstring_line = class_docstring_lines[i]
                    # Potentially remove excess blank line
                    if class_docstring_line == "" and i == len(class_docstring_lines) - 1:
                        break
                    if first_time:
                        first_time = False
                    else:
                        class_docstring_formatted += "\n    "
                    class_docstring_formatted += class_docstring_line

                # load into raw_services (if we're not skipping)
                if not skip_file:
                    if service_name in raw_services:
                        raise StandardError("Duplicate service name found: %s" % service_name)

                    raw_services[service_name] = { 'name'           : service_name,
                                                   'docstring'      : class_docstring_formatted,
                                                   'dependencies'   : dependencies,
                                                   'methods'        : meth_list,
                                                   'interface_file' : interface_file,
                                                   'interface_name' : interface_name,
                                                   'client_path'    : client_path }

                # dep capturing (we check cycles when we topologically sort later)
                if not service_name in service_dep_graph:
                    service_dep_graph[service_name] = set()

                for dep in dependencies:
                    service_dep_graph[service_name].add(dep)

                # update list of client paths for the client to this service
                client_defs[service_name] = client_path

    print "About to generate", len(raw_services), "services"

    # topological sort of services to make sure we do things in order
    # http://en.wikipedia.org/wiki/Topological_sorting
    sorted_services = []
    service_set = set([k for k,v in service_dep_graph.iteritems() if len(v) == 0])

    while len(service_set) > 0:
        n = service_set.pop()

        # topo sort is over the whole dep tree, but raw_services only contains the stuff we're really generating
        # so if it doesn't exist in raw_services, don't bother!
        if n in raw_services:
            sorted_services.append((n, raw_services[n]))

        # get list of all services that depend on the current service
        depending_services = [k for k,v in service_dep_graph.iteritems() if n in v]

        for depending_service in depending_services:

            # remove this dep
            service_dep_graph[depending_service].remove(n)

            # if it has no more deps, add it to the service_set list
            if len(service_dep_graph[depending_service]) == 0:
                service_set.add(depending_service)

    # ok, check for any remaining deps that we never found - indicates a cycle
    remaining_deps = set([k for k,v in service_dep_graph.iteritems() if len(v) > 0])
    if len(remaining_deps):
        raise StandardError("Cycle found in dependencies: could not resolve %s" % str(remaining_deps))

    for svc in sorted_services:
        svc_name, raw_def = svc
        generate_service(raw_def['interface_file'], raw_def, client_defs)
        count+=1

    if count > 0 and not opts.dryrun:

        # write current svc_signatures
        print "Writing signature file to", sigfile
        with open(sigfile, 'w') as f:
            f.write(yaml.dump(svc_signatures))

        # Load interface base classes
        load_mods("interface/services", True)
        base_subtypes = find_subtypes(BaseService)
        # Load impl classes
        load_mods("ion", False)

        # write client public file
        # @TODO: reenable when 'as' directory goes away
        '''
        clientfile = os.path.join('interface', 'clients.py')
        print "Writing public client file to", clientfile

        with open(clientfile, 'w') as f:
            f.write(templates['client_file'].substitute(when_generated=currtime,
                                                        client_imports="\n".join([templates['dep_client_imports'].substitute(clientmodule=x[0], clientclass=x[1]) for x in client_defs.itervalues()])))
        '''

    # Generate validation report
    validation_results = "Report generated on " + currtime + "\n"
    load_mods("interface/services", True)
    base_subtypes = find_subtypes(BaseService)
    load_mods("ion", False)
    load_mods("examples", False)
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
        impl_subtypes = find_subtypes(base_subtype)
        if len(impl_subtypes) == 0:
            validation_results += "\nBase service: %s \n" % base_subtype_name
            validation_results += "  No impl subtypes found\n"
        for impl_subtype in find_subtypes(base_subtype):
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

    reportfile = os.path.join('interface', 'validation_report.txt')
    try:
        os.unlink(reportfile)
    except:
        pass
    print "Writing validation report to '" + reportfile + "'"
    with open(reportfile, 'w') as f:
        f.write(validation_results)

    exitcode = 0

    # only exit with 1 if we notice changes, and we specified dryrun
    if count > 0 and opts.dryrun:
        exitcode = 1

    sys.exit(exitcode)

def load_mods(path, interfaces):
    import pkgutil
    import string
    mod_prefix = string.replace(path, "/", ".")

    for mod_imp, mod_name, is_pkg in pkgutil.iter_modules([path]):
        if is_pkg:
            load_mods(path+"/"+mod_name, interfaces)
        else:
            mod_qual = "%s.%s" % (mod_prefix, mod_name)
            try:
                named_any(mod_qual)
            except Exception, ex:
                print "Import module '%s' failed: %s" % (mod_qual, ex)
                if not interfaces:
                    print "Make sure that you have defined an __init__.py in your directory and that you have imported the correct base type"

def find_subtypes(clz):
    res = []
    for cls in clz.__subclasses__():
        assert hasattr(cls,'name'), 'Service class must define name value. Service class in error: %s' % cls
        res.append(cls)
    return res

if __name__ == '__main__':
    main()
