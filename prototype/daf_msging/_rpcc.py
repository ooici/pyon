#!/usr/bin/env python

from pyon.net.endpoint import RPCClient
from pyon.net.messaging import makeNode
import gevent

from interface.services.ibank_service import IBankService

node,iowat=makeNode()

rpcc = RPCClient(node=node, name="bank", iface=IBankService)


