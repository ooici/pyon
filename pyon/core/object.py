#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import copy
import re
import os
import fnmatch
import hashlib
from collections import OrderedDict, defaultdict, Mapping, Iterable
from weakref import WeakSet, WeakValueDictionary

import yaml

from pyon.util.log import log

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

    def register_def(self, name, schema, def_text=None):
        """
        Register a type in the registry. It will index by both name and version,
        where version is the SHA1 hash of the definition. The definition should
        typically be in YAML canonical form (for consistent hashing).
        """

        log.debug('Registering object definition')
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

        return _def

    def register_yaml(self, yaml_text):
        """ Parse the contents of a YAML file that contains one or more object definitions. """

        defs = yaml.load_all(yaml_text, Loader=IonYamlLoader)
        obj_defs = []
        for def_set in defs:
            for name,_def in def_set.iteritems():
                reg_def = self.register_def(name, _def)
                obj_defs.append(reg_def)

        return obj_defs

    def _list_files_recursive(self, file_dir, pattern, do_first=[], exclude_dirs=[]):
        """
        Recursively find all files matching pattern under file_dir and return a list.
        """

        all_files = [os.path.join(file_dir, file) for file in do_first]
        skip_me = set(all_files)
        exclude_dirs = set([os.path.join(file_dir, path) for path in exclude_dirs])

        for root, dirs, files in os.walk(file_dir):
            if root in exclude_dirs: continue
            log.debug('Registering yaml files in dir: %s', root)
            for file in fnmatch.filter(files, pattern):
                path = os.path.join(root, file)
                if not path in skip_me:
                    all_files.append(path)

        return all_files

    def register_obj_dir(self, yaml_dir, do_first=[], exclude_dirs=[]):
        """
        Recursively find all *.yml files under yaml_dir, concatenate into a big blob, and merge the yaml
        contents into the registry. Files in do_first will be prepended to the blob if found.
        """

        yaml_files = self._list_files_recursive(yaml_dir, '*.yml', do_first, exclude_dirs)

        yaml_text = '\n\n'.join((file.read() for file in (open(path, 'r') for path in yaml_files)))
        obj_defs = self.register_yaml(yaml_text)
        self.source_files += yaml_files
        return obj_defs

class IonServiceMethod(object):
    """ Reference the object definitions for a service method. """

    def __init__(self, def_in, def_out):
        self.def_in = def_in
        self.def_out = def_out

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
        yaml_files = self._list_files_recursive(yaml_dir, '*.yml', do_first, exclude_dirs)
        for yaml_file in yaml_files:
            svc_name = service_name_from_file_name(yaml_file)
            yaml_text = open(yaml_file, 'r').read()

            defs = yaml.load_all(yaml_text, Loader=IonYamlLoader)
            obj_defs = []
            for def_set in defs:
                # Register all supporting objects first
                for obj_name,obj_def in def_set.get('obj', {}).iteritems():
                    if not obj_def: continue

                    #obj_name = '%s_%s' % (svc_name, obj_name)   # Prefix the service name
                    reg_def = self.register_def(obj_name, obj_def)
                    obj_defs.append(reg_def)

                # Register the service and its ops in/out objects
                if 'name' in def_set:
                    name, deps, version = def_set['name'], def_set.get('dependencies', None), def_set.get('version', '')
                    svc_def = IonServiceDefinition(name, deps, version)
                    log.debug('Registering service "%s"' % (name))

                    for op_name,op_def in def_set.get('methods', {}).iteritems():
                        if not op_def: continue
                        def_in, def_out = (self._reg_method_part(svc_name, op_name, op_def, d) for d in ('in', 'out'))
                        [obj_defs.append(reg_def) for reg_def in (def_in, def_out)]
                        method = IonServiceMethod(def_in, def_out)
                        svc_def.methods.append(method)

                    self.services.add(svc_def)
                    self.services_by_name[svc_def.name] = svc_def

        return obj_defs
    