#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'



# A profile is a collection of views
COUCHDB_PROFILES = {
    "OBJECTS":{
        'views': ['object','association','attachment']
    },
    "RESOURCES":{
        'views': ['resource','directory','association','attachment']
    },
    "DIRECTORY":{
        'views': ['resource','directory','association','attachment']
    },
    "EVENTS":{
        'views': ['event']
    },
    "STATE":{
        'views': []
    },
    "BASIC":{
        'views': []
    },
    "FILESYSTEM": {
        'views': ['catalog']
    },
}

# Defines all the available CouchDB views and their map/reduce functions.
# Views are associated to datastore based on profile.
# Several views are in one design document.
COUCHDB_VIEWS = {
    # -------------------------------------------------------------------------
    # Views for ION Resource objects
    # Resources all have a type, life cycle state and name
    # Note: adding additional entries to the index such as name leads to a sort by name but prevents range queries
    'resource':{
        # Find resource by exact type, ordered by name (important for pagination)
        'by_type':{
            'map':"""
function(doc) {
  if (doc.type_ && doc.lcstate != undefined && doc.lcstate != 'RETIRED' && doc.name != undefined) {
    name = String(doc.name).substring(0,200);
    emit([doc.type_, name], null);
  }
}""",
        },
        # Find resource by lcstate (maturity)
        # The following is a more sophisticated index. It does two things for each Resource object:
        # 1: It emits an index value prefixed by 0 for the lcstate maturity
        # 2: It emits an index value prefixed by 0 for the lcstate availability
        # The results are ordered by type_ first then name (important for pagination)
        'by_lcstate':{
            'map':"""
function(doc) {
  if (doc.type_ && doc.lcstate != undefined && doc.availability != undefined && doc.name != undefined) {
    name = String(doc.name).substring(0,200);
    emit([0, doc.lcstate, doc.type_, name], null);
    emit([1, doc.availability, doc.type_, name], null);
  }
}""",
        },
        # Find by name, ordered by type_ (important for pagination)
        'by_name':{
            'map':"""
function(doc) {
  if (doc.type_ && doc.lcstate != undefined && doc.lcstate != 'RETIRED' && doc.name != undefined) {
    emit([doc.name, doc.type_], null);
  }
}""",
        },
        # Find by alternative ID (e.g. as used in preload)
        'by_altid':{
            'map':"""
function(doc) {
  if (doc.type_ && doc.alt_ids && doc.lcstate != 'RETIRED') {
    for (var i = 0; i < doc.alt_ids.length; i++ ) {
      altid = doc.alt_ids[i];
      parts = altid.split(":");
      if (parts.length == 2) {
        emit([parts[1], parts[0]], null);
      } else {
        emit([altid, "_"], null);
      }
    }
  } else if (doc.type_ && doc.uirefid && doc.lcstate != 'RETIRED') {
    emit([doc.uirefid, "UIREFID"], null);
  }
}""",
        },
        # Find by keyword then res type (one entry per keyword in a resource)
        'by_keyword':{
            'map':"""
function(doc) {
  if (doc.type_ && doc.lcstate != 'RETIRED' && doc.keywords != undefined) {
    for (var i = 0; i < doc.keywords.length; i++ ) {
      emit([doc.keywords[i], doc.type_], null);
    }
  }
}""",
        },
        # Find by name of nested type, then res type (one record per nested ION object type)
        'by_nestedtype':{
            'map':"""
function(doc) {
  if (doc.type_ && doc.lcstate != 'RETIRED') {
    for (var attr in doc) {
      if (doc[attr] != undefined && doc[attr].type_) {
        emit([doc[attr].type_, doc.type_], null);
      }
    }
  }
}""",
        },
        # Find by attribute only for special resources.
        # This is a special case treatment. Add emits below as needed for access elsewhere in the code.
        'by_attribute':{
            'map':"""
function(doc) {
  if (doc.type_ && doc.lcstate != 'RETIRED') {
    if (doc.type_ == "UserInfo" && doc.contact != undefined && doc.contact.email != undefined) {
      emit([doc.type_, "contact.email", doc.contact.email], null);
    } else if (doc.type_ == "DataProduct" && doc.ooi_product_name) {
      emit([doc.type_, "ooi_product_name", doc.ooi_product_name], null);
    } else if (doc.type_ == "NotificationRequest" && doc.origin) {
      emit([doc.type_, "origin", doc.origin], null);
    } else if (doc.type_ == "Org" && doc.org_governance_name != undefined) {
      emit([doc.type_, "org_governance_name", doc.org_governance_name], null);
    } else if (doc.type_ == "UserRole" && doc.governance_name != undefined) {
      emit([doc.type_, "governance_name", doc.governance_name], null);
    }
  }
}""",
        },
    },

    # -------------------------------------------------------------------------
    # Pure ION object related views
    # Every object has a type and ID
    'object':{
        'by_type':{
            'map':"""
function(doc) {
  if (doc.type_ != undefined) {
    emit([doc.type_], null);
  }
}""",
            },
        },

    # -------------------------------------------------------------------------
    # Attachment objects
    'attachment':{
        # Attachment for an object, ordered by create timestamp
        # Note: the keywords list is part of the index so that it can be checked
        # before retrieving attachment objects
        'by_resource':{
            'map':"""
function(doc) {
  if (doc.type_ == "Attachment") {
    emit([doc.object_id, doc.ts_created, doc.keywords], null);
  }
}""",
        },

    },

    # -------------------------------------------------------------------------
    # Association (triple) related views
    'association':{
        # Subject to object lookup (for range queries)
        'by_sub':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association" &&! doc.retired) {
    emit([doc.s, doc.p, doc.ot, doc.o], doc);
  }
}""",
            },
        # Object to subject lookup (for range queries)
        'by_obj':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association" &&! doc.retired) {
    emit([doc.o, doc.p, doc.st, doc.s], doc);
  }
}""",
            },
        # For matching association lookup (for range queries)
        'by_match':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association" &&! doc.retired) {
    emit([doc.s, doc.o, doc.p], doc);
  }
}""",
            },
        # For undirected association lookup with predicate (range queries)
        'by_idpred':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association" &&! doc.retired) {
    emit([doc.s, doc.p], doc);
    emit([doc.o, doc.p], doc);
  }
}""",
            },
        # For undirected association lookup with id only (multi key queries)
        'by_id':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association" &&! doc.retired) {
    emit(doc.s, doc);
    emit(doc.o, doc);
  }
}""",
            },
        # By predicate then subject then object
        'by_pred':{
            'map':"""
