import ast
import datetime
import fnmatch
import inspect
import pkgutil
import os
import re
import sys
import string

import yaml
import hashlib
import argparse

from collections import OrderedDict
from pyon.core.path import list_files_recursive
from pyon.service.service import BaseService
from pyon.util.containers import named_any

# Do not remove any of the imports below this comment!!!!!!
from pyon.util import yaml_ordered_dict

class IonYamlLoader(yaml.Loader):
    """ For ION-specific overrides of YAML loading behavior. """
    pass

enums_by_name = {}

class ObjectModelGenerator:


    data_yaml_text = ''
    service_yaml_text = ''
    dataobject_output_text = ''
    def_dict = {}
    args = []
    fields = []
    field_details = []
    class_args_dict = {}


    #
    # Write object model to object.py file
    #
    def write_to_object_model_file (self):

        datadir = 'interface'
        if not os.path.exists(datadir):
            os.makedirs(datadir)
            open(os.path.join(datadir, '__init__.py'), 'w').close()
        datamodelfile = os.path.join(datadir, 'objects.py')
        try:
            os.unlink(datamodelfile)
        except:
            pass
        print "Writing object model to '" + datamodelfile + "'"
        with open(datamodelfile, 'w') as f:
            f.write(self.dataobject_output_text)




    #
    # Gets the data from YAML files
    #
    def get_yaml_text(self):

        data_yaml_files = list_files_recursive('obj/data', '*.yml', ['ion.yml', 'resource.yml'])
        self.data_yaml_text = '\n\n'.join((file.read() for file in (open(path, 'r') for path in data_yaml_files if os.path.exists(path))))
        service_yaml_files = list_files_recursive('obj/services', '*.yml')
        self.service_yaml_text = '\n\n'.join((file.read() for file in (open(path, 'r') for path in service_yaml_files if os.path.exists(path))))

        combined_yaml_text = self.data_yaml_text + "\n" + self.service_yaml_text

        return combined_yaml_text



    #
    # Recursively generates right hand value for a class attribute.
    #
    def convert_val(self,value):

        if isinstance(value, list):
            outline = '['
            first_time = True
            for val in value:
                if first_time:
                    first_time = False
                else:
                    outline += ", "
                outline += self.convert_val(val)
            outline += ']'
        elif isinstance(value, dict) and "__IsEnum" in value:
            outline = value["value"]
        elif isinstance(value, OrderedDict):
            outline = '{'
            first_time = True
            for key in value:
                if first_time:
                    first_time = False
                else:
                    outline += ", "
                outline += "'" + key + "': " + self.convert_val(value[key])
            outline +=  '}'
        elif isinstance(value, str):
            outline = "'" + value + "'"
        else:
            outline = str(value)

        return outline




    #
    # Parse YAML text data
    #
    def parse_yaml_text (self, combined_yaml_text):

        dataobject_output_text = ''
        for line in combined_yaml_text.split('\n'):
            if '!enum ' in line:
                # If stand alone enum type definition
                tokens = line.split(':')
                classname = tokens[0].strip()

                enum_def = tokens[1].strip(' )').replace('!enum (', '')
                if 'name' in enum_def:
                    name_str = enum_def.split(',', 1)[0]
                    name_val = name_str.split('=')[1].strip()
                    if line[0].isalpha():
                        assert line.startswith(name_val + ':'), "enum name/class name mismatch %s/%s" % (classname, name_val)
                else:
                    name_str = ''
                    name_val = classname
                default_str = enum_def.rsplit(',', 1)[1]
                default_val = default_str.split('=')[1].strip()
                value_str = enum_def.replace(name_str, '').replace(default_str, '').strip(', ')
                value_val = value_str.split('=')[1].replace(' ', '').strip('()').split(',')
                assert name_val not in enums_by_name, "enum with type name %s redefined" % name_val
                enums_by_name[name_val] = {"values": value_val, "default": default_val}

                dataobject_output_text += "\nclass " + name_val + "(object):\n"
                for i, val in enumerate(value_val, 1):
                    dataobject_output_text += "    " + val + " = " + str(i) + "\n"
                dataobject_output_text += "    _value_map = {"
                for i, val in enumerate(value_val, 1):
                    if i > 1:
                        dataobject_output_text += ", "
                    dataobject_output_text += "'" + val + "': " + str(i)
                dataobject_output_text += "}\n"
                dataobject_output_text += "    _str_map = {"
                for i, val in enumerate(value_val, 1):
                    if i > 1:
                        dataobject_output_text += ", "
                    dataobject_output_text += str(i) + ": '" + val + "'"
                dataobject_output_text += "}\n"

        return dataobject_output_text



    #
    # Walk the data model definition and add Yaml constructors
    #
    def add_yaml_constructor (self):
        defs = yaml.load_all(self.data_yaml_text, Loader=IonYamlLoader)
        self.def_dict = {}
        for def_set in defs:
            for name,_def in def_set.iteritems():
                if isinstance(_def, OrderedDict):
                    self.def_dict[name] = _def
                tag = u'!%s' % (name)
                def constructor(loader, node):
                    value = node.tag.strip('!')
                    # See if this is an enum ref
                    if value in enums_by_name:
                        return {"__IsEnum": True, "value": value + "." + enums_by_name[value]["default"], "type": value}
                    else:
                        return str(value) + "()"
                yaml.add_constructor(tag, constructor, Loader=IonYamlLoader)

                xtag = u'!Extends_%s' % (name)
                def extends_constructor(loader, node):
                    if isinstance(node, yaml.MappingNode):
                        value = loader.construct_mapping(node)
                    else:
                        value = {}
                    return value
                yaml.add_constructor(xtag, extends_constructor, Loader=IonYamlLoader)


        # Do the same for any data model objects in the service
        # definition files.
        defs = yaml.load_all(self.service_yaml_text, Loader=IonYamlLoader)
        for def_set in defs:
            for name,_def in def_set.get('obj', {}).iteritems():
                if isinstance(_def, OrderedDict):
                    self.def_dict[name] = _def
                tag = u'!%s' % (name)
                def constructor(loader, node):
                    value = node.tag.strip('!')
                    # See if this is an enum ref
                    if value in enums_by_name:
                        return {"__IsEnum": True, "value": value + "." + enums_by_name[value]["default"], "type": value}
                    else:
                        return str(value) + "()"
                yaml.add_constructor(tag, constructor, Loader=IonYamlLoader)

                xtag = u'!Extends_%s' % (name)
                def extends_constructor(loader, node):
                    if isinstance(node, yaml.MappingNode):
                        value = loader.construct_mapping(node)
                    else:
                        value = {}
                    return value
                yaml.add_constructor(xtag, extends_constructor, Loader=IonYamlLoader)


    def lookup_associations(classname):
        from pyon.util.config import Config
        from pyon.util.containers import DotDict
        Predicates = DotDict()
        Predicates.update(Config(["res/config/associations.yml"]).data['PredicateTypes'])
        output = {}
        for key in Predicates:
            domain = str(Predicates[key]["domain"])
            range = str(Predicates[key]["range"])
            if classname in domain:
                output[key] = Predicates[key]
            if classname in range:
                output[key] = Predicates[key]
        return output


    #
    # Now walk the data model definition yaml files.  Generate
    # corresponding classes in the objects.py file.
    #
    def generate_object (self, opts):

        current_class_def_dict = None
        schema_extended = False
        current_class_schema = ""
        current_class = ""
        super_class = "IonObjectBase"
        self.class_args_dict = {}
        self.args = []
        self.fields = []
        self.field_details = []
        init_lines = []
        first_time = True

        for line in self.data_yaml_text.split('\n'):
            if line.isspace():
                continue
            elif line.startswith('  #'):
                init_lines.append('      ' + line + '\n')
            elif line.startswith('  '):
                if current_class_def_dict:
                    field = line.split(":")[0].strip()
                    try:
                        value = current_class_def_dict[field]
                    except KeyError:
                        # Ignore key error because value is nested
                        continue

                    enum_type = ""
                    if isinstance(value, str) and '()' in value:
                        value_type = value.strip('()')
                        converted_value = value
                        self.args.append(", ")
                        self.args.append(field + "=None")
                        init_lines.append('        self.' + field + " = " + field + " or " + value_type + "()\n")
                    else:
                        value_type = type(value).__name__
                        if value_type == 'dict' and "__IsEnum" in value:
                            enum_type = value["type"]
                            value_type = 'int'
                        converted_value = self.convert_val(value)
                        if value_type in ['OrderedDict', 'list', 'tuple']:
                            if value_type == 'OrderedDict':
                                value_type = 'dict'
                            self.args.append(", ")
                            self.args.append(field + "=None")
                            init_lines.append('        self.' + field + " = " + field + " or " + converted_value + "\n")
                        else:
                            self.args.append(", ")
                            self.args.append(field + "=" + converted_value)
                            init_lines.append('        self.' + field + " = " + field + "\n")
                    self.fields.append(field)
                    ###self.field_details.append({"attrname": field, "attrtype": value_type, "attrdefault": converted_value})
                    self.field_details.append((field, value_type, converted_value))
                    if enum_type:
                        current_class_schema += "\n                '" + field + "': {'type': '" + value_type + "', 'default': " + converted_value + ", 'enum_type': '" + enum_type + "'},"
                    else:
                        current_class_schema += "\n                '" + field + "': {'type': '" + value_type + "', 'default': " + converted_value + "},"
            elif line and line[0].isalpha():
                if '!enum' in line:
                    continue
                if first_time:
                    first_time = False
                else:
                    if opts.objectdoc:
                        attrtableentries = ""
                        field_details.sort()
                        for self.field_detail in self.field_details:
                            ###attrtableentries += html_doc_templates['attribute_table_entry'].substitute(attrname=self.field_detail["attrname"], type=self.field_detail["attrtype"], default=self.field_detail["attrdefault"], attrcomment="TODO")
                            attrtableentries += html_doc_templates['attribute_table_entry'].substitute(attrname=field_detail[0], type=field_detail[1].replace("'",'"'), default=field_detail[2].replace("'",'"'), attrcomment="")

                        related_associations = self.lookup_associations(current_class)
                        assoctableentries = ""
                        ###for assockey in related_associations:
                            ### assoctableentries += html_doc_templates['association_table_entry'].substitute(subject=str(related_associations[assockey]["domain"]), predicate=assockey, object=str(related_associations[assockey]["range"]), constraints="TODO", description="TODO2")

                        ###doc_output = html_doc_templates['obj_doc'].substitute(classname=current_class, baseclassname=super_class, classcomment="TODO", attrtableentries=attrtableentries, assoctableentries=assoctableentries)
                        for assoc in related_associations:
                            assoctableentries += html_doc_templates['association_table_entry'].substitute(subject=assoc[0], predicate=assoc[1], object=assoc[2], constraints="", description="")

                        super_classes = ""
                        sup = super_class
                        super_class_attribute_tables = ""
                        while sup != "IonObjectBase":
                            super_classes += '<a href="#' + sup + '">' + sup + '</a>, '
                            fld_details = class_args_dict[sup]["field_details"]
                            superclassattrtableentries = ""
                            fld_details.sort()
                            for fld_detail in fld_details:
                                superclassattrtableentries += html_doc_templates['attribute_table_entry'].substitute(attrname=fld_detail[0], type=fld_detail[1].replace("'",'"'), default=fld_detail[2].replace("'",'"'), attrcomment="")
                            super_class_attribute_tables += html_doc_templates['super_class_attribute_table'].substitute(super_class_name=sup, superclassattrtableentries=superclassattrtableentries)
                            sup = class_args_dict[sup]["extends"]
                        super_classes += '<a href="#IonObjectBase">IonObjectBase</a>'

                        doc_output = html_doc_templates['obj_doc'].substitute(classname=current_class, baseclasses=super_classes, classcomment="", attrtableentries=attrtableentries, super_class_attr_tables=super_class_attribute_tables, assoctableentries=assoctableentries)


                        datamodelhtmldir = 'interface/object_html'
                        if not os.path.exists(datamodelhtmldir):
                            os.makedirs(datamodelhtmldir)
                        datamodelhtmlfile = os.path.join(datamodelhtmldir, current_class + ".html")
                        try:
                            os.unlink(datamodelhtmlfile)
                        except:
                            pass
                        with open(datamodelhtmlfile, 'w') as f:
                            f.write(doc_output)                        
                        
                    ###class_args_dict[current_class] = {'args': self.args, 'fields': self.fields, 'field_details': self.field_details}
                    self.class_args_dict[current_class] = {'args': self.args, 'fields': self.fields, 'field_details': self.field_details, 'extends': super_class}

                    for arg in self.args:
                        self.dataobject_output_text += arg
                    self.dataobject_output_text += "):\n"
                    for init_line in init_lines:
                        self.dataobject_output_text += init_line
                if len(current_class_schema) > 0:
                    if schema_extended:
                        self.dataobject_output_text += current_class_schema + "\n              }.items())\n"
                    else:
                        self.dataobject_output_text += current_class_schema + "\n              }\n"
                self.dataobject_output_text += '\n'
                self.args = []
                self.fields = []
                init_lines = []
                current_class = line.split(":")[0]
                try:
                    current_class_def_dict = self.def_dict[current_class]           
                except KeyError:
                    current_class_def_dict = {}
                super_class = "IonObjectBase"
                if ': !Extends_' in line:
                    super_class = line.split("!Extends_")[1]
                    self.args = self.args + self.class_args_dict[super_class]["args"]
                    init_lines.append('        ' + super_class + ".__init__(self")
                    self.fields = self.fields + self.class_args_dict[super_class]["fields"]
                    for super_field in self.fields:
                        init_lines.append(", " + super_field)
                    init_lines.append(")\n")
                    schema_extended = True
                    current_class_schema = "\n    _schema = dict(" + super_class + "._schema.items() + {"
                    line = line.replace(': !Extends_','(')
                else:
                    schema_extended = False
                    current_class_schema = "\n    _schema = {"
                    line = line.replace(':','(IonObjectBase')
                ### self.dataobject_output_text += 'class ' + line + '):\n    def __init__(self'
                init_lines.append("        self.type_ = '" + current_class + "'\n")
                self.dataobject_output_text += "class " + line + "):\n\n    def __init__(self"


        data =  self.generate_service_object (current_class, init_lines, current_class_schema, schema_extended)

        init_lines = data['init_lines']
        current_class_schema = data['current_class_schema']
        schema_extended = data['schema_extended']


        if len(self.args) > 0:
            for arg in self.args:
                self.dataobject_output_text += arg
            self.dataobject_output_text += "):\n"
            for init_line in init_lines:
                self.dataobject_output_text += init_line
        if len(current_class_schema) > 0:
            if schema_extended:
                self.dataobject_output_text += current_class_schema + "\n              }.items())\n"
            else:
                self.dataobject_output_text += current_class_schema + "\n              }\n"




    #
    # Find any data model definitions lurking in the service interface
    # definition yaml files and generate classes for them.
    #
    def generate_service_object (self, current_class, init_lines, current_class_schema, schema_extended):

        # Find any data model definitions lurking in the service interface
        # definition yaml files and generate classes for them.
        lines = self.service_yaml_text.split('\n')
        for index in range(1,len(lines)):
            if lines[index].startswith('obj:'):
                index += 1
                while index in range(1,len(lines)) and not lines[index].startswith('---'):
                    line = lines[index]
                    if line.isspace():
                        index += 1
                        continue
                    line = line.replace('  ', '', 1)
                    if line.startswith('  #'):
                        init_lines.append('  ' + line + '\n')
                    elif line.startswith('  '):
                        if current_class_def_dict:
                            field = line.split(":")[0].strip()
                            try:
                                value = current_class_def_dict[field]
                            except KeyError:
                                # Ignore key error because value is nested
                                index += 1
                                continue

                            enum_type = ""
                            if isinstance(value, str) and '()' in value:
                                value_type = value.strip('()')
                                converted_value = value
                                self.args.append(", ")
                                self.args.append(field + "=" + converted_value)
                                init_lines.append('        self.' + field + " = " + field + " or " + value_type + "()\n")
                            else:
                                value_type = type(value).__name__
                                if value_type == 'dict' and "__IsEnum" in value:
                                    enum_type = value["type"]
                                    value_type = 'int'
                                converted_value = self.convert_val(value)
                                if value_type in ['OrderedDict', 'list', 'tuple']:
                                    if value_type == 'OrderedDict':
                                        value_type = 'dict'
                                    self.args.append(", ")
                                    self.args.append(field + "=None")
                                    init_lines.append('        self.' + field + " = " + field + " or " + converted_value + "\n")
                                else:
                                    self.args.append(", ")
                                    self.args.append(field + "=" + converted_value)
                                    init_lines.append('        self.' + field + " = " + field + "\n")
                            self.fields.append(field)
                            if enum_type:
                                 current_class_schema += "\n                '" + field + "': {'type': '" + value_type + "', 'default': " + converted_value + ", 'enum_type': '" + enum_type + "'},"
                            else:
                                current_class_schema += "\n                '" + field + "': {'type': '" + value_type + "', 'default': " + converted_value + "},"
                    elif line and line[0].isalpha():
                        if '!enum' in line:
                            index += 1
                            continue
                        self.class_args_dict[current_class] = {'args': self.args, 'fields': self.fields}
                        for arg in self.args:
                            self.dataobject_output_text += arg
                        self.dataobject_output_text += "):\n"
                        for init_line in init_lines:
                            self.dataobject_output_text += init_line
                        if len(current_class_schema) > 0:
                            if schema_extended:
                                self.dataobject_output_text += current_class_schema + "\n              }.items())\n"
                            else:
                                self.dataobject_output_text += current_class_schema + "\n              }\n"
                        self.dataobject_output_text += '\n'
                        self.dataobject_output_text += '\n'
                        self.args = []
                        self.fields = []
                        init_lines = []
                        current_class = line.split(":")[0]
                        try:
                            current_class_def_dict = self.def_dict[current_class]
                        except KeyError:
                            current_class_def_dict = None
                        super_class = "IonObjectBase"
                        if ': !Extends_' in line:
                            super_class = line.split("!Extends_")[1]
                            self.args = self.args + self.class_args_dict[super_class]["args"]
                            init_lines.append('        ' + super_class + ".__init__(self")
                            self.fields = self.fields + self.class_args_dict[super_class]["fields"]
                            for super_field in self.fields:
                                init_lines.append(", " + super_field)
                            init_lines.append(")\n")
                            schema_extended = True
                            current_class_schema = "\n    _schema = dict(" + super_class + "._schema.items() + {"
                            line = line.replace(': !Extends_','(')
                        else:
                            schema_extended = False
                            current_class_schema = "\n    _schema = {"
                            line = line.replace(':','(IonObjectBase')
                        ### self.dataobject_output_text += 'class ' + line + '):\n    def __init__(self'
                        init_lines.append("        self.type_ = '" + current_class + "'\n")
                        self.dataobject_output_text += "class " + line + "):\n\n    def __init__(self"
                        
                    index += 1
        return {'init_lines': init_lines, 'current_class_schema': current_class_schema, 'schema_extended':schema_extended}




    #
    # Generate object model
    #
    def generate (self, opts):
       

        # Get data from the file
        combined_yaml_text = self.get_yaml_text();


        # Parse once looking for enum types.  These classes will go at
        # the top of the objects.py.  Defs are also put into a dict
        # so we can easily reference their values later in the parsing
        # logic.
        self.dataobject_output_text = "#!/usr/bin/env python\n\n"
        self.dataobject_output_text += "#\n# This file is auto generated\n#\n\n"
        self.dataobject_output_text += "from pyon.core.object import IonObjectBase\n"
        self.dataobject_output_text += "# Enums\n"

        # Parse the data
        self.dataobject_output_text += self.parse_yaml_text(combined_yaml_text)
        enum_tag = u'!enum'
        def enum_constructor(loader, node):
            val_str = str(node.value)
            val_str = val_str[1:-1].strip()
            if 'name' in val_str:
                name_str = val_str.split(',', 1)[0]
                name_val = name_str.split('=')[1].strip()
                return {"__IsEnum": True, "value": name_val + "." + enums_by_name[name_val]["default"], "type": name_val}

            else:
                return {"__IsEnum": True, "_NameNotProvided": True}

        # Add YAML constructors
        yaml.add_constructor(enum_tag, enum_constructor, Loader=IonYamlLoader)
        self.add_yaml_constructor ()


        # Delimit the break between the enum classes and
        # and the data model classes
        self.dataobject_output_text += "\n\n# Data Objects\n"


        # Generate corresponding classes in the object.py file
        self.generate_object (opts)
        
        # Write to the objects.py file
        self.write_to_object_model_file ()

