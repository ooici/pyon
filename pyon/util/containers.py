#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import collections

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

    def __getattr__(self, key):
        """ Make attempts to lookup by nonexistent attributes also attempt key lookups. """
        try:
            val = self.__getitem__(key)
        except KeyError:
            raise AttributeError(key)

        return val

    def copy(self):
        return DotDict(dict.copy(self))

    @classmethod
    def fromkeys(cls, seq, value=None):
        return DotDict(dict.fromkeys(seq, value))

class DictModifier(DotDict):
    """
    Subclass of DotDict that allows the sparse overriding of dict values.
    """
    def __init__(self, base, data=None):
        # base should be a DotDict, raise TypeError exception if not
        if not isinstance(base, DotDict):
            raise TypeError("Base must be of type DotDict")
        self.base = base

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

# dict_merge from: http://appdelegateinc.com/blog/2011/01/12/merge-deeply-nested-dicts-in-python/

def quacks_like_dict(object):
    """Check if object is dict-like"""
    return isinstance(object, collections.Mapping)

def dict_merge(a, b):
    """Merge two deep dicts non-destructively

    Uses a stack to avoid maximum recursion depth exceptions

    >>> a = {'a': 1, 'b': {1: 1, 2: 2}, 'd': 6}
    >>> b = {'c': 3, 'b': {2: 7}, 'd': {'z': [1, 2, 3]}}
    >>> c = merge(a, b)
    >>> from pprint import pprint; pprint(c)
    {'a': 1, 'b': {1: 1, 2: 7}, 'c': 3, 'd': {'z': [1, 2, 3]}}
    """
    assert quacks_like_dict(a), quacks_like_dict(b)
    dst = a.copy()

    stack = [(dst, b)]
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


if __name__ == '__main__':
    dd = DotDict({'a':{'b':{'c':1, 'd':2}}})
    print dd.a.b.c, dd.a.b.d
    print dd.a.b
    #print dd.foo

    print dict.fromkeys(('a','b','c'), 'foo')
    print DotDict.fromkeys(('a','b','c'), 'foo').a

    dl = DotList([1, {'a':{'b':{'c':1, 'd':2}}}])
    print dl[1].a.b.c
    