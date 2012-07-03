#!/usr/bin/env python

"""Script to store configuration and interfaces into the directory"""

__author__ = 'Seman Said, Michael Meisinger'

import argparse

import pyon
from pyon.core import bootstrap, config
from pyon.core.interfaces.interfaces import InterfaceAdmin
from script_util import parse_args

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
    parser.add_argument('-fc', '--force_clean', action='store_true',
            help='Force clean.')
    parser.add_argument("-of", "--object", dest="fobject",
            help="Load object definition from a file")
    parser.add_argument("-s", "--sysname", dest="sysname", help="System name")
    parser.add_argument("-sf", "--service", dest="fservice",
            help="Load service definition from a file")

    options, extra = parser.parse_known_args()
    args, command_line_config = parse_args(extra)

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
    config.apply_configuration(bootstrap_config, command_line_config)

    # Delete sysname datastores if option "force_clean" is set
    if options.force_clean:
        from pyon.datastore import clear_couch_util
        print "store_configuration: force_clean=True. DROP DATASTORES for sysname=%s" % bootstrap.get_sys_name()
        clear_couch_util.clear_couch(bootstrap_config, prefix=bootstrap.get_sys_name())


    # This holds the new CFG object for the system
    # @TODO: Could add command line --config
    ion_config = config.read_standard_configuration()
    config.apply_configuration(ion_config, command_line_config)


    # -------------------------------------------------------------------------
    # Store config and interfaces

    iadm = InterfaceAdmin(bootstrap.get_sys_name(), config=bootstrap_config)

    # Make sure core datastores exist
    iadm.create_core_datastores()

    # Store system CFG properties
    iadm.store_config(ion_config)

    # Store system interfaces
    iadm.store_interfaces(options.fobject, options.fservice)

if __name__ == '__main__':
    main()
