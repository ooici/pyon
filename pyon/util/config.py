#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import yaml

from pyon.util.containers import DotDict, dict_merge
from pyon.core.exception import ConfigNotFound

import logging.config
import os

class Config(object):
    """
    YAML-based config loader that supports multiple paths.
    Later paths get deep-merged over earlier ones.
    """

    def __init__(self, paths=(), dict_class=DotDict, ignore_not_found=False):
        self.paths = list(paths)
        self.paths_loaded = set()
        self.dict_class = dict_class
        self.data = self.dict_class()

        if paths: self.load(ignore_not_found)

    def add_path(self, path, ignore_not_found=False):
        """ Add this path at the end of the list and load/merge its contents. """
        self.paths.append(path)
        self.load(ignore_not_found)

    def load(self, ignore_not_found=False):
        """ Load each path in order. Remember paths already loaded and only load new ones. """
        data = self.dict_class()
        
        for path in self.paths:
            if path in self.paths_loaded: continue
            
            try:
                with open(path, 'r') as file:
                    path_data = yaml.load(file.read())
                    if path_data is not None:
                        data = dict_merge(data, path_data)
                self.paths_loaded.add(path)
            except IOError:
                if not ignore_not_found:
                    raise ConfigNotFound("Config URL '%s' not found" % path)

        self.data = data

    def reload(self):
        self.paths_loaded.clear()
        self.load()

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
        
