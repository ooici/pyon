
import ast
import os
from pyon.core.path import list_files_recursive


enums_by_name = {}

class MessageObjectGenerator:


    def generate (self, opts):
        service_yaml_files = list_files_recursive('obj/services', '*.yml')

        ### messageobject_output_text = "# Message Objects\n\nimport interface.objects\nfrom pyon.core.object import IonObjectBase\n"
        messageobject_output_text = "# Message Objects\n\nimport interface.objects\nfrom pyon.core.object import IonMessageObjectBase\n"
        current_class_schema = ""

        # Now process the service definition yaml files to
        # generate message classes for input and return messages.
        # Do this on a per file basis to simplify figuring out
        # when we've reached the end of a service's ops.
        args = []
        init_lines = []
        for yaml_file in (open(path, 'r') for path in service_yaml_files if os.path.exists(path)):
            index = 0
            
            yaml_text = yaml_file.read() 
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
                ###messageobject_output_text += '\nclass ' + current_service_name + "_" + current_op_name + "_in(IonObjectBase):\n"
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

                while index < len(lines) and not lines[index].startswith('    out:'):
                    if lines[index].isspace():
                        index += 1
                        continue

                    line = lines[index].replace('    ', '', 1)
                    if line.startswith('  #'):
                        init_lines.append('  ' + line + '\n')
                        index += 1
                        continue
                    elif line.startswith('  '):
                        is_required = False
                        field = line.split(":", 1)[0].strip()
                        try:
                            value = line.split(":", 1)[1].strip()
                            if '#' in value:
                                if '_required' in value:
                                    is_required = True
                                value = value.split('#')[0].strip()
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
    #                    if is_required:
    #                        init_lines.append("        if " + field + " is None:\n")
    #                        init_lines.append("            raise BadRequest('Required parameter " + field + " was not provided')\n")
                        init_lines.append('        self.' + field + " = " + field + "\n")
                        current_class_schema += "\n                '" + field + "': {'type': '" + value_type + "', 'default': " + default + ", 'required': " + str(is_required) + "},"
                    index += 1

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
                    ###messageobject_output_text += '\nclass ' + current_service_name + "_" + current_op_name + "_out(IonObjectBase):\n"
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
                        if line.startswith('  #'):
                            index += 1
                            continue
                        field = line.split(":", 1)[0].strip()
                        try:
                            value = line.split(":", 1)[1].strip()
                            if '#' in value:
                                value = value.split('#')[0].strip()
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
    #                    messageobject_output_text += '        self.' + field + " = kwargs.get('" + field + "', " + value + ")\n"
                        init_lines.append('        self.' + field + " = " + field + "\n")
                        current_class_schema += "\n                '" + field + "': {'type': '" + value_type + "', 'default': " + default + "},"
                        index += 1

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
        try:
            os.unlink(messagemodelfile)
        except:
            pass
        print "Writing message model to '" + messagemodelfile + "'"
        with open(messagemodelfile, 'w') as f:
            f.write(messageobject_output_text)

