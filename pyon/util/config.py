#!/usr/bin/env python

__author__ = 'Adam R. Smith'


import yaml

from pyon.util.containers import DotDict, dict_merge
from pyon.core.exception import ConfigNotFound

class Config(object):
    """
    YAML-based config loader that supports multiple paths.
    Later paths get deep-merged over earlier ones.
    """

    def __init__(self, paths=(), dict_class=DotDict, ignore_not_found=False):
        self.paths = [path for path in paths if path] if paths is not None else []
        self.paths_loaded = set()
        self.dict_class = dict_class
        self.data = self.dict_class()

        if paths:
            self.load(ignore_not_found)

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
