#!/usr/bin/env python

from pyon.net.endpoint import RPCClient
#from interface.services.idatastore_service import IDatastoreService
from interface.services.examples.hello.ihello_service import HelloServiceClient, IHelloService
from pyon.net.messaging import make_node
import gevent
import time
import base64
import os
import argparse
import msgpack
from pyon.core import bootstrap

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--datasize', type=int, help='Size of data in bytes')
parser.add_argument('-p', '--parallel', type=int, help='Number of parallel requests to run')
parser.add_argument('-m', '--msgpack', action='store_true', help='Encode data with msgpack')
parser.add_argument('-s', '--sysname', action='store', help='ION System Name')
parser.set_defaults(datasize=1024, parallel=1, sysname='tt')
opts = parser.parse_args()

bootstrap.sys_name = opts.sysname
bootstrap.bootstrap_pyon()

node,iowat=make_node()
#dsclient = RPCClient(node=node, name="datastore", iface=IDatastoreService)
hsclient = HelloServiceClient(node=node)#RPCClient(node=node, name="hello", iface=IHelloService)

# make data (bytes)
DATA_SIZE = opts.datasize
# base64 encoding wastes a lot of space, truncate it at the exact data size we requested
data = base64.urlsafe_b64encode(os.urandom(DATA_SIZE))[:DATA_SIZE]
if opts.msgpack:
    data = msgpack.dumps(data)

PARALLEL = opts.parallel

print "Datasize:", DATA_SIZE, "Parallel:", PARALLEL

counter = [0] * PARALLEL
st = time.time()

def tick():
    global counter, st
    while True:
        time.sleep(2)
        ct = time.time()
        elapsed_s = ct - st
        sc = sum(counter)

        mps = sc / elapsed_s

        print counter, sc, "requests, per sec:", mps

def work(wid):
    global counter
    while True:
        hsclient.noop(data)
        #hsclient.hello(str(counter[wid]))
        counter[wid] += 1

_gt = gevent.spawn(tick)

workers = []
for x in range(PARALLEL):
    workers.append(gevent.spawn(work, x))

gevent.joinall([_gt] + workers)

