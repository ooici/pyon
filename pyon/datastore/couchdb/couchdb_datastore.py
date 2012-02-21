#!/usr/bin/env python
from couchdb.client import ViewResults, Row

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from uuid import uuid4

import couchdb
from couchdb.http import PreconditionFailed, ResourceConflict, ResourceNotFound

from pyon.core.bootstrap import obj_registry
from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.core.object import IonObjectBase, IonObjectSerializer, IonObjectDeserializer
from pyon.datastore.datastore import DataStore
from pyon.datastore.couchdb.couchdb_config import get_couchdb_views
from pyon.ion.resource import ResourceLifeCycleSM
from pyon.util.log import log
from pyon.core.bootstrap import CFG
import hashlib

# Marks key range upper bound
END_MARKER = "ZZZZZ"

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


class CouchDB_DataStore(DataStore):
    """
    Data store implementation utilizing CouchDB to persist documents.
    For API info, see: http://packages.python.org/CouchDB/client.html
    """
    def __init__(self, host=None, port=None, datastore_name='prototype', options="", profile=DataStore.DS_PROFILE.BASIC):
        log.debug('__init__(host=%s, port=%s, datastore_name=%s, options=%s' % (host, port, datastore_name, options))
        self.host = host or CFG.server.couchdb.host
        self.port = port or CFG.server.couchdb.port
        # The scoped name of the datastore
        self.datastore_name = datastore_name
        self.auth_str = ""
        try:
            if CFG.server.couchdb.username and CFG.server.couchdb.password:
                self.auth_str = "%s:%s@" % (CFG.server.couchdb.username, CFG.server.couchdb.password)
                log.debug("Using username:password authentication to connect to datastore")
        except AttributeError:
            log.error("CouchDB username:password not configured correctly. Trying anonymous...")

        connection_str = "http://%s%s:%s" % (self.auth_str, self.host, self.port)
        #connection_str = "http://%s:%s" % (self.host, self.port)
        # TODO: Security risk to emit password into log. Remove later.
        log.info('Connecting to CouchDB server: %s' % connection_str)
        self.server = couchdb.Server(connection_str)

        # Datastore specialization
        self.profile = profile

        # serializers
        self._io_serializer     = IonObjectSerializer()
        self._io_deserializer   = IonObjectDeserializer(obj_registry=obj_registry)

    def close(self):
        log.info("Closing connection to CouchDB")
        map(lambda x: map(lambda y: y.close(), x), self.server.resource.session.conns.values())
        self.server.resource.session.conns = {}     # just in case we try to reuse this, for some reason

    def create_datastore(self, datastore_name="", create_indexes=True, profile=None):
        if not datastore_name:
            datastore_name = self.datastore_name
        profile = profile or self.profile
        log.info('Creating data store %s with profile=%s' % (datastore_name, profile))
        if self.datastore_exists(datastore_name):
            raise BadRequest("Data store with name %s already exists" % datastore_name)
        try:
            self.server.create(datastore_name)
        except ValueError:
            raise BadRequest("Data store name %s invalid" % datastore_name)
        if create_indexes:
            self._define_views(datastore_name, profile)

    def delete_datastore(self, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        log.info('Deleting data store %s' % datastore_name)
        try:
            self.server.delete(datastore_name)
        except ResourceNotFound:
            log.info('Data store %s does not exist' % datastore_name)
        except ValueError:
            raise BadRequest("Data store name %s invalid" % datastore_name)

    def list_datastores(self):
        dbs = [db for db in self.server]
        log.debug('Data stores: %s' % str(dbs))
        return dbs

    def info_datastore(self, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        log.debug('Listing information about data store %s' % datastore_name)
        try:
            info = self.server[datastore_name].info()
        except ResourceNotFound:
            raise BadRequest("Data store with name %s does not exist" % datastore_name)
        except ValueError:
            raise BadRequest("Data store name %s invalid" % datastore_name)
        log.debug('Data store info: %s' % str(info))
        return info

    def datastore_exists(self, datastore_name=""):
        for db in self.server:
            if db == datastore_name:
                return True
        return False

    def list_objects(self, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        log.warning('Listing all objects in data store %s' % datastore_name)
        try:
            objs = [obj for obj in self.server[datastore_name]]
        except ValueError:
            raise BadRequest("Data store name %s invalid" % datastore_name)
        log.debug('Objects: %s' % str(objs))
        return objs

    def list_object_revisions(self, object_id, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        try:
            db = self.server[datastore_name]
        except ValueError:
            raise BadRequest("Data store name %s invalid" % datastore_name)
        log.debug('Listing all versions of object %s/%s' % (datastore_name, object_id))
        gen = db.revisions(object_id)
        res = [ent["_rev"] for ent in gen]
        log.debug('Object versions: %s' % str(res))
        return res

    def create(self, obj, object_id=None, datastore_name=""):
        if not isinstance(obj, IonObjectBase):
            raise BadRequest("Obj param is not instance of IonObjectBase")
        return self.create_doc(self._ion_object_to_persistence_dict(obj),
                               object_id=object_id, datastore_name=datastore_name)

    def create_doc(self, doc, object_id=None, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        if '_id' in doc:
            raise BadRequest("Doc must not have '_id'")
        if '_rev' in doc:
            raise BadRequest("Doc must not have '_rev'")

        if object_id:
            try:
                self.read(object_id, '', datastore_name)
                raise BadRequest("Object with id %s already exist" % object_id)
            except NotFound:
                pass

        # Assign an id to doc (recommended in CouchDB documentation)
        doc["_id"] = object_id or uuid4().hex
        log.info('Creating new object %s/%s' % (datastore_name, doc["_id"]))
        log.debug('create doc contents: %s', doc)

        # Save doc.  CouchDB will assign version to doc.
        try:
            res = self.server[datastore_name].save(doc)
        except ResourceNotFound:
            raise BadRequest("Data store %s does not exist" % datastore_name)
        except ResourceConflict:
            raise BadRequest("Object with id %s already exist" % doc["_id"])
        except ValueError:
            raise BadRequest("Data store name %s invalid" % datastore_name)
        log.debug('Create result: %s' % str(res))
        id, version = res
        return (id, version)


    def _preload_create_doc(self, doc):
        log.info('Preloading object %s/%s' % (self.datastore_name, doc["_id"]))
        log.debug('create doc contents: %s', doc)

        # Save doc.  CouchDB will assign version to doc.
        try:
            res = self.server[self.datastore_name].save(doc)
        except ResourceNotFound:
            raise BadRequest("Data store %s does not exist" % self.datastore_name)
        except ResourceConflict:
            raise BadRequest("Object with id %s already exist" % doc["_id"])
        except ValueError:
            raise BadRequest("Data store name %s invalid" % self.datastore_name)
        log.debug('Create result: %s' % str(res))

    def create_mult(self, objects, object_ids=None):
        if any([not isinstance(obj, IonObjectBase) for obj in objects]):
            raise BadRequest("Obj param is not instance of IonObjectBase")
        return self.create_doc_mult([self._ion_object_to_persistence_dict(obj) for obj in objects],
                                    object_ids)

    def create_doc_mult(self, docs, object_ids=None):
        if any(["_id" in doc for doc in docs]):
            raise BadRequest("Docs must not have '_id'")
        if any(["_rev" in doc for doc in docs]):
            raise BadRequest("Docs must not have '_rev'")
        if object_ids and len(object_ids) != len(docs):
            raise BadRequest("Invalid object_ids")

        # Assign an id to doc (recommended in CouchDB documentation)
        object_ids = object_ids or [uuid4().hex for i in xrange(len(docs))]

        for doc, oid in zip(docs, object_ids):
            doc["_id"] = oid

        # Update docs.  CouchDB will assign versions to docs.
        res = self.server[self.datastore_name].update(docs)
        if not res or not all([success for success, oid, rev in res]):
            log.error('Create error. Result: %s' % str(res))
        else:
            log.debug('Create result: %s' % str(res))
        return res

    def read(self, object_id, rev_id="", datastore_name=""):
        if not isinstance(object_id, str):
            raise BadRequest("Object id param is not string")
        doc = self.read_doc(object_id, rev_id, datastore_name)

        # Convert doc into Ion object
        obj = self._persistence_dict_to_ion_object(doc)
        log.debug('Ion object: %s' % str(obj))
        return obj

    def read_doc(self, doc_id, rev_id="", datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        try:
            db = self.server[datastore_name]
        except ValueError:
            raise BadRequest("Data store name %s is invalid" % datastore_name)
        if not rev_id:
            log.debug('Reading head version of object %s/%s' % (datastore_name, doc_id))
            doc = db.get(doc_id)
            if doc is None:
                raise NotFound('Object with id %s does not exist.' % str(doc_id))
        else:
            log.debug('Reading version %s of object %s/%s' % (rev_id, datastore_name, doc_id))
            doc = db.get(doc_id, rev=rev_id)
            if doc is None:
                raise NotFound('Object with id %s does not exist.' % str(doc_id))
        log.debug('read doc contents: %s', doc)
        return doc

    def read_mult(self, object_ids, datastore_name=""):
        if any([not isinstance(object_id, str) for object_id in object_ids]):
            raise BadRequest("Object id param is not string")
        docs = self.read_doc_mult(object_ids, datastore_name)
        # Convert docs into Ion objects
        obj_list = [self._persistence_dict_to_ion_object(doc) for doc in docs]
        return obj_list

    def read_doc_mult(self, object_ids, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        try:
            db = self.server[datastore_name]
        except ValueError:
            raise BadRequest("Data store name %s is invalid" % datastore_name)
        log.info('Reading head version of objects %s/%s' % (datastore_name, object_ids))
        docs = db.view("_all_docs", keys=object_ids, include_docs=True)
        # Check for docs not found
        error_str = ""
        for row in docs:
            if row.doc is None:
                if error_str != "":
                    error_str += "\n"
                error_str += 'Object with id %s does not exist.' % str(row.key)
        if error_str != "":
            raise NotFound(error_str)

        doc_list = [row.doc.copy() for row in docs]
        return doc_list
    
    def update(self, obj, datastore_name=""):
        if not isinstance(obj, IonObjectBase):
            raise BadRequest("Obj param is not instance of IonObjectBase")
        return self.update_doc(self._ion_object_to_persistence_dict(obj))

    def update_doc(self, doc, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        if '_id' not in doc:
            raise BadRequest("Doc must have '_id'")
        if '_rev' not in doc:
            raise BadRequest("Doc must have '_rev'")
        
        # First, try to read document to ensure it exists
        # Have to do this because save will create a new doc
        # if it doesn't exist.  We don't want this side-effect.
        self.read_doc(doc["_id"], doc["_rev"], datastore_name)

        log.info('Saving new version of object %s/%s' % (datastore_name, doc["_id"]))
        log.debug('update doc contents: %s', doc)
        try:
            res = self.server[datastore_name].save(doc)
        except ResourceConflict:
            raise Conflict('Object not based on most current version')
        log.debug('Update result: %s' % str(res))
        id, version = res
        return (id, version)

    def delete(self, obj, datastore_name=""):
        if not isinstance(obj, IonObjectBase) and not isinstance(obj, str):
            raise BadRequest("Obj param is not instance of IonObjectBase or string id")
        if type(obj) is str:
            self.delete_doc(obj, datastore_name=datastore_name)
        else:
            if '_id' not in obj:
                raise BadRequest("Doc must have '_id'")
            if '_rev' not in obj:
                raise BadRequest("Doc must have '_rev'")
            self.delete_doc(self._ion_object_to_persistence_dict(obj), datastore_name=datastore_name)

    def delete_doc(self, doc, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        try:
            db = self.server[datastore_name]
        except ValueError:
            raise BadRequest("Data store name %s is invalid" % datastore_name)
        if type(doc) is str:
            log.info('Deleting object %s/%s' % (datastore_name, doc))
            if self._is_in_association(doc, datastore_name):
                obj = self.read(doc, datastore_name)
                log.warn("XXXXXXX Attempt to delete object %s that still has associations" % str(obj))
#                raise BadRequest("Object cannot be deleted until associations are broken")
            try:
                del db[doc]
            except ResourceNotFound:
                raise NotFound('Object with id %s does not exist.' % str(doc))
        else:
            log.info('Deleting object %s/%s' % (datastore_name, doc["_id"]))
            if self._is_in_association(doc["_id"], datastore_name):
                log.warn("XXXXXXX Attempt to delete object %s that still has associations" % str(doc))
#                raise BadRequest("Object cannot be deleted until associations are broken")
            try:
                res = db.delete(doc)
            except ResourceNotFound:
                raise NotFound('Object with id %s does not exist.' % str(doc["_id"]))
            log.debug('Delete result: %s' % str(res))

    def find(self, criteria=[], datastore_name=""):
        doc_list = self.find_doc(criteria, datastore_name)
        results = [self._persistence_dict_to_ion_object(doc) for doc in doc_list]
        return results

    def find_doc(self, criteria=[], datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        try:
            db = self.server[datastore_name]
        except ValueError:
            raise BadRequest("Data store name %s is invalid" % datastore_name)

        if len(criteria) == 0:
            # Return set of all objects indexed by doc id
            map_fun =\
'''function(doc) {
    emit(doc._id, doc);
}'''
        else:
            map_fun =\
'''function(doc) {
    if ('''
            for criterion in criteria:
                if isinstance(criterion, list):
                    if len(criterion) != 3:
                        raise BadRequest("Insufficient criterion values specified.  Much match [<field>, <logical constant>, <value>]")
                    map_fun += "doc." + criterion[0]
                    map_fun += " " + criterion[1] + " "
                    map_fun += "\"" + str(criterion[2]) + "\""
                else:
                    if criterion == DataStore.AND:
                        map_fun += ' && '
                    else:
                        map_fun += ' || '

            map_fun +=\
''') {
        emit(doc._id, doc);
    }
}'''

        log.debug("map_fun: %s" % str(map_fun))
        try:
            queryList = list(db.query(map_fun))
        except ResourceNotFound:
            raise NotFound("Data store query for criteria %s failed" % str(criteria))
        if len(queryList) == 0:
            raise NotFound("Data store query for criteria %s returned no objects" % str(criteria))
        results = [row.value for row in queryList]

        log.debug('Find results: %s' % str(results))
        log.warning('Find is an expensive debug only function. Use a specific find function instead.')
        return results

    def find_by_idref(self, criteria=[], association="", datastore_name=""):
        doc_list = self.find_by_idref_doc(criteria, association, datastore_name)
        results = [self._persistence_dict_to_ion_object(doc) for doc in doc_list]
        return results

    def find_by_idref_doc(self, criteria=[], association="", datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        try:
            db = self.server[datastore_name]
        except ValueError:
            raise BadRequest("Data store name %s is invalid" % datastore_name)

        if len(criteria) == 0:
            # Return set of all objects indexed by doc id
            map_fun =\
'''function(doc) {
    if (doc.'''
            map_fun += association
            map_fun +=\
''') {
        for (var i in doc.'''
            map_fun += association
            map_fun +=\
''') {
            emit(i, {_id: doc.'''
            map_fun += association
            map_fun +=\
'''[i]});
        }
    }
}'''
        else:
            map_fun =\
'''function(doc) {
    if ('''
            for criterion in criteria:
                if isinstance(criterion, list):
                    map_fun += "doc." + criterion[0]
                    map_fun += " " + criterion[1] + " "
                    map_fun += "\"" + criterion[2] + "\""
                else:
                    if criterion == DataStore.AND:
                        map_fun += ' && '
                    else:
                        map_fun += ' || '

            map_fun +=\
''') {
        if (doc.'''
            map_fun += association
            map_fun +=\
''') {
            for (var i in doc.'''
            map_fun += association
            map_fun +=\
''') {
                emit([doc.'''
            map_fun += association
            map_fun +=\
''', i], {_id: doc.'''
            map_fun += association
            map_fun +=\
'''[i]});
            }
        }
    }
}'''

        log.debug("map_fun: %s" % str(map_fun))
        try:
            queryList = list(db.query(map_fun, include_docs=True))
        except ResourceNotFound:
            return []
        if len(queryList) == 0:
            return []
        results = [row.doc for row in queryList]
        log.debug('Find results: %s' % str(results))
        return results

    def resolve_idref(self, subject="", predicate="", obj="", datastore_name=""):
        res_list = self.resolve_idref_doc(subject, predicate, obj, datastore_name)

        results = []
        # Convert each returned doc to its associated Ion object
        for item in res_list:
            subject_dict = item[0]
            object_dict = item[2]
            subject = self._persistence_dict_to_ion_object(subject_dict)
            log.debug('Subject Ion object: %s' % str(subject))
            ion_obj = self._persistence_dict_to_ion_object(object_dict)
            log.debug('Object Ion object: %s' % str(ion_obj))
            results.append([subject, item[1], ion_obj])

        return results

    def resolve_idref_doc(self, subject="", predicate="", obj="", datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        try:
            db = self.server[datastore_name]
        except ValueError:
            raise BadRequest("Data store name %s is invalid" % datastore_name)

        if subject == "":
            if predicate == "":
                if obj == "":
                    # throw exception
                    raise BadRequest("Data store query does not specify subject, predicate or object")
                else:
                    # Find all subjects with any association to object
                    object_doc = self.read_doc(obj, "", datastore_name)
                    res = []
                    all_doc_ids = self.list_objects(datastore_name)
                    for subject_doc_id in all_doc_ids:
                        if subject_doc_id == obj:
                            continue
                        subject_doc = self.read_doc(subject_doc_id, "", datastore_name)
                        for key in subject_doc:
                            if isinstance(subject_doc[key], list):
                                if obj in subject_doc[key]:
                                    res.append([subject_doc, key, object_doc])
                            else:
                                if obj == subject_doc[key]:
                                    res.append([subject_doc, key, object_doc])

                    return res
            else:
                # Find all subjects with association to object
                map_fun =\
'''function(doc) {
    if (doc.'''
                map_fun += predicate
                map_fun +=\
''') {
        for (var i in doc.'''
                map_fun += predicate
                map_fun +=\
''') {
            if (doc.'''
                map_fun += predicate
                map_fun +=\
'''[i] == \"'''
                map_fun += obj
                map_fun +=\
'''") {
                emit(doc._id, doc);
            }
        }
    }
}'''

                log.debug("map_fun: %s" % str(map_fun))
                try:
                    queryList = list(db.query(map_fun, include_docs=True))
                except ResourceNotFound:
                    return []
                if len(queryList) == 0:
                    return []
                res = []
                object_doc = self.read_doc(obj, "", datastore_name)
                for row in queryList:
                    subject_doc = row.doc
                    res.append([subject_doc, predicate, object_doc])

                return res
        else:
            if predicate == "":
                if obj == "":
                    # Find all objects with any association to subject
                    # TODO would need some way to indicate a key is an association predicate
                    pass
                else:
                    # Find all associations between subject and object
                    subject_doc = self.read_doc(subject, "", datastore_name)
                    object_doc = self.read_doc(obj, "", datastore_name)
                    res = []
                    for key in subject_doc:
                        if isinstance(subject_doc[key], list):
                            if obj in subject_doc[key]:
                                res.append([subject_doc, key, object_doc])
                        else:
                            if obj == subject_doc[key]:
                                res.append([subject_doc, key, object_doc])

                    if len(res) == 0:
                        return []
                    else:
                        return res
            else:
                if obj == "":
                    # Find all associated objects
                    subject_doc = self.read_doc(subject, "", datastore_name)
                    res = []
                    if predicate in subject_doc:
                        for id in subject_doc[predicate]:
                            object_doc = self.read_doc(id, "", datastore_name)
                            res.append([subject_doc, predicate, object_doc])
                    return res
                else:
                    # Determine if association exists
                    subject_doc = self.read_doc(subject, "", datastore_name)
                    object_doc = self.read_doc(obj, "", datastore_name)
                    if predicate in subject_doc:
                        if obj in subject_doc[predicate]:
                            return [[subject_doc, predicate, object_doc]]
                    return []

    def _get_viewname(self, design, name):
        return "_design/%s/_view/%s" % (design, name)

    def _define_views(self, datastore_name=None, profile=None, keepviews=False):
        datastore_name = datastore_name or self.datastore_name
        profile = profile or self.profile

        ds_views = get_couchdb_views(profile)
        for design, viewdef in ds_views.iteritems():
            self._define_view(design, viewdef, datastore_name=datastore_name, keepviews=keepviews)

    def _define_view(self, design, viewdef, datastore_name=None, keepviews=False):
        datastore_name = datastore_name or self.datastore_name
        db = self.server[datastore_name]
        viewname = "_design/%s" % design
        if keepviews and viewname in db:
            return
        try:
            del db[viewname]
        except ResourceNotFound:
            pass
        db[viewname] = dict(views=viewdef)

    def _update_views(self, datastore_name="", profile=None):
        if not datastore_name:
            datastore_name = self.datastore_name
        db = self.server[datastore_name]

        profile = profile or self.profile
        ds_views = get_couchdb_views(profile)

        for design, viewdef in ds_views.iteritems():
            for viewname in viewdef:
                try:
                    rows = db.view("_design/%s/_view/%s" % (design, viewname))
                    log.debug("View %s/_design/%s/_view/%s: %s rows" % (datastore_name, design, viewname, len(rows)))
                except Exception, ex:
                    log.exception("Problem with view %s/_design/%s/_view/%s" % (datastore_name, design, viewname))

    _refresh_views = _update_views

    def _delete_views(self, datastore_name="", profile=None):
        if not datastore_name:
            datastore_name = self.datastore_name
        db = self.server[datastore_name]

        profile = profile or self.profile
        ds_views = get_couchdb_views(profile)

        for design, viewdef in ds_views.iteritems():
            try:
                del db["_design/%s" % design]
            except ResourceNotFound:
                pass

    def _is_in_association(self, obj_id, datastore_name=""):
        log.debug("_is_in_association(%s)" % obj_id)
        if not obj_id:
            raise BadRequest("Must provide object id")
        if not datastore_name:
            datastore_name = self.datastore_name
        db = self.server[datastore_name]

        view = db.view(self._get_viewname("association","all"))
        associations = [row.value for row in view]

        for association in associations:
            if association["s"] == obj_id or association["o"] == obj_id:
                log.debug("association found(%s)" % association)
                return True
        return False

    def find_objects(self, subject, predicate=None, object_type=None, id_only=False):
        log.debug("find_objects(subject=%s, predicate=%s, object_type=%s, id_only=%s" % (subject, predicate, object_type, id_only))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not subject:
            raise BadRequest("Must provide subject")
        db = self.server[self.datastore_name]

        if type(subject) is str:
            subject_id = subject
        else:
            if "_id" not in subject:
                raise BadRequest("Object id not available in subject")
            else:
                subject_id = subject._id
        view = db.view(self._get_viewname("association","all"))
        associations = [row.value for row in view]

        obj_assocs = []
        obj_ids = []
        for association in associations:
            if association["s"] == subject_id:
                if predicate:
                    if association["p"] == predicate:
                        if object_type:
                            if association["ot"] == object_type:
                                obj_assocs.append(self._persistence_dict_to_ion_object(association))
                                obj_ids.append(association["o"])
                        else:
                            obj_assocs.append(self._persistence_dict_to_ion_object(association))
                            obj_ids.append(association["o"])
                else:
                    obj_assocs.append(self._persistence_dict_to_ion_object(association))
                    obj_ids.append(association["o"])

        log.debug("find_objects() found %s objects" % (len(obj_ids)))
        if id_only:
            return (obj_ids, obj_assocs)

        obj_list = self.read_mult(obj_ids)
        return (obj_list, obj_assocs)

    def find_subjects(self, subject_type=None, predicate=None, obj=None, id_only=False):
        log.debug("find_subjects(subject_type=%s, predicate=%s, object=%s, id_only=%s" % (subject_type, predicate, obj, id_only))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not obj:
            raise BadRequest("Must provide object")
        db = self.server[self.datastore_name]

        if type(obj) is str:
            object_id = obj
        else:
            if "_id" not in obj:
                raise BadRequest("Object id not available in object")
            else:
                object_id = obj._id
        view = db.view(self._get_viewname("association","all"))
        associations = [row.value for row in view]

        sub_assocs = []
        sub_ids = []
        for association in associations:
            if association["o"] == object_id:
                if predicate:
                    if association["p"] == predicate:
                        if subject_type:
                            if association["st"] == subject_type:
                                sub_assocs.append(self._persistence_dict_to_ion_object(association))
                                sub_ids.append(association["s"])
                        else:
                            sub_assocs.append(self._persistence_dict_to_ion_object(association))
                            sub_ids.append(association["s"])
                else:
                    sub_assocs.append(self._persistence_dict_to_ion_object(association))
                    sub_ids.append(association["s"])

        log.debug("find_subjects() found %s subjects" % (len(sub_ids)))
        if id_only:
            return (sub_ids, sub_assocs)

        sub_list = self.read_mult(sub_ids)
        return (sub_list, sub_assocs)

    def find_associations(self, subject=None, predicate=None, obj=None, id_only=True):
        log.debug("find_associations(subject=%s, predicate=%s, object=%s)" % (subject, predicate, obj))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if subject and obj or predicate:
            pass
        else:
            raise BadRequest("Illegal parameters")
        db = self.server[self.datastore_name]

        if subject and obj:
            if type(subject) is str:
                subject_id = subject
            else:
                if "_id" not in subject:
                    raise BadRequest("Object id not available in subject")
                else:
                    subject_id = subject._id
            if type(obj) is str:
                object_id = obj
            else:
                if "_id" not in obj:
                    raise BadRequest("Object id not available in object")
                else:
                    object_id = obj._id
            view = db.view(self._get_viewname("association","by_ids"), include_docs=(not id_only))
            key = [subject_id, object_id]
            if predicate:
                key.append(predicate)
            endkey = list(key)
            endkey.append(END_MARKER)
            rows = view[key:endkey]
        else:
            view = db.view(self._get_viewname("association","by_pred"), include_docs=(not id_only))
            key = [predicate]
            endkey = list(key)
            endkey.append(END_MARKER)
            rows = view[key:endkey]

        if id_only:
            assocs = [row.id for row in rows]
        else:
            assocs = [self._persistence_dict_to_ion_object(row.doc.copy()) for row in rows]
        log.debug("find_associations() found %s associations" % (len(assocs)))
        return assocs

    def find_res_by_type(self, restype, lcstate=None, id_only=False):
        log.debug("find_res_by_type(restype=%s, lcstate=%s)" % (restype, lcstate))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        db = self.server[self.datastore_name]
        view = db.view(self._get_viewname("resource","by_type"), include_docs=(not id_only))
        if restype:
            key = [restype]
            if lcstate:
                key.append(lcstate)
            endkey = list(key)
            endkey.append(END_MARKER)
            rows = view[key:endkey]
        else:
            rows = view

        res_assocs = [dict(type=row['key'][0], lcstate=row['key'][1], name=row['key'][2], id=row.id) for row in rows]
        log.debug("find_res_by_type() found %s objects" % (len(res_assocs)))
        if id_only:
            res_ids = [row.id for row in rows]
            return (res_ids, res_assocs)
        else:
            res_docs = [self._persistence_dict_to_ion_object(row.doc) for row in rows]
            return (res_docs, res_assocs)

    def find_res_by_lcstate(self, lcstate, restype=None, id_only=False):
        log.debug("find_res_by_lcstate(lcstate=%s, restype=%s)" % (lcstate, restype))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        db = self.server[self.datastore_name]
        view = db.view(self._get_viewname("resource","by_lcstate"), include_docs=(not id_only))
        is_hierarchical = (lcstate in ResourceLifeCycleSM.STATE_ALIASES)
        # lcstate is a hiearachical state and we need to treat the view differently
        if is_hierarchical:
            key = [1, lcstate]
        else:
            key = [0, lcstate]
        if restype:
            key.append(restype)
        endkey = list(key)
        endkey.append(END_MARKER)
        rows = view[key:endkey]

        if is_hierarchical:
            res_assocs = [dict(lcstate=row['key'][3], type=row['key'][2], name=row['key'][4], id=row.id) for row in rows]
        else:
            res_assocs = [dict(lcstate=row['key'][1], type=row['key'][2], name=row['key'][3], id=row.id) for row in rows]

        log.debug("find_res_by_lcstate() found %s objects" % (len(res_assocs)))
        if id_only:
            res_ids = [row.id for row in rows]
            return (res_ids, res_assocs)
        else:
            res_docs = [self._persistence_dict_to_ion_object(row.doc) for row in rows]
            return (res_docs, res_assocs)

    def find_res_by_name(self, name, restype=None, id_only=False):
        log.debug("find_res_by_name(name=%s, restype=%s)" % (name, restype))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        db = self.server[self.datastore_name]
        view = db.view(self._get_viewname("resource","by_name"), include_docs=(not id_only))
        key = [name]
        if restype:
            key.append(restype)
        endkey = list(key)
        endkey.append(END_MARKER)
        rows = view[key:endkey]

        res_assocs = [dict(name=row['key'][0], type=row['key'][1], lcstate=row['key'][2], id=row.id) for row in rows]
        log.debug("find_res_by_name() found %s objects" % (len(res_assocs)))
        if id_only:
            res_ids = [row.id for row in rows]
            return (res_ids, res_assocs)
        else:
            res_docs = [self._persistence_dict_to_ion_object(row.doc) for row in rows]
            return (res_docs, res_assocs)

    def find_dir_entries(self, qname):
        log.debug("find_dir_entries(qname=%s)" % (qname))
        if not str(qname).startswith('/'):
            raise BadRequest("Illegal directory qname=%s" % qname)
        db = self.server[self.datastore_name]
        view = db.view(self._get_viewname("directory","by_path"))
        key = str(qname).split('/')[1:]
        endkey = list(key)
        endkey.append(END_MARKER)
        if qname == '/': del endkey[0]
        rows = view[key:endkey]
        res_entries = [self._persistence_dict_to_ion_object(row.value) for row in rows]
        log.debug("find_dir_entries() found %s objects" % (len(res_entries)))
        return res_entries

    def find_by_view(self, design_name, view_name, start_key=None, end_key=None,
                           max_res=0, reverse=False, id_only=True, convert_doc=True):
        """
        @brief Generic find function using an defined index
        """
        log.debug("find_by_view(%s/%s)" % (design_name, view_name))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        db = self.server[self.datastore_name]
        kwargs = {}
        kwargs['include_docs'] = (not id_only)
        if max_res > 0:
            kwargs['limit'] = max_res
        if reverse:
            kwargs['descending'] = True
        # TODO: Add more view params (see http://wiki.apache.org/couchdb/HTTP_view_API)
        view_doc = design_name if design_name == "_all_docs" else self._get_viewname(design_name, view_name)
        view = db.view(view_doc, **kwargs)
        key = start_key or []
        endkey = end_key or []
        endkey.append(END_MARKER)
        if reverse:
            rows = view[endkey:key]
        else:
            rows = view[key:endkey]

        if id_only:
            res_rows = [(row['id'],row['key'], None) for row in rows]
        else:
            if convert_doc:
                res_rows = [(row['id'],row['key'],self._persistence_dict_to_ion_object(row['doc'])) for row in rows]
            else:
                res_rows = [(row['id'],row['key'],row['doc']) for row in rows]

        log.debug("find_by_view() found %s objects" % (len(res_rows)))
        return res_rows

    def _ion_object_to_persistence_dict(self, ion_object):
        if ion_object is None: return None

        obj_dict = self._io_serializer.serialize(ion_object)
        return obj_dict

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
            if 'id' in doc:
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
                return self._persistence_dict_to_ion_object(doc)

            for key,value in doc.iteritems():
                ret[key] = self._parse_results(value)
            return ret

        #-------------------------------
        # Primitive type
        #-------------------------------
        return doc

    def _persistence_dict_to_ion_object(self, obj_dict):
        if obj_dict is None: return None

        ion_object = self._io_deserializer.deserialize(obj_dict)
        return ion_object

