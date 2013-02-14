#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger, Tom Lennan'
__license__ = 'Apache 2.0'

import os
import re
import inspect
from collections import OrderedDict, Mapping, Iterable
import pprint
import StringIO

from pyon.util.log import log
from pyon.core.exception import BadRequest
try:
    import numpy as np
    _have_numpy = True
except ImportError as e:
    _have_numpy = False

built_in_attrs = set(['_id', '_rev', 'type_', 'blame_'])

class IonObjectBase(object):

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, other):
        if type(other) == type(self):
            if other.__dict__ == self.__dict__:
                return True
        return False

    def _validate(self):
        """
        Compare fields to the schema and raise AttributeError if mismatched.
        Named _validate instead of validate because the data may have a field named "validate".
        """
        fields, schema = self.__dict__, self._schema

        # Check for extra fields not defined in the schema
        extra_fields = fields.viewkeys() - schema.viewkeys() - built_in_attrs
        if len(extra_fields) > 0:
            raise AttributeError('Fields found that are not in the schema: %r' % (list(extra_fields)))

        required_decorator = 'Required'
        content_type_decorator = 'ContentType'
        content_count_decorator = 'ContentCount'
        value_range_decorator = 'ValueRange'
        value_pattern_decorator = 'ValuePattern'

        # Check required field criteria met
        for key in schema:
            if 'decorators' in schema[key] and required_decorator in schema[key]['decorators']:
                if not key in fields or fields[key] is None:
                    raise AttributeError('Required value "%s" not set' % key)

        # Check each attribute
        for key in fields.iterkeys():
            if key in built_in_attrs:
                continue

            schema_val = schema[key]

            # Correct any float or long types that got downgraded to int
            if isinstance(fields[key], int):
                if schema_val['type'] == 'float':
                    fields[key] = float(fields[key])
                elif schema_val['type'] == 'long':
                    fields[key] = long(fields[key])

            # argh, annoying work around for OrderedDict vs dict issue
            if type(fields[key]) == dict and schema_val['type'] == 'OrderedDict':
                fields[key] = OrderedDict(fields[key])

            # Basic type checking
            field_val = fields[key]
            if 'decorators' in schema_val:
                log.debug("Validating %s: %s: %s: %s" % (key, schema_val["type"], schema_val["decorators"], str(field_val)))
            else:
                log.debug("Validating %s: %s: %s" % (key, schema_val["type"], str(field_val)))
            if type(field_val).__name__ != schema_val['type']:

                # if the schema doesn't define a type, we can't very well validate it
                if schema_val['type'] == 'NoneType':
                    continue

                # Already checked for required above.  Assume optional and continue
                if field_val is None:
                    continue

                # IonObjects are ok for dict fields too!
                if isinstance(field_val, IonObjectBase) and schema_val['type'] == 'OrderedDict':
                    continue

                if not key in fields or fields[key] is None:
                    raise AttributeError('Required value "%s" not set' % key)

                # Check for inheritance
                if self.check_inheritance_chain(type(field_val), schema_val['type']):
                    continue

                # Check enum types
                from pyon.core.registry import enum_classes
                if isinstance(field_val, int) and schema_val['type'] in enum_classes:
                    if field_val not in enum_classes(schema_val['type'])._str_map:
                        raise AttributeError('Invalid enum value "%d" for field "%s.%s", should be between 1 and %d' %
                                     (fields[key], type(self).__name__, key, len(enum_classes(schema_val['type'])._str_map)))
                    else:
                        continue

                # TODO work around for msgpack issue
                if type(field_val) == tuple and schema_val['type'] == 'list':
                    continue

                # TODO remove this at some point
                if isinstance(field_val, IonObjectBase) and schema_val['type'] == 'dict':
                    log.warn('TODO: Please convert generic dict attribute type to abstract type for field "%s.%s"' % (type(self).__name__, key))
                    continue

                # Special case check for ION object being passed where default type is dict or str
                if 'decorators' in schema_val:
                    if content_type_decorator in schema_val['decorators']:
                        if isinstance(field_val, IonObjectBase) and schema_val['type'] == 'dict' or schema_val['type'] == 'str':
                            self.check_content(key, field_val, schema_val['decorators'][content_type_decorator])
                            continue

                raise AttributeError('Invalid type "%s" for field "%s.%s", should be "%s"' %
                                     (type(fields[key]), type(self).__name__, key, schema_val['type']))

            if type(field_val).__name__ == 'str':
                if value_pattern_decorator in schema_val['decorators']:
                    self.check_string_pattern_match(key, field_val, schema_val['decorators'][value_pattern_decorator])

            if type(field_val).__name__ in ['int', 'float', 'long']:
                if value_range_decorator in schema_val['decorators']:
                    self.check_numeric_value_range(key, field_val, schema_val['decorators'][value_range_decorator])

            if 'decorators' in schema_val:
                if content_type_decorator in schema_val['decorators']:
                    if schema_val['type'] == 'list':
                        self.check_collection_content(key, field_val, schema_val['decorators'][content_type_decorator])
                    elif schema_val['type'] == 'dict' or schema_val['type'] == 'OrderedDict':
                        self.check_collection_content(key, field_val.values(), schema_val['decorators'][content_type_decorator])
                    else:
                        self.check_content(key, field_val, schema_val['decorators'][content_type_decorator])
                if content_count_decorator in schema_val['decorators']:
                    if schema_val['type'] == 'list':
                        self.check_collection_length(key, field_val, schema_val['decorators'][content_count_decorator])
                    if schema_val['type'] == 'dict' or schema_val['type'] == 'OrderedDict':
                        self.check_collection_length(key, field_val.values(), schema_val['decorators'][content_count_decorator])

            if isinstance(field_val, IonObjectBase):
                field_val._validate()

            # Next validate only IonObjects found in child collections.
            # Note that this is non-recursive; only for first-level collections.
            elif isinstance(field_val, Mapping):
                for subkey in field_val:
                    subval = field_val[subkey]
                    if isinstance(subval, IonObjectBase):
                        subval._validate()
            elif isinstance(field_val, Iterable):
                for subval in field_val:
                    if isinstance(subval, IonObjectBase):
                        subval._validate()

    def _get_type(self):
        return self.__class__.__name__

    def _get_extends(self):
        parents = [parent.__name__ for parent in self.__class__.__mro__ if parent.__name__ not in ['IonObjectBase', 'object', self._get_type()]]
        return parents

    def __contains__(self, item):
        return hasattr(self, item)

    def update(self, other):
        """
        Method that allows self object attributes to be updated with other object.
        Other object must be of same type or super type.
        """
        if type(other) != type(self):
            bases = inspect.getmro(self.__class__)
            if other.__class__ not in bases:
                raise BadRequest("Object %s and %s do not have compatible types for update" % (type(self).__name__, type(other).__name__))
        for key in other.__dict__:
            setattr(self, key, other.__dict__[key])

    #Decorator methods

    def is_decorator(self, field, decorator):
        if self._schema[field]['decorators'].has_key(decorator):
            return True

        return False

    def get_decorator_value(self, field, decorator):
        if self._schema[field]['decorators'].has_key(decorator):
            return self._schema[field]['decorators'][decorator]

        return None

    def find_field_for_decorator(self, decorator='', decorator_value=None):
        '''
        This method will iterate the set of fields in te object and look for the first field
        that has the specified decorator and decorator value, if supplied.
        @param decorator: The decorator on the field to be searched for
        @param decorator_value: An optional value to search on
        @return fld: The name of the field that has the decorator
        '''
        for fld in self._schema:
            if self.is_decorator(fld, decorator ):
                if decorator_value is not None and self.get_decorator_value(fld, decorator) == decorator_value:
                    return fld
                else:
                    return fld

        return None

    # Decorator validation methods

    def check_string_pattern_match(self, key, value, pattern):
        m = re.match(pattern, value)

        if not m:
            raise AttributeError('Invalid value pattern %s for field "%s.%s", should match regular expression %s' %
                (value, type(self).__name__, key, pattern))

    def check_numeric_value_range(self, key, value, value_range):
        if ',' in value_range:
            min = eval(value_range.split(',')[0].strip())
            max = eval(value_range.split(',')[1].strip())
        else:
            min = max = eval(value_range.split(',')[0].strip())

        if value < min or value > max:
            raise AttributeError('Invalid value %s for field "%s.%s", should be between %d and %d' %
                (str(value), type(self).__name__, key, min, max))

    def check_inheritance_chain(self, typ, expected_type):

        for baseclz in typ.__bases__:
            if baseclz.__name__ == expected_type.strip():
                return True
            if baseclz.__name__ == "object":
                return False
            else:
                val = self.check_inheritance_chain(baseclz, expected_type)
                return val
        return False

    def check_collection_content(self, key, list_values, content_types):
        split_content_types = []
        if ',' in content_types:
            split_content_types = content_types.split(',')
        else:
            split_content_types.append(content_types)

        for value in list_values:
            match_found = False
            for content_type in split_content_types:
                if type(value).__name__ == content_type.strip():
                    match_found = True
                    break
                # Check for inheritance
                if self.check_inheritance_chain(type(value), content_type):
                    match_found = True
                    break

            if not match_found:
                raise AttributeError('Invalid value type %s in collection field "%s.%s", should be one of "%s"' %
                    (str(list_values), type(self).__name__, key, content_types))

    def check_content(self, key, value, content_types):
        split_content_types = []
        if ',' in content_types:
            split_content_types = content_types.split(',')
        else:
            split_content_types.append(content_types)
        log.info("split_content_types: %s", split_content_types)

        for content_type in split_content_types:
            if type(value).__name__ == content_type.strip():
                return

            # Check for inheritance
            if self.check_inheritance_chain(type(value), content_type):
                return

        raise AttributeError('Invalid value type %s in field "%s.%s", should be one of "%s"' %
                (str(value), type(self).__name__, key, content_types))

    def check_collection_length(self, key, list_values, length):
        if ',' in length:
            min = int(length.split(',')[0].strip())
            max = int(length.split(',')[1].strip())
        else:
            min = max = int(length.split(',')[0].strip())

        if len(list_values) < min or len(list_values) > max:
            raise AttributeError('Invalid value length for collection field "%s.%s", should be between %d and %d' %
                (type(self).__name__, key, min, max))


