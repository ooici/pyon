#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import yaml
from ion.util.containers import DotDict, dict_merge

class Config(object):
    """
    YAML-based config loader that supports multiple paths.
    Later paths get deep-merged over earlier ones.
    """

    def __init__(self, paths=(), dict_class=DotDict):
        self.paths = list(paths)
        self.paths_loaded = set()
        self.dict_class = dict_class
        self.data = self.dict_class()

        if paths: self.load()

    def add_path(self, path):
        """ Add this path at the end of the list and load/merge its contents. """
        self.paths.append(path)
        self.load()

    def load(self):
        """ Load each path in order. Remember paths already loaded and only load new ones. """
        data = self.dict_class()
        
        for path in self.paths:
            if path in self.paths_loaded: continue
            
            try:
                with open(path, 'r') as file:
                    path_data = yaml.load(file.read())
                    data = dict_merge(data, path_data)
                self.paths_loaded.add(path)
            except IOError:
                # TODO: Log this correctly once logging is implemented
                print 'CONFIG NOT FOUND: %s' % (path)

        self.data = data

    def reload(self):
        self.paths_loaded.clear()
        self.load()
        