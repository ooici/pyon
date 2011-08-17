import couchdb

from anode.datastore.datastore import DataStore, NotFoundError

from couchdb.http import ResourceNotFound

from anode.core.bootstrap import AnodeObject

from uuid import uuid4

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

    def create(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Creating new object ' + dataStoreName + '/' + object.type_
        object._id = uuid4().hex
        res = self.server[dataStoreName].save(object.__dict__)
        return res

    def read(self, objectId, rev_id=None, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]
        if rev_id == None:
            print 'Reading head version of object ' + dataStoreName + '/' + str(objectId)
            doc = db.get(objectId)
        else:
            print 'Reading version ' + str(rev_id) + ' of object ' + dataStoreName + '/' + str(objectId)
            doc = db.get(objectId, rev=rev_id)
        obj = AnodeObject(doc["type_"], doc)
        return obj

    def update(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Saving new version of object ' + dataStoreName + '/' + object.type_ + '/' + object._id
        res = self.server[dataStoreName].save(object.__dict__)
        return res

    def delete(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]
        print 'Deleting object ' + dataStoreName + '/' + object._id
        res = db.delete(object.__dict__)
        return True

    def find(self, type, key=None, keyValue=None, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        db = self.server[dataStoreName]

        map_fun = '''function(doc) {
            emit([doc.type_],doc);
        }'''
        query = db.query(map_fun)
        results = []
        print "Searching for objects of type: " + str(type) + " in data store: " + dataStoreName
        if key != None:
            print "where key: " + key + " has value: " + str(keyValue)
        for row in list(query[[type]]):
            doc = row.value
            try:
                if keyValue == None:
                    obj = AnodeObject(doc["type_"], doc)
                    results.append(obj)
                else:
                    if doc[key] == keyValue:
                        obj = AnodeObject(doc["type_"], doc)
                        results.append(obj)
            except KeyError:
                pass

        return results