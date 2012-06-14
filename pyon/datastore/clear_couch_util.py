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

from pyon.datastore.couchdb.couchdb_standalone import CouchdbStandalone


def main():

    usage = \
    """
    %prog [options] prefix
    """
    description = \
    """Use this program to clear databases in couch that match a given prefix
    """
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-p", "--port", dest="couch_port", default=5984, help="Port number for couch", action="store", type=int, metavar="PORT")
    parser.add_option("-n", "--host", dest="couch_host", default='localhost', help="The host name or ip address of the couch server", action="store", type=str, metavar="HOST")
    parser.add_option("-u", "--username", dest="couch_uname", default=None, help="Username for the couch server", action="store", type=str, metavar="UNAME")
    parser.add_option("-s", "--password", dest="couch_pword", default=None, help="Password for the couch server", action="store", type=str, metavar="PWORD")
    #parser.add_option("-s", "--sysname", dest="sysname", default=None, help="The sysname prefix to clear in couch", action="store", type=str, metavar="SYSNAME")
    parser.add_option("-v", "--verbose", help="More verbose output", action="store_true")


    (options, args) = parser.parse_args()

    # Hack to set the user name and password
    if len(args) ==0:
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

    _clear_couch(options.couch_host, options.couch_port, options.couch_uname, options.couch_pword, prefix=prefix, verbose=bool(options.verbose))

def clear_couch(config, prefix):
    _clear_couch(
        config.server.couchdb.host,
        config.server.couchdb.port,
        config.server.couchdb.username,
        config.server.couchdb.password,
        prefix=prefix)

def _clear_couch(host, port, username, password, prefix, verbose=False):
    db_server = CouchdbStandalone(host=host, port=str(port), username=username, password=password)

    if verbose:
        print "clear_couch: Connected to couch server http://%s:%d" % (host, port)

    db_list = db_server.list_datastores()

    ignored_num = 0
    for db_name in db_list:

        if (prefix == '*' and not db_name.startswith('_')) or db_name.startswith(prefix):
            db_server.delete_datastore(db_name)
            print 'clear_couch: Dropped couch database: %s' % db_name

        else:
            if verbose:
                print 'clear_couch: Ignored couch database: %s' % db_name

            ignored_num += 1
    print 'clear_couch: Ignored %s existing databases' % ignored_num


if __name__ == '__main__':
    main()
