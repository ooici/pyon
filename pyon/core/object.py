#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

import copy
import re
import os
import fnmatch
import hashlib
from collections import OrderedDict, defaultdict, Mapping, Iterable
from weakref import WeakSet, WeakValueDictionary

import yaml

from pyon.core.path import list_files_recursive
from pyon.util.log import log
#from pyon.util import yaml_ordered_dict

class IonObjectError(Exception):
    pass

class IonYamlLoader(yaml.Loader):
    """ For ION-specific overrides of YAML loading behavior. """
    pass

class IonYamlDumper(yaml.Dumper):
    """ For ION-specific overrides of YAML dumping behavior. """
    pass

def service_name_from_file_name(file_name):
    file_name = os.path.basename(file_name).split('.', 1)[0]
    return file_name.title().replace('_', '').replace('-', '')

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
            cls_dict.update(copy.deepcopy(_def.schema))
            #cls_dict['__slots__'] = cls_dict.keys() + ['__weakref__']

            cls_type = IonObjectMetaType.__new__(IonObjectMetaType, cls_name, (cls,), cls_dict)
            IonObjectMetaType._type_cache[_def] = cls_type

        # Auto-copy the schema so we can use __dict__ authoritatively and simplify the code
        __dict__ = copy.deepcopy(dict(_def.schema))
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
        # TODO: Add a yaml representer for IonObjects to match their tag constructors

        _dict = self.__dict__
        #return '%s(%r)' % (self.__class__, _dict)
        # If the yaml is too slow revert to the line above
        name = '%s <%s>' % (self.__class__.__name__, id(self))
        return yaml.dump({name: _dict}, default_flow_style=False, Dumper=IonYamlDumper)

    def _validate(self):
        """
        Compare fields to the schema and raise AttributeError if mismatched.
        Named _validate instead of validate because the data may have a field named "validate".
        """
        id_and_rev_set = set(['_id','_rev'])
        fields, schema = self.__dict__, self._def.schema
        extra_fields = fields.viewkeys() - schema.viewkeys() - id_and_rev_set
        if len(extra_fields) > 0:
            raise AttributeError('Fields found that are not in the schema: %r' % (list(extra_fields)))
        for key in fields.iterkeys():
            if key in id_and_rev_set:
                continue
            field_val, schema_val = fields[key], schema[key]
            if type(field_val) is not type(schema_val):

                # if the schema doesn't define a type, we can't very well validate it
                if type(schema_val) == type(None):
                    continue

                # Special handle numeric types.  Allow int to be
                # passed for long and float.  Auto convert to the
                # right type.
                if isinstance(field_val, int):
                    if isinstance(schema_val, float):
                        fields[key] = float(fields[key])
                        continue
                    elif isinstance(schema_val,long):
                        fields[key] = long(fields[key])
                        continue

                # argh, annoying work around for OrderedDict vs dict issue
                if type(field_val) == dict and type(schema_val) == OrderedDict:
                     fields[key] = OrderedDict(field_val)
                     continue

                # optional fields ok?
                if field_val is None:
                    continue

                # IonObjects are ok for dict fields too!
                if isinstance(field_val, IonObjectBase) and type(schema_val) == OrderedDict:
                    continue

                # TODO work around for msgpack issue
                if type(fields[key]) == tuple and type(schema[key]) == list:
                    continue

                raise AttributeError('Invalid type "%s" for field "%s", should be "%s"' %
                                     (type(fields[key]), key, type(schema[key])))
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

    def __contains__(self, item):
        return hasattr(self, item)

class IonEnumObject(object):
    def __init__(self, enum, default_key=None):
        self.enum = enum
        self.default_key = default_key
        self.value = self.enum.get(default_key) if default_key else None

    def __str__(self):
        return str(self.value)

def hashfunc(text):
    return hashlib.sha1(text).hexdigest()

_sha_re = re.compile('[0-9a-f]{40}')
def is_hash(val):
    return len(val) == 40 and _sha_re.match(val) is not None

