#!/usr/bin/env python

from pyon.net.endpoint import Publisher, PublisherEndpointUnit
from pyon.net.messaging import make_node
import gevent
import time

class SpeedPublisherEndpoint(PublisherEndpointUnit):
    def _build_msg(self, raw_msg):
        return raw_msg

class SpeedPublisher(Publisher):
    endpoint_type = SpeedPublisherEndpoint

node,iowat=make_node()
pub=Publisher(node=node, name="hassan")
#pub=SpeedPublisher(node=node, name="hassan")

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
        pub.publish(str(counter))
        counter += 1

_gt = gevent.spawn(tick)
_gw = gevent.spawn(work)

gevent.joinall([_gt, _gw])

