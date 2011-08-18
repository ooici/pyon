class DataStoreError(Exception):
    pass

class NotFoundError(DataStoreError):
    pass

class VersionConflictError(DataStoreError):
    pass

class DataStore(object):
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
        List all object types existing in the data store instance.
        """
        pass

    def list_object_revisions(self, objectId, dataStoreName=None):
        """
        Method for itemizing all the versions of a particular object
        known to the data store.
        """
        pass

    def create(self, object, dataStoreName=None):
        """"
        Persist a new Anode object in the data store. An '_id' and initial
        '_rev' value will be added to the doc.
        """
        pass

    def create_doc(self, object, dataStoreName=None):
        """"
        Persist a new raw doc in the data store. An '_id' and initial
        '_rev' value will be added to the doc.
        """
        pass

    def read(self, objectId, rev_id=None, dataStoreName=None):
        """"
        Fetch an Anode object instance.  If rev_id is specified, an attempt
        will be made to return that specific object version.  Otherwise,
        the HEAD version is returned.
        """
        pass

    def read_doc(self, objectId, rev_id=None, dataStoreName=None):
        """"
        Fetch a raw doc instance.  If rev_id is specified, an attempt
        will be made to return that specific doc version.  Otherwise,
        the HEAD version is returned.
        """
        pass

    def update(self, object, dataStoreName=None):
        """
        Update an existing Anode object in the data store.  The '_rev' value
        must exist in the object and must be the most recent known object
        version. If not, a VersionConflictError is thrown.
        """
        pass

    def update_doc(self, object, dataStoreName=None):
        """
        Update an existing raw doc in the data store.  The '_rev' value
        must exist in the doc and must be the most recent known doc
        version. If not, a VersionConflictError is thrown.
        """
        pass

    def delete(self, object, dataStoreName=None):
        """
        Remove all versions of specified Anode object from the data store.
        This method will check the '_rev' value to ensure that the object
        provided is the most recent known object version.  If not, a
        VersionConflictError is thrown.
        """
        pass

    def delete_doc(self, object, dataStoreName=None):
        """
        Remove all versions of specified raw doc from the data store.
        This method will check the '_rev' value to ensure that the doc
        provided is the most recent known doc version.  If not, a
        VersionConflictError is thrown.
        """
        pass

    def find(self, type, key=None, keyValue=None, dataStoreName=None):
        """
        Generic query function that allows searching on:
        Anode object type -- or -- Anode object type and key value
        """
        pass

    def find_doc(self, type, key=None, keyValue=None, dataStoreName=None):
        """
        Generic query function that allows searching on:
        doc type -- or -- doc type and key value
        """
        pass
