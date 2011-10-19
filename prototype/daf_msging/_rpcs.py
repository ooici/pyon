#!/usr/bin/env python
"""

from pyon.net.endpoint import RPCServer
from pyon.net.messaging import makeNode
import gevent

from prototype.bank import BankService

node,iowat=makeNode()

bs = BankService()

rpcs = RPCServer(node=node, name="bank", service=bs)

mooo=rpcs.listen()

gevent.joinall([mooo])
"""

from pyon.container.cc import Container
cc=Container()
cc.start()
cc.start_rel_from_url('res/deploy/r2deploy.yml')

cc.serve_forever()

