
from pyon.core import bootstrap
from pyon.core.bootstrap import IonObject, CFG
from pyon.core.exception import Conflict, NotFound
from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from pyon.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from pyon.util.log import log

class Directory(object):
    """
    Singleton class that uses a data store to
    provide a directory lookup mechanism
    """
    class __impl:

        root_obj_id = ""

        def __init__(self):
            persistent = False
            datastore_name = bootstrap.sys_name + "_directory"
            if 'directory' in CFG:
                directory_cfg = CFG['directory']
                if 'persistent' in directory_cfg:
                    persistent = directory_cfg['persistent']
                if 'datastore_name' in directory_cfg:
                    datastore_name = directory_cfg['datastore_name']
            if persistent:
                self.datastore = CouchDB_DataStore(datastore_name=datastore_name)
            else:
                self.datastore = MockDB_DataStore(datastore_name=datastore_name)
            self._delete()
            self._create()

        def _delete(self):
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

        def _create(self):
            """
            Method which will create the underlying data store and
            persist an empty Directory object.
            """
            log.debug("Creating data store and Directory")
            self.datastore.create_datastore()

            # Persist empty Directory object
            directory_obj = IonObject('Directory')
            createTuple = self.datastore.create(directory_obj)

            # Save document id for later use
            log.debug("Saving Directory object id %s" % str(createTuple[0]))
            self.root_obj_id = createTuple[0]

        def _find_dict(self, parent):
            """
            Helper method that reads the Directory object from the data store
            and then traverses the dict of dicts to find the desired parent
            dict within the directory hierarchy.
            """
            log.debug("Looking for parent dict %s" % str(parent))
            directory = self.datastore.read(self.root_obj_id)

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
            directory, parent_dict = self._find_dict(parent)

            # Add key and value, throwing exception if key already exists.
            if key in parent_dict:
                raise Conflict("Directory entry with key %s already exists", key)

            parent_dict[key] = value
            self.datastore.update(directory)
            return value

        def update(self, parent, key, value):
            """
            Update key/value pair in directory at parent
            node level.
            """
            log.debug("Updating key %s and value %s at path %s" % (key, str(value), parent))
            directory, parent_dict = self._find_dict(parent)

            # Replace value, throwing exception if key not found.
            if key not in parent_dict:
                raise NotFound("Directory entry with key %s does not exist", key)

            parent_dict[key] = value
            self.datastore.update(directory)
            return value

        def read(self, parent, key=None):
            """
            Read key/value pair(s) residing in directory at parent
            node level.
            """
            log.debug("Reading content at path %s" % str(parent))
            directory, parent_dict = self._find_dict(parent)
            if key is None or key == '*':
                return parent_dict

            try:
                val = parent_dict[key]
            except KeyError:
                raise NotFound("Directory entry with key %s does not exist", key)
            return val

        def remove(self, parent, key):
            """
            Remove key/value residing in directory at parent
            node level.
            """
            log.debug("Removing content at path %s" % str(parent))
            directory, parent_dict = self._find_dict(parent)
            try:
                val = parent_dict.pop(key)
                self.datastore.update(directory)
            except KeyError:
                raise NotFound("Directory entry with key %s does not exist", key)
            return val

    # Storage for the instance reference
    __instance = None

    def __init__(self):
        """
        Create singleton instance
        """
        if Directory.__instance is None:
            # Create and remember instance
            Directory.__instance = Directory.__impl()

        # Store instance reference as the only member in the handle
        self.__dict__['_Directory__instance'] = Directory.__instance

    def __getattr__(self, attr):
        """ Delegate access to implementation """
        return getattr(self.__instance, attr)

    def __setattr__(self, attr, value):
        """ Delegate access to implementation """
        return setattr(self.__instance, attr, value)
