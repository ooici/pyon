#!/usr/bin/env python

from pyon.net.entity import Publisher
from pyon.net.messaging import makeNode
import gevent

node,iowat=makeNode()

pub=Publisher(node=node, name="hassan")