function(doc) {
  if (doc.type_ == "Association" &&! doc.retired) {
    emit([doc.p, doc.s, doc.o], doc);
  }
}""",
            },
        # Subject to object lookup (for multi key queries)
        'by_bulk':{
            'map':"""
function(doc) {
  if(doc.type_ == "Association" &&! doc.retired) {
    emit(doc.s, doc.o);
  }
}""",
            },
        'by_subject_bulk':{
            'map':"""
function(doc) {
  if(doc.type_ == "Association" &&! doc.retired) {
    emit(doc.o, doc.s);
  }
}""",
            }
    },

    # -------------------------------------------------------------------------
    # Directory related objects
    # DirEntry objects are the elements of the directory tree
    'directory':{
        'by_path':{
            'map':"""
function(doc) {
  if (doc.type_ == "DirEntry") {
    levels = doc.parent.split('/');
    levels.splice(0, 1);
    if (doc.parent == "/") levels.splice(0, 1);
    levels.push(doc.key);
    emit([doc.org, levels], doc);
  }
}""",
        },
        'by_key':{
            'map':"""
function(doc) {
  if (doc.type_ == "DirEntry") {
    emit([doc.org, doc.key, doc.parent], doc);
  }
}""",
        },
        'by_parent':{
            'map':"""
function(doc) {
  if (doc.type_ == "DirEntry") {
    emit([doc.org, doc.parent, doc.key], doc);
  }
}""",
        },
        'by_attribute':{
            'map':"""
function(doc) {
  if (doc.type_ == "DirEntry") {
    for (var attr in doc.attributes) {
      attval = doc.attributes[attr];
      if (attval != undefined && attval.length > 0) {
        attval = String(attval).substring(0,200);
      }
      emit([doc.org, attr, attval, doc.parent], doc);
    }
  }
}""",
        },
    },

    # -------------------------------------------------------------------------
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

    # -------------------------------------------------------------------------
    # Catalog is used by current preservation_management_service (which in turn is not used)
    'catalog': {
        'file_by_name': {
            "map": "\nfunction(doc) { \n\n    emit([doc.name + doc.extension, doc.owner_id, doc.group_id, doc.permissions, doc.modified_date, doc.created_date], doc._id);\n}\n\n        \n"
        },
        "file_by_created_date": {
            "map": "function(doc) {\n  emit(doc.created_date, doc._id);\n}"
        },
        "file_by_modified_date": {
            "map": "function(doc) {\n  emit(doc.modified_date, doc._id);\n}"
        },
        "file_by_owner": {
            "map": "function(doc) {\n  emit([doc.owner_id, doc.group_id, doc.name], doc._id);\n}"
        },
    }
}

def get_couchdb_view_designs(profile):
    store_profile = COUCHDB_PROFILES.get(profile, None) or COUCHDB_PROFILES["BASIC"]
    view_designs = store_profile['views']
    res_designs = {}
    for design in view_designs:
        res_designs[design] = COUCHDB_VIEWS[design]
    return res_designs
