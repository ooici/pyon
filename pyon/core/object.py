#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import copy
import re
import os
import fnmatch
import hashlib
from collections import OrderedDict, defaultdict
from weakref import WeakSet, WeakValueDictionary

import yaml

from pyon.util.log import log

class IonObjectError(Exception):
    pass

class IonObjectMetaType(type):
    """
    Metaclass that automatically generates subclasses of IonObject with the appropriate defaults for each field.
    """

    _type_cache = {}

    def __call__(cls, _def, _dict=None, *args, **kwargs):
        if _def in IonObjectMetaType._type_cache:
            cls_type = IonObjectMetaType._type_cache[_def]
        else:
            # Check that the object we are wrapping is an IonObjectDefinition
            if not isinstance(_def, IonObjectDefinition):
                raise IonObjectError('IonObject init first argument must be an IonObjectDefinition')

            # Generate a unique class name
            base_name = 'IonObject'
            cls_name = '%s_%s_%s' % (base_name, _def.type.name, _def.hash[:8])
            cls_dict = {'_def': _def}
            cls_dict.update(copy.deepcopy(_def.default))
            #cls_dict['__slots__'] = cls_dict.keys() + ['__weakref__']

            cls_type = IonObjectMetaType.__new__(IonObjectMetaType, cls_name, (cls,), cls_dict)
            IonObjectMetaType._type_cache[_def] = cls_type

        # Auto-copy the defaults so we can use __dict__ authoritatively and simplify the code
        __dict__ = copy.deepcopy(dict(_def.default))
        if _dict is not None:
            __dict__.update(_dict)
            
        # Finally allow the instantiation to occur, but slip in our new class type
        obj = super(IonObjectMetaType, cls_type).__call__(__dict__, *args, **kwargs)
        return obj

class IonObjectBase(object):
    __metaclass__ = IonObjectMetaType
    
    def __init__(self, _dict=None, **kwargs):
        """
        Instead of instantiating these directly, you should go through an IonObjectRegistry.
        If you need to instantiate directly, set _def to an instance of IonObjectDefinition.
        """
        
        if _dict is not None:
            self.__dict__ = _dict       # Don't copy here, assume this came through the metaclass
        self.__dict__.update(kwargs)

    def __str__(self):
        """ This method will probably be too expensive to use frequently due to object allocation and YAML. """
        _dict = self.__dict__
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
                raise AttributeError('Invalid type "%s" for field "%s", should be "%s"' %
                                     (type(fields[key]), key, type(schema[key])))

def hashfunc(text):
    return hashlib.sha1(text).hexdigest()

_sha_re = re.compile('[0-9a-f]{40}')
def is_hash(val):
    return len(val) == 40 and _sha_re.match(val) is not None

class IonObjectDefinition(object):
    """ An ION object definition, with a single parent type and a specific version. """

    __slots__ = ('type', 'hash', 'default', 'def_text')

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

    __slots__ = ('name', 'versions', 'latest_def')

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
        self.source_files = []

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
        log.debug("In IonObjectRegistry.new")
        log.debug("_def: %s" % _def)
        log.debug("_dict: %s" % str(_dict))
        _def = self.get_def(_def)
        obj = IonObjectBase(_def, _dict, **kwargs)
        self.instances.add(obj)
        self.instances_by_name[_def.type.name] = obj
        return obj

    def register_def(self, name, default, def_text):
        """
        Register a type in the registry. It will index by both name and version,
        where version is the SHA1 hash of the definition. The definition should
        typically be in YAML canonical form (for consistent hashing).
        """

        log.debug('Registering object definition "%s"', name)
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

    def register_yaml_dir(self, yaml_dir, do_first=[], exclude_dirs=[]):
        """
        Recursively find all *.yml files under yaml_dir, concatenate into a big blob, and merge the yaml
        contents into the registry. Files in do_first will be prepended to the blob if found.
        """

        yaml_files = [os.path.join(yaml_dir, file) for file in do_first]
        skip_me = set(yaml_files)
        exclude_dirs = set([os.path.join(yaml_dir, path) for path in exclude_dirs])

        for root, dirs, files in os.walk(yaml_dir):
            if root in exclude_dirs: continue
            log.debug('Registering yaml files in dir: %s', root)
            for file in fnmatch.filter(files, '*.yml'):
                path = os.path.join(root, file)
                if not path in skip_me:
                    yaml_files.append(path)

        yaml_text = '\n\n'.join((file.read() for file in (open(path, 'r') for path in yaml_files)))
        self.register_yaml(yaml_text)
        self.source_files += yaml_files

