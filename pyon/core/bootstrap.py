#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.registry import IonObjectRegistry
from pyon.util.config import CFG
from pyon.service.service import IonServiceRegistry

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

# This sets the sys_name.
# DANGER: Don't import sys_name from here, use get_sys_name() instead.
# NOTE: This sys_name may be changed by the container later if command line args override
sys_name = CFG.system.name or 'ion_%s' % os.uname()[1].replace('.', '_')

def get_sys_name():
    return sys_name

# OBJECTS. Object and message definitions.
# Make a default factory for IonObjects
obj_registry = IonObjectRegistry()
IonObject = obj_registry.new

# SERVICES. Service definitions
service_registry = IonServiceRegistry()

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

    # Resource definitions
    from pyon.ion import resource
    resource.load_definitions()

    # Load interceptors
    from pyon.net.endpoint import instantiate_interceptors
    instantiate_interceptors(CFG.interceptor)

    # Services
    service_registry.load_service_mods('interface/services')
    service_registry.build_service_map()

    # Set initialized flag
    pyon_initialized = True
