#!/usr/bin/env python

__author__ = 'Adam Smith, Tom Lennan'

import inspect
from copy import deepcopy

from pyon.core.exception import NotFound
from pyon.core.object import walk

import interface.objects
import interface.messages


enum_classes = {}
model_classes = {}
message_classes = {}


def getextends(type):
    """
    Returns a list of classes that the object with the given type extends.
    @param type (str) Object type
    @retval List of object types that are extended by given type
    """
    ret = []
    base_clzz = model_classes[type]
    for name in model_classes:
        clzz = model_classes[name]
        bases = inspect.getmro(clzz)
        if base_clzz in bases:
            ret.append(name)
    return ret


def issubtype(obj_type, base_type):
    obj_cls = model_classes.get(obj_type, None)
    base_cls = model_classes.get(base_type, None)

    if obj_cls and base_cls:
        return base_cls in obj_cls.__mro__

    return False


def isenum(clzz_name):
    return clzz_name in enum_classes


def get_message_class_parm_type(service_name, service_operation, parameter, in_out):
    """
    Utility function to return the type for the specified parameters
    """
    class_name = service_name + '_' + service_operation + '_' + in_out
    if class_name in message_classes:
        cls = message_classes[class_name]
    else:
        raise NotFound("Message class $%s is not found in the ION registry." % class_name)

    if parameter in cls._schema:
        parm_type = cls._schema[parameter]['type']
    else:
        raise NotFound("Parameter %s not found in class %s" % (parameter, class_name))

    return parm_type


def get_message_class_in_parm_type(service_name, service_operation, parameter):
    """
    Helper function for get_message_class_parm_type
    """
    return get_message_class_parm_type(service_name, service_operation, parameter, 'in')


def get_message_class_out_parm_type(service_name, service_operation, parameter):
    """
    Helper function for get_message_class_parm_type
    """
    return get_message_class_parm_type(service_name, service_operation, parameter, 'out')


def is_ion_object(_def):
    try:
        if _def in model_classes:
            return True
        elif _def in message_classes:
            return True
    except Exception:
        pass

    return False


def is_ion_object_dict(obj):
    try:
        if "type_" in obj:
            return True
    except Exception:
        pass

    return False


def has_class_decorator(class_obj, decorator):
    if getattr(class_obj, '_class_info'):
        if class_obj._class_info['decorators'].has_key(decorator):
            return True
    return False


def get_class_decorator_value(class_obj, decorator):

    if getattr(class_obj, '_class_info'):
        if class_obj._class_info['decorators'].has_key(decorator):
            return class_obj._class_info['decorators'][decorator]

    return None


class IonObjectRegistry(object):
    """
    In memory registry for all ION object types and factory for creating new object instances.
    Supports data objects, enum objects and message objects.
    """

    validate_setattr = False

    def __init__(self):
        classes = inspect.getmembers(interface.objects, inspect.isclass)
        for name, clzz in classes:
            if clzz.__bases__[0].__name__ == "IonEnum":
                enum_classes[name] = clzz
            else:
                model_classes[name] = clzz
        classes = inspect.getmembers(interface.messages, inspect.isclass)
        for name, clzz in classes:
            message_classes[name] = clzz

        from pyon.core.bootstrap import CFG
        self.validate_setattr = CFG.get_safe('container.objects.validate.setattr', False)

    def new(self, _def, _dict=None, **kwargs):
        """Instantiates an IonObject based on given object type name and initial values.
        Note: This is called for the IonObject() instantiation but not for the ObjType() instantiation.
        @param _def    Name of object type
        @param _dict   A dict/DotDict/derivative with initial values
        @param kwargs  Additional initial values
        """
        if _def in model_classes:
            clzz = model_classes[_def]
        elif _def in message_classes:
            clzz = message_classes[_def]
        elif _def in enum_classes:
            clzz = enum_classes[_def]
        else:
            raise NotFound("No matching class found for name %s" % _def)

        # Conditionally override the __setattr__ method to include additional client side validation
        # NOTE: currently mandatory because it performs unicode to UTF-8 str conversion as side effect
        if self.validate_setattr:
            def validating_setattr(self, name, value):
                from pyon.core.object import BUILT_IN_ATTRS
                if name not in self._schema and name not in BUILT_IN_ATTRS:
                    raise AttributeError("'%s' object has no attribute '%s'" % (type(self).__name__, name))
                self.__dict__[name] = value
            setattrmethod = validating_setattr
            setattr(clzz, "__setattr__", setattrmethod)

        if _dict:
            # Traverse input parameters looking for dict values being passed in as
            # the init values of complex types.  Instantiate new object and substitute
            # into the argument dict.
            tmpdict = deepcopy(_dict)

            for key in tmpdict:
                if key in clzz._schema:
                    if isinstance(tmpdict[key], dict) and clzz._schema[key]["type"] in model_classes:
                        obj_param = self.new(clzz._schema[key]["type"], tmpdict[key])
                        tmpdict[key] = obj_param
                else:
                    raise AttributeError("'%s' object has no attribute '%s'" % (clzz.__name__, key))

            # Apply dict values, then override with kwargs
            keywordargs = tmpdict
            keywordargs.update(kwargs)
            obj = clzz(**keywordargs)
        else:
            obj = clzz(**kwargs)

        return obj
