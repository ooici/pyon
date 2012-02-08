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
from pyon.datastore.datastore import DataStore
import pyon.datastore.couchdb.couchdb_config as couch_config

import hashlib

COUCHDB_CONFIGS = couch_config.COUCHDB_CONFIGS
COUCHDB_VIEWS = couch_config.COUCHDB_VIEWS

# Overriding an existing function
def get_couchdb_views(config):
    '''
    Overrides the existing function to support design objects having the non-default view templates.
    '''
    if config in COUCHDB_CONFIGS:
        store_config = COUCHDB_CONFIGS[config]
    else:
        store_config = COUCHDB_CONFIGS[DataStore.DS_PROFILE.BASIC]
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
    '''
    CouchDB_DM_DataStore is an extension of the CouchDB_DataStore to add functionality in support of DM,
    the ability to query views is very important as well as improving performance in any manner we can.
    Below, several views have been added for the type dm_datastore to support several view templates.

    '''
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
                },
                "posts_by_author_date": {
                    "map": "function(doc) {\n  if(doc.type_==\"BlogPost\")\n    emit([doc.author.name,doc.updated,doc.post_id], doc.post_id);\n  else if(doc.type==\"BlogComment\")\n    emit([doc.author.name,doc.updated,doc.ref_id], doc.ref_id);\n}"
                }
        }

                

    def query_view(self, view_name='', opts={}, datastore_name=''):
        '''
        query_view is a straight through method for querying a view in CouchDB. query_view provides us the interface
        to the view structure in couch, in lieu of implementing a method for every type of query we could want, we
        now have the capability for clients to make queries to couch in a straight-through manner.
        '''
        if not datastore_name:
            datastore_name = self.datastore_name

        # Handle the possibility of the datastore not existing, convert the ResourceNotFound exception to a BadRequest
        try:
            db = self.server[datastore_name]
        except ResourceNotFound as e:
            raise BadRequest('No datastore with name: %s' % datastore_name)

        # Actually obtain the results and place them in rows
        rows = db.view(view_name, **opts)

        # Parse the results and convert the results into ionobjects and python types.
        result = self._parse_results(rows)

        return result


    def doc_to_object(self, doc):
        '''
        May add extended handling for data sets in the future, for now it's transient.
        '''
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
            try:
                ret = self._parse_results(doc.rows)
            except ResourceNotFound as e:
                raise BadRequest('The desired resource does not exist.')

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
        '''
        custom_query sets up a temporary view in couchdb, the map_fun is a string consisting
        of the javascript map function

        Warning: Please note that temporary views are not suitable for use in production,
        as they are really slow for any database with more than a few dozen documents.
        You can use a temporary view to experiment with view functions, but switch to a
        permanent view before using them in an application.
        '''
        if not datastore_name:
            datastore_name = self.datastore_name
        db = self.server[datastore_name]
        res = db.query(map_fun,reduce_fun,**options)

        return self._parse_results(res)



    def _define_views(self, datastore_name="", profile=None):
        '''
        Ensure that when the datastore is created that it uses the defined view templates not the default 'all'
        '''
        if not datastore_name:
            datastore_name = self.datastore_name

        views = get_couchdb_views(datastore_name)
        for design, viewdef in views.iteritems():
            self._define_view(design, viewdef, datastore_name=datastore_name)


    def _update_views(self, datastore_name=""):
        '''
        Ensure that when the datastore is created that it uses the defined view templates not the default 'all'
        '''
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
