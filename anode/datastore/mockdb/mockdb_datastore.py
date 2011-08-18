from uuid import uuid4

from anode.core.bootstrap import AnodeObject
from anode.datastore.datastore import DataStore, DataStoreError, VersionConflictError
from anode.util.log import log

class MockDB_DataStore(DataStore):
    """
    Data store implementation utilizing in-memory dict of dicts
    to persist documents.
    """

    def __init__(self, dataStoreName='prototype'):
        self.dataStoreName = dataStoreName
        print 'Creating in-memory dict of dicts that will simulate data stores'
        self.root = {dataStoreName:{}}

    def create_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        log.debug('Creating data store %s' % dataStoreName)
        if dataStoreName not in self.root:
            self.root[dataStoreName] = {}
        return True

    def delete_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        log.debug('Deleting data store %s' % dataStoreName)
        if dataStoreName in self.root:
            del self.root[dataStoreName]
        return True

    def list_datastores(self):
        log.debug('Listing all data stores')
        dsList = self.root.keys()
        log.debug('Data stores: %s' % str(dsList))
        return dsList

    def info_datastore(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        log.debug('Listing information about data store %s' % dataStoreName)
        if dataStoreName in self.root:
            info = 'Data store exists'
        else:
            info = 'Data store does not exist'
        log.debug('Data store info: %s' % str(info))
        return info

    def list_objects(self, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        log.debug('Listing all objects in data store %s' % dataStoreName)
        objs = []
        for key, value in self.root[dataStoreName].items():
            if key.find('_version_counter') == -1 and key.find('_version_') == -1:
                objs.append(key)
        log.debug('Objects: %s' % str(objs))
        return objs

    def list_object_revisions(self, objectId, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        log.debug('Listing all versions of object %s/%s' % (dataStoreName, str(objectId)))
        res = []
        for key, value in self.root[dataStoreName].items():
            if (key.find('_version_counter') == -1
                and (key.find(objectId + '_version_') == 0)):
                res.append(key)
        log.debug('Versions: %s' % str(res))
        return res

    def create(self, object, dataStoreName=None):
        return self.create_doc(object.__dict__)

    def create_doc(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        try:
            dataStoreDict = self.root[dataStoreName]
        except KeyError:
            raise DataStoreException('Data store ' + dataStoreName + ' does not exist.')

        log.debug('Creating new object %s/%s' % (dataStoreName, object["type_"]))

        # Assign an id to doc
        object["_id"] = uuid4().hex
        objectId = object["_id"]

        # Create key for version counter entry.  Will be used
        # on update to increment version number easily.
        versionCounterKey = '__' + objectId + '_version_counter'
        versionCounter = 1

        # Assign initial version to doc
        object["_rev"] = versionCounter

        # Write HEAD, version and version counter dicts
        dataStoreDict[objectId] = object
        dataStoreDict[versionCounterKey] = versionCounter
        dataStoreDict[objectId + '_version_' + str(versionCounter)] = object

        # Return tuple that identifies the id of the new doc and its version
        res = (objectId, str(versionCounter))
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
        try:
            dataStoreDict = self.root[dataStoreName]
        except KeyError:
            raise DataStoreException('Data store ' + dataStoreName + ' does not exist.')

        try:
            key = objectId
            if rev_id == None:
                log.debug('Reading head version of object %s/%s' % (dataStoreName, str(objectId)))
            else:
                log.debug('Reading version %s of object %s/%s' % (str(rev_id), dataStoreName, str(objectId)))
                key += '_version_' + str(rev_id)
            doc = dataStoreDict[key]
        except KeyError:
            raise DataStoreError('Object does not exist.')
        log.debug('Read result: %s' % str(doc))
        return doc

    def update(self, object, dataStoreName=None):
        return self.update_doc(object.__dict__)

    def update_doc(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        try:
            dataStoreDict = self.root[dataStoreName]
        except KeyError:
            raise DataStoreException('Data store ' + dataStoreName + ' does not exist.')

        try:
            objectId = object["_id"]

            # Find the next doc version
            versionCounterKey = '__' + objectId + '_version_counter'
            baseVersion = object["_rev"]
            versionCounter = dataStoreDict[versionCounterKey] + 1
            if baseVersion != versionCounter - 1:
                raise VersionConflictError('Object not based on most current version')
        except KeyError:
            raise DataStoreError("Object missing required _id and/or _rev values")

        log.debug('Saving new version of object %s/%s/%s' % (dataStoreName, object["type_"], object["_id"]))
        object["_rev"] = versionCounter

        # Overwrite HEAD and version counter dicts, add new version dict
        dataStoreDict[objectId] = object
        dataStoreDict[versionCounterKey] = versionCounter
        dataStoreDict[objectId + '_version_' + str(versionCounter)] = object
        res = (objectId, str(versionCounter))
        log.debug('Update result: %s' % str(res))
        return res

    def delete(self, object, dataStoreName=None):
        return self.delete_doc(object.__dict__)

    def delete_doc(self, object, dataStoreName=None):
        if dataStoreName == None:
            dataStoreName = self.dataStoreName
        try:
            dataStoreDict = self.root[dataStoreName]
        except KeyError:
            raise DataStoreException('Data store ' + dataStoreName + ' does not exist.')

        objectId = object["_id"]
        log.debug('Deleting object %s/%s' % (dataStoreName, object["_id"]))
        try:
            if objectId in dataStoreDict.keys():
                # Find all version dicts and delete them
                for key in dataStoreDict.keys():
                    if key.find(objectId + '_version_') == 0:
                        del dataStoreDict[key]
                # Delete the HEAD dict
                del dataStoreDict[objectId]
                # Delete the version counter dict
                del dataStoreDict['__' + objectId + '_version_counter']
        except KeyError:
            raise DataStoreError('Object ' + objectId + ' does not exist.')
        log.debug('Delete result: True')
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
        try:
            dataStoreDict = self.root[dataStoreName]
        except KeyError:
            raise DataStoreException('Data store ' + dataStoreName + ' does not exist.')

        results = []
        logString = "Searching for objects of type: " + type + " in data store " + dataStoreName
        if key != None:
            logString += "where key: " + key + " has value: " + str(keyValue)
        log.debug(logString)

        # Traverse entire data store, checking each HEAD version for equality on:
        #  - type
        #  - optionally, key/value match
        for objId in self.list_objects(dataStoreName):
            try:
                doc = self.read_doc(objId, rev_id=None, dataStoreName=dataStoreName)
                log.debug("Doc: %s" % str(doc))
                if doc["type_"] == type:
                    if keyValue == None:
                        log.debug("No key, appending doc to results")
                        results.append(doc)
                    else:
                        log.debug("Checking key value")
                        if doc[key] == keyValue:
                            log.debug("Key value matches, appending doc to results")
                            results.append(doc)
            except KeyError:
                pass

        log.debug('Find results: %s' % str(results))
        return results
