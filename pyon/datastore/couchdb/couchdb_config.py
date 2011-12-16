#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

COUCHDB_CONFIGS = {
    'object_store':{
        'views': ['object','association']
    },
    'resource_store':{
        'views': ['resource','association']
    },
    'directory_store':{
        'views': ['directory']
    },
    'all':{
        'views': ['object', 'resource', 'association', 'directory']
    }
}

COUCHDB_VIEWS = {
    # Association (triple) related views
    'association':{
        'by_sub':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association") {
    emit([doc.s, doc.p, doc.ot, doc.o], null);
  }
}""",
        },
        'by_obj':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association") {
    emit([doc.o, doc.p, doc.st, doc.s], null);
  }
}""",
        },
        'by_ids':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association") {
    emit([doc.s, doc.o, doc.p], null);
  }
}""",
        },
        'by_pred':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association") {
    emit([doc.p, doc.s, doc.o], null);
  }
}""",
        }
    },

    # Pure ION object related views
    # Every object has a type and ID
    'object':{
        'by_type':{
            'map':"""
function(doc) {
  emit([doc.type_], null);
}""",
        },
    },

    # Resource ION object related views
    # Resources have a type, life cycle state and name
    # Note: the name in  the indexes leads to a sort by name
    'resource':{
        'by_type':{
            'map':"""
function(doc) {
  emit([doc.type_, doc.lcstate, doc.name], null);
}""",
        },
        'by_lcstate':{
            'map':"""
function(doc) {
  emit([doc.lcstate, doc.type_, doc.name], null);
}""",
        },
        'by_name':{
            'map':"""
function(doc) {
  emit([doc.name, doc.type_, doc.lcstate], null);
}""",
        }
    },

    # Directory related objects
    # DirEntry objects are the elements of the directory tree
    'directory':{
        'by_path':{
            'map':"""
function(doc) {
  if (doc.type_ == "DirEntry") {
    if (doc.parent.indexOf('/') != 0) return;
    levels = doc.parent.split('/');
    levels.splice(0,1);
    if (doc.parent == "/") levels.pop();
    levels.push(doc.key);
    emit(levels, doc);
  }
}""",
        },
        'by_key':{
            'map':"""
function(doc) {
  if (doc.type_ == "DirEntry") {
    if (doc.parent.indexOf('/') != 0) return;
    emit([doc.key, doc.parent], doc);
  }
}""",
        },
    },
}

def get_couchdb_views(config):
    store_config = COUCHDB_CONFIGS[config]
    views = store_config['views']
    res_views = {}
    for view in views:
        res_views[view] = COUCHDB_VIEWS[view]
    return res_views
