#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from uuid import uuid4

import couchdb
from couchdb.http import ResourceNotFound

from anode.datastore.datastore import DataStore, NotFoundError
from anode.core.bootstrap import AnodeObject
from anode.util.log import log

class CouchDB_DataStore(DataStore):
    """
    Data store implementation utilizing CouchDB to persist documents.
    For API info, see: http://packages.python.org/CouchDB/client.html#
    """

    def __init__(self, host='localhost', port=5984, dataStoreName='prototype', options=None):
        log.debug('host %s port %d data store name %s options %s' % (host, port, str(dataStoreName), str(options)))
        self.host = host
        self.port = port
        self.dataStoreName = dataStoreName
        connectionStr = "http://" + host + ":" + str(port)
        log.info('Connecting to couchDB server: %s' % connectionStr)
        self.server = couchdb.Server(connectionStr)

    def create_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        log.debug('Creating data store %s' % dataStoreName)
        self.server.create(dataStoreName)
        return True

    def delete_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        log.debug('Deleting data store %s' % dataStoreName)
        try:
            self.server.delete(dataStoreName)
            return True
        except ResourceNotFound:
            log.info('Data store delete failed.  Data store %s not found' % dataStoreName)
            raise NotFoundError

    def list_datastores(self):
        log.debug('Listing all data stores')
        dbs = []
        for db in self.server:
            dbs.append(db)
        log.debug('Data stores: %s' % str(dbs))
        return dbs

    def info_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        log.debug('Listing information about data store %s' % dataStoreName)
        info = self.server[dataStoreName].info()
        log.debug('Data store info: %s' % str(info))
        return info

    def list_objects(self, dataStoreName=None):
        if not dataStoreName:
            dataStoreName = self.dataStoreName
        log.debug('Listing all objects in data store %s' % dataStoreName)
        objs = []
        for obj in self.server[dataStoreName]:
            objs.append(obj)
        log.debug('Objects: %s' % str(objs))
        return objs

    def list_object_revisions(self, objectId, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]
        log.debug('Listing all versions of object %s/%s' % (dataStoreName, str(objectId)))
        gen = db.revisions(objectId)
        res = []
        for ent in gen:
            res.append(ent["_rev"])
        log.debug('Versions: %s' % str(res))
        return res

    def create(self, object, dataStoreName=None):
        return self.create_doc(object.__dict__)

    def create_doc(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        log.debug('Creating new object %s/%s' % (dataStoreName, object["type_"]))

        # Assign an id to doc (recommended in CouchDB documentation)
        object["_id"] = uuid4().hex

        # Save doc.  CouchDB will assign version to doc.
        res = self.server[dataStoreName].save(object)
        log.debug('Create result: %s' % str(res))
        return res

    def read(self, objectId, rev_id=None, dataStoreName=None):
        doc = self.read_doc(objectId, rev_id, dataStoreName)

        # Convert doc into Anode object
        obj = AnodeObject(doc["type_"], doc)
        log.debug('Anode object: %s' % str(obj))
        return obj

    def read_doc(self, objectId, rev_id=None, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]
        if rev_id == None:
            log.debug('Reading head version of object %s/%s' % (dataStoreName, str(objectId)))
            doc = db.get(objectId)
        else:
            log.debug('Reading version %s of object %s/%s' % (str(rev_id), dataStoreName, str(objectId)))
            doc = db.get(objectId, rev=rev_id)
        log.debug('Read result: %s' % str(doc))
        return doc

    def update(self, object, dataStoreName=None):
        return self.update_doc(object.__dict__)

    def update_doc(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        log.debug('Saving new version of object %s/%s/%s' % (dataStoreName, object["type_"], object["_id"]))
        res = self.server[dataStoreName].save(object)
        log.debug('Update result: %s' % str(res))
        return res

    def delete(self, object, dataStoreName=None):
        return self.delete_doc(object.__dict__)

    def delete_doc(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]
        log.debug('Deleting object %s/%s' % (dataStoreName, object["_id"]))
        res = db.delete(object)
        log.debug('Delete result: %s' % str(res))
        return True

    def find(self, type, key=None, keyValue=None, dataStoreName=None):
        docList = self.find_doc(type, key, keyValue, dataStoreName)

        results = []
        # Convert each returned doc to its associated Anode object
        for doc in docList:
            obj = AnodeObject(doc["type_"], doc)
            log.debug('Anode object: %s' % str(obj))
            results.append(obj)

        return results

    def find_doc(self, type, key=None, keyValue=None, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]

        if key != None and keyValue != None:
            map_fun = '''function(doc) {
                if (doc.type_ === "''' + type + '''" && doc.''' + key + ''' === "''' + keyValue + '''") {
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
        queryList = list(db.query(map_fun))
        results = []
        for row in queryList:
            doc = row.value
            results.append(doc)

        log.debug('Find results: %s' % str(results))
        return results
