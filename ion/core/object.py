#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import re
import hashlib
from collections import OrderedDict, defaultdict
from weakref import WeakSet, WeakValueDictionary

import yaml

class IonObjectError(Exception):
    pass

class IonObject(object):
    def __init__(self, _def, _dict=None, **kwargs):
        """
        _def should be an instance of IonObjectDefinition.
        Instead of instantiating these directly, you should go through an IonObjectRegistry.

        TODO: Use metaclasses to cache __dict__ defaults and generate custom types.
        """

        self._def = _def
        if _dict is not None:
            self.__dict__ = _dict
        else:
            # TODO: Probably needs to be a deepcopy
            self.__dict__ = _def.default.copy()
        
        self.__dict__.update(kwargs)

def hashfunc(text):
    return hashlib.sha1(text).hexdigest()

_sha_re = re.compile('[0-9a-f]{40}')
def is_hash(val):
    return len(val) == 40 and _sha_re.match(val) is not None

class IonObjectDefinition(object):
    """ An ION object definition, with a single parent type and a specific version. """

    def __init__(self, _type, hash, default, def_text):
        self.type = _type
        self.hash = hash
        self.default = default
        self.def_text = def_text

class IonObjectType(object):
    """
    An ION object type, with a single name and one or more defined versions.
    Versions are ordered by registration time, so the last version added is considered the latest.
    """

    def __init__(self, name='<default>'):
        self.name = name
        # Map the definition version hash to the actual definition
        self.versions = OrderedDict()

        # Cache pointer to the latest version definition
        self.latest_def = None

    def register_def_raw(self, default, def_text):
        """ The definition should be in something like YAML canonical form, see IonObjectRegistry for more. """
        hash = hashfunc(def_text)
        definition = IonObjectDefinition(self, hash, default, def_text)
        self.register_def(hash, definition)
        return definition

    def register_def(self, hash, definition):
        self.versions[hash] = definition
        self.latest_def = definition


class IonObjectRegistry(object):
    """
    A simple key-value store that stores by name and by definition hash for versioning.
    Also includes optional persistence to a document database.

    TODO: Implement persistence once the document DB type is chosen.
    """

    do_validate = True

    def __init__(self):
        self.def_by_hash = {}
        self.type_by_name = defaultdict(IonObjectType)
        self.instances = WeakSet()
        self.instances_by_name = WeakValueDictionary()

    def get_def(self, _def):
        """
        _def can be an instance of IonObjectDefinition, an instance of IonObjectType
        (to use the latest version of that type), a definition name (to use the latest version of that type),
        or a hash to lookup a specific definition.
        """
        if not isinstance(_def, IonObjectDefinition):
            if isinstance(_def, IonObjectType):
                _type = _def
                _def = _type.latest_def
            if is_hash(_def):
                hash = _def
                if not hash in self.def_by_hash:
                    raise IonObjectError('ION object hash "%s" not in registry' % (hash))
                _def = self.def_by_hash[hash]
            elif isinstance(_def, str):     # Don't support unicode strings
                name = _def
                if not name in self.type_by_name:
                    raise IonObjectError('ION object type "%s" not in registry' % (name))
                _type = self.type_by_name[name]
                _def = _type.latest_def
            else:
                raise IonObjectError("Invalid ION object definition")
        return _def

    def new(self, _def, _dict=None, **kwargs):
        """ See get_def() for definition lookup options. """

        _def = self.get_def(_def)
        obj = IonObject(_def, _dict, **kwargs)
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

