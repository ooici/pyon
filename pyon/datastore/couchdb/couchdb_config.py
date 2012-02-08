#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'


from pyon.datastore.datastore import DataStore

COUCHDB_CONFIGS = {
    DataStore.DS_PROFILE.OBJECTS:{
        'views': ['object','association']
    },
    DataStore.DS_PROFILE.RESOURCES:{
        'views': ['resource','association']
    },
    DataStore.DS_PROFILE.DIRECTORY:{
        'views': ['directory','association']
    },
    DataStore.DS_PROFILE.EVENTS:{
        'views': ['event']
    },
    DataStore.DS_PROFILE.STATE:{
        'views': []
    },
    DataStore.DS_PROFILE.SCIDATA:{
        'views': []
    },
    DataStore.DS_PROFILE.BASIC:{
        'views': []
    },
}

COUCHDB_VIEWS = {
    # Association (triple) related views
    'association':{
        'all':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association") {
    emit(doc._id, doc);
  }
}""",
        },
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
  if (doc.type_ && doc.type_!="Association") {
    emit([doc.type_, doc.lcstate, doc.name], null);
  }
}""",
        },
        # The following is a more sophisticated index. It does two things for each Resource object:
        # 1: It emits an index value prefixed by 0 for the actual lcstate
        # 2: It emits an index value prefixed by 1,parent_state for all parent states
        # Thereby it is possible to search for resources by hieararchical state and still be able
        # to return result sets that objects once only.
        # Note: the order of the type_ in the key is important for case 2, so that range queries are possible
        # with both type_ without.
        'by_lcstate':{
            'map':"""
function(doc) {
  if (doc.type_ && doc.type_!="Association") {
    emit([0, doc.lcstate, doc.type_, doc.name], null);
    if (doc.lcstate != undefined && doc.lcstate != "" && doc.lcstate != "DRAFT" && doc.lcstate != "RETIRED") {
      emit([1, "REGISTERED", doc.type_, doc.lcstate, doc.name], null);
      if (doc.lcstate == "PLANNED" || doc.lcstate == "DEVELOPED" || doc.lcstate == "INTEGRATED") {
        emit([1, "UNDEPLOYED", doc.type_, doc.lcstate, doc.name], null);
      } else {
        emit([1, "DEPLOYED", doc.type_, doc.lcstate, doc.name], null);
        if (doc.lcstate == "DISCOVERABLE" || doc.lcstate == "AVAILABLE") {
          emit([1, "PUBLIC", doc.type_, doc.lcstate, doc.name], null);
        }
      }
    }
  }
}""",
        },
        'by_name':{
            'map':"""
function(doc) {
  if (doc.type_ && doc.type_!="Association") {
    emit([doc.name, doc.type_, doc.lcstate], null);
  }
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

    # Event related objects
    'event':{
        'by_time':{
            'map':"""
function(doc) {
  if (doc.origin) {
    emit([doc.ts_created]);
  }
}""",
            },
        'by_type':{
            'map':"""
function(doc) {
  if (doc.origin) {
    emit([doc.type_, doc.ts_created]);
  }
}""",
        },
        'by_origin':{
            'map':"""
function(doc) {
  if (doc.origin) {
    emit([doc.origin, doc.ts_created]);
  }
}""",
        },
        'by_origintype':{
            'map':"""
function(doc) {
  if (doc.origin) {
    emit([doc.origin, doc.type_, doc.ts_created]);
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