class IonObjectDefinition(object):
    """ An ION object definition, with a single parent type and a specific version. """

    __slots__ = ('type', 'hash', 'schema', 'def_text')

    def __init__(self, _type, hash, schema, def_text):
        self.type = _type
        self.hash = hash
        self.schema = schema
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

    def register_def_raw(self, schema, def_text):
        """ The definition should be in something like YAML canonical form, see IonObjectRegistry for more. """
        hash = hashfunc(def_text)
        definition = IonObjectDefinition(self, hash, schema, def_text)
        self.register_def(hash, definition)
        return definition

    def register_def(self, hash, definition):
        self.versions[hash] = definition
        self.latest_def = definition


class IonObjectRegistry(object):
    """
    A simple key-value store that stores by name and by definition hash for versioning.
    Also includes optional persistence to a document database.
    """

    do_validate = True

    # Maps object name and extends
    extends_objects = dict()
    extended_objects = defaultdict(set)
    allextends = defaultdict(set)

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

    def register_def(self, name, schema, def_text=None):
        """
        Register a type in the registry. It will index by both name and version,
        where version is the SHA1 hash of the definition. The definition should
        typically be in YAML canonical form (for consistent hashing).
        """

        log.debug('Registering object definition: %s', name)
        if def_text is None:
            # TODO: Hook into pyyaml's event emitting stuff to try to get the canonical form without re-dumping
            def_text = yaml.dump(schema, canonical=True, allow_unicode=True, Dumper=IonYamlDumper)

        _type = self.type_by_name[name]
        _type.name = name
        _def = _type.register_def_raw(schema, def_text)
        self.def_by_hash[_def.hash] = _def

        # Support for composite objects in definitions via YAML tags
        tag = u'!%s' % (name)
        def constructor(loader, node):
            if isinstance(node, yaml.MappingNode):
                value = loader.construct_mapping(node)
            else:
                value = {}
            return self.new(_def, value)
        log.debug('Added YAML constructor for tag: %s' % tag)
        yaml.add_constructor(tag, constructor, Loader=IonYamlLoader)

        # Support for extended objects in definitions via YAML tags
        xtag = u'!Extends_%s' % (name)
        def extends_constructor(loader, node):
            if isinstance(node, yaml.MappingNode):
                value = loader.construct_mapping(node)
            else:
                value = {}
            value.update(_def.schema)
            return value
        yaml.add_constructor(xtag, extends_constructor, Loader=IonYamlLoader)

        return _def

    def register_yaml(self, yaml_text):
        """ Parse the contents of a YAML file that contains one or more object definitions. """

        # Add support for enum types in definitions via YAML tags
        enum_tag = u'!enum'
        def enum_constructor(loader, node):
            if isinstance(node, yaml.MappingNode):
                value = loader.construct_mapping(node)
            else:
                value = {}
            enum_val = IonEnumObject(value, value.get("_default", None))
            return enum_val
        yaml.add_constructor(enum_tag, enum_constructor, Loader=IonYamlLoader)

        defs = yaml.load_all(yaml_text, Loader=IonYamlLoader)
        obj_defs = []
        for def_set in defs:
            for name,_def in def_set.iteritems():
                reg_def = self.register_def(name, _def)
                obj_defs.append(reg_def)

        return obj_defs

    def _register_extends(self, name, extends):
        self.extends_objects[name] = extends
        self.extended_objects[extends].add(name)

    def _compute_allextends(self):
        for name,base in self.extends_objects.iteritems():
            while base:
                # Now go up the inheritance tree
                self.allextends[base].add(name)
                base = self.extends_objects.get(base, None)

    def register_obj_dir(self, yaml_dir, do_first=[], exclude_dirs=[]):
        """
        Recursively find all *.yml files under yaml_dir, concatenate into a big blob, and merge the yaml
        contents into the registry. Files in do_first will be prepended to the blob if found.
        """

        yaml_files = list_files_recursive(yaml_dir, '*.yml', do_first, exclude_dirs)

        yaml_text = '\n\n'.join((file.read() for file in (open(path, 'r') for path in yaml_files if os.path.exists(path))))

        # Extract resource types (everything that extends from Resource)
        # TODO: What if a resource extends from another resource?
        import re
        res = re.findall(r'(\w+?):\s+!Extends_(\w*)\s', yaml_text)
        # Returns a list of matches or tuples of matches
        [self._register_extends(name, extends) for (name, extends) in res]
        self._compute_allextends()
        
        obj_defs = self.register_yaml(yaml_text)
        self.source_files += yaml_files
        return obj_defs

