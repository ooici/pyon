#!/usr/bin/env python

"""Management of datastores in the container"""

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import get_sys_name
from pyon.util.containers import DotDict
from pyon.util.log import log
from pyon.util.arg_check import validate_true


class DataStore(object):
    """
    Common utilities for datastores
    """
    # Constants for common datastore names
    DS_RESOURCES = "resources"
    DS_OBJECTS = "objects"
    DS_EVENTS = "events"
    DS_DIRECTORY = DS_RESOURCES
    DS_STATE = "state"

    # Enumeration of index profiles for datastores
    DS_PROFILE_LIST = ['OBJECTS', 'RESOURCES', 'DIRECTORY', 'STATE', 'EVENTS', 'EXAMPLES', 'SCIDATA', 'FILESYSTEM', 'BASIC']
    DS_PROFILE = DotDict(zip(DS_PROFILE_LIST, DS_PROFILE_LIST))

    # Maps common datastore logical names to index profiles
    DS_PROFILE_MAPPING = {
        DS_RESOURCES: DS_PROFILE.RESOURCES,
        DS_OBJECTS: DS_PROFILE.OBJECTS,
        DS_EVENTS: DS_PROFILE.EVENTS,
        DS_STATE: DS_PROFILE.STATE,
    }


class DatastoreManager(object):
    """
    Container manager for datastore instances.
    @TODO: Remove caching. This is harmful and no good
    """
    def __init__(self, container=None):
        self._datastores = {}
        self.container = container

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

    @classmethod
    def get_scoped_name(cls, ds_name):
        return ("%s_%s" % (get_sys_name(), ds_name)).lower()

    def get_datastore(self, ds_name, profile=None, config=None):
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

        profile = profile or DataStore.DS_PROFILE_MAPPING.get(ds_name, DataStore.DS_PROFILE.BASIC)

        # Create a datastore instance
        log.info("get_datastore(): Create instance of store '%s' as database=%s (profile=%s)" % (ds_name, scoped_name, profile))
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

