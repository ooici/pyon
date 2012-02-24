#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import get_sys_name
from pyon.core.exception import BadRequest, NotFound
from pyon.ion.resource import AT
from pyon.util.containers import DotDict, get_ion_ts, get_safe
from pyon.util.log import log


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


    def create_association(self, subject=None, predicate=None, obj=None, assoc_type=AT.H2H):
        """
        Create an association between two IonObjects with a given predicate
        """
        if not subject or not predicate or not obj:
            raise BadRequest("Association must have all elements set")
        if type(subject) is str:
            subject_id = subject
            subject = self.read(subject_id)
        else:
            if "_id" not in subject or "_rev" not in subject:
                raise BadRequest("Subject id or rev not available")
            subject_id = subject._id
        st = type(subject).__name__

        if type(obj) is str:
            object_id = obj
            obj = self.read(object_id)
        else:
            if "_id" not in obj or "_rev" not in obj:
                raise BadRequest("Object id or rev not available")
            object_id = obj._id
        ot = type(obj).__name__

        assoc_type = assoc_type or AT.H2H
        if not assoc_type in AT:
            raise BadRequest("Unsupported assoc_type: %s" % assoc_type)

        # Check that subject and object type are permitted by association definition
        # Note: Need import here, so that import orders are not screwed up
        from pyon.core.registry import getextends
        from pyon.ion.resource import Predicates
        from pyon.core.bootstrap import IonObject

        try:
            pt = Predicates.get(predicate)
        except AttributeError:
            raise BadRequest("Predicate unknown %s" % predicate)
        if not st in pt['domain']:
            found_st = False
            for domt in pt['domain']:
                if st in getextends(domt):
                    found_st = True
                    break
            if not found_st:
                raise BadRequest("Illegal subject type %s for predicate %s" % (st, predicate))
        if not ot in pt['range']:
            found_ot = False
            for rant in pt['range']:
                if ot in getextends(rant):
                    found_ot = True
                    break
            if not found_ot:
                raise BadRequest("Illegal object type %s for predicate %s" % (ot, predicate))

        # Finally, ensure this isn't a duplicate
        assoc_list = self.find_associations(subject, predicate, obj, assoc_type, False)
        if len(assoc_list) != 0:
            assoc = assoc_list[0]
            if assoc_type == AT.H2H:
                raise BadRequest("Association between %s and %s with predicate %s and type %s already exists" % (subject, obj, predicate, assoc_type))
            else:
                if subject._rev == assoc.srv and object._rev == assoc.orv:
                    raise BadRequest("Association between %s and %s with predicate %s and type %s already exists" % (subject, obj, predicate, assoc_type))

        assoc = IonObject("Association",
                          at=assoc_type,
                          s=subject_id, st=st, srv=subject._rev,
                          p=predicate,
                          o=object_id, ot=ot, orv=obj._rev,
                          ts=get_ion_ts())
        return self.create(assoc)

    def delete_association(self, association=''):
        """
        Delete an association between two IonObjects
        """
        return self.delete(association)

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

    def find_associations(self, subject="", predicate="", obj="", assoc_type=AT.H2H, id_only=True):
        """
        Find associations by subject, predicate, object. Either subject and predicate have
        to be provided or predicate only. Returns either a list of associations or
        a list of association ids.
        """
        pass

    def find_resources(self, restype="", lcstate="", name="", id_only=True):
        if name:
            if lcstate:
                raise BadRequest("find by name does not support lcstate")
            return self.find_res_by_name(name, restype, id_only)
        elif restype and lcstate:
            return self.find_res_by_lcstate(lcstate, restype, id_only)
        elif restype:
            return self.find_res_by_type(restype, lcstate, id_only)
        elif lcstate:
            return self.find_res_by_lcstate(lcstate, restype, id_only)
        elif not restype and not lcstate and not name:
            return self.find_res_by_type(None, None, id_only)

    def _preload_create_doc(self, doc):
        """
        Stealth method used to force pre-defined objects into the data store
        """
        pass

class DatastoreManager(object):
    """
    Container manager for datastore instances.
    """

    persistent = None
    force_clean = None

    def __init__(self):
        self._datastores = {}

    @classmethod
    def get_scoped_name(cls, ds_name):
        return ("%s_%s" % (get_sys_name(), ds_name)).lower()


    def get_datastore(self, ds_name, profile=DataStore.DS_PROFILE.BASIC, config=None):
        """
        Factory method to get a datastore instance from given name, profile and config.
        This is the central point to cache these instances, to decide persistent or mock
        and to force clean the store on first use.
        @param ds_name  Logical name of datastore (will be scoped with sysname)
        @param profile  One of known constants determining the use of the store
        @param config  Override config to use
        """
        assert ds_name, "Must provide ds_name"
        if ds_name in self._datastores:
            log.debug("get_datastore(): Found instance of store '%s'" % ds_name)
            return self._datastores[ds_name]

        scoped_name = DatastoreManager.get_scoped_name(ds_name)

        # Imports here to prevent cyclic module dependency
        from pyon.core.bootstrap import CFG
        config = config or CFG

        if self.persistent is None:
            self.persistent = not bool(get_safe(config, "system.mockdb"))
        if self.force_clean is None:
            self.force_clean = bool(get_safe(config, "system.force_clean"))

        # Create a datastore instance
        log.info("get_datastore(): Create instance of store '%s' {persistent=%s, scoped_name=%s}" % (
            ds_name, self.persistent, scoped_name))
        new_ds = DatastoreManager.get_datastore_instance(ds_name, self.persistent, profile)

        # Clean the store instance
        # TBD: Do we really want to do it here? or make it more manual?
        if self.force_clean:
            log.info("get_datastore(): Force clean store '%s'" % ds_name)
            try:
                new_ds.delete_datastore(scoped_name)
            except NotFound:
                pass

        # Create store if not existing
        if not new_ds.datastore_exists(scoped_name):
            new_ds.create_datastore(scoped_name)
        else:
            if self.persistent:
                # NOTE: This may be expensive if called more than once per container
                # If views exist and are dropped and recreated
                new_ds._define_views(profile=profile, keepviews=True)

        # Set a few standard datastore instance fields
        new_ds.local_name = ds_name
        new_ds.ds_profile = profile

        self._datastores[ds_name] = new_ds

        return new_ds

    @classmethod
    def get_datastore_instance(cls, ds_name, persistent=None, profile=DataStore.DS_PROFILE.BASIC):
        scoped_name = DatastoreManager.get_scoped_name(ds_name)

        # Imports here to prevent cyclic module dependency
        from pyon.core.bootstrap import CFG
        if persistent is None:
            persistent = not bool(get_safe(CFG, "system.mockdb"))

        # Persistent (CouchDB) or MockDB?
        if persistent:
            # Use inline import to prevent circular import dependency
            from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
            new_ds = CouchDB_DataStore(datastore_name=scoped_name, profile=profile)
        else:
            # Use inline import to prevent circular import dependency
            from pyon.datastore.mockdb.mockdb_datastore import MockDB_DataStore
            new_ds = MockDB_DataStore(datastore_name=scoped_name)

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
