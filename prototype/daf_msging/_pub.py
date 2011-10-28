#!/usr/bin/env python

from pyon.net.endpoint import Publisher
from pyon.net.messaging import make_node
import gevent

node,iowat=make_node()

pub=Publisher(node=node, name="hassan")

