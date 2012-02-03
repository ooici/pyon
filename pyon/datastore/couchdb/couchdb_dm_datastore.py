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
import hashlib

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


def sha1hex(doc):
    """
    Compare the content of the doc without its id or revision...
    """
    doc_id = doc.pop('_id',None)
    doc_rev = doc.get('_rev',None)
    doc_string = str(doc)

    if doc_id is not None:
        doc['_id'] = doc_id

    if doc_rev is not None:
        doc['_rev'] = doc_rev

    return hashlib.sha1(doc_string).hexdigest().upper()




class CouchDB_DM_DataStore(CouchDB_DataStore):
    def __init__(self, *args, **kwargs):
        super(CouchDB_DM_DataStore, self).__init__(*args, **kwargs)
        
        COUCHDB_CONFIGS['dm_datastore'] = {'views': ['posts']}
        COUCHDB_VIEWS['posts'] = {
                "posts_by_id": {
                    "map": "function(doc)\n{\tif(doc.type_==\"BlogPost\") { emit(doc.post_id,doc._id);}}"
                },
                "posts_by_title": {
                    "map": "function(doc)\n{\tif(doc.type_==\"BlogPost\") { emit(doc.title,doc._id);}}"
                },
                "posts_by_updated": {
                    "map": "function(doc)\n{\tif(doc.type_==\"BlogPost\") { emit(doc.updated,doc._id);}}"
                },
                "posts_by_author": {
                    "map": "function(doc)\n{\tif(doc.type_==\"BlogPost\") { emit(doc.author.name,doc._id);}}"
                },
                "comments_by_post_id": {
                    "map": "function(doc)\n{\tif(doc.type_==\"BlogComment\") { emit(doc.ref_id,doc._id);}}"
                },
                "comments_by_author": {
                    "map": "function(doc)\n{\tif(doc.type_==\"BlogComment\") { emit(doc.author.name,doc._id);}}"
                },
                "comments_by_updated": {
                    "map": "function(doc)\n{\tif(doc.type_==\"BlogComment\") { emit(doc.updated,doc._id);}}"
                },
                "posts_join_comments": {
                    "map": "function(doc)\n{\tif(doc.type_==\"BlogPost\") { emit([doc.post_id,0],doc._id);}\n\telse if(doc.type_==\"BlogComment\") { emit([doc.ref_id,1],doc._id);}\n}"
                }

        }

    def query_view(self, view_name='', opts={}, datastore_name=''):
        if not datastore_name:
            datastore_name = self.datastore_name

        try:
            db = self.server[datastore_name]
        except ResourceNotFound as e:
            raise BadRequest('No datastore with name: %s' % datastore_name)

        #@todo: DELTE THIS BEFORE PUSHING
        log.warn('CouchDB_DM_DATA: %s', opts)
        rows = db.view(view_name, **opts)
        result = self._parse_results(rows)
        log.warn('CouchDB_DM_DATA: %s', result)

        return result
    def doc_to_object(self, doc):
        obj = self._persistence_dict_to_ion_object(doc)
        return obj

    def _parse_results(self, doc):
        ''' Parses a complex object and organizes it into basic types
        '''
        ret = {}

        #-------------------------------
        # Handle ViewResults type (CouchDB type)
        #-------------------------------
        # \_ Ignore the meta data and parse the rows only
        if isinstance(doc,ViewResults):
            ret = self._parse_results(doc.rows)
            return ret

        #-------------------------------
        # Handle A Row (CouchDB type)
        #-------------------------------
        # \_ Split it into a dict with a key and a value
        #    Recursively parse down through the structure.
        if isinstance(doc,Row):
            ret['id'] = doc['id']
            ret['key'] = self._parse_results(doc['key'])
            ret['value'] = self._parse_results(doc['value'])
            if 'doc' in doc:
                ret['doc'] = self._parse_results(doc['doc'])
            return ret

        #-------------------------------
        # Handling a list
        #-------------------------------
        # \_ Break it apart and parse each element in the list

        if isinstance(doc,list):
            ret = []
            for element in doc:
                ret.append(self._parse_results(element))
            return ret
        #-------------------------------
        # Handle a dic
        #-------------------------------
        # \_ Check to make sure it's not an IonObject
        # \_ Parse the key value structure for other objects
        if isinstance(doc,dict):
            if '_id' in doc:
                # IonObject
                return self.doc_to_object(doc)

            for key,value in doc:
                ret[key] = self._parse_results(value)
            return ret

        #-------------------------------
        # Primitive type
        #-------------------------------
        return doc

    def custom_query(self, map_fun, reduce_fun=None, datastore_name='', **options):
        if not datastore_name:
            datastore_name = self.datastore_name
        db = self.server[datastore_name]
        res = db.query(map_fun,reduce_fun,**options)

        return self._parse_results(res)



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
