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
from pyon.event.event import EventPublisher, EventSubscriber
from pyon.util.log import log
from pyon.util.containers import get_ion_ts, dict_merge

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

        self.event_pub = None
        self.event_sub = None

        self._init()
        self._init_change_notification()

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.dir_store.close()

    def _init(self):
        # Check for existence of root dir entry.  If not found, call
        # create to initialize top level dir entries.
        try:
            root_de = self.dir_store.read(self.orgname)
        except NotFound as nf:
            self._create()

    def _create(self):
        """
        Method which will create the underlying data store and
        persist an empty Directory object.
        """
        # Persist ROOT Directory object
        root_obj = DirEntry(parent='', key=self.orgname, attributes=dict(sys_name=bootstrap.get_sys_name()))
        root_id,rev = self.dir_store.create(root_obj, self.orgname)

        self._assert_existence("/", "Agents",
                description="Running agents are registered here")

        self._assert_existence("/", "Config",
                description="System configuration is registered here")

        self._assert_existence("/", "Containers",
                description="Running containers are registered here")

        self._assert_existence("/", "ObjectTypes",
                description="ObjectTypes are registered here")

        self._assert_existence("/", "Org",
                description="Org specifics are registered here",
                is_root=self.is_root)

        self._assert_existence("/Org", "Resources",
                description="Shared Org resources are registered here")

        self._assert_existence("/", "ResourceTypes",
                description="Resource types are registered here")

        self._assert_existence("/", "ServiceInterfaces",
                description="Service interface definitions are registered here")

        self._assert_existence("/", "Services",
                description="Service instances are registered here")

    def receive_directory_change_event(self, event_msg, headers):
        # @TODO add support to fold updated config into container config
        pass

    def _init_change_notification(self):
                
        # init change event publisher
        self.event_pub = EventPublisher()
        
        # Register to receive directory changes
        self.event_sub = EventSubscriber(event_type="ContainerConfigModifiedEvent",
                                         origin="Directory",
                                         callback=self.receive_directory_change_event)

    def _get_dn(self, parent, key=None, org=None):
        """
        Returns the distinguished name (= name qualified with org name) for a directory
        path (parent only) or entry (parent + key). Uses the instance org name by default
        if no other org name is specified.
        """
        org = org or self.orgname
        if parent == '/':
            return "%s/%s" % (org, key) if key is not None else org
        elif parent.startswith("/"):
            return "%s%s/%s" % (org, parent,key) if key is not None else "%s%s" % (org, parent)
        else:
            raise BadRequest("Illegal directory parent: %s" % parent)

    def _get_key(self, qname):
        parent_dn, key = qname.rsplit("/", 1)
        return key

    def _assert_existence(self, parent, key, **kwargs):
        """
        Make sure an entry is in the directory.
        @retval True if entry existed
        """
        dn = self._get_dn(parent, key)
        direntry = self._safe_read(dn)
        existed = bool(direntry)
        if not direntry:
            cur_time = get_ion_ts()
            parent_dn = self._get_dn(parent)
            direntry = DirEntry(parent=parent_dn, key=key, attributes=kwargs, ts_created=cur_time, ts_updated=cur_time)
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


    def register(self, parent, key, **kwargs):
        """
        Add/replace an entry to directory below a parent node.
        Note: Does not merge the attribute values of the entry if existing
        """
        if not (parent and key):
            raise BadRequest("Illegal arguments")
        if not type(parent) is str or not parent.startswith("/"):
            raise BadRequest("Illegal arguments: parent")

        dn = self._get_dn(parent, key)
        log.debug("Directory.add(%s): %s" % (dn, kwargs))

        entry_old = None
        direntry = self._safe_read(dn)
        cur_time = get_ion_ts()
        if direntry:
            entry_old = direntry.attributes
            direntry.attributes = kwargs
            direntry.ts_updated=cur_time
            # TODO: This may fail because of concurrent update
            self.dir_store.update(direntry)
        else:
            parent_dn = self._get_dn(parent)
            direntry = DirEntry(parent=parent_dn, key=key, attributes=kwargs, ts_created=cur_time, ts_updated=cur_time)
            self.dir_store.create(direntry, dn)

        if self.event_pub:
            if parent.startswith("/Config"):
                self.event_pub.publish_event(event_type="ContainerConfigModifiedEvent",
                                             origin="Directory")

        return entry_old

    def register_safe(self, parent, key, **kwargs):
        try:
            return self.register(parent, key, **kwargs)
        except Exception as ex:
            log.exception("Error registering key=%s/%s, args=%s" % (parent, key, kwargs))

    def register_mult(self, entries):
        """
        Registers multiple directory entries efficiently in one datastore access.
        Note: this fails of entries are currently existing, so works for create only.
        """
        if type(entries) not in (list, tuple):
            raise BadRequest("Bad entries type")
        de_list = []
        deid_list = []
        cur_time = get_ion_ts()
        for parent, key, attrs in entries:
            parent_dn = self._get_dn(parent)
            de = DirEntry(parent=parent_dn, key=key, attributes=attrs, ts_created=cur_time, ts_updated=cur_time)
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

        if self.event_pub:
            if parent.startswith("/Config"):
                self.event_pub.publish_event(event_type="ContainerConfigModifiedEvent",
                                             origin="Directory")

        return entry_old

    def unregister_safe(self, parent, key):
        try:
            return self.unregister(parent, key)
        except Exception as ex:
            log.exception("Error unregistering key=%s/%s" % (parent, key))

    def find_entries(self, qname='/'):
        if not type(qname) is str or not qname.startswith("/"):
            raise BadRequest("Illegal argument qname: qname=%s" % qname)

        delist = self.dir_store.find_dir_entries(qname)
        return delist

    def find_child_entries(self, parent='/', **kwargs):
        parent_dn = self._get_dn(parent)
        start_key = [parent_dn]
        res = self.dir_store.find_by_view('directory', 'by_parent',
            start_key=start_key, end_key=list(start_key), id_only=False, **kwargs)

        match = [doc for qname, index, doc in res]
        return match

    def remove_child_entries(self, parent, delete_parent=False):
        pass

    def find_by_key(self, subtree='/', key=None, **kwargs):
        """
        Returns a tuple (qname, attributes) for each directory entry that matches the
        given key name.
        """
        if key is None:
            raise BadRequest("Illegal arguments")
        if subtree is None:
            raise BadRequest("Illegal arguments")
        subtree_dn = self._get_dn(subtree)
        start_key = [key]
        if subtree is not None:
            start_key.append(subtree_dn)
        res = self.dir_store.find_by_view('directory', 'by_key',
            start_key=start_key, end_key=start_key, id_only=False, **kwargs)

        match = [(qname, doc.attributes) for qname, index, doc in res]
        return match

    def find_by_value(self, subtree='/', attribute=None, value=None, **kwargs):
        """
        Returns a tuple (qname, attributes) for each directory entry that has an attribute
        with the given value.
        """
        if attribute is None:
            raise BadRequest("Illegal arguments")
        if subtree is None:
            raise BadRequest("Illegal arguments")
        subtree_dn = self._get_dn(subtree)
        start_key = [attribute, value, subtree_dn]
        end_key = [attribute, value, subtree_dn+"ZZZZZZ"]
        res = self.dir_store.find_by_view('directory', 'by_attribute',
                        start_key=start_key, end_key=end_key, id_only=False, **kwargs)

        match = [(qname, doc.attributes) for qname, index, doc in res]
        return match

    # ------------------------------------------
    # Specific directory entry methods


    # ------------------------------------------
    # Internal methods

