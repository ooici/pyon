#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import get_sys_name
from pyon.util.containers import DotDict
from pyon.util.log import log
from pyon.util.arg_check import validate_true


class DataStore(object):
    """
    Think of this class as a database server.
    Every instance is a different schema.
    Every type of ION object is a table
    """
    DS_PROFILE_LIST = ['OBJECTS','RESOURCES','DIRECTORY','STATE','EVENTS','EXAMPLES','SCIDATA','BASIC']
    DS_PROFILE = DotDict(zip(DS_PROFILE_LIST, DS_PROFILE_LIST))

    def close(self):
        """
        Close any connections required for this datastore.
        """
        pass

    def create_datastore(self, datastore_name="", create_indexes=True):
        """
        Create a data store with the given name.  This is
        equivalent to creating a database on a database server.
        """
        pass

    def delete_datastore(self, datastore_name=""):
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

    def info_datastore(self, datastore_name=""):
        """
        List information about a data store.  Content may vary based
        on data store type.
        """
        pass

    def datastore_exists(self, datastore_name=""):
        """
        Indicates whether named data store currently exists.
        """
        pass

    def list_objects(self, datastore_name=""):
        """
        List all object types existing in the data store instance.
        """
        pass

    def list_object_revisions(self, object_id, datastore_name=""):
        """
        Method for itemizing all the versions of a particular object
        known to the data store.
        """
        pass

    def create(self, obj, object_id=None, datastore_name=""):
        """"
        Persist a new Ion object in the data store. An '_id' and initial
        '_rev' value will be added to the doc.
        """
        pass

    def create_doc(self, obj, object_id=None, datastore_name=""):
        """"
        Persist a new raw doc in the data store. An '_id' and initial
        '_rev' value will be added to the doc.
        """
        pass

    def create_mult(self, objects, object_ids=None):
        """
        Create more than one ION object.
        """
        pass

    def create_doc_mult(self, docs, object_ids=None):
        """
        Create multiple raw docs.
        Returns list of (Success, Oid, rev)
        """
        pass

    def read(self, object_id, rev_id="", datastore_name=""):
        """"
        Fetch an Ion object instance.  If rev_id is specified, an attempt
        will be made to return that specific object version.  Otherwise,
        the HEAD version is returned.
        """
        pass

    def read_doc(self, object_id, rev_id="", datastore_name=""):
        """"
        Fetch a raw doc instance.  If rev_id is specified, an attempt
        will be made to return that specific doc version.  Otherwise,
        the HEAD version is returned.
        """
        pass

    def read_mult(self, object_ids, datastore_name=""):
        """"
        Fetch multiple Ion object instances, HEAD rev.
        """
        pass

    def read_doc_mult(self, object_ids, datastore_name=""):
        """"
        Fetch a raw doc instances, HEAD rev.
        """
        pass

    def update(self, obj, datastore_name=""):
        """
        Update an existing Ion object in the data store.  The '_rev' value
        must exist in the object and must be the most recent known object
        version. If not, a Conflict exception is thrown.
        """
        pass

    def update_doc(self, obj, datastore_name=""):
        """
        Update an existing raw doc in the data store.  The '_rev' value
        must exist in the doc and must be the most recent known doc
        version. If not, a Conflict exception is thrown.
        """
        pass

    def delete(self, obj, datastore_name=""):
        """
        Remove all versions of specified Ion object from the data store.
        This method will check the '_rev' value to ensure that the object
        provided is the most recent known object version.  If not, a
        Conflict exception is thrown.
        If object id (str) is given instead of an object, deletes the
        object with the given id.
        """
        pass

    def delete_doc(self, obj, datastore_name=""):
        """
        Remove all versions of specified raw doc from the data store.
        This method will check the '_rev' value to ensure that the doc
        provided is the most recent known doc version.  If not, a
        Conflict exception is thrown.
        If object id (str) is given instead of an object, deletes the
        object with the given id.
        """
        pass

    def find_objects(self, subject, predicate="", object_type="", id_only=False):
        """
        Find objects (or object ids) by association from a given subject or subject id (if str).
        Returns a tuple (list_of_objects, list_of_associations) if id_only == False, or
        (list_of_object_ids, list_of_associations) if id_only == True.
        Predicate and object_type are optional to narrow the search down. Object_type can only
        be set if predicate is set as well.
        """
        pass

    def find_subjects(self, subject_type="", predicate="", obj="", id_only=False):
        """
        Find subjects (or subject ids) by association from a given object or object id (if str).
        Returns a tuple (list_of_subjects, list_of_associations) if id_only == False, or
        (list_of_subject_ids, list_of_associations) if id_only == True.
        Predicate and subject_type are optional to narrow the search down. Subject_type can only
        be set if predicate is set as well.
        """
        pass

    def find_associations(self, subject="", predicate="", obj="", assoc_type='H2H', id_only=True):
        """
        Find associations by subject, predicate, object. Either subject and predicate have
        to be provided or predicate only. Returns either a list of associations or
        a list of association ids.
        """
        pass

    def _preload_create_doc(self, doc):
        """
        Stealth method used to force pre-defined objects into the data store
        """
        pass

class DatastoreManager(object):
    """
    Container manager for datastore instances.
    @TODO: Remove caching. This is harmful and no good
    """
    def __init__(self):
        self._datastores = {}

    @classmethod
    def get_scoped_name(cls, ds_name):
        return ("%s_%s" % (get_sys_name(), ds_name)).lower()

    def get_datastore(self, ds_name, profile=DataStore.DS_PROFILE.BASIC, config=None):
        """
        Factory method to get a datastore instance from given name, profile and config.
        @param ds_name  Logical name of datastore (will be scoped with sysname)
        @param profile  One of known constants determining the use of the store
        @param config  Override config to use
        """
        validate_true(ds_name, 'ds_name must be provided')
        if ds_name in self._datastores:
            log.debug("get_datastore(): Found instance of store '%s'" % ds_name)
            return self._datastores[ds_name]

        scoped_name = DatastoreManager.get_scoped_name(ds_name)

        # Create a datastore instance
        log.info("get_datastore(): Create instance of store '%s' as database=%s" % (ds_name, scoped_name))
        new_ds = DatastoreManager.get_datastore_instance(ds_name, profile)

        # Create store if not existing
        if not new_ds.datastore_exists(scoped_name):
            new_ds.create_datastore(scoped_name, create_indexes=True, profile=profile)
        else:
            # NOTE: This may be expensive if called more than once per container
            # If views exist and are dropped and recreated
            new_ds._define_views(profile=profile, keepviews=True)

        # Set a few standard datastore instance fields
        new_ds.local_name = ds_name
        new_ds.ds_profile = profile

        self._datastores[ds_name] = new_ds

        return new_ds

    @classmethod
    def get_datastore_instance(cls, ds_name, profile=DataStore.DS_PROFILE.BASIC):
        scoped_name = DatastoreManager.get_scoped_name(ds_name)

        # Use inline import to prevent circular import dependency
        from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
        new_ds = CouchDB_DataStore(datastore_name=scoped_name, profile=profile)

        return new_ds

    @classmethod
    def exists(cls, ds_name, scoped=True, config=None):
        if scoped:
            ds_name = DatastoreManager.get_scoped_name(ds_name)
        generic_ds = cls.get_datastore_instance("")
        return generic_ds.datastore_exists(ds_name)

    def start(self):
        pass

    def stop(self):
        log.debug("DatastoreManager.stop() [%d datastores]", len(self._datastores))
        for x in self._datastores.itervalues():
            try:
                x.close()
            except Exception as ex:
                log.exception("Error closing datastore")

        self._datastores = {}
