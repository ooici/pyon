#!/usr/bin/env python

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

import uuid
import os

import pyon
# NOTE: no other imports inside pyon

# @WARN: GLOBAL STATE

# -----------------------------------------------------------------------------
# Internal pyon variables

# Is pyon already initialized?
pyon_initialized = False

# Handle to the object interface registry -- use getter function instead
_obj_registry = None

# Handle to the service interface registry -- use getter function instead
_service_registry = None

# -----------------------------------------------------------------------------
# Global pyon variables

# The global pyon configuration object (DotDict)
from pyon.util.containers import DotDict
CFG = DotDict()

# Is pyon running in non-container testing mode? (Note: pycc will set this to False)
testing = True

# Identifies the unique name and namespace of this ION distributed system instance
sys_name = None

# Factory metaclass to create ION objects
def IonObject(*args, **kwargs):
    return _obj_registry.new(*args, **kwargs)

# Keep the current container instance
container_instance = None


# -----------------------------------------------------------------------------
# Initialization helper functions
# NOTE: no static initializers here!!

def assert_environment():
    """
    This asserts the mandatory (minimal) execution environment for pyon
    """
    import os.path
    from pyon.core.exception import ContainerStartupError
    if not os.path.exists("res"):
        raise ContainerStartupError("pyon environment assertion failed: res/ directory not found")
    if not os.path.exists("res/config"):
        raise ContainerStartupError("pyon environment assertion failed: res/config directory not found")
    if not os.path.exists("res/config/pyon.yml"):
        raise ContainerStartupError("pyon environment assertion failed: pyon.yml config missing")
    if not os.path.exists("obj"):
        raise ContainerStartupError("pyon environment assertion failed: obj/ directory not found")
    if not os.path.exists("obj/services"):
        raise ContainerStartupError("pyon environment assertion failed: obj/services directory not found")
    if not os.path.exists("obj/data"):
        raise ContainerStartupError("pyon environment assertion failed: obj/data directory not found")

def load_logging_config(logging_config_override=None):
    """
    Initialize pyon logging system
    """
    from pyon.core import log
    log.configure_logging(pyon.DEFAULT_LOGGING_PATHS, logging_config_override=logging_config_override)

def set_config(pyon_cfg=None):
    """
    Initialize pyon global configuration
    """
    from pyon.core import config

    if pyon_cfg:
        # Variant 1: if provided, set pyon_cfg as pyon global CFG
        config.apply_configuration(CFG, pyon_cfg)
    else:
        # Variant 2: default, load standard configuration sequence
        std_cfg = config.read_standard_configuration()
        config.apply_configuration(CFG, std_cfg)

    assert_configuration(CFG)

def assert_configuration(config):
    """
    Checks that configuration is OK.
    This is separate so that it can be called after config changes (from directory, command line etc)
    """
    from pyon.core.exception import ContainerConfigError
    from pyon.util.containers import is_basic_identifier
    if not is_basic_identifier(config.get_safe("system.root_org", "")):
        raise ContainerConfigError("Config entry 'system.root_org' has illegal value")

def is_testing():
    return testing

def set_sys_name(sysname=None):
    global sys_name
    old_sys_name = sys_name
    sys_name = sysname
    print "pyon: sys_name changed from '%s' to '%s'" % (old_sys_name, sys_name)

def get_sys_name():
    if sys_name:
        return sys_name

    from pyon.util.containers import get_default_sysname
    default_sys_name = get_default_sysname()
    testing_sys_name = "ion_test_%s" % str(uuid.uuid4())[0:6]

    if is_testing():
        testing_override = CFG.get_safe("system.testing_sysname", None)
        if testing_override:
            testing_sys_name = testing_override
        set_sys_name(testing_sys_name)
        return testing_sys_name
    else:
        set_sys_name(default_sys_name)
        return default_sys_name

def get_obj_registry():
    return _obj_registry

def get_service_registry():
    return _service_registry

# -----------------------------------------------------------------------------

def bootstrap_pyon(logging_config_override=None, pyon_cfg=None):
    """
    This function initializes the core elements of the Pyon framework in a controlled way.
    It does not initialize the ION container or the ION system.
    @param logging_config_override  A dict to initialize the Python logging subsystem (None loads default files)
    @param pyon_cfg   A DotDict with the fully loaded pyon configuration to set as CFG (None loads default files)
    """
    print "pyon: pyon.bootstrap (bootstrap_pyon) executing..."

    # Make sure Pyon is only initialized only once
    global pyon_initialized
    if pyon_initialized:
        print "pyon: WARNING -- bootstrap_pyon() called again!"
        return

    # ENVIRONMENT. Check we are called in an expected environment (files, directories, etc)
    assert_environment()

    # LOGGING. Initialize logging from config
    load_logging_config(logging_config_override=logging_config_override)

    # YAML patch: OrderedDicts instead of dicts
    from pyon.util.yaml_ordered_dict import apply_yaml_patch
    apply_yaml_patch()

    # CONFIG. Initialize pyon global configuration from local files
    set_config(pyon_cfg)

    # OBJECTS. Object and message definitions.
    from pyon.core.registry import IonObjectRegistry
    global _obj_registry
    _obj_registry = IonObjectRegistry()

    # SERVICES. Service definitions
    from pyon.service.service import IonServiceRegistry
    global _service_registry
    _service_registry = IonServiceRegistry()
    _service_registry.load_service_mods('interface/services')
    _service_registry.build_service_map()

    # INTERCEPTORS.
    # TODO: Is
    from pyon.net.endpoint import instantiate_interceptors
    instantiate_interceptors(CFG.interceptor)

    # RESOURCES. Load and initialize definitions
    from pyon.ion import resource
    resource.load_definitions()

    # Set initialized flag
    pyon_initialized = True
