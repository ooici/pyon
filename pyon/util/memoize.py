#!/usr/bin/env
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@file  pyon/util/memoize.py
@date Thu Aug  2 10:21:37 EDT 2012
@description Decorator for memoizing a function

Original concept taken from: http://code.activestate.com/recipes/498245-lru-and-lfu-cache-decorators/
Resources:
http://en.wikipedia.org/wiki/Memoize
http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used
http://citeseer.ist.psu.edu/viewdoc/summary?doi=10.1.1.13.5210
'''

import collections
import functools
from itertools import ifilterfalse
from heapq import nsmallest
from operator import itemgetter
from collections import deque
from putil.hash import hash_any

from heapq import heapify, heappush, heappop, heapreplace


class Counter(dict):
    'Mapping where default values are zero'
    def __missing__(self, key):
        return 0

def memoize_lru(maxsize=100, use_hash_any=False):
    '''Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    '''
    def decorating_function(user_function):
        cache = collections.OrderedDict()    # order: least recent to most recent

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            key = args
            if kwds:
                key += tuple(sorted(kwds.items()))

            if use_hash_any:
                key = hash_any(key)
            try:
                result = cache.pop(key)
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                wrapper.misses += 1
                if len(cache) >= maxsize:
                    cache.popitem(0)    # purge least recently used cache entry
            cache[key] = result         # record recent use of this key
            return result
        wrapper.hits = wrapper.misses = 0
        return wrapper
    return decorating_function



def memoize_lfu(maxsize=100, use_hash_any=False):
    '''Least-frequenty-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Least_Frequently_Used

    '''
    def decorating_function(user_function):
        cache = {}                      # mapping of args to results
        use_count = Counter()           # times each key has been accessed
        kwarg_mark = object()             # separate positional and keyword args

        @functools.wraps(user_function)
        def wrapper(*args, **kwargs):
            key = args
            if kwargs:
                key += (kwarg_mark,) + tuple(sorted(kwargs.items()))

            if use_hash_any:
                key = hash_any(key)
            # get cache entry or compute if not found
            try:
                result = cache[key]
                use_count[key] += 1
                wrapper.hits += 1
            except KeyError:
                # need to add something to the cache, make room if necessary
                if len(cache) == maxsize:
                    for k, _ in nsmallest(maxsize // 10 or 1,
                                            use_count.iteritems(),
                                            key=itemgetter(1)):
                        del cache[k], use_count[k]
                cache[key] = user_function(*args, **kwargs)
                result = cache[key]
                use_count[key] += 1
                wrapper.misses += 1
            return result

        def clear():
            cache.clear()
            use_count.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        wrapper.cache = cache
        return wrapper
    return decorating_function




if __name__ == '__main__':
    @memoize_lru(maxsize=20)
    def f(x, y):
        return 3*x+y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f(choice(domain), choice(domain))

    print(f.hits, f.misses)

    @memoize_lfu(maxsize=20)
    def f(x, y):
        return 3*x+y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f(choice(domain), choice(domain))

    print(f.hits, f.misses)

