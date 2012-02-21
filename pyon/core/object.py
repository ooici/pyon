#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger, Tom Lennan'
__license__ = 'Apache 2.0'

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
        id_and_rev_set = set(['_id','_rev', 'type_'])
        fields, schema = self.__dict__, self._schema
        extra_fields = fields.viewkeys() - schema.viewkeys() - id_and_rev_set
        if len(extra_fields) > 0:
            raise AttributeError('Fields found that are not in the schema: %r' % (list(extra_fields)))
        for key in fields.iterkeys():
            if key in id_and_rev_set:
                continue
            field_val, schema_val = fields[key], schema[key]
            if type(field_val).__name__ != schema_val['type']:

                if field_val is None and schema_val['required'] == True:
                    raise AttributeError('Required parameter "%s" not set' % key)

                # if the schema doesn't define a type, we can't very well validate it
                if schema_val['type'] == 'NoneType':
                    continue

                # Special handle numeric types.  Allow int to be
                # passed for long and float.  Auto convert to the
                # right type.
                if isinstance(field_val, int):
                    if schema_val['type'] == 'float':
                        fields[key] = float(fields[key])
                        continue
                    elif schema_val['type'] == 'long':
                        fields[key] = long(fields[key])
                        continue

                # argh, annoying work around for OrderedDict vs dict issue
                if type(field_val) == dict and schema_val['type'] == 'OrderedDict':
                     fields[key] = OrderedDict(field_val)
                     continue

                # optional fields ok?
                if field_val is None:
                    continue

                # IonObjects are ok for dict fields too!
                if isinstance(field_val, IonObjectBase) and schema_val['type'] == 'OrderedDict':
                    continue

                # TODO work around for msgpack issue
                if type(field_val) == tuple and schema_val['type'] == 'list':
                    continue

                raise AttributeError('Invalid type "%s" for field "%s", should be "%s"' %
                                     (type(fields[key]), key, schema_val['type']))
            if isinstance(field_val, IonObjectBase):
                field_val._validate()
            # Next validate only IonObjects found in child collections. Other than that, don't validate collections.
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
        if isinstance(newo,np.ndarray):
            return newo
    if hasattr(newo, '__iter__'):
        if isinstance(newo, dict):
            return dict(((k, walk(v, cb)) for k,v in newo.iteritems()))
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
        self._transform_method  = transform_method or self._transform

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
            res = dict((k, v) for k, v in obj.__dict__.iteritems() if k in obj._schema or k in ['_id', '_rev'])
            res["type_"] = obj.__class__.__name__
            return res
        if _have_numpy:
            if isinstance(obj,np.ndarray):
                log.debug('got numpy: %s', type(obj))
                res = {'numpy': {
                    'type':str(obj.dtype),
                    'shape':obj.shape,
                    'body':obj.tostring()
                }}
                log.debug('res: %s', res)
                return res

        return obj

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
            type    = objc.pop('type_')

            # don't supply a dict - we want the object to initialize with all its defaults intact,
            # which preserves things like IonEnumObject and invokes the setattr behavior we want there.
            ion_obj = self._obj_registry.new(type.encode('ascii'))
            for k, v in objc.iteritems():
                setattr(ion_obj, k, v)

            return ion_obj
        if _have_numpy:
            if isinstance(obj, dict):
                msg = obj.get('numpy',False)
                log.debug('message = %s', msg)
                if msg:
                    shape = msg.get('shape')
                    type = msg.get('type')
                    data = msg.get('body')
                    log.debug('Numpy Array Detected:\n  type: %s\n  shape: %s\n  body: %s',type,shape,data)
                    ret = np.fromstring(string=data,dtype=type).reshape(shape)
                    return np.array(ret)


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
