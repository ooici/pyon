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
        "dataset_by_latlong": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n        var pack = {\"lat\":doc.lattitude, \"long\":doc.longitude, \"lat_h\":doc.lattitude_hemisphere, \"long_h\":doc.longitude_hemisphere};\n        emit(pack,doc._id);\n    }\n}"
        },
        "dataset_by_lat": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n        var pack = [doc.lattitude_hemisphere,doc.lattitude];\n        emit(pack,doc._id);\n    }\n}"
        },
        "dataset_by_long": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n        var pack = [doc.longitude_hemisphere,doc.longitude];\n        emit(pack,doc._id);\n    }\n}"
        },
        "lat_max": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n        var pack = [doc.lattitude_hemisphere,doc.lattitude];\n        emit(pack,doc.lattitude);\n    }\n}",
            "reduce": "\nfunction (keys,values,rereduce) {\n    var max = 0.0;\n    for(var i in values) {\n        if(values[i] > max)\n            max = values[i];\n    }\n    return max;\n    \n}\n"
        },
        "longitude_max": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n        var pack = [doc.longitude_hemisphere,doc.longitude];\n        emit(pack,doc.longitude);\n    }\n}",
            "reduce": "function (keys,values,rereduce) {\n    var max = 0.0;\n    for(var i in values) {\n        if(values[i] > max)\n            max = values[i];\n    }\n    return max;\n    \n}\n"
        },
        "longitude_min": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n        var pack = [doc.longitude_hemisphere,doc.longitude];\n        emit(pack,doc.longitude);\n    }\n}",
            "reduce": "function (keys,values,rereduce) {\n    var min = 0.0;\n    for(var i in values) {\n        if(min==0.0)\n            min = values[i];\n        else if(values[i] < min)\n            min = values[i];\n    }\n    return min;\n    \n}\n"
        },
        "lattitude_max": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n        var pack = [doc.lattitude_hemisphere,doc.lattitude];\n        emit(pack,doc.lattitude);\n    }\n}",
            "reduce": "\nfunction (keys,values,rereduce) {\n    var max = 0.0;\n    for(var i in values) {\n        if(values[i] > max)\n            max = values[i];\n    }\n    return max;\n    \n}\n"
        },
        "lattitude_min": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n        var pack = [doc.lattitude_hemisphere,doc.lattitude];\n        emit(pack,doc.lattitude);\n    }\n}",
            "reduce": "function (keys,values,rereduce) {\n    var min = 0.0;\n    for(var i in values) {\n        if(min==0.0)\n            min = values[i];\n        else if(values[i] < min)\n            min = values[i];\n    }\n    return min;\n    \n}\n"
        },
        "dataset_by_depth": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n\temit(doc.depth, doc._id);       \n    }\n}"
        },
        "depth_min": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n\temit(doc._id, doc.depth);       \n    }\n}",
            "reduce": "function (keys,values,rereduce) {\n    var min = 0.0;\n    for(var i in values) {\n        if(min==0.0)\n            min = values[i];\n        else if(values[i] < min)\n            min = values[i];\n    }\n    return min;\n    \n}\n"
        },
        "depth_max": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n\temit(doc._id, doc.depth);       \n    }\n}",
            "reduce": "\n\nfunction (keys,values,rereduce) {\n    var max = 0.0;\n    for(var i in values) {\n        if(values[i] > max)\n            max = values[i];\n    }\n    return max;\n    \n}"
        },
        "dataset_by_time": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n\temit(doc.time, doc._id);       \n    }\n}"
        },
        "time_max": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n\temit(doc.time, doc.time);       \n    }\n}",
            "reduce": "function (keys,values,rereduce) {\n    var max = \"\";\n    for(var i in values) {\n        if(values[i].localeCompare(max)>0)\n            max = values[i];\n    }\n    return max;\n    \n}"
        },
        "time_min": {
            "map": "function(doc) {\n    if(doc.type_ == \"SciData\") {\n\temit(doc.time, doc.time);       \n    }\n}",
            "reduce": "function (keys,values,rereduce) {\n    var min = 0.0;\n    for(var i in values) {\n        if(min==0.0)\n            min = values[i];\n        else if(values[i].localeCompare(min) < 0)\n            min = values[i];\n    }\n    return min;\n    \n}"
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
