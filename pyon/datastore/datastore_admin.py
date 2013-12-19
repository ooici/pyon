#!/usr/bin/env python

"""Helper functions for managing the datastore, e.g. from tests"""

import json
import datetime
import os
import os.path

from pyon.core.exception import BadRequest, NotFound
from pyon.datastore.datastore_common import DatastoreFactory
from pyon.public import log


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
        @param compact if True, saves all objects in one big YML file
        """
        if not path:
            dtstr = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')
            path = "res/preload/local/dump_%s" % dtstr
        if ds_name:
            ds = DatastoreFactory.get_datastore(datastore_name=ds_name, config=self.config, scope=self.sysname)
            if ds.datastore_exists(ds_name):
                self._dump_datastore(path, ds_name, clear_dir)
            else:
                log.warn("Datastore does not exist")
            ds.close()
        else:
            ds_list = ['resources', 'objects', 'state', 'events']
            for dsn in ds_list:
                self._dump_datastore(path, dsn, clear_dir)

    def _dump_datastore(self, outpath_base, ds_name, clear_dir=True):
        ds = DatastoreFactory.get_datastore(datastore_name=ds_name, config=self.config, scope=self.sysname)
        try:
            if not ds.datastore_exists(ds_name):
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
            compact_obj = [obj for obj_id, obj_key, obj in objs]
            compact_obj= ["COMPACTDUMP", compact_obj]
            with open("%s/%s_compact.json" % (outpath, ds_name), 'w') as f:
                json.dump(compact_obj, f)
            numwrites = len(objs)

            log.info("Wrote %s files to %s" % (numwrites, outpath))
        finally:
            ds.close()

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
        ds = DatastoreFactory.get_datastore(datastore_name=ds_name, config=self.config, scope=self.sysname)
        try:
            objects = []
            for fn in os.listdir(path):
                fp = os.path.join(path, fn)
                try:
                    with open(fp, 'r') as f:
                        json_text = f.read()
                    obj = json.loads(json_text)
                    if obj and type(obj) is list and obj[0] == "COMPACTDUMP":
                        objects.extend(obj[1])
                    else:
                        objects.append(obj)
                except Exception as ex:
                    if ignore_errors:
                        log.warn("load error id=%s err=%s" % (fn, str(ex)))
                    else:
                        raise ex

            if objects:
                for obj in objects:
                    if "_rev" in obj:
                        del obj["_rev"]
                try:
                    res = ds.create_doc_mult(objects)
                    log.info("DatastoreLoader: Loaded %s objects into %s" % (len(res), ds_name))
                except Exception as ex:
                    if ignore_errors:
                        log.warn("load error err=%s" % (str(ex)))
                    else:
                        raise ex
        finally:
            ds.close()

    def _get_datastore_names(self, prefix=None):
        return []

    def clear_datastore(self, ds_name=None, prefix=None):
        """
        Clears a datastore or a set of datastores of common prefix
        """
        ds = DatastoreFactory.get_datastore(config=self.config, scope=self.sysname)
        try:
            if ds_name:
                try:
                    ds.delete_datastore(ds_name)
                except NotFound:
                    try:
                        # Try the unscoped version
                        ds1 = DatastoreFactory.get_datastore(config=self.config)
                        ds1.delete_datastore(ds_name)
                    except NotFound:
                        pass
            elif prefix:
                prefix = prefix.lower()
                ds_noscope = DatastoreFactory.get_datastore(config=self.config)
                for dsn in ds_noscope.list_datastores():
                    if dsn.lower().startswith(prefix):
                        ds_noscope.delete_datastore(dsn)
            else:
                log.warn("Cannot clear datastore without prefix or datastore name")
        finally:
            ds.close()

    def get_blame_objects(self):
        ds_list = ['resources', 'objects', 'state', 'events']
        blame_objs = {}
        for ds_name in ds_list:
            ret_objs = []
            try:
                ds = DatastoreFactory.get_datastore(datastore_name=ds_name, config=self.config, scope=self.sysname)
                ret_objs = ds.find_docs_by_view("_all_docs", None, id_only=False)
                ds.close()
            except BadRequest:
                continue
            objs = []
            for obj_id, obj_key, obj in ret_objs:
                if "blame_" in obj:
                    objs.append(obj)
            blame_objs[ds_name] = objs
        return blame_objs
