#!/usr/bin/env python

from pyon.net.endpoint import RPCClient
from interface.services.idatastore_service import IDatastoreService
from pyon.net.messaging import makeNode
import gevent
import time

node,iowat=makeNode()
dsclient = RPCClient(node=node, name="datastore", iface=IDatastoreService)

counter = 0
st = time.time()

def tick():
    global counter, st
    while True:
        time.sleep(2)
        ct = time.time()
        elapsed_s = ct - st

        mps = counter / elapsed_s

        print counter, "messages, per sec:", mps

def work():
    global counter
    while True:
        dsclient.list_datastores()
        counter += 1

_gt = gevent.spawn(tick)
_gw = gevent.spawn(work)

gevent.joinall([_gt, _gw])

