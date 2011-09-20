
from anode.core.bootstrap import AnodeObject
from anode.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from anode.core.exception import NotFound
from anode.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from anode.util.log import log

class Directory(object):
    """
    Sample class that uses a data store and Anode object to
    provide a directory lookup mechanism
    """

    obj_id = ""
    objType = "DirectoryObjType_"

    def __init__(self, datastore_name, persistent=False):
        log.debug("Data store name: %s, persistent = %s" % (datastore_name, str(persistent)))
        if persistent:
            self.datastore = CouchDB_DataStore(datastore_name=datastore_name)
        else:
            self.datastore = MockDB_DataStore(datastore_name=datastore_name)

    def delete(self):
        """
        Method to delete directory.  Delete occurs as side effect
        of deleting the underlying data store.
        TODO: Change this functionality in the future?
        """
        log.debug("Deleting data store and Directory")
        try:
            self.datastore.delete_datastore()
        except NotFound:
            pass

    def create(self):
        """
        Method which will creat the underlying data store and
        persist an empty Directory object.
        """
        log.debug("Creating data store and Directory")
        self.datastore.create_datastore()

        # Persist empty Directory object
        directory_obj = AnodeObject('Directory')
        createTuple = self.datastore.create(directory_obj)

        # Save document id for later use
        log.debug("Saving Directory object id %s" % str(createTuple[0]))
        self.obj_id = createTuple[0]

    def find_dict(self, parent):
        """
        Helper method that reads the Directory object from the data store
        and then traverses the dict of dicts to find the desired parent
        dict within the directory hierarchy.
        """
        log.debug("Looking for parent dict %s" % str(parent))
        directory = self.datastore.read(self.obj_id)

        # Get the actual dict of dicts from the object.
        parent_dict = directory.content
        log.debug("Root Directory dict content %s" % str(parent_dict))

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
                        parent_dict = parent_dict[pathElement]
                        log.debug("Intermediate Directory dict content %s" % str(parent_dict))
                    except KeyError:
                        log.debug("Intermediate Directory dict doesn't exist, creating.")
                        parent_dict[pathElement] = {}
                        parent_dict = parent_dict[pathElement]
        return directory, parent_dict

    def add(self, parent, key, value):
        """
        Add a key/value pair to directory below parent
        node level.
        """
        log.debug("Adding key %s and value %s at path %s" % (key, str(value), parent))
        directory, parent_dict = self.find_dict(parent)

        # Add key and value, throwing exception if key already exists.
        if key in parent_dict:
            raise KeyAlreadyExistsError

        parent_dict[key] = value
        self.datastore.update(directory)
        return value

    def update(self, parent, key, value):
        """
        Update key/value pair in directory at parent
        node level.
        """
        log.debug("Updating key %s and value %s at path %s" % (key, str(value), parent))
        directory, parent_dict = self.find_dict(parent)

        # Replace value, throwing exception if key not found.
        try:
            val = parent_dict[key]
        except KeyError:
            raise KeyNotFoundError

        parent_dict[key] = value
        self.datastore.update(directory)
        return value

    def read(self, parent, key=None):
        """
        Read key/value pair(s) residing in directory at parent
        node level.
        """
        log.debug("Reading content at path %s" % str(parent))
        directory, parent_dict = self.find_dict(parent)
        if key is None:
            return parent_dict

        try:
            val = parent_dict[key]
        except KeyError:
            raise KeyNotFoundError
        return val

    def remove(self, parent, key):
        """
        Remove key/value residing in directory at parent
        node level.
        """
        log.debug("Removing content at path %s" % str(parent))
        directory, parent_dict = self.find_dict(parent)
        try:
            val = parent_dict.pop(key)
            self.datastore.update(directory)
        except KeyError:
            raise KeyNotFoundError
        return val

