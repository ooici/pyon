#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

import collections
import datetime
import string
import time
import simplejson
import base64
import uuid
import os

class DotNotationGetItem(object):
    """ Drive the behavior for DotList and DotDict lookups by dot notation, JSON-style. """

    def _convert(self, val):
        """ Convert the type if necessary and return if a conversion happened. """
        if isinstance(val, dict) and not isinstance(val, DotDict):
            return DotDict(val), True
        elif isinstance(val, list) and not isinstance(val, DotList):
            return DotList(val), True

        return val, False

    def __getitem__(self, key):
        val = super(DotNotationGetItem, self).__getitem__(key)
        val, converted = self._convert(val)
        if converted: self[key] = val

        return val

    def __contains__(self, item):
        return hasattr(self, item)

class DotList(DotNotationGetItem, list):
    """ Partner class for DotDict; see that for docs. Both are needed to fully support JSON/YAML blocks. """

    #def DotListIterator(list.)

    def __iter__(self):
        """ Monkey-patch the "next" iterator method to return modified versions. This will be slow. """
        #it = super(DotList, self).__iter__()
        #it_next = getattr(it, 'next')
        #setattr(it, 'next', lambda: it_next(it))
        #return it
        for val in super(DotList, self).__iter__():
            val, converted = self._convert(val)
            yield val

class DotDict(DotNotationGetItem, dict):
    """
    Subclass of dict that will recursively look up attributes with dot notation.
    This is primarily for working with JSON-style data in a cleaner way like javascript.
    Note that this will instantiate a number of child DotDicts when you first access attributes;
    do not use in performance-critical parts of your code.
    """

    def __dir__(self):
        return self.__dict__.keys() + self.keys()

    def __getattr__(self, key):
        """ Make attempts to lookup by nonexistent attributes also attempt key lookups. """
        if self.has_key(key):
            return self[key]
        import sys
        import dis
        frame = sys._getframe(1)
        if '\x00%c' % dis.opmap['STORE_ATTR'] in frame.f_code.co_code:
            self[key] = DotDict()
            return self[key]

        raise AttributeError(key)

    def __setattr__(self,key,value):
        if key in dir(dict):
            raise AttributeError('%s conflicts with builtin.' % key)
        if isinstance(value, dict):
            self[key] = DotDict(value)
        else:
            self[key] = value


    def copy(self):
        return DotDict(dict.copy(self))

    def get_safe(self, qual_key, default=None):
        """
        @brief Returns value of qualified key, such as "system.name" or None if not exists.
                If default is given, returns the default. No exception thrown.
        """
        value = get_safe(self, qual_key)
        if value is None:
            value = default
        return value

    @classmethod
    def fromkeys(cls, seq, value=None):
        return DotDict(dict.fromkeys(seq, value))

class DictModifier(DotDict):
    """
    Subclass of DotDict that allows the sparse overriding of dict values.
    """
    def __init__(self, base, data=None):
        # base should be a dict or DotDict, raise TypeError exception if not
        if isinstance(data, dict):
            data = DotDict(data)
        elif not isinstance(base, DotDict):
            raise TypeError("Base must be of type DotDict")
        dict.__setattr__(self,'base',base)

        if data is not None:
            self.update(data)

    def __getattr__(self, key):
        try:
            return DotDict.__getattr__(self, key)
        except AttributeError, ae:
            # Delegate to base
            return getattr(self.base, key)

    def __getitem__(self, key):
        try:
            return DotDict.__getitem__(self, key)
        except KeyError, ke:
            # Delegate to base
            return getattr(self.base, key)

    def __str__(self):
        merged = self.base.copy()
        merged.update(self)
        return str(merged)

    def __repr__(self):
        return self.__str__()


class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, current_dict, past_dict):
        self.current_dict, self.past_dict = current_dict, past_dict
        self.set_current, self.set_past = set(current_dict.keys()), set(past_dict.keys())
        self.intersect = self.set_current.intersection(self.set_past)
    def added(self):
        return self.set_current - self.intersect
    def removed(self):
        return self.set_past - self.intersect
    def changed(self):
        return set(o for o in self.intersect if self.past_dict[o] != self.current_dict[o])
    def unchanged(self):
        return set(o for o in self.intersect if self.past_dict[o] == self.current_dict[o])


# dict_merge from: http://appdelegateinc.com/blog/2011/01/12/merge-deeply-nested-dicts-in-python/

def quacks_like_dict(object):
    """Check if object is dict-like"""
    return isinstance(object, collections.Mapping)

def dict_merge(base, upd, inplace=False):
    """Merge two deep dicts non-destructively.
    Uses a stack to avoid maximum recursion depth exceptions.
    @param base the dict to merge into
    @param upd the content to merge
    @param inplace change base if True
    @retval the merged dict (base of inplace else a merged copy)
    """
    assert quacks_like_dict(base), quacks_like_dict(upd)
    dst = base if inplace else base.copy()

    stack = [(dst, upd)]
    while stack:
        current_dst, current_src = stack.pop()
        for key in current_src:
            if key not in current_dst:
                current_dst[key] = current_src[key]
            else:
                if quacks_like_dict(current_src[key]) and quacks_like_dict(current_dst[key]) :
                    stack.append((current_dst[key], current_src[key]))
                else:
                    current_dst[key] = current_src[key]
    return dst

