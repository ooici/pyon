#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from pyon.directory.directory import Directory
from interface.services.idirectory_service import BaseDirectoryService

class DirectoryService(BaseDirectoryService):

    def on_init(self):
        self.directory = Directory()

    def add(self, parent='/', key='foo', value={}):
        return self.directory.add(parent, key, value)

    def update(self, parent='/', key='foo', value={}):
        return self.directory.update(parent, key, value)

    def read(self, parent='/', key='foo'):
        return self.directory.read(parent, key)

    def remove(self, parent='/', key='foo'):
        return self.directory.remove(parent, key)
