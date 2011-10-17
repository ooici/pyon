#!/usr/bin/env python

from pyon.net.endpoint import RPCClient
from pyon.net.messaging import makeNode
import gevent

from interface.services.ibank_service import IBankService
from interface.services.idatastore_service import IDatastoreService

node,iowat=makeNode()

bank = RPCClient(node=node, name="bank", iface=IBankService)
data = RPCClient(node=node, name="datastore", iface=IDatastoreService)



