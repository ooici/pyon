#!/usr/bin/env python

from pyon.net.endpoint import Subscriber, BinderListener
from pyon.net.channel import PubSub
from pyon.net.messaging import make_node
import gevent
import time

node,iowat=make_node()

def msg_recv(msg):
    global counter
    counter += 1

sub=Subscriber(callback=msg_recv)
bl=BinderListener(node=node, name="hassan", endpoint_factory=sub, listening_channel_type=PubSub, spawn_callable=None)

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
_gw = gevent.spawn(bl.listen)

gevent.joinall([_gt, _gw])

