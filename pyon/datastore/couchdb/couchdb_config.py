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
emit([doc.s, doc.p, doc.ot, doc.o, doc._id], null);
  }
}""",
        },
        'by_obj':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association") {
emit([doc.o, doc.p, doc.st, doc.s, doc._id], null);
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
    'resource':{
        'by_type':{
            'map':"""
function(doc) {
  emit([doc.type_, doc.lcstate, doc.name], doc._id);
}""",
        },
        'by_lcstate':{
            'map':"""
function(doc) {
  emit([doc.lcstate, doc.type_, doc.name], doc._id);
}""",
        },
        'by_name':{
            'map':"""
function(doc) {
  emit([doc.name, doc.type_, doc.lcstate], doc._id);
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
    levels = [node for each (node in doc.parent.split('/'))]
    //if (doc.parent == "/") { levels.pop(); }
    //levels.splice(0,1)
    levels.push(doc.key)
    emit(levels, doc);
  }
}""",
        },
        'by_key':{
            'map':"""
function(doc) {
  if (doc.type_ == "DirEntry") {
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
    print "************", res_views
    return res_views
