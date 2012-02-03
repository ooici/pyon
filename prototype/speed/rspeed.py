#!/usr/bin/env python

from pyon.net.endpoint import Subscriber
from pyon.net.messaging import make_node
import gevent
import time

node,iowat=make_node()

def msg_recv(msg, h):
    global counter
    counter += 1

sub=Subscriber(node=node, name="hassan", callback=msg_recv)

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


_gt = gevent.spawn(tick)
_gw = gevent.spawn(sub.listen)

gevent.joinall([_gt, _gw])

