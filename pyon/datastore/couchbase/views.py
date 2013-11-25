#!/usr/bin/env python

__author__ = 'Michael Meisinger, Seman Said'

from pyon.datastore.couchdb.views import COUCHDB_PROFILES, COUCHDB_VIEWS

COUCH_PROFILES = COUCHDB_PROFILES

COUCH_VIEWS = COUCHDB_VIEWS

# Modifications for Couchbase
COUCH_VIEWS["association"]["by_doc"] = {
         'map':"""
function(doc, meta) {
    emit(meta.id, null);
}""",
     }
# Subject to object lookup (for range queries)
# Todo Not a good way to get all the data.

def get_couch_view_designs(profile):
    store_profile = COUCH_PROFILES[profile]
    view_designs = store_profile['views']
    res_views = {}
    for design in view_designs:
        res_views[design] = COUCH_VIEWS[design]
    return res_views