class IonServiceMethod(object):
    """ Reference the object definitions for a service method. """

    def __init__(self, def_in, def_out, op_name=None):
        self.def_in = def_in
        self.def_out = def_out
        self.op_name = op_name

    def __str__(self):
        str = "op:%s\nin:%s\nout:%s" % (self.op_name, self.def_in, self.def_out)
        return str

class IonServiceDefinition(object):
    """ Provides a walkable structure for ION service metadata and object definitions. """

    def __init__(self, name, dependencies=[], version=''):
        self.name = name
        self.dependencies = list(dependencies)
        self.version = version
        self.methods = []

class IonServiceRegistry(IonObjectRegistry):
    """
    Adds a layer of service-specific syntax to the object definitions.
    """

    def __init__(self):
        super(IonServiceRegistry, self).__init__()
        self.services = set()
        self.services_by_name = {}

    def _reg_method_part(self, svc_name, op_name, op_def, direction, required=False):
        if not direction in op_def:
            if required:
                raise IonObjectError('Method definition missing "%s" block in service "%s".' % (direction, svc_name))
            else:
                return

        def_name = '%s_%s_%s' % (svc_name, op_name, direction)   # Prefix the service name
        reg_def = self.register_def(def_name, op_def[direction])
        return reg_def

    def register_svc_dir(self, yaml_dir, do_first=[], exclude_dirs=[]):
        yaml_files = list_files_recursive(yaml_dir, '*.yml', do_first, exclude_dirs)
        obj_defs = []
        for yaml_file in yaml_files:
            svc_name = service_name_from_file_name(yaml_file)
            yaml_text = open(yaml_file, 'r').read()

            defs = yaml.load_all(yaml_text, Loader=IonYamlLoader)
            for def_set in defs:
                # Register all supporting objects first
                for obj_name,obj_def in def_set.get('obj', {}).iteritems():
                    if not obj_def: continue

                    #obj_name = '%s_%s' % (svc_name, obj_name)   # Prefix the service name
                    reg_def = self.register_def(obj_name, obj_def)
                    obj_defs.append(reg_def)

                # Register the service and its ops in/out objects
                if 'name' in def_set:
                    name, deps, version = def_set['name'], def_set.get('dependencies', []), def_set.get('version', '')
                    if deps is None:
                        deps = []
                    svc_def = IonServiceDefinition(name, deps, version)
                    log.debug('Registering service "%s"' % (name))

                    # It seems that despite the get with default arg, there still can be None resulting (YAML?)
                    meth_list = def_set.get('methods', {}) or {}
                    for op_name,op_def in meth_list.iteritems():
                        if not op_def: continue
                        def_in, def_out = (self._reg_method_part(svc_name, op_name, op_def, d) for d in ('in', 'out'))
                        [obj_defs.append(reg_def) for reg_def in (def_in, def_out)]
                        method = IonServiceMethod(def_in, def_out, op_name)
                        svc_def.methods.append(method)

                    self.services.add(svc_def)
                    self.services_by_name[svc_def.name] = svc_def

        return obj_defs


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
    if hasattr(newo, '__iter__'):
        if isinstance(newo, dict):
            return dict(((k, walk(v, cb)) for k,v in newo.iteritems()))
        else:
            return [walk(x, cb) for x in newo]
    elif isinstance(newo, IonObjectBase):
        # IOs are not iterable and are a huge pain to make them look iterable, special casing is fine then
        # @TODO consolidate with _validate method in IonObjectBase
        fields, set_fields = newo.__dict__, set(newo._def.schema)
        set_fields.intersection_update(fields)

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
            res = obj.__dict__
            res["type_"] = obj._def.type.name
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
        if isinstance(obj, dict) and "type_" in obj:
            objc    = obj.copy()
            type    = objc.pop('type_')
            ionObj  = self._obj_registry.new(type.encode('ascii'), objc)
            return ionObj
        return obj


