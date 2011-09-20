#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from uuid import uuid4

import couchdb
from couchdb.http import ResourceNotFound

from ion.core.bootstrap import IonObject
from ion.core.exception import NotFound
from ion.datastore.datastore import DataStore
from ion.util.log import log

class CouchDB_DataStore(DataStore):
    """
    Data store implementation utilizing CouchDB to persist documents.
    For API info, see: http://packages.python.org/CouchDB/client.html#
    """

    def __init__(self, host='localhost', port=5984, datastore_name='prototype', options=""):
        log.debug('host %s port %d data store name %s options %s' % (host, port, str(datastore_name), str(options)))
        self.host = host
        self.port = port
        self.datastore_name = datastore_name
        connection_str = "http://" + host + ":" + str(port)
        log.info('Connecting to couchDB server: %s' % connection_str)
        self.server = couchdb.Server(connection_str)

    def create_datastore(self, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Creating data store %s' % datastore_name)
        self.server.create(datastore_name)
        return True

    def delete_datastore(self, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Deleting data store %s' % datastore_name)
        try:
            self.server.delete(datastore_name)
            return True
        except ResourceNotFound:
            log.info('Data store delete failed.  Data store %s not found' % datastore_name)
            raise NotFound('Data store delete failed.  Data store %s not found' % datastore_name)

    def list_datastores(self):
        log.debug('Listing all data stores')
        dbs = []
        for db in self.server:
            dbs.append(db)
        log.debug('Data stores: %s' % str(dbs))
        return dbs

    def info_datastore(self, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Listing information about data store %s' % datastore_name)
        info = self.server[datastore_name].info()
        log.debug('Data store info: %s' % str(info))
        return info

    def list_objects(self, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        log.debug('Listing all objects in data store %s' % datastore_name)
        objs = []
        for obj in self.server[datastore_name]:
            objs.append(obj)
        log.debug('Objects: %s' % str(objs))
        return objs

    def list_object_revisions(self, object_id, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        db = self.server[datastore_name]
        log.debug('Listing all versions of object %s/%s' % (datastore_name, str(object_id)))
        gen = db.revisions(object_id)
        res = []
        for ent in gen:
            res.append(ent["_rev"])
        log.debug('Versions: %s' % str(res))
        return res

    def create(self, object, datastore_name=""):
        return self.create_doc(object.__dict__)

    def create_doc(self, object, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Creating new object %s/%s' % (datastore_name, object["type_"]))

        # Assign an id to doc (recommended in CouchDB documentation)
        object["_id"] = uuid4().hex

        # Save doc.  CouchDB will assign version to doc.
        res = self.server[datastore_name].save(object)
        log.debug('Create result: %s' % str(res))
        return res

    def read(self, object_id, rev_id="", datastore_name=""):
        doc = self.read_doc(object_id, rev_id, datastore_name)

        # Convert doc into Ion object
        obj = IonObject(doc["type_"], doc)
        log.debug('Ion object: %s' % str(obj))
        return obj

    def read_doc(self, object_id, rev_id="", datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        db = self.server[datastore_name]
        if rev_id == "":
            log.debug('Reading head version of object %s/%s' % (datastore_name, str(object_id)))
            doc = db.get(object_id)
        else:
            log.debug('Reading version %s of object %s/%s' % (str(rev_id), datastore_name, str(object_id)))
            doc = db.get(object_id, rev=rev_id)
        log.debug('Read result: %s' % str(doc))
        return doc

    def update(self, object, datastore_name=""):
        return self.update_doc(object.__dict__)

    def update_doc(self, object, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Saving new version of object %s/%s/%s' % (datastore_name, object["type_"], object["_id"]))
        res = self.server[datastore_name].save(object)
        log.debug('Update result: %s' % str(res))
        return res

    def delete(self, object, datastore_name=""):
        return self.delete_doc(object.__dict__)

    def delete_doc(self, object, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        db = self.server[datastore_name]
        log.debug('Deleting object %s/%s' % (datastore_name, object["_id"]))
        res = db.delete(object)
        log.debug('Delete result: %s' % str(res))
        return True

    def find(self, type, key="", key_value="", datastore_name=""):
        docList = self.find_doc(type, key, key_value, datastore_name)

        results = []
        # Convert each returned doc to its associated Ion object
        for doc in docList:
            obj = IonObject(doc["type_"], doc)
            log.debug('Ion object: %s' % str(obj))
            results.append(obj)

        return results

    def find_doc(self, type, key="", key_value="", datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        db = self.server[datastore_name]

        if key != "" and key_value != "":
            map_fun = '''function(doc) {
                if (doc.type_ === "''' + type + '''" && doc.''' + key + ''' === "''' + key_value + '''") {
                    emit(doc._id,doc);
                }
            }'''
        else:
            map_fun = '''function(doc) {
                if (doc.type_ == "''' + type + '''") {
                    emit(doc._id,doc);
                }
            }'''
        log.debug("map_fun: %s" % str(map_fun))
        try:
            queryList = list(db.query(map_fun))
        except ResourceNotFound:
            raise NotFound("Data store query for type %s with key %s and key_value %s failed" % (type, key, str(key_value)))
        if len(queryList) == 0:
            raise NotFound("Data store query for type %s with key %s and key_value %s returned no objects" % (type, key, str(key_value)))
        results = []
        for row in queryList:
            doc = row.value
            results.append(doc)

        log.debug('Find results: %s' % str(results))
        return results
