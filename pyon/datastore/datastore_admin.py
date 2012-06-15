#!/usr/bin/env python

"""Helper functions for managing the datastore"""

import yaml
import datetime
import os
import os.path

from pyon.public import CFG, log, iex
from pyon.datastore.couchdb.couchdb_standalone import CouchdbStandalone
from pyon.core import bootstrap
from pyon.core.exception import BadRequest

class DatastoreAdmin(object):

    def __init__(self):
        pass

    def load_datastore(self, path=None, ds_name=None, ignore_errors=True):
        path = path or "res/preload/default"
        if not os.path.exists(path):
            log.warn("Load path not found: %s" % path)
            return
        if not os.path.isdir(path):
            log.error("Path is not a directory: %s" % path)

        if ds_name:
            # Here we expect path to contain YML files for given datastore
            log.info("DatastoreLoader: LOAD datastore=%s" % ds_name)
            self._load_datastore(path, ds_name, ignore_errors)
        else:
            # Here we expect path to have subdirs that are named according to logical
            # datastores, e.g. "resources"
            log.info("DatastoreLoader: LOAD ALL DATASTORES")
            for fn in os.listdir(path):
                fp = os.path.join(path, fn)
                if not os.path.exists(path):
                    log.warn("Item %s is not a directory" % fp)
                    continue
                self._load_datastore(fp, fn, ignore_errors)

    def _load_datastore(self, path=None, ds_name=None, ignore_errors=True):
        ds = CouchdbStandalone(ds_name)
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
                res = ds.create_doc_mult(objects, allow_ids=True)
                log.info("DatastoreLoader: Loaded %s objects into %s" % (len(res), ds_name))
            except Exception as ex:
                if ignore_errors:
                    log.warn("load error id=%s err=%s" % (fn, str(ex)))
                else:
                    raise ex

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
            ds = CouchdbStandalone(ds_name)
            if ds.datastore_exists(ds_name):
                self._dump_datastore(ds_name, path, clear_dir)
            else:
                log.warn("Datastore does not exist")
        else:
            ds_list = ['resources', 'objects', 'state', 'events',
                       'directory', 'scidata']
            for ds in ds_list:
                self._dump_datastore(path, ds, clear_dir)

    def _dump_datastore(self, outpath_base, ds_name, clear_dir=True):
        ds = CouchdbStandalone(ds_name)
        if not ds.datastore_exists(ds_name):
            log.warn("Datastore does not exist: %s" % ds_name)
            return
        ds = DatastoreManager.get_datastore_instance(ds_name)

        if not os.path.exists(outpath_base):
            os.makedirs(outpath_base)

        outpath = "%s/%s" % (outpath_base, ds_name)
        if not os.path.exists(outpath):
            os.makedirs(outpath)
        if clear_dir:
            [os.remove(os.path.join(outpath, f)) for f in os.listdir(outpath)]

        objs = ds.find_by_view("_all_docs", None, id_only=False, convert_doc=False)
        numwrites = 0
        for obj_id, obj_key, obj in objs:
            fn = obj_id
            # Some object ids have slashes
            fn = obj_id.replace("/","_")
            with open("%s/%s.yml" % (outpath, fn), 'w') as f:
                yaml.dump(obj, f, default_flow_style=False)
                numwrites += 1
        log.info("Wrote %s objects to %s" % (numwrites, outpath))

    def _get_datastore_names(self, prefix=None):
        return []

    def clear_datastore(self, ds_name=None, prefix=None):
        if ds_name:
            from pyon.datastore import clear_couch_util
            clear_couch_util.clear_couch(CFG, prefix=ds_name)
            clear_couch_util.clear_couch(CFG, prefix=bootstrap.get_sys_name() + "_" + ds_name)
        elif prefix:
            from pyon.datastore import clear_couch_util
            clear_couch_util.clear_couch(CFG, prefix=prefix)
        else:
            log.warn("Cannot clear datastore without prefix or datastore name")

    def get_blame_objects(self):
        ds_list = ['resources', 'objects', 'state', 'events', 'directory', 'scidata']
        blame_objs = {}
        for ds_name in ds_list:
            ret_objs = []
            try:
                ds = CouchdbStandalone(ds_name)
                ret_objs = ds.find_by_view("_all_docs", None, id_only=False, convert_doc=False)
            except BadRequest:
                continue
            objs = []
            for obj_id, obj_key, obj in ret_objs:
                if "blame_" in obj:
                    objs.append(obj)
            blame_objs[ds_name] = objs
        return blame_objs

    def bulk_delete(self, objs):
        for ds_name in objs:
            ds = DatastoreManager.get_datastore_instance(ds_name)
            for obj in objs[ds_name]:
                ds.delete(obj["_id"])
