#!/usr/bin/env python

"""Script to store configuration and interfaces into the directory"""

__author__ = 'Seman Said, Michael Meisinger'

import argparse
import ast

import pyon
from pyon.core import bootstrap, config
from pyon.core.interfaces.interfaces import InterfaceAdmin
from putil.script_util import parse_args

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
    parser.add_argument('-c', '--config', type=str, help='Additional config files to load or dict config content.', default=[])
    parser.add_argument('-fc', '--force_clean', action='store_true', help='Force clean.')
    parser.add_argument("-of", "--object", dest="fobject", help="Load object definition from a file")
    parser.add_argument("-s", "--sysname", dest="sysname", help="System name")
    parser.add_argument("-sf", "--service", dest="fservice", help="Load service definition from a file")

    options, extra = parser.parse_known_args()
    args, command_line_config = parse_args(extra)

    print "store_interfaces: Storing ION config and interfaces in datastore, with options:" , str(options)

    # -------------------------------------------------------------------------
    # Store config and interfaces

    # Set global testing flag to False. We are running as standalone script. This is NO TEST.
    bootstrap.testing = False

    # Set sysname if provided in startup argument
    if options.sysname:
        bootstrap.set_sys_name(options.sysname)

    # Load config override if provided. Supports variants literal and list of paths
    config_override = None
    if options.config:
        if '{' in options.config:
            # Variant 1: Dict of config values
            try:
                eval_value = ast.literal_eval(options.config)
                config_override = eval_value
            except ValueError:
                raise Exception("Value error in config arg '%s'" % options.config)
        else:
            # Variant 2: List of paths
            from pyon.util.config import Config
            config_override = Config([options.config]).data

    # bootstrap_config - Used for running this store_interfaces script
    bootstrap_config = config.read_local_configuration(['res/config/pyon_min_boot.yml'])
    config.apply_local_configuration(bootstrap_config, pyon.DEFAULT_LOCAL_CONFIG_PATHS)
    if config_override:
        config.apply_configuration(bootstrap_config, config_override)
    config.apply_configuration(bootstrap_config, command_line_config)

    # Override sysname from config file or command line
    if not options.sysname and bootstrap_config.get_safe("system.name", None):
        new_sysname = bootstrap_config.get_safe("system.name")
        bootstrap.set_sys_name(new_sysname)

    # Delete sysname datastores if option "force_clean" is set
    if options.force_clean:
        from pyon.datastore import clear_couch_util
        from pyon.util.file_sys import FileSystem
        print "store_interfaces: force_clean=True. DROP DATASTORES for sysname=%s" % bootstrap.get_sys_name()
        pyon_config = config.read_standard_configuration()      # Initial pyon.yml + pyon.local.yml
        clear_couch_util.clear_couch(bootstrap_config, prefix=bootstrap.get_sys_name(), sysname=bootstrap.get_sys_name())
        FileSystem._clean(pyon_config)


    # ion_config - Holds the new CFG object for the system (independent of this tool's config)
    ion_config = config.read_standard_configuration()
    if config_override:
        config.apply_configuration(ion_config, config_override)
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

    iadm.close()

if __name__ == '__main__':
    main()
