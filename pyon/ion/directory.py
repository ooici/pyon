#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core import bootstrap
from pyon.core.bootstrap import IonObject, CFG
from pyon.core.exception import Conflict, NotFound, BadRequest
from pyon.datastore.datastore import DataStore, DatastoreManager
from pyon.util.log import log


class Directory(object):
    """
    Singleton class that uses a data store to provide a directory lookup mechanism.
    """

    # Storage for the instance reference
    __instance = None

    @classmethod
    def get_instance(cls, datastore_manager):
        """
        Create singleton instance
        """
        if Directory.__instance == "NEW":
            log.warn("Somehow __instance is 'NEW' outside of get_instance() singleton code")
            Directory.__instance = None

        if Directory.__instance is None:
            Directory.__instance = "NEW"
            # Create and remember instance
            Directory.__instance = Directory(datastore_manager)
            assert Directory.__instance != "NEW", "Directory was not instantiated"
        return Directory.__instance

    def __init__(self, datastore_manager):
        assert Directory.__instance == "NEW", "Cannot instantiate Directory multiple times"

        # Get an instance of datastore configured as directory.
        # May be persistent or mock, forced clean, with indexes
        self.dir_store = datastore_manager.get_datastore("directory", DataStore.DS_PROFILE.DIRECTORY)

        self._init()

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.dir_store.close()

    def _get_dn(self, parent, key):
        if parent == '/':
            return "/%s" % (key)
        else:
            return "%s/%s" % (parent,key)

    def _init(self):
        self._assert_existence("/", "Agents")
        self._assert_existence("/", "Config")
        self._assert_existence("/", "Containers")
        self._assert_existence("/", "ObjectTypes")
        self._assert_existence("/", "ResourceTypes")
        self._assert_existence("/", "ServiceInterfaces")
        self._assert_existence("/", "Services")

    def _assert_existence(self, parent, key):
        """
        Make sure an entry is in the directory
        """
        dn = self._get_dn(parent, key)
        direntry = self._safe_read(dn)
        if not direntry:
            direntry = IonObject("DirEntry", parent=parent, key=key, attributes={})
            # TODO: This may fail because of concurrent create
            self.dir_store.create(direntry, dn)

    def _safe_read(self, oid):
        try:
            res = self.dir_store.read(oid)
            return res
        except NotFound:
            return None

    def _create(self):
        """
        Method which will create the underlying data store and
        persist an empty Directory object.
        """
        log.debug("Creating data store and Directory")
        self.dir_store.create_datastore()

        # Persist empty Directory object under known name
        self.dir_name = bootstrap.sys_name
        directory_obj = IonObject('Directory', name=self.dir_name)
        dir_id,rev = self.dir_store.create(directory_obj, 'DIR')

        # Persist ROOT Directory object
        root_obj = IonObject('DirEntry', parent='/', key="ROOT", attributes=dict(sys_name=bootstrap.sys_name))
        root_id,rev = self.dir_store.create(root_obj, self._get_dn(root_obj.parent, root_obj.key))

    def register(self, parent, key, **kwargs):
        """
        Add/replace an entry to directory below a parent node.
        Note: Does not merge the attribute values of the entry if existing
        """
        assert parent and key, "Malformed Directory register"
        dn = self._get_dn(parent, key)
        log.debug("Directory.add(%s): %s" % (dn, kwargs))

        entry_old = None
        direntry = self._safe_read(dn)
        if direntry:
            entry_old = direntry.attributes
            direntry.attributes = kwargs
            # TODO: This may fail because of concurrent update
            self.dir_store.update(direntry)
        else:
            direntry = IonObject("DirEntry", parent=parent, key=key, attributes=kwargs)
            # TODO: This may fail because of concurrent create
            self.dir_store.create(direntry, dn)

        return entry_old

    def lookup(self, qualified_key='/'):
        """
        Read entry residing in directory at parent node level.
        """
        log.debug("Reading content at path %s" % qualified_key)
        direntry = self._safe_read(qualified_key)
        return direntry.attributes if direntry else None

    def unregister(self, parent, key):
        """
        Remove entry residing in directory at parent node level.
        """
        dn = self._get_dn(parent, key)
        log.debug("Removing content at path %s" % dn)

        entry_old = None
        direntry = self._safe_read(dn)
        if direntry:
            entry_old = direntry.attributes
            self.dir_store.delete(direntry)

        return entry_old

    def find_entries(self, qname='/'):
        if not str(qname).startswith('/'):
            raise BadRequest("Illegal directory node: qname=%s" % qname)
        delist = self.dir_store.find_dir_entries(qname)
        return delist