def get_safe(dict_instance, keypath, default=None):
    """
    Returns a value with in a nested dict structure from a dot separated
    path expression such as "system.server.host" or a list of key entries
    @retval Value if found or None
    """
    try:
        obj = dict_instance
        keylist = keypath if type(keypath) is list else keypath.split('.')
        for key in keylist:
            obj = obj[key]
        return obj
    except Exception, ex:
        return default

def named_any(name):
    """
    Retrieve a Python object by its fully qualified name from the global Python
    module namespace.  The first part of the name, that describes a module,
    will be discovered and imported.  Each subsequent part of the name is
    treated as the name of an attribute of the object specified by all of the
    name which came before it.
    @param name: The name of the object to return.
    @return: the Python object identified by 'name'.
    """
    assert name, 'Empty module name'
    names = name.split('.')

    topLevelPackage = None
    moduleNames = names[:]
    while not topLevelPackage:
        if moduleNames:
            trialname = '.'.join(moduleNames)
            try:
                topLevelPackage = __import__(trialname)
            except Exception, ex:
                moduleNames.pop()
        else:
            if len(names) == 1:
                raise Exception("No module named %r" % (name,))
            else:
                raise Exception('%r does not name an object' % (name,))

    obj = topLevelPackage
    for n in names[1:]:
        obj = getattr(obj, n)

    return obj

def for_name(modpath, classname):
    '''
    Returns a class of "classname" from module "modname".
    '''
    module = __import__(modpath, fromlist=[classname])
    classobj = getattr(module, classname)
    return classobj()

def current_time_millis():
    return int(time.time() * 1000)

def get_ion_ts():
    """
    Returns standard ION representation of a global timestamp.
    It is defined as a str representing an integer number, the millis in UNIX epoch
    """
    return str(current_time_millis())

def get_datetime(ts, local_time=True):
    """
    Returns a datatime instance in either local time or GMT time based on the given ION
    timestamp
    @param ts  ION timestamp (str with millis in epoch)
    @param local_time  if True, returns local time (default), otherwise GMT
    @retval  datetime instance
    """
    tsf = float(ts) / 1000
    timev = time.localtime(tsf) if local_time else time.gmtime(tsf)
    dt = datetime.datetime.fromtimestamp(time.mktime(timev))
    return dt

def get_datetime_str(ts, show_millis=False, local_time=True):
    """
    Returns a string with date and time representation from an ION timestamp
    @param ts  ION timestamp (str with millis in epoch)
    @param show_millis  If True, appends the milli seconds
    @param local_time  if True, returns local time (default), otherwise GMT
    @retval  str with ION standard date and time representation
    """
    dt = get_datetime(ts, local_time)
    dts = str(dt)
    if show_millis:
        dts += "." + ts[-3:]
    return dts

def parse_ion_ts(ts):
    return float(ts) / 1000.0

if __name__ == '__main__':
    dd = DotDict({'a':{'b':{'c':1, 'd':2}}})
    print dd.a.b.c, dd.a.b.d
    print dd.a.b
    #print dd.foo

    print dict.fromkeys(('a','b','c'), 'foo')
    print DotDict.fromkeys(('a','b','c'), 'foo').a

    dl = DotList([1, {'a':{'b':{'c':1, 'd':2}}}])
    print dl[1].a.b.c

def itersubclasses(cls, _seen=None):
    """
    itersubclasses(cls)
    http://code.activestate.com/recipes/576949-find-all-subclasses-of-a-given-class/

    Generator over all subclasses of a given class, in depth first order.
    """

    if not isinstance(cls, type):
        raise TypeError('itersubclasses must be called with '
                        'new-style classes, not %.100r' % cls)
    if _seen is None: _seen = set()
    try:
        subs = cls.__subclasses__()
    except TypeError: # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, _seen):
                yield sub

def getleafsubclasses(cls):
    """
    Returns all subclasses that have no further subclasses, for the given class
    """
    scls = itersubclasses(cls)
    return [s for s in scls if not s.__subclasses__()]

# _abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
BASIC_VALID = "_%s%s" % (string.ascii_letters, string.digits)
# -_.()abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789
NORMAL_VALID = "-_.() %s%s" % (string.ascii_letters, string.digits)

def create_valid_identifier(name, valid_chars=BASIC_VALID, dot_sub=None, ws_sub=None):
    if dot_sub:
        name = name.replace('.', dot_sub)
    if ws_sub:
        name = name.replace(' ', ws_sub)
    return ''.join(c for c in name if c in valid_chars)

def create_basic_identifier(name):
    return create_valid_identifier(name, dot_sub='_', ws_sub='_')

def is_basic_identifier(name):
    return name == create_basic_identifier(name)

def is_valid_identifier(name, valid_chars=BASIC_VALID, dot_sub=None, ws_sub=None):
    return name == create_valid_identifier(name, valid_chars=valid_chars, dot_sub=dot_sub, ws_sub=ws_sub)

#Used by json encoder
def ion_object_encoder(obj):
    return obj.__dict__

def make_json(data):
    result = simplejson.dumps(data, default=ion_object_encoder, indent=2)
    return result


#Global utility functions for generating unique names and UUIDs
# get a UUID - URL safe, Base64
def get_a_Uuid():
    r_uuid = base64.urlsafe_b64encode(uuid.uuid4().bytes)
    return r_uuid.replace('=', '')

# generate a unique identifier based on a UUID and optional information
def create_unique_identifier(prefix=''):
    return prefix + '_' + get_a_Uuid()

def get_default_sysname():
    return 'ion_%s' % os.uname()[1].replace('.', '_')

def get_default_container_id():
    return string.replace('%s_%d' % (os.uname()[1], os.getpid()), ".", "_")
