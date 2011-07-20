#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from gevent import monkey; monkey.patch_all()
import gevent
import string
import time
import threading
from itertools import permutations

from HTTP4Store import HTTP4Store

from ion.util.async import *

class Concurrent4Store(HTTP4Store, threading.local):
    pass

def chunks(l, n):
    return [l[i:i+n] for i in range(0, len(l), n)]

store = Concurrent4Store('http://localhost:8000')
status = store.status()
print status

uri = 'http://ooici.net/graph1/'
graph = '''
<adam> <likes> <chocolate> .
<adam> <hates> <vinegar> .
<hannah> <likes> <disney> .
<hannah> <hates> <roaches> .
'''
store.add_graph(uri, graph, content_type='turtle')

# 15600 unique "words"
words = [''.join(letters) for letters in permutations(string.ascii_uppercase, 3)]
triples = ['<%s> <%s> <%s> .' % (words[i], 'connects', words[i - 1])
           for i in xrange(len(words))]
triple_count = len(triples)
graph = '\n'.join(triples)

def send_batch():
    # First just send the full graph
    time_start = time.time()
    store.append_graph(uri, graph, content_type='turtle')
    time_diff = time.time() - time_start
    print 'Took %.2f seconds to batch import %d triples' % (time_diff, len(triples))

def send_concurrent():
    # Now send each triple individually, in batches of 10 requests at a time
    time_start = time.time()
    concurrency = 10
    for i in xrange(0, triple_count, concurrency):
        some_triples = triples[i:i + concurrency]
        wait([spawn(store.append_graph, uri, triple) for triple in some_triples])

    time_diff = time.time() - time_start
    print 'Took %.2f seconds to concurrent import %d triples' % (time_diff, len(triples))

def send_concurrent_reuse():
    # Send each triple individually, but reuse HTTP connections
    @spawnf
    def append_all(triples):
        for triple in triples:
            store.append_graph(uri, triple)
    
    time_start = time.time()
    concurrency = 10
    wait([append_all(some_triples) for some_triples in chunks(triples, triple_count/concurrency)])
    time_diff = time.time() - time_start
    print 'Took %.2f seconds to concurrent import %d triples, reusing connections' % (time_diff, len(triples))

#import cProfile, pstats
#filename = 'fourstore.pstats'
#cProfile.run('send_concurrent_reuse()', filename)
#pstats.Stats(filename).sort_stats('time').print_stats(60)

send_concurrent_reuse()

#print store.sparql('SELECT * WHERE { ?s ?p ?o } LIMIT 10')

