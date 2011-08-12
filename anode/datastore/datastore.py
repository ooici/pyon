class DataStoreError(Exception):
    pass

class NotFoundError(DataStoreError):
    pass

class VersionConflictError(DataStoreError):
    pass

class DataStore:
    """
    Think of this class as a database server.
    """

    def create_datastore(self, dataStoreName=None):
        """
        Create a data store with the given name.  This is
        equivalent to creating a database on a database server.
        """
        pass

    def delete_datastore(self, dataStoreName=None):
        """
        Delete the data store with the given name.  This is
        equivalent to deleting a database from a database server.
        """
        pass

    def list_datastores(self):
        """
        List all data stores within this data store server. This is
        equivalent to listing all databases hosted on a database server.
        """
        pass

    def info_datastore(self, dataStoreName=None):
        """
        List information about a data store.  Content may vary based
        on data store type.
        """
        pass

    def list_objects(self, dataStoreName=None):
        """
        List all data types existing in the data store instance.
        """
        pass

    def read_object(self, objectId, rev_id=None, dataStoreName=None):
        """"
        Fetch an object instance.  If rev_id is specified, an attempt
        will be made to return that specific object version.  Otherwise,
        the HEAD version is returned.
        """
        pass

    def list_object_revisions(self, objectId, dataStoreName=None):
        """
        Method for itemizing all the versions of a particular object
        known to the data source.
        """
        pass

    def write_object(self, object, dataStoreName=None):
        """
        Persist an object to the data store.  If this is a new object,
        an initial '_rev' value will be added to the doc.  If this is
        an object update, the '_rev' value must exist in the object.
        This method will check the '_rev' value to ensure that the object
        being written is based on the most recent known object version.
        If not, a VersionConflictError is thrown.
        """
        pass

    def delete_object(self, object, dataStoreName=None):
        """
        Remove all versions of specified type from the data store.
        This method will check the '_rev' value to ensure that the object
        provided is the most recent known object version.  If not, a
        VersionConflictError is thrown.
        """
        pass

    def find_objects(self, type, key=None, keyValue=None, dataStoreName=None):
        """
        Generic query function that allows searching on:
        object type -- or -- object type and key value
        """
        pass