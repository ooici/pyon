import couchdb
import json
import simplejson

from anode.datastore.datastore import DataStore, NotFoundError

from couchdb.http import ResourceNotFound

class CouchDB_DataStore(DataStore):

    def __init__(self, host='localhost', port=5984, dataStoreName='prototype', options=None):
        self.host = host
        self.port = port
        self.dataStoreName = dataStoreName
        connectionStr = "http://" + host + ":" + str(port)
        print 'Connecting to couchDB server: ' + connectionStr
        self.server = couchdb.Server(connectionStr)

    def create_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Creating data store ' + dataStoreName
        self.server.create(dataStoreName)
        return True

    def delete_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Deleting data store ' + dataStoreName
        try:
            self.server.delete(dataStoreName)
            return True
        except ResourceNotFound:
            raise NotFoundError

    def list_datastores(self):
        print 'Listing all data stores'
        dbs = []
        for db in self.server:
            dbs.append(db)
        return dbs

    def info_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Listing information about data store ' + dataStoreName
        info = self.server[dataStoreName].info()
        return info

    def list_objects(self, dataStoreName=None):
        if not dataStoreName:
            dataStoreName = self.dataStoreName
        print 'Listing all objects in data store ' + dataStoreName
        objs = []
        for obj in self.server[dataStoreName]:
            objs.append(obj)
        return objs

    def read_object(self, objectId, rev_id=None, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]
        if rev_id == None:
            print 'Reading head version of object ' + dataStoreName + '/' + str(objectId)
            obj = db.get(objectId)
        else:
            print 'Reading version ' + str(rev_id) + ' of object ' + dataStoreName + '/' + str(objectId)
            obj = db.get(objectId,rev=rev_id)
        return obj

    def list_object_revisions(self, objectId, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]
        print 'Listing all versions of object ' + dataStoreName + '/' + str(objectId)
        gen = db.revisions(objectId)
        res = []
        for ent in gen:
            res.append(ent["_rev"])
        return res

    def write_object(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Saving new version of object ' + dataStoreName + '/' + object["_id"]
        res = self.server[dataStoreName].save(object)
        return res

    def delete_object(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]
        print 'Deleting object ' + dataStoreName + '/' + object["_id"]
        res = db.delete(object)
        return True

    def find_objects(self, type, key=None, keyValue=None, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]

        map_fun = '''function(doc) {
            emit([doc.type_],doc);
        }'''
        query = db.query(map_fun)
        results = []
        for obj in list(query[[type]]):
            try:
                if keyValue == None:
                    results.append(obj.value)
                else:
                    if obj.value[key] == keyValue:
                        results.append(obj.value)
            except KeyError:
                pass

        return results
