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

class Counter(dict):
    'Mapping where default values are zero'
    def __missing__(self, key):
        return 0

def lru_cache(maxsize=100):
    '''Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    '''
    maxqueue = maxsize * 10
    def decorating_function(user_function,
            len=len, iter=iter, tuple=tuple, sorted=sorted, KeyError=KeyError):
        cache = {}                  # mapping of args to results
        queue = collections.deque() # order that keys have been used
        refcount = Counter()        # times each key is in the queue
        sentinel = object()         # marker for looping around the queue
        kwd_mark = object()         # separate positional and keyword args

        # lookup optimizations (ugly but fast)
        queue_append, queue_popleft = queue.append, queue.popleft
        queue_appendleft, queue_pop = queue.appendleft, queue.pop

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            # cache key records both positional and keyword args
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))

            # record recent use of this key
            queue_append(key)
            refcount[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                cache[key] = result
                wrapper.misses += 1

                # purge least recently used cache entry
                if len(cache) > maxsize:
                    key = queue_popleft()
                    refcount[key] -= 1
                    while refcount[key]:
                        key = queue_popleft()
                        refcount[key] -= 1
                    del cache[key], refcount[key]

            # periodically compact the queue by eliminating duplicate keys
            # while preserving order of most recent access
            if len(queue) > maxqueue:
                refcount.clear()
                queue_appendleft(sentinel)
                for key in ifilterfalse(refcount.__contains__,
                                        iter(queue_pop, sentinel)):
                    queue_appendleft(key)
                    refcount[key] = 1


            return result

        def clear():
            cache.clear()
            queue.clear()
            refcount.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper
    return decorating_function


def lfu_cache(maxsize=100):
    '''Least-frequenty-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Least_Frequently_Used

    '''
    def decorating_function(user_function):
        cache = {}                      # mapping of args to results
        use_count = Counter()           # times each key has been accessed
        kwd_mark = object()             # separate positional and keyword args

        @functools.wraps(user_function)
        def wrapper(*args, **kwds):
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))
            use_count[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
                wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                cache[key] = result
                wrapper.misses += 1

                # purge least frequently used cache entry
                if len(cache) > maxsize:
                    for key, _ in nsmallest(maxsize // 10,
                                            use_count.iteritems(),
                                            key=itemgetter(1)):
                        del cache[key], use_count[key]

            return result

        def clear():
            cache.clear()
            use_count.clear()
            wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        return wrapper
    return decorating_function


'''
Memoize
In computing, memoization is an optimization technique used primarily to speed up computer programs by having function calls avoid repeating the calculation of results for previously processed inputs. 

This is a decorator used on a function whose arguments can be hashed. Ideal for transforms which need to access CouchDB or any data which does not lie in memory.


Example:
    @memoize(maxsize=100)
    def fetch_resource(self,resource_id):
        return self.repository.read(resource_id)

The above will cache the key, resource_id, and if a subsequent call is made to this method and the key is cached, then the value is immediately returned instead of reaching out into the repository for the data.

Internal measurements are maintained (for now) which will allow us to improve performance if need be but this is good enough for most uses.
'''
def memoize(maxsize=20):
    def decorating_function(f):
        cache   = {}
        heap    = deque()
        
        def wrapper(*args):
            key = repr(args)
            if key in heap:
                heap.remove(key)
                heap.appendleft(key)
                wrapper.hits += 1
                return cache[key]
            if wrapper.size >= maxsize:
                dkey = heap.pop()
                del cache[dkey]
            else:
                wrapper.size += 1
            heap.appendleft(key)
            cache[key] = f(*args)
            wrapper.misses += 1
            return cache[key]
        def clear():
            for i in heap:
                print i
            cache.clear()
            heap.clear()
            wrapper.size = 0
            wrapper.hits = wrapper.misses = 0
        wrapper.clear = clear
        wrapper.hits = wrapper.misses = 0
        wrapper.size = 0
        return wrapper
    return decorating_function




if __name__ == '__main__':
    @lru_cache(maxsize=20)
    def f(x, y):
        return 3*x+y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f(choice(domain), choice(domain))

    print(f.hits, f.misses)

    @lfu_cache(maxsize=20)
    def f(x, y):
        return 3*x+y

    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f(choice(domain), choice(domain))

    print(f.hits, f.misses)

    @better_memoize(maxsize=20)
    def f(x, y):
        return 3*x+y
    domain = range(5)
    from random import choice
    for i in range(1000):
        r = f(choice(domain), choice(domain))

    print(f.hits, f.misses)

