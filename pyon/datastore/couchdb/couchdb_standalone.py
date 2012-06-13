#!/usr/bin/env python

__author__ = 'Seman Said'

import couchdb
from couchdb.http import PreconditionFailed, ResourceConflict, ResourceNotFound
from uuid import uuid4


class CouchdbStandalone(object):

    def __init__(self, database_name=None, host='', port='', username='', password='', config=None):
        self.host = host or config['server']['couchdb']['host']
        self.port = str(port or config['server']['couchdb']['port'])
        username = username or config['server']['couchdb']['username'] if config else ''
        password = username or config['server']['couchdb']['password'] if config else ''
        self.authentication = username + ":" + password + "@" if username and password else ""
        self.database_url = "http://" + self.authentication + self.host + ":" + self.port
        self.server = None
        self.database = None
        self.database_name = database_name.lower() if database_name else None

        self._connect()

    def _connect(self):
        try:
            self.server = couchdb.Server(url=self.database_url)
        except Exception as exc:
            raise exc("Couldn't connect to the database: " + self.database_url)

        if self.database_name:
            # Side effect: Create database if not existing (REALLY?)
            try:
                self.database = self.server.create(self.database_name)
            except PreconditionFailed:
                # Failing is still okay. The database is already created
                self.database = self.server[self.database_name]

    def close(self):
        map(lambda x: map(lambda y: y.close(), x), self.server.resource.session.conns.values())
        self.server.resource.session.conns = {}     # just in case we try to reuse this, for some reason

    def list_datastores(self):
        dbs = [db for db in self.server]
        return dbs

    def delete_datastore(self, database_name=None):
        database_name = database_name or self.database_name
        try:
            #print "CouchdbStandalone: Deleting database", database_name
            self.server.delete(database_name)
        except ResourceNotFound:
            raise Exception("Cannot delete database: %s" % database_name)

    def write(self, doc, object_id=None):
        if not self.server or not self.database:
            raise Exception("Not connected to the database")

        if "_id" not in doc:
            doc['_id'] = object_id or uuid4().hex
        try:
            id, version = self.database.save(doc)
        except ResourceConflict:
            raise Exception("Object with id %s already exist" % doc["_id"])
        return id, version

    def create_doc_mult(self, docs, object_ids=None, allow_ids=False):
        if not allow_ids:
            if any(["_id" in doc for doc in docs]):
                raise Exception("Docs must not have '_id'")
            if any(["_rev" in doc for doc in docs]):
                raise Exception("Docs must not have '_rev'")
        if object_ids and len(object_ids) != len(docs):
            raise Exception("Invalid object_ids")
        if type(docs) is not list:
            raise Exception("Invalid type for docs:%s" % type(docs))

        if object_ids:
            for doc, oid in zip(docs, object_ids):
                doc["_id"] = oid
        else:
            for doc in docs:
                doc["_id"] = doc.get("_id", None) or uuid4().hex

        # Update docs.  CouchDB will assign versions to docs.
        res = self.database.update(docs)
        return res

    def read(self, document_id):
        try:
            return self.database[document_id]
        except Exception:
            return None

    def update(self, doc):
        if '_id' not in doc:
            raise Exception("Doc must have '_id'")
        if '_rev' not in doc:
            raise Exception("Doc must have '_rev'")

        self.database[doc['_id']] = doc
        #self.database.update(doc)

    def delete(self, doc):
        return self.database.delete(doc)

    def query(self, map):
        return self.database.query(map)