class IonMessageObjectBase(IonObjectBase):
    pass

def walk(o, cb):
    """
    Utility method to do recursive walking of a possible iterable (inc dicts) and do inline transformations.
    You supply a callback which receives an object. That object may be an iterable (which will then be walked
    after you return it, as long as it remains an iterable), or it may be another object inside of that.

    If a dict is discovered, your callback will receive the dict as a whole and the contents of values only. Keys are left untouched.

    @TODO move to a general utils area?
    """
    newo = cb(o)

    # is now or is still an iterable? iterate it.
    if _have_numpy:
        if isinstance(newo, np.ndarray):
            return newo
    if hasattr(newo, '__iter__'):
        if isinstance(newo, dict):
            return dict(((k, walk(v, cb)) for k, v in newo.iteritems()))
        else:
            return [walk(x, cb) for x in newo]

    elif isinstance(newo, IonObjectBase):
        # IOs are not iterable and are a huge pain to make them look iterable, special casing is fine then
        # @TODO consolidate with _validate method in IonObjectBase
        fields, set_fields = newo.__dict__, newo._schema

        for fieldname in set_fields:
            fieldval = getattr(newo, fieldname)
            newfo = walk(fieldval, cb)
            if newfo != fieldval:
                setattr(newo, fieldname, newfo)

        return newo

    else:
        return newo


