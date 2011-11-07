#!/usr/bin/env python

from pyon.net.endpoint import RPCClient
#from interface.services.idatastore_service import IDatastoreService
from interface.services.ihello_service import IHelloService
from pyon.net.messaging import make_node
import gevent
import time
import base64
import os
import argparse
import msgpack

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--datasize', type=int, help='Maximum size of data in bytes')
parser.add_argument('-m', '--msgpack', action='store_true', help='Encode data with msgpack')
parser.set_defaults(datasize=1024*1024, parallel=1)
opts = parser.parse_args()


node,iowat=make_node()
#dsclient = RPCClient(node=node, name="datastore", iface=IDatastoreService)
hsclient = RPCClient(node=node, name="hello", iface=IHelloService)

def notif(*args, **kwargs):
    print "GOT A BACKPRESSURE NOTICE", str(args), str(kwargs)

node.client.add_backpressure_callback(notif)
node.client.set_backpressure_multiplier(2)

# make data (bytes)
DATA_SIZE = opts.datasize
# base64 encoding wastes a lot of space, truncate it at the exact data size we requested
data = base64.urlsafe_b64encode(os.urandom(DATA_SIZE))[:DATA_SIZE]
if opts.msgpack:
    data = msgpack.dumps(data)

counter = 0
st = 0

def tick():
    global counter, st
    while True:
        time.sleep(2)
        ct = time.time()
        elapsed_s = ct - st
        sc = sum(counter)

        mps = sc / elapsed_s

        print counter, sc, "requests, per sec:", mps

def work(ds):
    curdata = data[:ds]
    global counter
    global st
    counter = 0
    st = time.time()

    while counter < 1000:
        hsclient.noop(curdata)
        #hsclient.hello(str(counter[wid]))
        counter += 1

    et = time.time()
    return et - st

#_gt = gevent.spawn(tick)

results = {}

for size in [1024, 2048, 4096, 8192, 16384, 32768, 65536, 131072, 262144]:
    _gl = gevent.spawn(work, size)
    try:
        rs = _gl.get(timeout=10)
    except gevent.Timeout:
        print "10s elapsed, cutting it"
        rs = time.time() - st
    results[size] = { "elapsed": rs, "count": counter, "ps":counter/rs }
    print "Size:", size, str(results[size]) 

import pprint
pprint.pprint(results)

