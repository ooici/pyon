#!/usr/bin/env python


__author__ = 'Seman'
__license__ = 'Apache 2.0'
import sys
import hashlib
import os
import couchdb
from uuid import uuid4
from couchdb.client import ViewResults, Row
from couchdb.http import PreconditionFailed, ResourceConflict, ResourceNotFound
import exceptions
import yaml


class CouchdbStandalone:

    def __init__(self, database_name, host = '', port = '', username = '', password = ''):
        sc = SystemConfiguration()

        self.host = host or sc.config['server']['couchdb']['host'] 
        self.port = port or str(sc.config['server']['couchdb']['port'])
        self.authentication = username + ":" + password + "@" if username and password else ""
        self.database_url = "http://" + self.authentication + self.host + ":" + self.port
        self.server = False
        self.database = False
        self.database_name = database_name 

        self._connect()

    def _connect(self):
        try:
            self.server = couchdb.Server(url=self.database_url)
        except Exception as e:
            raise e("Couldn't connect to the database: " + self.database_url)

        #Create database
        try:
            self.database = self.server.create(self.database_name)
        except PreconditionFailed:
            # Failing is still okay. The database is already created
            self.database = self.server[self.database_name]

    def close(self):
        pass

    def delete_database (self):
        try:
            print "deleteing ", self.database_name   
            self.server.delete(self.database_name)
        except ResourceNotFound:
            raise Exception("Database name not found")

    def write(self, doc, object_id=None):
        if not self.server or not self.database:
            raise Exception("Not connected to the database")

        doc['_id'] = object_id or uuid4().hex
        try:
            res = self.database.save(doc)
        except ResourceConflict:
            raise Exception("Object with id %s already exist" % doc["_id"])
        id, version = res
        return (id, version)


    def read(self, document_id):
        try:
            return self.database[document_id]
        except:
            return None

    def update(self, doc):
        if '_id' not in doc:
            raise Exception("Doc must have '_id'")
        if '_rev' not in doc:
            raise Exception("Doc must have '_rev'")

        self.database[doc['_id']] = doc
        #self.database.update(doc)

    def delete_doc(self, doc):
        return self.database.delete(doc)

    def query (self, map):
        return self.database.query(map)


class SystemConfiguration:
    config = "" 

    def __init__ (self):
        config_file_path = 'res/config/pyon_min_boot.yml'
        if os.path.exists(config_file_path):
            with open(config_file_path) as f:
                file_content = f.read()
        else:
            raise Exception ("Couldn't find config file: " + config_file_path)
        self.config = yaml.load(file_content)
        

