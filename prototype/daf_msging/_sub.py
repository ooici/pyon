#!/usr/bin/env python

from pyon.net.endpoint import Subscriber
from pyon.net.messaging import make_node
import gevent

node,iowat=make_node()

def msg_recv(msg):
    print "\n\n========================================\n\nHASSAN SAYS: %s\n\n========================================\n\n" % str(msg)

sub=Subscriber(node=node, name="hassan", callback=msg_recv)
meh=gevent.spawn(sub.listen)

gevent.joinall([meh])
