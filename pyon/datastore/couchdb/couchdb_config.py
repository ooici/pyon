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
        'views': ['datasets']
    },
    DataStore.DS_PROFILE.EXAMPLES:{
        'views':['posts']
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
    'posts' : {
        "dataset_by_id": {
            "map": "function(doc)\n{\tif(doc.type_==\"BlogPost\") { emit([doc.post_id,0],doc._id);}\n\telse if(doc.type_==\"BlogComment\") { emit([doc.ref_id,1],doc._id);}\n}"
        },
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
    },
    'datasets': {
        # Bounds
        # Map: https://gist.github.com/1781675#file_maps.js
        # Reduce: https://gist.github.com/1781675#file_reduce_bounds.js
        "bounds": {
            "map": "\n/*\n * Author: Luke Campbell <lcampbell@asascience.com>\n * Description: Utility and map functions to map the DataContainer's bounding elements.\n */\n\n/*\n * Traverses an \"identifiable\" in a document to see if it contains a CoordinateAxis\n */\nfunction traverse(identifiable) {\n    if(identifiable.type_==\"CoordinateAxis\")\n    {\n        return identifiable.bounds_id;\n    }\n    else return null;\n}\n/*\n * Gets the CoordinateAxis objects and their bounds_ids\n */\nfunction get_bounds(doc)\n{\n    identifiables = doc.identifiables;\n    var bounds = [];\n    for(var i in identifiables)\n    {\n        var bounds_id = traverse(identifiables[i]);\n        if(bounds_id)\n            bounds.push(bounds_id);\n    }\n    return bounds;\n}\n\n/* Data map */\nfunction (doc) {\n    if(doc.type_ == \"StreamGranuleContainer\"){\n        var bounds = get_bounds(doc);\n        for(var b in bounds)\n        {\n            var key = bounds[b];\n            var s = String(key)\n            var pack = {};\n            pack[key] = doc.identifiables[key].value_pair;\n\n            emit([doc.stream_resource_id,1], pack);\n        }\n    }\n}\n\n",
            "reduce": "\n\nfunction value_in(value,ary) {\n    for(var i in ary)\n    {\n        if(value == ary[i])\n            return i;\n    }\n}\nfunction get_keys(obj){\n    var keys = [];\n    for(var key in obj)\n        keys.push(key);\n    return keys;\n}\nfunction print_dic(obj) {\n    for(var key in obj)\n    {\n        debug(key);\n        debug(obj[key]);\n    }\n}\n\nfunction(keys,values,rereduce) {\n    var keys = [];\n    var results = values[0];\n        \n    /* Not a rereduce so populate the results dictionary */\n\n\n    for(var i in values)\n    {\n        var key = get_keys(values[i])[0];\n        // The k,v pair is new, put it in results.\n        if(! value_in(key,keys))\n        {\n            keys.push(key);\n            results[key] = values[i][key];\n            continue;\n        }\n        var value = values[i][key];\n        /* minimum between the result and the new value */\n        if(value[0] < results[key][0])\n            results[key][0] = value[0];\n        if(value[1] > results[key][1])\n            results[key][1] = value[1];\n\n    }\n    return results;\n\n    \n    \n}"
        },
        # Stream join granule
        # Map: https://gist.github.com/1781675#file_map_stream_join_granule.js
        "stream_join_granule": {
            "map": "function (doc) {\n    if(doc.type_ == \"StreamDefinitionContainer\")\n        emit([doc.stream_resource_id,0],doc._id);\n    else if(doc.type_ == \"StreamGranuleContainer\")\n        emit([doc.stream_resource_id,1], doc._id);\n}\n"
        },
        # Cannonical reference to Stream join granule
        "dataset_by_id": {
            "map": "function (doc) {\n    if(doc.type_ == \"StreamDefinitionContainer\")\n        emit([doc.stream_resource_id,0],doc._id);\n    else if(doc.type_ == \"StreamGranuleContainer\")\n        emit([doc.stream_resource_id,1], doc._id);\n}\n"
        }


    
    }
}

def get_couchdb_views(config):
    store_config = COUCHDB_CONFIGS[config]
    views = store_config['views']
    res_views = {}
    for view in views:
        res_views[view] = COUCHDB_VIEWS[view]
    return res_views
