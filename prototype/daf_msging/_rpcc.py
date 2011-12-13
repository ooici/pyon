#!/usr/bin/env python

from pyon.net.endpoint import RPCClient
from pyon.net.messaging import make_node
from interface.services.examples.hello.ihello_service import IHelloService
"""
import gevent

from interface.services.ibank_service import IBankService
from interface.services.idatastore_service import IDatastoreService

node,iowat=make_node()

bank = RPCClient(node=node, name="bank", iface=IBankService)
data = RPCClient(node=node, name="datastore", iface=IDatastoreService)
"""

n,io=make_node()

hello=RPCClient(node=n, name=('qq', 'hello'), iface=IHelloService)


