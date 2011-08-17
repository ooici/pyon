import json
import simplejson

from anode.datastore.datastore import DataStore, DataStoreError, VersionConflictError

from anode.core.bootstrap import AnodeObject

from uuid import uuid4

class MockDB_DataStore(DataStore):

    def __init__(self, dataStoreName='prototype'):
        self.dataStoreName = dataStoreName
        print 'Creating in-memory dict of dicts that will simulate data stores'
        self.root = {dataStoreName:{}}

    def create_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Creating data store ' + dataStoreName
        if dataStoreName not in self.root:
            self.root[dataStoreName] = {}
        return True

    def delete_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Deleting data store ' + dataStoreName
        if dataStoreName in self.root:
            del self.root[dataStoreName]
        return True

    def list_datastores(self):
        print 'Listing all data stores'
        return self.root.keys()

    def info_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Listing information about data store ' + dataStoreName
        if dataStoreName in self.root:
            return 'Data store exists'
        else:
            return 'Data store does not exist'

    def list_objects(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Listing all objects in data store ' + dataStoreName
        objs = []
        for key, value in self.root[dataStoreName].items():
            if key.find('_version_counter') == -1 and key.find('_version_') == -1:
                objs.append(key)
        return objs

    def list_object_revisions(self, objectId, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        print 'Listing all versions of object ' + dataStoreName + '/' + str(objectId)
        objs = []
        for key, value in self.root[dataStoreName].items():
            if key.find('_version_counter') == -1 and (key == objectId or key.find(objectId + '_version_') == 0):
                objs.append(key)
        return objs

    def create(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        try:
            dataStoreDict = self.root[dataStoreName]
        except KeyError:
            raise DataStoreException('Data store ' + dataStoreName + ' does not exist.')

        print 'Creating new object ' + dataStoreName + '/' + object.type_

        # Assign an id
        object._id = uuid4().hex
        objectId = object._id

        # Also add specific version element
        versionCounterKey = '__' + objectId + '_version_counter'
        versionCounter = 1

        object._rev = versionCounter

        # Overwrite HEAD
        dataStoreDict[objectId] = object.__dict__
        dataStoreDict[versionCounterKey] = versionCounter
        dataStoreDict[objectId + '_version_' + str(versionCounter)] = object.__dict__
        return (objectId, str(versionCounter))

    def read(self, objectId, rev_id=None, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        try:
            dataStoreDict = self.root[dataStoreName]
        except KeyError:
            raise DataStoreException('Data store ' + dataStoreName + ' does not exist.')

        try:
            key = objectId
            if rev_id == None:
                print 'Reading head version of object ' + dataStoreName + '/' + str(objectId)
            else:
                print 'Reading version ' + str(rev_id) + ' of object ' + dataStoreName + '/' + str(objectId)
                key += '_version_' + str(rev_id)
            doc = dataStoreDict[key]

            obj = AnodeObject(doc["type_"], doc)
        except KeyError:
            raise DataStoreError('Object does not exist.')
        return obj

    def update(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        try:
            dataStoreDict = self.root[dataStoreName]
        except KeyError:
            raise DataStoreException('Data store ' + dataStoreName + ' does not exist.')

        try:
            objectId = object._id
            versionCounterKey = '__' + objectId + '_version_counter'
            baseVersion = object._rev
            versionCounter = dataStoreDict[versionCounterKey] + 1
            if baseVersion != versionCounter - 1:
                raise VersionConflictError('Object not based on most current version')
        except KeyError:
            raise DataStoreError("Object missing required _id and/or _rev values")

        print 'Saving new version of object ' + dataStoreName + '/' + object.type_ + '/' + object._id
        object._rev = versionCounter

        # Overwrite HEAD
        dataStoreDict[objectId] = object.__dict__
        dataStoreDict[versionCounterKey] = versionCounter
        dataStoreDict[objectId + '_version_' + str(versionCounter)] = object.__dict__
        return (objectId, str(versionCounter))

    def delete(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        try:
            dataStoreDict = self.root[dataStoreName]
        except KeyError:
            raise DataStoreException('Data store ' + dataStoreName + ' does not exist.')
        print 'Deleting object ' + dataStoreName + '/' + object.type_ + '/' + object._id
        objectId = object._id
        try:
            if objectId in dataStoreDict.keys():
                for key in dataStoreDict.keys():
                    if key.find(objectId + '_version_') == 0:
                        del dataStoreDict[key]
                del dataStoreDict[objectId]
                del dataStoreDict['__' + objectId + '_version_counter']
        except KeyError:
            raise DataStoreError('Object ' + objectId + ' does not exist.')
        return True

    def find(self, type, key=None, keyValue=None, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        try:
            dataStoreDict = self.root[dataStoreName]
        except KeyError:
            raise DataStoreException('Data store ' + dataStoreName + ' does not exist.')

        results = []
        print "Searching for objects of type: " + str(type) + " in data store: " + dataStoreName
        if key != None:
            print "where key: " + key + " has value: " + str(keyValue)
        for objId in self.list_objects(dataStoreName):
            try:
                obj = self.read(objId, rev_id=None, dataStoreName=dataStoreName)
                if obj.type_ == type:
                    if keyValue == None:
                        results.append(obj)
                    else:
                        if getattr(obj, key) == keyValue:
                            results.append(obj)
            except KeyError:
                pass

        return results
