#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.config import Config
from pyon.core.object import IonServiceRegistry

import logging.config
import os

# THE CODE BELOW EXECUTES ON IMPORT OF THIS MODULE
# IT BOOTSTRAPS THE PYON ENVIRONMENT

# ENVIRONMENT. Check we are started in a proper way.
def assert_environment():
    """This asserts the mandatory (minimal) execution environment for pyon"""
    import os.path
    if not os.path.exists("res"):
        raise Exception("pyon environment assertion failed: res/ directory not found")
    if not os.path.exists("res/config"):
        raise Exception("pyon environment assertion failed: res/config directory not found")
    if not os.path.exists("res/config/pyon.yml"):
        raise Exception("pyon environment assertion failed: pyon.yml config missing")
    if not os.path.exists("obj"):
        raise Exception("pyon environment assertion failed: obj/ directory not found")
    if not os.path.exists("obj/services"):
        raise Exception("pyon environment assertion failed: obj/services directory not found")
    if not os.path.exists("obj/data"):
        raise Exception("pyon environment assertion failed: obj/data directory not found")

assert_environment()

pyon_initialized = False

# LOGGING. Read the logging config files
logging_conf_paths = ['res/config/logging.yml', 'res/config/logging.local.yml']

LOGGING_CFG = None

def initialize_logging():
    global LOGGING_CFG
    LOGGING_CFG = Config(logging_conf_paths, ignore_not_found=True).data

    # Ensure the logging directories exist
    for handler in LOGGING_CFG.get('handlers', {}).itervalues():
        if 'filename' in handler:
            log_dir = os.path.dirname(handler['filename'])
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)

    # if there's no logging config, we can't configure it: the call requires version at a minimum
    if LOGGING_CFG:
        logging.config.dictConfig(LOGGING_CFG)

initialize_logging()

# CONFIG. Read global configuration
conf_paths = ['res/config/pyon.yml', 'res/config/pyon.local.yml']
CFG = Config(conf_paths, ignore_not_found=True).data
sys_name = CFG.system.name or 'pyon_%s' % os.uname()[1].replace('.', '_')

# OBJECTS. Object and service definitions.
# Make a default factory for IonObjects
obj_registry = IonServiceRegistry()
IonObject = obj_registry.new

def populate_registry():
    obj_registry.register_obj_dir('obj/data', do_first=['ion.yml', 'resource.yml'])
    obj_registry.register_svc_dir('obj/services')

def bootstrap_pyon():
    """
    This function initializes the Pyon framework in a controlled way.
    Note: It does not initialize the ION container or the ION system.
    """
    
    #Make sure Pyon is only initialized once
    global pyon_initialized
    if pyon_initialized:
        return

    #TODO: Call initialize_logging here

    # YAML patch: OrderedDicts instead of dicts
    from pyon.util.yaml_ordered_dict import apply_yaml_patch
    # OK the following does not work (early enough??)!!!!
    #apply_yaml_patch()

    # Objects
    populate_registry()

    # Resource definitions
    from pyon.ion import resource
    resource.load_definitions()

    # Load interceptors
    from pyon.net.endpoint import instantiate_interceptors
    instantiate_interceptors(CFG.interceptor)

    # Services.
    from pyon.service import service
    service.load_service_mods('interface/services')
    service.build_service_map()

    # Set initialized flag
    pyon_initialized = True
