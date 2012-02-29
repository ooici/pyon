#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

# PYON CC CONTROLLER SCRIPT

import argparse
import msgpack
import os
from interface.services.icontainer_agent import IContainerAgent, ContainerAgentClient
from pyon.net.messaging import make_node

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

    node, ioloop = make_node(parms['messaging'])
    cc = ContainerAgentClient(node=node, to_name=(parms['container-xp'], parms['container-agent']))

    # make a manual call - this is to avoid having to have the IonObject for the call
    methdefs = [x[1] for x in IContainerAgent.namesAndDescriptions() if x[0] == opts.command]
    assert len(methdefs) == 1

    arg_names = methdefs[0].positional                                  # ('name', 'module', 'cls', 'config')
    msg_args = msgpack.dumps(dict(zip(arg_names, opts.commandargs)))    # ('name', <usrinp1>, 'cls', <usrinp2>) -> { 'name' : <usrinp1>, 'cls': <usrinp2> }
    retval = cc.request(msg_args, op=opts.command)

    # special case: status
    if opts.command == "status":
        statstr = msgpack.loads(retval)
        print "Status:", statstr

        if statstr != "RUNNING":
            node.client.close()
            sys.exit(1)
    else:
        print "Returned", retval

    node.client.close()

if __name__ == '__main__':
    main()
