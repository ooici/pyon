#!/usr/bin/env python

__author__ = 'Seman Said, Michael Meisinger'

from pyon.core.exception import NotFound, BadRequest, Inconsistent
from pyon.datastore.datastore_common import DatastoreFactory, DataStore
from pyon.ion.identifier import create_unique_directory_id
from pyon.util.containers import get_ion_ts, get_default_sysname, get_safe


class DirectoryStandalone(object):
    """
    Directory service standalone class
    """
    def __init__(self, sysname=None, orgname=None, config=None):
        self.orgname = orgname or get_safe(config, 'system.root_org', 'ION')
        sysname = sysname or get_default_sysname()
        self.datastore_name = "resources"
        self.datastore = DatastoreFactory.get_datastore(datastore_name=self.datastore_name, config=config,
                                                        scope=sysname, profile=DataStore.DS_PROFILE.DIRECTORY,
                                                        variant=DatastoreFactory.DS_BASE)

    def close(self):
        self.datastore.close()
        self.datastore = None

    def _get_path(self, parent, key):
        """
        Returns the qualified directory path for a directory entry.
        """
        if parent == "/":
            return parent + key
        elif parent.startswith("/"):
            return parent + "/" + key
        else:
            raise BadRequest("Illegal parent: %s" % parent)

    def _get_key(self, path):
        """
        Returns the key from a qualified directory path
        """
        parent, key = path.rsplit("/", 1)
        return key

    def _read_by_path(self, path, orgname=None):
        """
        Given a qualified path, find entry in directory and return DirEntry
        document or None if not found
        """
        if path is None:
            raise BadRequest("Illegal arguments")
        orgname = orgname or self.orgname
        parent, key = path.rsplit("/", 1)
        parent = parent or "/"
        find_key = [orgname, key, parent]
        view_res = self.datastore.find_docs_by_view('directory', 'by_key', key=find_key, id_only=True)

        if len(view_res) > 1:
            raise Inconsistent("More than one directory entry found for key %s" % path)
        elif view_res:
            return view_res[0][2]  # First value
        return None

    def lookup(self, parent, key=None, return_entry=False):
        """
        Read entry residing in directory at parent node level.
        """
        path = self._get_path(parent, key) if key else parent
        direntry = self._read_by_path(path)
        if return_entry:
            return direntry
        else:
            return direntry['attributes'] if direntry else None

    def _get_unique_parents(self, entry_list):
        """Returns a sorted, unique list of parents of DirEntries (excluding the root /)"""
        if entry_list and type(entry_list) not in (list, tuple):
            entry_list = [entry_list]
        parents = set()
        for entry in entry_list:
            parents.add(entry.get("parent", "/"))
        if "/" in parents:
            parents.remove("/")
        return sorted(parents)

    def _ensure_parents_exist(self, entry_list, create=True):
        parents_list = self._get_unique_parents(entry_list)
        pe_list = []
        try:
            for parent in parents_list:
                pe = self.lookup(parent)
                if pe is None:
                    pp, pk = parent.rsplit("/", 1)
                    doc = self._create_dir_entry(object_id=create_unique_directory_id(), parent=pp, key=pk)
                    pe_list.append(doc)
                    if create:
                        self.datastore.create_doc(doc)
        except Exception as ex:
            print "_ensure_parents_exist(): Error creating directory parents", ex
        return pe_list

    def register(self, parent, key, create_only=False, **kwargs):
        """
        Add/replace an entry within directory, below a parent node or "/".
        Note: Replaces (not merges) the attribute values of the entry if existing
        @retval  DirEntry if previously existing
        """
        if not (parent and key):
            raise BadRequest("Illegal arguments")
        if not type(parent) is str or not parent.startswith("/"):
            raise BadRequest("Illegal arguments: parent")

        dn = self._get_path(parent, key)

        entry_old = None
        direntry = self._read_by_path(dn)
        cur_time = get_ion_ts()

        if direntry and create_only:
            # We only wanted to make sure entry exists. Do not change
            return direntry
        elif direntry:
            # Change existing entry's attributes
            entry_old = direntry.get('attributes')
            direntry['attributes'] = kwargs
            direntry['ts_updated'] = cur_time
            self.datastore.update_doc(direntry)
        else:
            doc = self._create_dir_entry(object_id=create_unique_directory_id(), parent=parent, key=key,
                attributes=kwargs)
            self._ensure_parents_exist([doc])
            self.datastore.create_doc(doc)

        return entry_old

    def register_mult(self, entries):
        """
        Registers multiple directory entries efficiently in one datastore access.
        Note: this fails of entries are currently existing, so works for create only.
        """
        if type(entries) not in (list, tuple):
            raise BadRequest("Bad entries type")
        de_list = []
        cur_time = get_ion_ts()
        for parent, key, attrs in entries:
            de = self._create_dir_entry(object_id=create_unique_directory_id(), parent=parent, key=key,
                attributes=attrs, ts_created=cur_time, ts_updated=cur_time)
            de_list.append(de)
        pe_list = self._ensure_parents_exist(de_list, create=False)
        self.datastore.create_doc_mult(pe_list + de_list)

    def _update_dir_entry(self, doc, parent, key, attributes=None, ts_updated=''):
        doc['attributes'] = attributes or {}
        doc['key'] = key
        doc['parent'] = parent
        doc['ts_updated'] = ts_updated or get_ion_ts()
        return doc

    def _create_dir_entry(self, object_id,  parent, key, attributes=None, ts_created='', ts_updated=''):
        doc = {}
        doc['_id'] = object_id
        doc['type_'] = 'DirEntry'
        doc['attributes'] = attributes or {}
        doc['key'] = key
        doc['parent'] = parent if parent else "/"
        doc['org'] = self.orgname
        doc['ts_created'] = ts_created or get_ion_ts()
        doc['ts_updated'] = ts_updated or get_ion_ts()
        return doc

    def find_child_entries(self, parent='/', direct_only=True, **kwargs):
        """
        Return all child entries (ordered by path) for the given parent path.
        Does not return the parent itself. Optionally returns child of child entries.
        Additional kwargs are applied to constrain the search results (limit, descending, skip).
        @param parent  Path to parent (must start with "/")
        @param direct_only  If False, includes child of child entries
        @retval  A list of DirEntry objects for the matches
        """
        if not type(parent) is str or not parent.startswith("/"):
            raise BadRequest("Illegal argument parent: %s" % parent)
        if direct_only:
            start_key = [self.orgname, parent, 0]
            end_key = [self.orgname, parent]
            res = self.datastore.find_docs_by_view('directory', 'by_parent',
                start_key=start_key, end_key=end_key, id_only=True, **kwargs)
        else:
            path = parent[1:].split("/")
            start_key = [self.orgname, path, 0]
            end_key = [self.orgname, list(path) + ["ZZZZZZ"]]
            res = self.datastore.find_docs_by_view('directory', 'by_path',
                start_key=start_key, end_key=end_key, id_only=True, **kwargs)

        match = [value for docid, indexkey, value in res]
        return match
