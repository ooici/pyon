#!/usr/bin/env python

"""Functions for generating Python message interfaces from service definitions"""

__author__ = 'Adam R. Smith, Thomas Lennan, Stephen Henrie, Dave Foster, Seman Said'
__license__ = 'Apache 2.0'


import ast
import os
import re

from pyon.core.path import list_files_recursive
from pyon.core.interfaces.interface_util import get_service_definition_from_datastore

enums_by_name = {}


class MessageObjectGenerator:

    def __init__(self, system_name=None, read_from_yaml_file=False):
        self.system_name = system_name
        self.read_from_yaml_file = read_from_yaml_file

    def generate(self, opts):
        service_yaml_data = self.get_yaml_data()
        messageobject_output_text = "# Message Objects. Don't edit, it is auto generated file.\n\nimport interface.objects\nfrom pyon.core.object import IonMessageObjectBase\n"
        if not service_yaml_data:
            print "message_model_generator: Error!!! the datastore (or the YAML file) is empty."
            exit()

        # Now process the service definition yaml files to
        # generate message classes for input and return messages.
        # Do this on a per file basis to simplify figuring out
        # when we've reached the end of a service's ops.
        for yaml_text in service_yaml_data:
            index = 0
            lines = yaml_text.split('\n')

            # Find service name
            while index < len(lines):
                if lines[index].startswith('name:'):
                    break
                index += 1

            if index >= len(lines):
                continue

            current_service_name = lines[index].split(':')[1].strip()
            index += 1
            # Find op definitions
            while index < len(lines):
                if lines[index].startswith('methods:'):
                    break
                index += 1
            index += 1

            if index >= len(lines):
                continue

            # Find op name
            while index < len(lines):
                if lines[index].startswith('  ') and lines[index][2].isalpha():
                    break
                index += 1

            if index >= len(lines):
                continue

            while index < len(lines):
                if len(lines[index]) == 0 or lines[index].isspace():
                    index += 1
                    continue

                if not (lines[index].startswith('  ') and lines[index][2].isalpha()):
                    index += 1
                    continue

                args = []
                init_lines = []
                current_op_name = lines[index].strip(' :')
                messageobject_output_text += '\nclass ' + current_service_name + "_" + current_op_name + "_in(IonMessageObjectBase):\n"
                messageobject_output_text += "    _svc_name = '" + current_service_name + "'\n"
                messageobject_output_text += "    _op_name = '" + current_op_name + "'\n"
                index += 1

                # Find in
                while index < len(lines):
                    if lines[index].startswith('    resource_type:'):
                        messageobject_output_text += "    _resource_type = '" + lines[index].split('    resource_type:')[1].strip() + "'\n"
                    if lines[index].startswith('    resource_id:'):
                        messageobject_output_text += "    _resource_id = '" + lines[index].split('    resource_id:')[1].strip() + "'\n"
                    if lines[index].startswith('    operation_type:'):
                        messageobject_output_text += "    _operation_type = '" + lines[index].split('    operation_type:')[1].strip() + "'\n"
                    if lines[index].startswith('    in:'):
                        break
                    index += 1
                index += 1

                messageobject_output_text += '\n    def __init__(self'
                current_class_schema = "\n    _schema = {"
                decorators = ''
                description = ''

                while index < len(lines) and not lines[index].startswith('    out:'):
                    if lines[index].isspace():
                        index += 1
                        continue

                    line = lines[index].replace('    ', '', 1)

                    # Find decorators and comments
                    if line.startswith('  #'):
                        # Check for decorators
                        if len(line) > 4 and line.startswith('  #@'):
                            dec = line.strip()[2:].split("=")
                            key = dec[0]
                            value = dec[1] if len(dec) == 2 else ""
                            # Add it to the decorator list
                            if not decorators:
                                decorators = '"' + key + '":"' + value + '"'
                            else:
                                decorators = decorators + ', "' + key + '":"' + value + '"'
                        else:
                            init_lines.append('  ' + line + '\n')
                            if not description:
                                description = line.strip()[1:]
                            else:
                                description = description + ' ' + line.strip()[1:]

                        index += 1
                        continue

                    elif line.startswith('  '):
                        field = line.split(":", 1)[0].strip()
                        try:
                            value = line.split(":", 1)[1].strip()
                            if '#' in value:
                                dsc = value.split('#', 1)[1].strip()[1:]
                                value = value.split('#')[0].strip()
                                # Get inline comment
                                if not description:
                                    description = dsc
                                else:
                                    description = description + ' ' + dsc
                        except KeyError:
                            # Ignore key error because value is nested
                            index += 1
                            continue

                        if len(value) == 0:
                            value = "None"
                            value_type = "str"
                            default = "None"
                        elif value.startswith('!'):
                            value = value.strip("!")
                            if value in enums_by_name:
                                value_type = 'int'
                                # Get default enum value
                                enum_def = enums_by_name[value]
                                value = default = "interface.objects." + value + "." + enum_def["default"]
                            else:
                                value_type = value
                                value = default = "None"
                        # Hacks, find a better way in the future
                        elif "'" in value or '"' in value:
                            value_type = "str"
                            default = value
                        # Hack
                        else:
                            try:
                                eval_value = ast.literal_eval(value)
                                value_type = type(eval_value).__name__
                            except ValueError:
                                value_type = "str"
                                value = "'" + value + "'"
                            except SyntaxError:
                                value_type = "str"
                                value = "'" + value + "'"
                            if value_type in ['dict', 'list', 'tuple']:
                                default = value = "None"
                            else:
                                default = value
                        args.append(", ")
                        args.append(field + "=" + value)
                        init_lines.append('        self.' + field + " = " + field + "\n")
                        current_class_schema += "\n                '" + field + "': {'type': '" + value_type + "', 'default': " + default + ", 'decorators': {" + decorators + "}" + ", 'description': '" + re.escape(description) + "' },"
                    index += 1
                    decorators = ''
                    description = ''

                if len(args) > 0:
                    for arg in args:
                        messageobject_output_text += arg
                    messageobject_output_text += "):\n"
                    for init_line in init_lines:
                        messageobject_output_text += init_line
                else:
                    messageobject_output_text += "):\n"
                    messageobject_output_text += '        pass\n'
                messageobject_output_text += current_class_schema + "\n              }\n"

                if index < len(lines) and lines[index].startswith('    out:'):
                    args = []
                    init_lines = []
                    messageobject_output_text += '\nclass ' + current_service_name + "_" + current_op_name + "_out(IonMessageObjectBase):\n"
                    messageobject_output_text += "    _svc_name = '" + current_service_name + "'\n"
                    messageobject_output_text += "    _op_name = '" + current_op_name + "'\n\n"
                    messageobject_output_text += '    def __init__(self'
                    current_class_schema = "\n    _schema = {"
                    index += 1
                    while index < len(lines):

                        line = lines[index]

                        if line.isspace() or len(line) == 0:
                            index += 1
                            continue

                        # Ignore
                        if not line.startswith('  '):
                            index += 1
                            continue

                        # Found next op
                        if line.startswith('  ') and line[2].isalpha():
                            break

                        if line.startswith('    throws:'):
                            index += 1
                            while index < len(lines):
                                if not lines[index].startswith('    '):
                                    break
                                index += 1
                            break
                        line = line.replace('    ', '', 1)

                        # Add comments and decorators
                        if line.startswith('  #'):
                            # Check for decorators
                            if len(line) > 4 and line.startswith('  #@'):
                                if not decorators:
                                    decorators = '"' + line.strip()[2:] + '"'
                                else:
                                    decorators = decorators + ', "' + line.strip()[2:] + '"'
                            else:
                                init_lines.append('  ' + line + '\n')
                                if not description:
                                    description = line.strip()[1:]
                                else:
                                    description = description + ' ' + line.strip()[1:]
                            index += 1
                            continue

                        field = line.split(":", 1)[0].strip()
                        try:
                            value = line.split(":", 1)[1].strip()
                            if '#' in value:
                                dsc = value.split('#', 1)[1].strip()
                                value = value.split('#')[0].strip()
                                # Get inline comment
                                if not description:
                                    description = dsc
                                else:
                                    description = description + ' ' + dsc
                        except KeyError:
                            # Ignore key error because value is nested
                            index += 1
                            continue

                        if len(value) == 0:
                            value = "None"
                            value_type = "str"
                            default = "None"
                        elif value.startswith('!'):
                            value = value.strip("!")
                            if value in enums_by_name:
                                value_type = 'int'
                                # Get default enum value
                                enum_def = enums_by_name[value]
                                value = default = "interface.objects." + value + "." + enum_def["default"]
                            else:
                                value_type = value
                                value = default = "None"
                        # Hacks, find a better way in the future
                        elif "'" in value or '"' in value:
                            value_type = "str"
                            default = value
                        # Hack
                        else:
                            try:
                                eval_value = ast.literal_eval(value)
                                value_type = type(eval_value).__name__
                            except ValueError:
                                value_type = "str"
                                value = "'" + value + "'"
                            except SyntaxError:
                                value_type = "str"
                                value = "'" + value + "'"
                            if value_type in ['dict', 'list', 'tuple']:
                                default = value = "None"
                            else:
                                default = value
                        args.append(", ")
                        args.append(field + "=" + value)
                        init_lines.append('        self.' + field + " = " + field + "\n")
                        current_class_schema += "\n                '" + field + "': {'type': '" + value_type + "', 'default': " + default + ", 'decorators': [" + decorators + "]" + ", 'description': '" + re.escape(description) + "' },"
                        index += 1
                        decorators = ''

                    if len(args) > 0:
                        for arg in args:
                            messageobject_output_text += arg
                        messageobject_output_text += "):\n"
                        for init_line in init_lines:
                            messageobject_output_text += init_line
                    else:
                        messageobject_output_text += "):\n"
                        messageobject_output_text += '        pass\n'
                    messageobject_output_text += current_class_schema + "\n              }\n"

        datadir = 'interface'
        messagemodelfile = os.path.join(datadir, 'messages.py')
        if not opts.dryrun:
            try:
                os.unlink(messagemodelfile)
            except:
                pass
            print " Writing message interfaces to '" + messagemodelfile + "'"
            with open(messagemodelfile, 'w') as f:
                f.write(messageobject_output_text)

    def get_yaml_data(self):
        data = []
        if self.read_from_yaml_file:
            print " Message interface generator: reading service definitions from files"
            service_yaml_files = list_files_recursive('obj/services', '*.yml')
            for path in service_yaml_files:
                if os.path.exists(path):
                    file = open(path, 'r')
                    data.append(file.read())
                    file.close()
        else:
            print " Message interface generator: reading service definitions from datastore"
            data = get_service_definition_from_datastore(self.system_name)
            if not data:
                data = []
        return data
