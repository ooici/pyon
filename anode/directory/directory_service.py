
class DirectoryServiceError(Exception):
    pass

class KeyAlreadyExistsError(DirectoryServiceError):
    pass

class KeyNotFoundError(DirectoryServiceError):
    pass

from anode.core.bootstrap import AnodeObject
from anode.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from anode.datastore.datastore import NotFoundError
from anode.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from anode.util.log import log

class Directory_Service(object):
    """
    Sample class that uses a data store and Anode object to
    provide a directory lookup mechanism
    """

    objId = ""
    objType = "DirectoryObjType_"

    def __init__(self, dataStoreName, persistent=False):
        log.debug("Data store name: %s, persistent = %s" % (dataStoreName, str(persistent)))
        if persistent:
            self.dataStore = CouchDB_DataStore(dataStoreName=dataStoreName)
        else:
            self.dataStore = MockDB_DataStore(dataStoreName=dataStoreName)

    def delete(self):
        """
        Method to delete directory.  Delete occurs as side effect
        of deleting the underlying data store.
        TODO: Change this functionality in the future?
        """
        log.debug("Deleting data store and Directory")
        try:
            self.dataStore.delete_datastore()
        except NotFoundError:
            pass

    def create(self):
        """
        Method which will creat the underlying data store and
        persist an empty Directory object.
        """
        log.debug("Creating data store and Directory")
        self.dataStore.create_datastore()

        # Persist empty Directory object
        directory_obj = AnodeObject('Directory')
        createTuple = self.dataStore.create(directory_obj)

        # Save document id for later use
        log.debug("Saving Directory object id %s" % str(createTuple[0]))
        self.objId = createTuple[0]

    def findDict(self, parent):
        """
        Helper method that reads the Directory object from the data store
        and then traverses the dict of dicts to find the desired parent
        dict within the directory hierarchy.
        """
        log.debug("Looking for parent dict %s" % str(parent))
        directory = self.dataStore.read(self.objId)

        # Get the actual dict of dicts from the object.
        parentDict = directory.Content
        log.debug("Root Directory dict content %s" % str(parentDict))

        # Traverse as necessary.
        if parent == '/':
            # We're already at the root.
            log.debug("Root Directory is desired parent.")
            pass
        else:
            for pathElement in parent.split('/'):
                if pathElement == '':
                    # slash separator, ignore.
                    pass
                else:
                    log.debug("Intermediate Directory path element %s" % str(pathElement))
                    try:
                        parentDict = parentDict[pathElement]
                        log.debug("Intermediate Directory dict content %s" % str(parentDict))
                    except KeyError:
                        log.debug("Intermediate Directory dict doesn't exist, creating.")
                        parentDict[pathElement] = {}
                        parentDict = parentDict[pathElement]
        return directory, parentDict

    def add(self, parent, key, value):
        """
        Add a key/value pair to directory below parent
        node level.
        """
        log.debug("Adding key %s and value %s at path %s" % (key, str(value), parent))
        directory, parentDict = self.findDict(parent)

        # Add key and value, throwing exception if key already exists.
        if key in parentDict:
            raise KeyAlreadyExistsError

        parentDict[key] = value
        self.dataStore.update(directory)
        return value

    def update(self, parent, key, value):
        """
        Update key/value pair in directory at parent
        node level.
        """
        log.debug("Updating key %s and value %s at path %s" % (key, str(value), parent))
        directory, parentDict = self.findDict(parent)

        # Replace value, throwing exception if key not found.
        try:
            val = parentDict[key]
        except KeyError:
            raise KeyNotFoundError

        parentDict[key] = value
        self.dataStore.update(directory)
        return value

    def read(self, parent, key=None):
        """
        Read key/value pair(s) residing in directory at parent
        node level.
        """
        log.debug("Reading content at path %s" % str(parent))
        directory, parentDict = self.findDict(parent)
        if key == None:
            return parentDict

        try:
            val = parentDict[key]
        except KeyError:
            raise KeyNotFoundError
        return val

    def remove(self, parent, key):
        """
        Remove key/value residing in directory at parent
        node level.
        """
        log.debug("Removing content at path %s" % str(parent))
        directory, parentDict = self.findDict(parent)
        try:
            val = parentDict.pop(key)
            self.dataStore.update(directory)
        except KeyError:
            raise KeyNotFoundError
        return val

