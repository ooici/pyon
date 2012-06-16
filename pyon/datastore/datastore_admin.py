#!/usr/bin/env python

"""Helper functions for managing the datastore, e.g. from tests"""

import yaml
import datetime
import os
import os.path

from pyon.core.exception import BadRequest
from pyon.datastore.couchdb.couchdb_standalone import CouchDataStore
from pyon.public import CFG, log, iex

class DatastoreAdmin(object):

    def __init__(self, config=None, sysname=None):
        if not config:
            from pyon.core.bootstrap import CFG
            config = CFG
        self.config = config
        if not sysname:
            from pyon.core.bootstrap import get_sys_name
            sysname = get_sys_name()
        self.sysname = sysname

    def _get_scoped_name(self, ds_name):
        if not ds_name:
            return None
        return ("%s_%s" % (self.sysname, ds_name)).lower()

    def dump_datastore(self, path=None, ds_name=None, clear_dir=True):
        """
        Dumps CouchDB datastores into a directory as YML files.
        @param ds_name Logical name (such as "resources") of an ION datastore
        @param path Directory to put dumped datastores into (defaults to
                    "res/preload/local/dump_[timestamp]")
        @param clear_dir if True, delete contents of datastore dump dirs
        """
        if not path:
            dtstr = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')
            path = "res/preload/local/dump_%s" % dtstr
        if ds_name:
            qual_ds_name = self._get_scoped_name(ds_name)
            ds = CouchDataStore(qual_ds_name, config=self.config)
            if ds.exists_datastore(qual_ds_name):
                self._dump_datastore(qual_ds_name, path, clear_dir)
            else:
                log.warn("Datastore does not exist")
        else:
            ds_list = ['resources', 'objects', 'state', 'events',
                       'directory', 'scidata']
            for dsn in ds_list:
                qual_ds_name = self._get_scoped_name(dsn)
                self._dump_datastore(path, qual_ds_name, clear_dir)

    def _dump_datastore(self, outpath_base, ds_name, clear_dir=True):
        ds = CouchDataStore(ds_name, config=self.config)
        if not ds.exists_datastore(ds_name):
            log.warn("Datastore does not exist: %s" % ds_name)
            return

        if not os.path.exists(outpath_base):
            os.makedirs(outpath_base)

        outpath = "%s/%s" % (outpath_base, ds_name)
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        if clear_dir:
            [os.remove(os.path.join(outpath, f)) for f in os.listdir(outpath)]

        objs = ds.find_docs_by_view("_all_docs", None, id_only=False)
        numwrites = 0
        for obj_id, obj_key, obj in objs:
            # Some object ids have slashes
            fn = obj_id.replace("/","_")
            with open("%s/%s.yml" % (outpath, fn), 'w') as f:
                yaml.dump(obj, f, default_flow_style=False)
                numwrites += 1
        log.info("Wrote %s objects to %s" % (numwrites, outpath))

    def load_datastore(self, path=None, ds_name=None, ignore_errors=True):
        """
        Loads data from files into a datastore
        """
        path = path or "res/preload/default"
        if not os.path.exists(path):
            log.warn("Load path not found: %s" % path)
            return
        if not os.path.isdir(path):
            log.error("Path is not a directory: %s" % path)

        if ds_name:
            # Here we expect path to contain YML files for given datastore
            qual_ds_name = self._get_scoped_name(ds_name)
            log.info("DatastoreLoader: LOAD datastore=%s" % qual_ds_name)
            self._load_datastore(path, qual_ds_name, ignore_errors)
        else:
            # Here we expect path to have subdirs that are named according to logical
            # datastores, e.g. "resources"
            log.info("DatastoreLoader: LOAD ALL DATASTORES")
            for fn in os.listdir(path):
                fp = os.path.join(path, fn)
                if not os.path.exists(path):
                    log.warn("Item %s is not a directory" % fp)
                    continue
                qual_ds_name = self._get_scoped_name(fn)
                self._load_datastore(fp, qual_ds_name, ignore_errors)

    def _load_datastore(self, path=None, ds_name=None, ignore_errors=True):
        ds = CouchDataStore(ds_name, config=self.config)
        objects = []
        for fn in os.listdir(path):
            fp = os.path.join(path, fn)
            try:
                with open(fp, 'r') as f:
                    yaml_text = f.read()
                obj = yaml.load(yaml_text)
                if "_rev" in obj:
                    del obj["_rev"]
                objects.append(obj)
            except Exception as ex:
                if ignore_errors:
                    log.warn("load error id=%s err=%s" % (fn, str(ex)))
                else:
                    raise ex

        if objects:
            try:
                res = ds.create_doc_mult(objects)
                log.info("DatastoreLoader: Loaded %s objects into %s" % (len(res), ds_name))
            except Exception as ex:
                if ignore_errors:
                    log.warn("load error id=%s err=%s" % (fn, str(ex)))
                else:
                    raise ex

    def _get_datastore_names(self, prefix=None):
        return []

    def clear_datastore(self, ds_name=None, prefix=None):
        """
        Clears a datastore or a set of datastores of common prefix
        """
        ds = CouchDataStore(config=self.config)
        if ds_name:
            qual_ds_name = self._get_scoped_name(ds_name)
            if ds.exists_datastore(qual_ds_name):
                ds.delete_datastore(qual_ds_name)
            elif ds.exists_datastore(ds_name):
                ds.delete_datastore(ds_name)
        elif prefix:
            for dsn in ds.list_datastores():
                if dsn.startswith(prefix):
                    ds.delete_datastore(dsn)
        else:
            log.warn("Cannot clear datastore without prefix or datastore name")

    def get_blame_objects(self):
        ds_list = ['resources', 'objects', 'state', 'events', 'directory', 'scidata']
        blame_objs = {}
        for ds_name in ds_list:
            ret_objs = []
            try:
                qual_ds_name = self._get_scoped_name(ds_name)
                ds = CouchDataStore(qual_ds_name, config=self.config)
                ret_objs = ds.find_docs_by_view("_all_docs", None, id_only=False)
            except BadRequest:
                continue
            objs = []
            for obj_id, obj_key, obj in ret_objs:
                if "blame_" in obj:
                    objs.append(obj)
            blame_objs[ds_name] = objs
        return blame_objs
