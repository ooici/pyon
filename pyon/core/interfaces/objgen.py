#!/usr/bin/env python

"""Resource and object export"""

__author__ = 'Michael Meisinger'

import csv
import os.path

from pyon.core.registry import getextends, isenum
from pyon.public import RT, OT

import interface.objects

class ObjectGenerator(object):

    @staticmethod
    def get_extends(obj_class):
        parents = [parent for parent in obj_class.__mro__ if parent.__name__ not in {'IonObjectBase', 'object', obj_class.__name__}]
        return parents

    def export_objects(self, filename=None):
        sub_types = {}
        for obj_type in OT.keys():
            ot_class = getattr(interface.objects, obj_type)
            base_type = ot_class.__mro__[1].__name__
            sub_types.setdefault(base_type, set()).add(obj_type)

        res_rows = []
        for obj_type in sorted(OT.keys()):
            # Compute type level info
            is_leaf = str(not bool(sub_types.get(obj_type, None)))
            ot_class = getattr(interface.objects, obj_type)
            if not hasattr(ot_class, "_schema"):
                continue
            base_types_list = [bc.__name__ for bc in reversed(self.get_extends(ot_class))]
            base_type = base_types_list[-1] if base_types_list else ""
            base_types = "/".join(base_types_list[:-1])
            oschema = ot_class._schema
            if obj_type in RT:
                group = "resource"
            elif isenum(obj_type):
                group = "enum"
            elif "origin" in oschema and "base_types" in oschema:
                # Not all events end in Event
                group = "event"
            else:
                group = "object"

            res_rows.append(["type", base_types, base_type, obj_type, "", group, is_leaf, "True", "", "", ot_class._class_info.get("docstring", "").replace("\\", "").strip(), ""])

            # Add a few default attributes
            #res_rows.append([group, base_types, obj_type, "type_", "str", is_leaf, "False" if base_types else "True", "", "", "Resource type"])
            if group == "resource" or group == "object":
                res_rows.append([group, base_types, base_type, obj_type, "__", "first", is_leaf, "True", "", "", "", ""])

            # List attributes
            for att in sorted(oschema.keys()):
                if group == "resource" and att in {"addl", "alt_ids", "_id", "name", "description", "lcstate", "availability", "ts_created", "ts_updated"}:
                    continue
                att_obj = oschema[att]
                ot, odef, odeco, odesc = att_obj["type"], att_obj["default"], att_obj["decorators"], att_obj["description"]
                if group == "resource" and att == "name":
                    odesc = "Human readable long name of the resource, displayable in lists"

                att_def = obj_type
                leaf_attr = True
                for base_class in self.get_extends(ot_class):
                    if hasattr(base_class, "_schema") and att in base_class._schema:
                        att_def = base_class.__name__
                        leaf_attr = False
                is_internal = ""
                attr_desc = odesc.replace("\\", "").strip()
                if "(SYS)" in attr_desc:
                    is_internal = "System"
                res_rows.append([group, base_types, base_type, obj_type, att, ot, is_leaf, leaf_attr, att_def, odef, attr_desc, is_internal])

        if not filename:
            csvfile_name = os.path.join("interface", 'object_model.csv')
            try:
                os.unlink(csvfile_name)
            except:
                pass
        else:
            csvfile_name = filename

        print " Writing object model csv to '" + csvfile_name + "'"
        csvfile = csv.writer(open(csvfile_name, 'wb'), delimiter=',',
            quotechar='"', quoting=csv.QUOTE_ALL)
        csvfile.writerow(["Group", "Base Types", "Base Type", "Type Name", "Attribute", "Attr Type", "Leaf Type", "Leaf Attr", "Definition Type", "Default", "Description", "Internal"])
        csvfile.writerows(res_rows)
