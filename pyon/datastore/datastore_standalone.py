#!/usr/bin/env python
__author__ = ''
__license__ = 'Apache 2.0'

import os
import exceptions
import time
from pyon.datastore.couchdb.couchdb_standalone import CouchdbStandalone, SystemConfiguration
from copy import deepcopy


class DirectorySa(object):
    '''
    Directory service standalone class
    '''
    
    def __init__(self, sysname=None, orgname=None, forceclean=False):
        sc = SystemConfiguration()
        self.orgname = sc.config['system']['root_org'] or 'ION'
        sysname  = sysname + "_directory" if sysname else None
        self.sysname = sysname or 'ion_%s_directory' % os.uname()[1].replace('.', '_').lower()
        self.datastore = CouchdbStandalone (database_name = self.sysname)
        self.forceclean = forceclean or sc.config['system']['force_clean']
        if self.forceclean:
            self.datastore.delete_database()
            self.datastore = CouchdbStandalone (database_name = self.sysname)

    def register(self, parent, key, file_path='', **kwargs):
        '''
        Register data into the directory
        Returns None on success
        Returns previously stored entry if multiple entries are found
        '''
        if not (parent and key):
            raise Exception("Illegal arguments")
        if not type(parent) is str or not parent.startswith("/"):
            raise Exception("Illegal arguments: parent")
        dir_name = self._get_directory_name(parent, key)

        # Check for entery
        entry = self.datastore.read(dir_name)
        doc = self._create_dir_entry(dir_name=dir_name, parent=self._get_directory_name(parent), key=key, 
                                     attributes=kwargs, file_path=file_path)
        if entry:
            temp_entry = deepcopy(entry)
            entry = self._update_dir_entry(doc=entry, parent=self._get_directory_name(parent), key=key,
                                           attributes=kwargs, file_path=file_path)
            self.datastore.update(entry)
            return temp_entry
        else:
            self.datastore.write(doc, doc['_id'])
        return None

    def _update_dir_entry(self, doc, parent, key, attributes=None, ts_updated='',
                          file_path=''):
        doc['attributes'] = attributes or {}
        doc['key'] = key
        doc['parent'] = parent
        doc['ts_updated'] = ts_updated or int(time.time() * 1000)
        doc['file_path'] = file_path
        return doc

    def _create_dir_entry(self, dir_name,  parent, key, attributes=None,
                          ts_created='', ts_updated='', file_path=''):
        doc = {}
        doc['_id'] = dir_name
        doc['attributes'] = attributes or {}
        doc['key'] = key
        doc['parent'] = parent
        doc['ts_created'] = ts_created or int(time.time() * 1000)
        doc['ts_updated'] = ts_updated or int(time.time() * 1000)
        doc['type_'] = 'DirEntry'
        doc['file_path'] = file_path
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

    def lookup_by_path(self, path):
        map_fun= "function(doc) { if (doc.file_path == '" + path + "') emit(doc.ts_updated, doc) }"
        return self.datastore.query(map_fun)

    def find_dir_child_entries(self, parent='/', **kwargs):
        parent_dn = self._get_directory_name(parent)
        map_fun= "function(doc) { if (doc.parent == '" + parent_dn +"') emit(doc.ts_updated, doc) }"
        return self.datastore.query(map_fun)

