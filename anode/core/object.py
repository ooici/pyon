#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import re
import hashlib
from collections import OrderedDict, defaultdict
from weakref import WeakSet, WeakValueDictionary

import yaml

class AnodeObjectError(Exception):
    pass

class AnodeObjectMetaType(type):
    """
    Metaclass that automatically generates subclasses of AnodeObject with the appropriate defaults for each field.
    """

    _type_cache = {}

    def __call__(cls, _def, _dict=None, *args, **kwargs):
        if _def in AnodeObjectMetaType._type_cache:
            clsType = AnodeObjectMetaType._type_cache[_def]
        else:
            # Check that the object we are wrapping is an AnodeObjectDefinition
            if not isinstance(_def, AnodeObjectDefinition):
                raise AnodeObjectError('AnodeObject init first argument must be an AnodeObjectDefinition')

            # Generate a unique class name
            clsName = '%s_%s_%s' % (cls.__name__, _def.type.name, _def.hash[:8])
            clsDict = {'_def': _def}
            clsDict.update(_def.default)
            #clsDict['__slots__'] = clsDict.keys() + ['__weakref__']

            clsType = AnodeObjectMetaType.__new__(AnodeObjectMetaType, clsName, (cls,), clsDict)
            AnodeObjectMetaType._type_cache[_def] = clsType

        # Finally allow the instantiation to occur, but slip in our new class type
        obj = super(AnodeObjectMetaType, clsType).__call__(_dict, *args, **kwargs)
        return obj

class AnodeObject(object):
    __metaclass__ = AnodeObjectMetaType
    
    def __init__(self, _dict=None, **kwargs):
        """
        Instead of instantiating these directly, you should go through an AnodeObjectRegistry.
        If you need to instantiate directly, set _def to an instance of AnodeObjectDefinition.
        """
        
        if _dict is not None:
            self.__dict__.update(_dict)
        self.__dict__.update(kwargs)

    def __str__(self):
        """ This method will probably be too expensive to use frequently due to object allocation and YAML. """
        _dict = self._def.default.copy()
        _dict.update(self.__dict__)
        #return '%s(%r)' % (self.__class__, _dict)
        # If the yaml is too slow revert to the line above
        name = '%s <%s>' % (self.__class__.__name__, id(self))
        return yaml.dump({name: _dict}, default_flow_style=False)

    def _validate(self):
        """
        Compare fields to the schema and raise AttributeError if mismatched.
        Named _validate instead of validate because the data may have a field named "validate".
        """
        fields, schema = self.__dict__, self._def.default
        extra_fields = fields.viewkeys() - schema.viewkeys()
        if len(extra_fields) > 0:
            raise AttributeError('Fields found that are not in the schema: %r' % (list(extra_fields)))
        for key in fields.iterkeys():
            if type(fields[key]) is not type(schema[key]):
                raise AttributeError('Invalid %s for field "%s", should be %s' %
                                     (type(fields[key]), key, type(schema[key])))

def hashfunc(text):
    return hashlib.sha1(text).hexdigest()

_sha_re = re.compile('[0-9a-f]{40}')
def is_hash(val):
    return len(val) == 40 and _sha_re.match(val) is not None

class AnodeObjectDefinition(object):
    """ An ION object definition, with a single parent type and a specific version. """

    __slots__ = ('type', 'hash', 'default', 'def_text')

    def __init__(self, _type, hash, default, def_text):
        self.type = _type
        self.hash = hash
        self.default = default
        self.def_text = def_text

class AnodeObjectType(object):
    """
    An ION object type, with a single name and one or more defined versions.
    Versions are ordered by registration time, so the last version added is considered the latest.
    """

    __slots__ = ('name', 'versions', 'latest_def')

    def __init__(self, name='<default>'):
        self.name = name
        # Map the definition version hash to the actual definition
        self.versions = OrderedDict()

        # Cache pointer to the latest version definition
        self.latest_def = None

    def register_def_raw(self, default, def_text):
        """ The definition should be in something like YAML canonical form, see AnodeObjectRegistry for more. """
        hash = hashfunc(def_text)
        definition = AnodeObjectDefinition(self, hash, default, def_text)
        self.register_def(hash, definition)
        return definition

    def register_def(self, hash, definition):
        self.versions[hash] = definition
        self.latest_def = definition


class AnodeObjectRegistry(object):
    """
    A simple key-value store that stores by name and by definition hash for versioning.
    Also includes optional persistence to a document database.

    TODO: Implement persistence once the document DB type is chosen.
    """

    do_validate = True

    def __init__(self):
        self.def_by_hash = {}
        self.type_by_name = defaultdict(AnodeObjectType)
        self.instances = WeakSet()
        self.instances_by_name = WeakValueDictionary()

    def get_def(self, _def):
        """
        _def can be an instance of AnodeObjectDefinition, an instance of AnodeObjectType
        (to use the latest version of that type), a definition name (to use the latest version of that type),
        or a hash to lookup a specific definition.
        """
        if not isinstance(_def, AnodeObjectDefinition):
            if isinstance(_def, AnodeObjectType):
                _type = _def
                _def = _type.latest_def
            if is_hash(_def):
                hash = _def
                if not hash in self.def_by_hash:
                    raise AnodeObjectError('ION object hash "%s" not in registry' % (hash))
                _def = self.def_by_hash[hash]
            elif isinstance(_def, str):     # Don't support unicode strings
                name = _def
                if not name in self.type_by_name:
                    raise AnodeObjectError('ION object type "%s" not in registry' % (name))
                _type = self.type_by_name[name]
                _def = _type.latest_def
            else:
                raise AnodeObjectError("Invalid ION object definition")
        return _def

    def new(self, _def, _dict=None, **kwargs):
        """ See get_def() for definition lookup options. """

        _def = self.get_def(_def)
        obj = AnodeObject(_def, _dict, **kwargs)
        self.instances.add(obj)
        self.instances_by_name[_def.type.name] = obj
        return obj

    def register_def(self, name, default, def_text):
        """
        Register a type in the registry. It will index by both name and version,
        where version is the SHA1 hash of the definition. The definition should
        typically be in YAML canonical form (for consistent hashing).
        """

        _type = self.type_by_name[name]
        _type.name = name
        _def = _type.register_def_raw(default, def_text)
        self.def_by_hash[_def.hash] = _def
        return _def

    def register_yaml(self, yaml_text):
        """ Parse the contents of a YAML file that contains one or more object definitions. """

        defs = yaml.load_all(yaml_text)
        for def_set in defs:
            for name,_def in def_set.iteritems():
                # TODO: Hook into pyyaml's event emitting stuff to try to get the canonical form without re-dumping
                def_text = yaml.dump(_def, canonical=True, allow_unicode=True)
                self.register_def(name, _def, def_text)

