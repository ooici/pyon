#!/usr/bin/env python

"""Script to store configuration and interfaces into the directory"""

__author__ = 'Seman Said, Michael Meisinger'

from collections import OrderedDict
import argparse

import pyon
from pyon.core import bootstrap, config
from pyon.core.interfaces.interfaces import InterfaceAdmin


def main():
    '''
    Store configuration and interfaces into the datastore
    How to run this from command line:
        bin/store_interfaces  -s system name [ -of filename | -sf filename | -fc true|false]
        -of Load object definition file
        -sf Load service definition file
        -fc Force clean the database

     Example:
        Load all object and service definitions
        bin/python bin/store_interfaces  -s mysysname

        Load all object and service definitions with force clean the database
        bin/python bin/store_interfaces  -s mysysname -fc

        Load object definition from a file
        bin/python bin/store_interfaces  -s mysysname -of obj/data/coi/org.yml

        Load service definition from a file
        bin/python bin/store_interfaces  -s mysysname -sf obj/services/coi/datastore_service.yml
    '''

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--individual', action='store_true',
        help='Store files individually.')
    parser.add_argument('-fc', '--force_clean', action='store_true',
        help='Force clean.')
    parser.add_argument("-of", "--object", dest="fobject",
        help="Load object definition from a file")
    parser.add_argument("-s", "--sysname", dest="sysname", help="System name")
    parser.add_argument("-sf", "--service", dest="fservice",
        help="Load service definition from a file")
    options = parser.parse_args()

    print "store_configuration: Storing ION config and interfaces in datastore, with options:" , str(options)

    # -------------------------------------------------------------------------
    # Store config and interfaces

    # Set global testing flag to False. We are running as standalone script. This is NO TEST.
    bootstrap.testing = False

    # Set sysname if provided in startup argument
    if options.sysname:
        bootstrap.set_sys_name(options.sysname)

    # Load minimal bootstrap config
    bootstrap_config = config.read_local_configuration(['res/config/pyon_min_boot.yml'])
    config.apply_local_configuration(bootstrap_config, pyon.DEFAULT_LOCAL_CONFIG_PATHS)

    # Delete sysname datastores if option "force_clean" is set
    if options.force_clean:
        from pyon.datastore import clear_couch_util
        print "store_configuration: force_clean=True. DROP DATASTORES for sysname=%s" % bootstrap.get_sys_name()
        clear_couch_util.clear_couch(bootstrap_config, prefix=bootstrap.get_sys_name())

    # -------------------------------------------------------------------------
    # Store config and interfaces

    ia = InterfaceAdmin(bootstrap.get_sys_name(), options.fobject, options.fservice, store_bulk=not options.individual)
    ia.store_interfaces()

if __name__ == '__main__':
    main()
