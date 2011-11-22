#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

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

        def __init__(self):
            persistent = False
            force_clean = False
            datastore_name = bootstrap.sys_name + "_directory"
            if 'directory' in CFG:
                directory_cfg = CFG['directory']
                if 'persistent' in directory_cfg:
                    persistent = directory_cfg['persistent']
                if 'force_clean' in directory_cfg:
                    force_clean = directory_cfg['force_clean']
            if persistent:
                self.datastore = CouchDB_DataStore(datastore_name=datastore_name)
            else:
                self.datastore = MockDB_DataStore(datastore_name=datastore_name)

            if force_clean:
                self._delete()

            if not self.datastore.datastore_exists(datastore_name):
                self._create()
            self._init()

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

        def _get_dn(self, parent, key):
            if parent == '/':
                return "/%s" % (key)
            else:
                return "%s/%s" % (parent,key)

        def _init(self):
            self._assert_existence("/", "Containers")
            self._assert_existence("/", "ServiceDefinitions")
            self._assert_existence("/", "Services")
            self._assert_existence("/", "ObjectTypes")
            self._assert_existence("/", "ResourceTypes")

        def _assert_existence(self, parent, key):
            dn = self._get_dn(parent, key)
            direntry = self._safe_read(dn)
            if not direntry:
                direntry = IonObject("DirEntry", parent=parent, key=key, attributes={})
                # TODO: This may fail because of concurrent create
                self.datastore.create(direntry, dn)

        def _safe_read(self, oid):
            try:
                res = self.datastore.read(oid)
                return res
            except NotFound:
                return None

        def _create(self):
            """
            Method which will create the underlying data store and
            persist an empty Directory object.
            """
            log.debug("Creating data store and Directory")
            self.datastore.create_datastore()

            # Persist empty Directory object under known name
            self.dir_name = bootstrap.sys_name
            directory_obj = IonObject('Directory', name=self.dir_name)
            dir_id,rev = self.datastore.create(directory_obj, 'DIR')

            # Persist ROOT Directory object
            root_obj = IonObject('DirEntry', parent='/', key="ROOT", attributes=dict(sys_name=bootstrap.sys_name))
            root_id,rev = self.datastore.create(root_obj, self._get_dn(root_obj.parent, root_obj.key))

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
                self.datastore.update(direntry)
            else:
                direntry = IonObject("DirEntry", parent=parent, key=key, attributes=kwargs)
                # TODO: This may fail because of concurrent create
                self.datastore.create(direntry, dn)

            return entry_old

        def read(self, qualified_key='/'):
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
                self.datastore.delete(direntry)

            return entry_old

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
