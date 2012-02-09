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
from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from pyon.core.bootstrap import CFG


def main():

    usage = \
    """
    %prog [options] prefix
    """
    description = \
    """Use this program to clear databases in couch that match a given prefix
    """
    parser = OptionParser(usage=usage, description=description)
    parser.add_option("-p", "--port", dest="couch_port", default=5984, help="specify a port for couch", action="store", type=int, metavar="PORT")
    parser.add_option("-n", "--host", dest="couch_host", default='localhost', help="The host name or ip address of the couch server", action="store", type=str, metavar="HOST")
    parser.add_option("-u", "--user_name", dest="couch_uname", default=None, help="User name for the couch server", action="store", type=str, metavar="UNAME")
    parser.add_option("-s", "--password", dest="couch_pword", default=None, help="Password for the couch server", action="store", type=str, metavar="PWORD")
    #parser.add_option("-s", "--sysname", dest="sysname", default=None, help="The sysname prefix to clear in couch", action="store", type=str, metavar="SYSNAME")


    (options, args) = parser.parse_args()

    # Hack to set the user name and password
    if len(args) ==0:
        print '$ Error: no prefix argument specified'
        parser.print_help()
        sys.exit()

    if len(args) != 1:
        print '$ Error: You can not specify multiple prefixes. Received args: %s' % str(args)
        parser.print_help()
        sys.exit()

    prefix = args[0]

    if prefix is '':
        print '$ Error: You can not give the empty string as a prefix!'
        parser.print_help()
        sys.exit()

    if options.couch_uname is not None:
        CFG.server.couchdb.username = options.couch_uname

    if options.couch_pword is not None:
        CFG.server.couchdb.password = options.couch_pword

    db_server = CouchDB_DataStore(host=options.couch_host, port=options.couch_port)

    print "$ Connected to couch database @: host %s, port %d" % (options.couch_host, options.couch_port)

    db_list = db_server.list_datastores()

    for db_name in db_list:

        if db_name.startswith(prefix):

            db_server.delete_datastore(db_name)
            print '$ Cleared couch db named: %s' % db_name

        else:
            print '$ Ignoring couch db named: %s' % db_name



if __name__ == '__main__':
    main()