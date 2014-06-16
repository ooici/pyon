#!/usr/bin/env python

"""Management of datastores in the container"""

__author__ = 'Thomas R. Lennan, Michael Meisinger'


from pyon.core.bootstrap import get_sys_name, CFG
from pyon.datastore.datastore_common import DatastoreFactory, DataStore
from pyon.util.log import log
from pyon.util.arg_check import validate_true


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
        some_datastore = None
        for ds in self._datastores.itervalues():
            if not some_datastore and hasattr(ds, "close_all"):
                some_datastore = ds
            try:
                ds.close()
            except Exception as ex:
                log.exception("Error closing datastore")

        self._datastores = {}
        if some_datastore:
            try:
                some_datastore.close_all()
            except Exception as ex:
                log.exception("Error closing datastore")

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
        if (ds_name, profile) in self._datastores:
            log.debug("get_datastore(): Found instance of store '%s' (profile=%s)" % (ds_name, profile))
            return self._datastores[(ds_name, profile)]

        # Create a datastore instance
        log.info("get_datastore(): Create instance of store '%s' as database=%s (profile=%s)" % (ds_name, ds_name, profile))
        new_ds = DatastoreManager.get_datastore_instance(ds_name, profile)

        # Create store if not existing
        if not new_ds.datastore_exists(ds_name):
            new_ds.create_datastore(ds_name, create_indexes=True, profile=profile)
        else:
            # NOTE: This may be expensive if called more than once per container
            # If views exist and are dropped and recreated
            new_ds.define_profile_views(profile=profile, keepviews=True)

        # Set a few standard datastore instance fields
        new_ds.local_name = ds_name
        new_ds.ds_profile = profile

        self._datastores[(ds_name, profile)] = new_ds

        return new_ds

    @classmethod
    def get_datastore_instance(cls, ds_name, profile=None):
        profile = profile or DataStore.DS_PROFILE_MAPPING.get(ds_name, DataStore.DS_PROFILE.BASIC)
        new_ds = DatastoreFactory.get_datastore(datastore_name=ds_name, profile=profile, scope=get_sys_name(),
                                                config=CFG, variant=DatastoreFactory.DS_FULL)

        return new_ds

    @classmethod
    def exists(cls, ds_name, scoped=True, config=None):
        if scoped:
            ds_name = DatastoreManager.get_scoped_name(ds_name)
        generic_ds = cls.get_datastore_instance("")
        return generic_ds.datastore_exists(ds_name)