class IonObjectSerializationBase(object):
    """
    Base serialization class for serializing/deserializing IonObjects.

    Provides the operate method, which walks and applies a transform method. The operate method is
    renamed serialize/deserialize in derived classes.

    At this base level, the _transform method is undefined - you must pass one in. Using
    IonObjectSerializer or IonObjectDeserializer defines them for you.
    """
    def __init__(self, transform_method=None, **kwargs):
        self._transform_method = transform_method or self._transform

    def operate(self, obj):
        return walk(obj, self._transform_method)

    def _transform(self, obj):
        raise NotImplementedError("Implement _transform in a derived class")


class IonObjectSerializer(IonObjectSerializationBase):
    """
    Serializer for IonObjects.

    Defines a _transform method to turn IonObjects into dictionaries to be deserialized by
    an IonObjectDeserializer.

    Used by the codec interceptor and when being written to CouchDB.
    """

    serialize = IonObjectSerializationBase.operate

    def _transform(self, obj):
        if isinstance(obj, IonObjectBase):
            res = dict((k, v) for k, v in obj.__dict__.iteritems() if k in obj._schema or k in built_in_attrs)
            return res

        return obj


class IonObjectBlameSerializer(IonObjectSerializer):

    def _transform(self, obj):
        res = IonObjectSerializer._transform(self, obj)
        blame = None
        try:
            blame = os.environ["BLAME"]
        except:
            pass
        if blame and isinstance(obj, IonObjectBase):
            res["blame_"] = blame

        return res


