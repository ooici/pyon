#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from anode.core.exception import NotFound
from anode.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from anode.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from interface.services.idatastore_service import BaseDatastoreService

from anode.util.log import log

class DataStoreService(BaseDatastoreService):

    def __init__(self, config_params={}):
        if config_params.has_key('type'):
            if config_params["type"] == 'CouchDB':
                self.datastore = CouchDB_DataStore()
                if config_params.has_key('forceClean'):
                    try:
                        self.datastore.delete_datastore()
                    except NotFound:
                        pass
                    self.datastore.create_datastore()
            else:
                self.datastore = MockDB_DataStore()
        else:
            self.datastore = MockDB_DataStore()

    def create_datastore(self, datastore_name=''):
        return self.datastore.create_datastore(datastore_name)

    def delete_datastore(self, datastore_name=''):
        return self.datastore.delete(object, datastore_name)

    def list_datastores(self):
        return self.datastore.list_datastores()

    def info_datastore(self, datastore_name=''):
        return self.datastore.info_datastore(datastore_name)

    def list_objects(self, datastore_name=''):
        return self.datastore.list_objects(datastore_name)

    def list_object_revisions(self, object_id='', datastore_name=''):
        return self.datastore.list_object_revisions(object_id, datastore_name)

    def create(self, object={}, datastore_name=''):
        return self.datastore.create(object, datastore_name)

    def create_doc(self, object={}, datastore_name=''):
        return self.datastore.create_doc(object, datastore_name)

    def read(self, object_id='', rev_id='', datastore_name=''):
        return self.datastore.read(object_id, rev_id, datastore_name)

    def read_doc(self, object_id='', rev_id='', datastore_name=''):
        return self.datastore.read_doc(object_id, rev_id, datastore_name)

    def update(self, object={}, datastore_name=''):
        return self.datastore.update(object, datastore_name)

    def update_doc(self, object={}, datastore_name=''):
        return self.datastore.update_doc(object, datastore_name)

    def delete(self, object={}, datastore_name=''):
        return self.datastore.delete_doc(object, datastore_name)

    def delete_doc(self, object={}, datastore_name=''):
        return self.datastore.delete_doc(object, datastore_name)

    def find(self, type='', key='', key_value='', datastore_name=''):
        return self.datastore.find(type, key, key_value, datastore_name)

    def find_doc(self, type='', key='', key_value='', datastore_name=''):
        return self.datastore.find_doc(type, key, key_value, datastore_name)
