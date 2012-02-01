#!/usr/bin/env python
'''
@author Luke Campbell
@file pyon/datastore/couchdb/couchdb_dm_datastore.py
@description An extension to the existing couchdb_datastore to support more dynamic mapping and view access.
'''
from couchdb.http import ResourceNotFound
from couchdb.client import ViewResults, Row
from pyon.core.exception import BadRequest
from pyon.util.log import log
from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
import pyon.datastore.couchdb.couchdb_config as couch_config


COUCHDB_CONFIGS = couch_config.COUCHDB_CONFIGS
COUCHDB_VIEWS = couch_config.COUCHDB_VIEWS
# Overriding an existing function
def get_couchdb_views(config):
    if config in COUCHDB_CONFIGS:
        store_config = COUCHDB_CONFIGS[config]
    else:
        store_config = COUCHDB_CONFIGS['all']
    views = store_config['views']
    res_views = {}
    for view in views:
        res_views[view] = COUCHDB_VIEWS[view]
    return res_views


class CouchDB_DM_DataStore(CouchDB_DataStore):
    def __init__(self, *args, **kwargs):
        super(CouchDB_DM_DataStore, self).__init__(*args, **kwargs)
        
        COUCHDB_CONFIGS['dm_datastore'] = {'views': ['posts']}
        COUCHDB_VIEWS['posts'] = {'post_comment':{'map':"""
function(doc) {
    if(doc.type_=="BlogPost") {
        emit([doc._id,0], doc);
    } else if (doc.type_ == "BlogComment") {
        emit([doc.ref_id, 1], doc);
    }
}"""}
}

    def query_view(self, view_name='', key='', datastore_name=''):
        if not datastore_name:
            datastore_name = self.datastore_name

        try:
            db = self.server[datastore_name]
        except ResourceNotFound as e:
            raise BadRequest('No datastore with name: %s' % datastore_name)

        rows = db.view(view_name, key)
        return self._parse_results(rows)

    def doc_to_object(self, doc):
        obj = self._persistence_dict_to_ion_object(doc)
        return obj

    def _parse_results(self, doc):
        ret = {}
        if type(doc) == ViewResults:
            ret = self._parse_results(doc.rows)
            return ret

        if type(doc) == Row:
            ret['key'] = self._parse_results(doc['key'])
            ret['value'] = self._parse_results(doc['value'])
            return ret
        if type(doc) == list:
            ret = []
            for element in doc:
                ret.append(self._parse_results(element))
            return ret

        if type(doc) == dict:
            if '_id' in doc:
                # IonObject
                return self.doc_to_object(doc)

            for key,value in doc:
                ret[key] = self._parse_results(value)
            return ret
        return doc


    def _define_views(self, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name

        views = get_couchdb_views(datastore_name)
        for design, viewdef in views.iteritems():
            self._define_view(design, viewdef, datastore_name=datastore_name)


    def _update_views(self, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        db = self.server[datastore_name]
        views = get_couchdb_views(datastore_name)
        for design, viewdef in views.iteritems():
            for viewname in viewdef:
                try:
                    rows = db.view("_design/%s/_view/%s" % (design, viewname))
                    log.debug("View %s/_design/%s/_view/%s: %s rows" % (datastore_name, design, viewname, len(rows)))
                except Exception, ex:
                    log.exception("Problem with view %s/_design/%s/_view/%s" % (datastore_name, design, viewname))
