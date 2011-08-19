#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from zope.interface import implements

from anode.directory.directory import Directory
from anode.service.service import BaseService
from interface.services.idirectory_service import IDirectoryService

class DirectoryService(BaseService):
    implements(IDirectoryService)

    def __init__(self, persistent=False):
        self.directory = Directory(dataStoreName="my_directory_data_store", persistent)

    def read(parent='/', key='foo'):
        self.directory.read(parent, key)

    def add(parent='/', key='foo', value={}):
        self.directory.add(parent, key, value)

    def update(parent='/', key='foo', value={}):
        self.directory.update(parent, key, value)

    def remove(parent='/', key='foo'):
        self.directory.read(parent, key)
