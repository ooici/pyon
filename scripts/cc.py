#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from ion.public import Container, GreenProcessSupervisor

import argparse
import yaml

version = "2.0"     # TODO: extract this from the code once versioning is automated again
description = '''
ion (ION capability container) v%s
''' % (version)

def main(opts, *args, **kwargs):
    # Run each container in a process (green or python subprocess)
    sup = GreenProcessSupervisor()
    for i in xrange(opts.count):
        container = Container(*args, **kwargs)
        sup.spawn(opts.proctype, container.serve_forever)

    # TODO: "notresident" should wait until the process is finished and then terminate, rather than just exiting now
    if not opts.notresident:
        sup.join_children()

def parse_args(tokens):
    # Exploit yaml's spectacular type inference (and ensure consistency with config files)
    args, kwargs = [], {}
    for token in tokens:
        token = token.lstrip('-')
        if '=' in token:
            key,val = token.split('=', 1)
            kwargs[key] = yaml.load(val)
        else:
            args.append(yaml.load(token))

    return args, kwargs

if __name__ == '__main__':
    proc_types = GreenProcessSupervisor.type_callables.keys()
    
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-d', '--daemon', action='store_true')
    parser.add_argument('--notresident', action='store_false')
    parser.add_argument('--version', action='version', version='ion v%s' % (version))
    parser.add_argument('--count', type=int, default=1, choices=xrange(1, 1<<10), help='How many containers to spawn (1 to 1024).')
    parser.add_argument('--proctype', type=str, default='green', choices=proc_types, help='What type of process to spawn each container in.')
    opts, extra = parser.parse_known_args()
    args, kwargs = parse_args(extra)

    if opts.daemon:
        # TODO: The daemonizing code may need to be moved inside the Container class (so it happens per-process)
        from daemon import DaemonContext
        from lockfile import FileLock

        # TODO: May need to generate a pidfile based on some parameter or cc name
        with DaemonContext(pidfile=FileLock('cc.pid')):
            main(opts, extra)
    else:
        main(opts, extra)
    
