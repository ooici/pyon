#!/usr/bin/env python

"""
@file pyon/datastore/clear_couch_util.py
@author David Stuebe

@brief This method is used to clear scoped couch databases via the command line.
@todo integrate logging with a module that runs under main?
@todo figure out why I can't import pyon stuff in the scripts directory. This should live there...
"""

import sys
from optparse import OptionParser

from pyon.datastore.datastore_common import DatastoreFactory


def main():

    usage = \
    """
    %prog [options] prefix
    """
    description = \
    """Use this program to clear databases in couch that match a given prefix
    """
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-P", "--port", dest="couch_port", default=5984, help="Port number for couch", action="store", type=int, metavar="PORT")
    parser.add_option("-H", "--host", dest="couch_host", default='localhost', help="The host name or ip address of the couch server", action="store", type=str, metavar="HOST")
    parser.add_option("-u", "--username", dest="couch_uname", default=None, help="Username for the couch server", action="store", type=str, metavar="UNAME")
    parser.add_option("-p", "--password", dest="couch_pword", default=None, help="Password for the couch server", action="store", type=str, metavar="PWORD")
    parser.add_option("-s", "--sysname", dest="sysname", default=None, help="The sysname prefix to clear in couch", action="store", type=str, metavar="SYSNAME")
    parser.add_option("-t", "--store_type", dest="couch_type", default="couchdb", help="Datastore type", action="store", type=str, metavar="DSTYPE")
    parser.add_option("-v", "--verbose", help="More verbose output", action="store_true")
    parser.add_option("-d", "--dump", dest="dump_path", default=None, help="Dump sysname datastores to path", action="store", type=str, metavar="DPATH")
    parser.add_option("-l", "--load", dest="load_path", default=None, help="Load dumped datastore from path", action="store", type=str, metavar="LPATH")

    (options, args) = parser.parse_args()

    if options.dump_path:
        config = create_config(options.couch_host, options.couch_port, options.couch_uname, options.couch_pword)
        sysname = options.sysname or "mine"
        print "clear_couch: dumping", sysname, "datastores to", options.dump_path
        from pyon.datastore.datastore_admin import DatastoreAdmin
        datastore_admin = DatastoreAdmin(config=config, sysname=sysname)
        datastore_admin.dump_datastore(path=options.dump_path, compact=True)
    elif options.load_path:
        config = create_config(options.couch_host, options.couch_port, options.couch_uname, options.couch_pword)
        sysname = options.sysname or "mine"
        print "clear_couch: loading", sysname, "datastores from dumped content in", options.dump_path
        from pyon.datastore.datastore_admin import DatastoreAdmin
        datastore_admin = DatastoreAdmin(config=config, sysname=sysname)
        datastore_admin.load_datastore(path=options.load_path)
    else:
        if len(args) == 0:
            print 'clear_couch: Error: no prefix argument specified'
            parser.print_help()
            sys.exit()

        if len(args) != 1:
            print 'clear_couch: Error: You can not specify multiple prefixes. Received args: %s' % str(args)
            parser.print_help()
            sys.exit()

        prefix = args[0]

        if prefix is '':
            print 'clear_couch: Error: You can not give the empty string as a prefix!'
            parser.print_help()
            sys.exit()

        config = create_config(options.couch_host, options.couch_port, options.couch_uname, options.couch_pword, options.couch_type)
        _clear_couch(config, prefix=prefix, verbose=bool(options.verbose))

def create_config(host, port, username, password, type="couchdb"):
    config = dict(host=host, port=port, username=username, password=password, type=type)
    return config

def clear_couch(config, prefix):
    config = DatastoreFactory.get_server_config(config)
    _clear_couch(
        config=config,
        prefix=prefix)

def _clear_couch(config, prefix, verbose=False):
    db_server = DatastoreFactory.get_datastore(config=config)

    if verbose:
        print "clear_couch: Connected to couch server with config %s" % (config)

    db_list = db_server.list_datastores()

    ignored_num = 0
    for db_name in db_list:

        if (prefix == '*' and not db_name.startswith('_')) or db_name.lower().startswith(prefix.lower()):
            db_server.delete_datastore(db_name)
            print 'clear_couch: Dropped couch database: %s' % db_name

        else:
            if verbose:
                print 'clear_couch: Ignored couch database: %s' % db_name

            ignored_num += 1
    print 'clear_couch: Ignored %s existing databases' % ignored_num

    db_server.close()


if __name__ == '__main__':
    main()
