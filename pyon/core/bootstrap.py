#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from pyon.util.config import Config
from pyon.core.object import IonServiceRegistry

import logging.config
import os

# Note: do we really want to do the res folder like this again?
logging_conf_paths = ['res/config/logging.yml', 'res/config/logging.local.yml']
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

# Read global configuration
conf_paths = ['res/config/pyon.yml', 'res/config/pyon.local.yml']
CFG = Config(conf_paths, ignore_not_found=True).data
sys_name = CFG.system.name or 'pyon_%s' % os.uname()[1].replace('.', '_')

# Make a default factory for IonObjects
obj_registry = IonServiceRegistry()
IonObject = obj_registry.new

def populate_registry():
    obj_registry.register_obj_dir('obj/data')
    obj_registry.register_svc_dir('obj/services')

