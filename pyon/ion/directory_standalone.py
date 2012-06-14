#!/usr/bin/env python

__author__ = 'Seman Said, Michael Meisinger'

import os

from pyon.datastore.couchdb.couchdb_standalone import CouchdbStandalone
from pyon.util.containers import get_ion_ts, get_default_sysname


class DirectoryStandalone(object):
    '''
    Directory service standalone class
    '''

    def __init__(self, sysname=None, orgname=None, config=None):
        self.orgname = orgname or config['system']['root_org'] if config else 'ION' or 'ION'
        sysname = sysname or get_default_sysname()
        self.database_name  = sysname + "_directory"
        self.datastore = CouchdbStandalone(database_name=self.database_name, config=config)

    def register(self, parent, key, **kwargs):
        '''
        Register data into the directory
        '''
        if not (parent and key):
            raise Exception("Illegal arguments")
        if not type(parent) is str or not parent.startswith("/"):
            raise Exception("Illegal arguments: parent")
        object_id = self._get_directory_name(parent, key)

        # Check for entry
        entry = self.datastore.read(object_id)
        doc = self._create_dir_entry(object_id=object_id, parent=self._get_directory_name(parent), key=key,
            attributes=kwargs)
        if entry:
            entry = self._update_dir_entry(doc=entry, parent=self._get_directory_name(parent), key=key,
                attributes=kwargs)
            self.datastore.update(entry)
        else:
            self.datastore.write(doc, doc['_id'])

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
            parent_dn = self._get_directory_name(parent)
            dn = self._get_directory_name(parent, key)
            de = self._create_dir_entry(object_id=dn, parent=parent_dn, key=key, attributes=attrs, ts_created=cur_time, ts_updated=cur_time)
            de_list.append(de)
        self.datastore.create_doc_mult(de_list, allow_ids=True)

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
        doc['parent'] = parent
        doc['ts_created'] = ts_created or get_ion_ts()
        doc['ts_updated'] = ts_updated or get_ion_ts()
        return doc

    def _get_directory_name(self, parent, key=None, org=None):
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
            raise Exception("Illegal directory parent: %s" % parent)

    def lookup(self, qualified_key='/'):
        dn = self._get_directory_name(qualified_key)
        entry = self.datastore.read(dn)
        return entry['attributes'] if entry else None

    def find_dir_child_entries(self, parent='/', **kwargs):
        parent_dn = self._get_directory_name(parent)
        map_fun= "function(doc) { if (doc.parent == '" + parent_dn +"') emit(doc.ts_updated, doc) }"
        results = self.datastore.query(map_fun)
        return results

