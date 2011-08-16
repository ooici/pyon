from anode.datastore.couchdb.couchdb_datastore import CouchDB_DataStore

from anode.datastore.mockdb.mockdb_datastore import MockDB_DataStore

from anode.datastore.datastore import NotFoundError

class DirectoryServiceError(Exception):
    pass

class KeyAlreadyExistsError(DirectoryServiceError):
    pass

class KeyNotFoundError(DirectoryServiceError):
    pass

class Directory_Service:

    objName = "DirectoryObj_"
    objType = "DirectoryObjType_"

    def __init__(self, dataStoreName, persistent=False):
        if persistent:
            self.dataStore = CouchDB_DataStore(dataStoreName=dataStoreName)
        else:
            self.dataStore = MockDB_DataStore(dataStoreName=dataStoreName)

    def delete(self):
        try:
            self.dataStore.delete_datastore()
        except NotFoundError:
            pass

    def create(self):
        self.dataStore.create_datastore()

        directory_obj = {}
        directory_obj["_id"] = self.objName
        directory_obj["type_"] = self.objType
        directory_obj["content"] = {}

        self.dataStore.write_object(directory_obj)

    def findDict(self, parent):
        directoryDoc = self.dataStore.read_object(self.objName)
        parentDict = directoryDoc["content"]

        if parent == '/':
            # We're already at the root
            pass
        else:
            for pathElement in parent.split('/'):
                if pathElement == '':
                    # slash separator, ignore
                    pass
                else:
                    try:
                        parentDict = parentDict[pathElement]
                    except KeyError:
                        parentDict[pathElement] = {}
                        parentDict = parentDict[pathElement]
        return directoryDoc, parentDict

    def add(self, parent, key, value):
        directoryDoc, parentDict = self.findDict(parent)

        # Now at end of parent path, add key and value, throwing
        # exception if key already exists
        try:
            if key in parentDict:
                raise KeyAlreadyExistsError
        except KeyError:
            pass

        parentDict[key] = value
        self.dataStore.write_object(directoryDoc)
        return value

    def update(self, parent, key, value):
        directoryDoc, parentDict = self.findDict(parent)

        # Now at end of parent path, add key and value, throwing
        # exception if key not found
        try:
            val = parentDict[key]
        except KeyError:
            raise KeyNotFoundError

        parentDict[key] = value
        self.dataStore.write_object(directoryDoc)
        return value

    def read(self, parent, key=None):
        directoryDoc, parentDict = self.findDict(parent)
        if key == None:
            return parentDict

        try:
            val = parentDict[key]
        except KeyError:
            raise KeyNotFoundError
        return val

    def remove(self, parent, key):
        directoryDoc, parentDict = self.findDict(parent)
        try:
            val = parentDict.pop(key)
            self.dataStore.write_object(directoryDoc)
        except KeyError:
            raise KeyNotFoundError
        return val

