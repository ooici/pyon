from anode.datastore.couchdb.couchdb_datastore import CouchDB_DataStore

from anode.datastore.mockdb.mockdb_datastore import MockDB_DataStore

from anode.datastore.datastore import NotFoundError

class DirectoryServiceError(Exception):
    pass

class KeyAlreadyExistsError(DirectoryServiceError):
    pass

class KeyNotFoundError(DirectoryServiceError):
    pass

from anode.core.bootstrap import AnodeObject

class Directory_Service:

    objId = ""
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

        directory_obj = AnodeObject('Directory')
        print "Directory obj: " + str(directory_obj)

        createTuple = self.dataStore.create(directory_obj)
        self.objId = createTuple[0]

    def findDict(self, parent):
        directory = self.dataStore.read(self.objId)
        parentDict = directory.Content

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
        return directory, parentDict

    def add(self, parent, key, value):
        directory, parentDict = self.findDict(parent)

        # Now at end of parent path, add key and value, throwing
        # exception if key already exists
        if key in parentDict:
            raise KeyAlreadyExistsError

        parentDict[key] = value
        self.dataStore.update(directory)
        return value

    def update(self, parent, key, value):
        directory, parentDict = self.findDict(parent)

        # Now at end of parent path, add key and value, throwing
        # exception if key not found
        try:
            val = parentDict[key]
        except KeyError:
            raise KeyNotFoundError

        parentDict[key] = value
        self.dataStore.update(directory)
        return value

    def read(self, parent, key=None):
        directory, parentDict = self.findDict(parent)
        if key == None:
            return parentDict

        try:
            val = parentDict[key]
        except KeyError:
            raise KeyNotFoundError
        return val

    def remove(self, parent, key):
        directory, parentDict = self.findDict(parent)
        try:
            val = parentDict.pop(key)
            self.dataStore.update(directory)
        except KeyError:
            raise KeyNotFoundError
        return val

