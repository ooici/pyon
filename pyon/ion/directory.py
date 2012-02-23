#!/usr/bin/env python

"""Directory is a frontend to a system-wide directory datastore, where system config and definitions live."""

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

import inspect

from pyon.core import bootstrap
from pyon.core.bootstrap import IonObject, CFG
from pyon.core.exception import Conflict, NotFound, BadRequest
from pyon.core.object import IonObjectBase
from pyon.datastore.datastore import DataStore
from pyon.util.log import log

from interface.objects import DirEntry


class Directory(object):
    """
    Class that uses a data store to provide a directory lookup mechanism.
    """

    def __init__(self, datastore_manager=None, orgname=None):
        # Get an instance of datastore configured as directory.
        # May be persistent or mock, forced clean, with indexes
        datastore_manager = datastore_manager or bootstrap.container_instance.datastore_manager
        self.dir_store = datastore_manager.get_datastore("directory", DataStore.DS_PROFILE.DIRECTORY)

        self.orgname = orgname or CFG.system.root_org
        self.is_root = (self.orgname == CFG.system.root_org)

        self._init()

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.dir_store.close()

    def _get_dn(self, parent, key=None, org=None):
        org = org or self.orgname
        if parent == '/':
            return "%s/%s" % (org, key) if key is not None else org
        elif parent.startswith("/"):
            return "%s%s/%s" % (org, parent,key) if key is not None else "%s%s" % (org, parent)
        else:
            raise BadRequest("Illegal directory parent: %s" % parent)

    def _init(self):
        self._assert_existence("/", "Agents",
                description="Running agents are registered here")

        if not self._assert_existence("/", "Config",
                description="System configuration is registered here"):
            if self.is_root:
                self._register_config()

        self._assert_existence("/", "Containers",
                description="Running containers are registered here")

        if not self._assert_existence("/", "ObjectTypes",
                description="ObjectTypes are registered here"):
            if self.is_root:
                self._register_object_types()

        self._assert_existence("/", "Org",
                description="Org specifics are registered here",
                is_root=self.is_root)

        self._assert_existence("/Org", "Resources",
                description="Shared Org resources are registered here")

        self._assert_existence("/", "ResourceTypes",
                description="Resource types are registered here")

        if not self._assert_existence("/", "ServiceInterfaces",
                description="Service interface definitions are registered here"):
            if self.is_root:
                self._register_service_definitions()

        self._assert_existence("/", "Services",
                description="Service instances are registered here")

    def _assert_existence(self, parent, key, **kwargs):
        """
        Make sure an entry is in the directory.
        @retval True if entry existed
        """
        dn = self._get_dn(parent, key)
        direntry = self._safe_read(dn)
        existed = bool(direntry)
        if not direntry:
            direntry = DirEntry(parent=parent, key=key, attributes=kwargs)
            # TODO: This may fail because of concurrent create
            self.dir_store.create(direntry, dn)
        return existed

    def _safe_read(self, key):
        try:
            res = self.dir_store.read(key)
            return res
        except NotFound:
            return None
        except BadRequest:
            return None

    def _create(self):
        """
        Method which will create the underlying data store and
        persist an empty Directory object.
        """
        log.debug("Creating data store and Directory")
        self.dir_store.create_datastore()

        # Persist empty Directory object under known name
        self.dir_name = bootstrap.get_sys_name()
        directory_obj = IonObject('Directory', name=self.dir_name)
        dir_id,rev = self.dir_store.create(directory_obj, 'DIR')

        # Persist ROOT Directory object
        root_obj = DirEntry(parent='/', key="ROOT", attributes=dict(sys_name=bootstrap.get_sys_name()))
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
            direntry = DirEntry(parent=parent, key=key, attributes=kwargs)
            # TODO: This may fail because of concurrent create
            self.dir_store.create(direntry, dn)

        return entry_old

    def register_safe(self, parent, key, **kwargs):
        try:
            return self.register(parent, key, **kwargs)
        except Exception as ex:
            log.exception("Error registering key=%s/%s, args=%s" % (parent, key, kwargs))

    def register_mult(self, entries):
        if type(entries) not in (list, tuple):
            raise BadRequest("Bad type")
        de_list = []
        deid_list = []
        for parent, key, attrs in entries:
            de = DirEntry(parent=parent, key=key, attributes=attrs)
            de_list.append(de)
            dn = self._get_dn(parent, key)
            deid_list.append(dn)
        self.dir_store.create_mult(de_list, deid_list)

    def lookup(self, qualified_key='/'):
        """
        Read entry residing in directory at parent node level.
        """
        log.debug("Reading content at path %s" % qualified_key)
        dn = self._get_dn(qualified_key)
        direntry = self._safe_read(dn)
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

    def unregister_safe(self, parent, key):
        try:
            return self.unregister(parent, key)
        except Exception as ex:
            log.exception("Error unregistering key=%s/%s" % (parent, key))

    def find_entries(self, qname='/'):
        if not str(qname).startswith('/'):
            raise BadRequest("Illegal directory node: qname=%s" % qname)
        delist = self.dir_store.find_dir_entries(qname)
        return delist

    # ------------------------------------------
    # Specific directory entry methods


    # ------------------------------------------
    # Internal methods

    def _register_config(self):
        self.register("/Config", "CFG", **CFG.copy())

    def _load_config(self):
        de = self.lookup("/Config/CFG")
        if not de:
            raise Conflict("Expected /Config/CFG in directory. Correct Org??")

    def _register_service_definitions(self):
        from pyon.core.bootstrap import service_registry
        svc_list = []
        for svcname, svc in service_registry.services.iteritems():
            svc_list.append(("/ServiceInterfaces", svcname, {}))
            #log.debug("Register service: %s" % svcname)
        self.register_mult(svc_list)
        log.info("Registered %d services in directory" % len(svc_list))

    def _register_object_types(self):
        from interface import objects
        delist = []
        for cname, cobj in inspect.getmembers(objects, inspect.isclass):
            if issubclass(cobj, IonObjectBase) and cobj != IonObjectBase:
                parentlist = [parent.__name__ for parent in cobj.__mro__ if parent.__name__ not in ['IonObjectBase','object']]
                delist.append(("/ObjectTypes", cname, dict(schema=cobj._schema, extends=parentlist)))
                #log.debug("Register object: %s" % cname)
        self.register_mult(delist)
        log.info("Registered %d objects in directory" % len(delist))

    def load_definitions(self):
        pass
