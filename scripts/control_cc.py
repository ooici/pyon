#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

# PYON CC CONTROLLER SCRIPT

import argparse
import msgpack
import os
from pyon.net.endpoint import RPCClient
from pyon.container.cc import IContainerAgent
from pyon.net.messaging import makeNode

def main():
    parser = argparse.ArgumentParser(description="CC Control script")
    parser.add_argument("pidfile", help="pidfile to use. If not specified, uses the first one found.")
    parser.add_argument("command", help="command to send to the container agent", choices=IContainerAgent.names())
    parser.add_argument("commandargs", metavar="arg", nargs="*", help="arguments to the command being sent")

    opts = parser.parse_args()

    pidfile = opts.pidfile
    if not pidfile:
        raise Exception("No pidfile specified")

    parms = {}
    with open(pidfile, 'r') as pf:
        parms = msgpack.loads(pf.read())

    assert parms, "No content in pidfile"

    node, ioloop = makeNode(parms['messaging'])
    cc = RPCClient(node=node, name=(parms['container-xp'], parms['container-agent']), iface=IContainerAgent)

    meth = getattr(cc, opts.command)
    retval = meth(*opts.commandargs)

    print "Returned", retval
    node.client.close()

if __name__ == '__main__':
    main()