class IonObjectDeserializer(IonObjectSerializationBase):
    """
    Deserializer for IonObjects.

    Defines a _transform method to transform dictionaries produced by IonObjectSerializer back
    into IonObjects. You *MUST* pass an object registry
    """

    deserialize = IonObjectSerializationBase.operate

    def __init__(self, transform_method=None, obj_registry=None, **kwargs):
        assert obj_registry
        self._obj_registry = obj_registry
        IonObjectSerializationBase.__init__(self, transform_method=transform_method)

    def _transform(self, obj):
        # Note: This check to detect an IonObject is a bit risky (only type_)
        if isinstance(obj, dict) and "type_" in obj:
            objc    = obj.copy()
            type    = objc['type_'].encode('ascii')

            # don't supply a dict - we want the object to initialize with all its defaults intact,
            # which preserves things like IonEnumObject and invokes the setattr behavior we want there.
            ion_obj = self._obj_registry.new(type)
            for k, v in objc.iteritems():

                # CouchDB adds _attachments and puts metadata in it
                # in pyon metadata is in the document
                # so we discard _attachments while transforming between the two
                if k not in ("type_", "_attachments", "_conflicts"):
                    setattr(ion_obj, k, v)
                if k == "_conflict":
                    log.warn("CouchDB conflict detected for ID=%S (ignored): %s", obj.get('_id', None), v)

            return ion_obj

        return obj


class IonObjectBlameDeserializer(IonObjectDeserializer):

    def _transform(self, obj):

        def handle_ion_obj(in_obj):
            objc    = in_obj.copy()
            type    = objc['type_'].encode('ascii')

            # don't supply a dict - we want the object to initialize with all its defaults intact,
            # which preserves things like IonEnumObject and invokes the setattr behavior we want there.
            ion_obj = self._obj_registry.new(type)
            for k, v in objc.iteritems():
                if k != "type_":
                    setattr(ion_obj, k, v)

            return ion_obj

        # Note: This check to detect an IonObject is a bit risky (only type_)
        if isinstance(obj, dict):
            if "blame_" in obj:
                if "type_" in obj:
                    return handle_ion_obj(obj)
                else:
                    obj.pop("blame_")
            else:
                if "type_" in obj:
                    return handle_ion_obj(obj)

        return obj

ion_serializer = IonObjectSerializer()


# Pretty print IonObjects
def ionprint(obj):
    d = ion_serializer.serialize(obj)

    fstream = StringIO.StringIO()

    pprint.pprint(d, stream=fstream)

    result = fstream.getvalue()
    fstream.close()
    return result
