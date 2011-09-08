#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from zope.interface import implements

from anode.core.bootstrap import CFG
from anode.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from anode.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from anode.service.service import BaseService
from interface.services.idatastore_service import IDatastoreService

class DataStoreService(BaseService):
    implements(IDatastoreService)

    def __init__(self):
        if CFG.datastore.type == 'persistent':
            self.dataStore = CouchDB_DataStore()
        else:
            self.dataStore = MockDB_DataStore()

    def list_objects(dataStoreName=None):
        return self.dataStore.list_objects(dataStoreName)

    def delete_datastore(dataStoreName=None):
        return self.dataStore.delete_datastore(dataStoreName)

    def list_object_revisions(dataStoreName=None, objectId=None):
        return self.dataStore.list_object_revisions(dataStoreName, objectId)

    def update(object=None, dataStoreName=None):
        return self.dataStore.update(object, dataStoreName)

    def info_datastore(dataStoreName=None):
        return self.dataStore.info_datastore(dataStoreName)

    def read_doc(dataStoreName=None, revId=None, objectId=None):
        return self.dataStore.read_doc(dataStoreName, revId, objectId)

    def find(type=None, dataStoreName=None, keyValue=None, key=None):
        return self.dataStore.find(type, dataStoreName, keyValue, key)

    def find_doc(type=None, dataStoreName=None, keyValue=None, key=None):
        return self.dataStore.find_doc(type, dataStoreName, keyValue, key)

    def list_datastores():
        return self.dataStore.list_datastores()

    def create(object=None, dataStoreName=None):
        return self.dataStore.create(object, dataStoreName)

    def create_datastore(dataStoreName=None):
        return self.dataStore.create_datastore(dataStoreName)

    def read(dataStoreName=None, revId=None, objectId=None):
        return self.dataStore.read(dataStoreName, revId, objectId)

    def update_doc(object=None, dataStoreName=None):
        return self.dataStore.update_doc(object, dataStoreName)

    def create_doc(object=None, dataStoreName=None):
        return self.dataStore.create_doc(object, dataStoreName)

    def delete_doc(object=None, dataStoreName=None):
        return self.dataStore.delete_doc(object, dataStoreName)

    def delete(object=None, dataStoreName=None):
        return self.dataStore.delete(object, dataStoreName)