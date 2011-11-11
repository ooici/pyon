#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from uuid import uuid4

import couchdb
from couchdb.http import ResourceConflict, ResourceNotFound

from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.datastore.datastore import DataStore
from pyon.util.log import log

class CouchDB_DataStore(DataStore):
    """
    Data store implementation utilizing CouchDB to persist documents.
    For API info, see: http://packages.python.org/CouchDB/client.html#
    """

    def __init__(self, host='localhost', port=5984, datastore_name='prototype', options=""):
        log.debug('host %s port %d data store name %s options %s' % (host, port, str(datastore_name), str(options)))
        self.host = host
        self.port = port
        self.datastore_name = datastore_name
        connection_str = "http://" + host + ":" + str(port)
        log.debug('Connecting to couchDB server: %s' % connection_str)
        self.server = couchdb.Server(connection_str)

    def create_datastore(self, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Creating data store %s' % datastore_name)
        self.server.create(datastore_name)
        return True

    def delete_datastore(self, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Deleting data store %s' % datastore_name)
        try:
            self.server.delete(datastore_name)
            return True
        except ResourceNotFound:
            log.info('Data store delete failed.  Data store %s not found' % datastore_name)
            raise NotFound('Data store delete failed.  Data store %s not found' % datastore_name)

    def list_datastores(self):
        log.debug('Listing all data stores')
        dbs = []
        for db in self.server:
            dbs.append(db)
        log.debug('Data stores: %s' % str(dbs))
        return dbs

    def info_datastore(self, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Listing information about data store %s' % datastore_name)
        info = self.server[datastore_name].info()
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
        log.debug('Listing all objects in data store %s' % datastore_name)
        objs = []
        for obj in self.server[datastore_name]:
            objs.append(obj)
        log.debug('Objects: %s' % str(objs))
        return objs

    def list_object_revisions(self, object_id, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        db = self.server[datastore_name]
        log.debug('Listing all versions of object %s/%s' % (datastore_name, str(object_id)))
        gen = db.revisions(object_id)
        res = []
        for ent in gen:
            res.append(ent["_rev"])
        log.debug('Versions: %s' % str(res))
        return res

    def create(self, object, object_id=None, datastore_name=""):
        return self.create_doc(self._ion_object_to_persistence_dict(object), object_id=object_id, datastore_name=datastore_name)

    def create_doc(self, doc, object_id=None, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name

        # Assign an id to doc (recommended in CouchDB documentation)
        doc["_id"] = object_id or uuid4().hex
        log.debug('Creating new object %s/%s' % (datastore_name, doc["_id"]))
        log.debug('create doc contents: %s', doc)

        # Save doc.  CouchDB will assign version to doc.
        res = self.server[datastore_name].save(doc)
        log.debug('Create result: %s' % str(res))
        id, version = res
        return [id, version]

    def read(self, object_id, rev_id="", datastore_name=""):
        doc = self.read_doc(object_id, rev_id, datastore_name)

        # Convert doc into Ion object
        obj = self._persistence_dict_to_ion_object(doc)
        log.debug('Ion object: %s' % str(obj))
        return obj

    def read_doc(self, doc_id, rev_id="", datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        db = self.server[datastore_name]
        if rev_id == "":
            log.debug('Reading head version of object %s/%s' % (datastore_name, str(doc_id)))
            doc = db.get(doc_id)
        else:
            log.debug('Reading version %s of object %s/%s' % (str(rev_id), datastore_name, str(doc_id)))
            doc = db.get(doc_id, rev=rev_id)
        log.debug('read doc contents: %s', doc)
        return doc

    def update(self, object, datastore_name=""):
        return self.update_doc(self._ion_object_to_persistence_dict(object))

    def update_doc(self, doc, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Saving new version of object %s/%s' % (datastore_name, doc["_id"]))
        log.debug('update doc contents: %s', doc)
        try:
            res = self.server[datastore_name].save(doc)
        except ResourceConflict:
            raise Conflict('Object not based on most current version')
        log.debug('Update result: %s' % str(res))
        id, version = res
        return [id, version]

    def delete(self, object, datastore_name=""):
        return self.delete_doc(self._ion_object_to_persistence_dict(object))

    def delete_doc(self, doc, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        db = self.server[datastore_name]
        log.debug('Deleting object %s/%s' % (datastore_name, doc["_id"]))
        res = db.delete(doc)
        log.debug('Delete result: %s' % str(res))
        return True

    def find(self, criteria=[], datastore_name=""):
        doc_list = self.find_docs(criteria, datastore_name)

        results = []
        # Convert each returned doc to its associated Ion object
        for doc in doc_list:
            obj = self._persistence_dict_to_ion_object(doc)
            log.debug('Ion object: %s' % str(obj))
            results.append(obj)

        return results

    def find_docs(self, criteria=[], datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        db = self.server[datastore_name]

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
        results = []
        for row in queryList:
            doc = row.value
            log.debug('find doc contents: %s', doc)
            results.append(doc)

        log.debug('Find results: %s' % str(results))
        return results

    def find_by_association(self, criteria=[], association="", datastore_name=""):
        doc_list = self.find_by_association_doc(criteria, association, datastore_name)

        results = []
        # Convert each returned doc to its associated Ion object
        for doc in doc_list:
            obj = self._persistence_dict_to_ion_object(doc)
            log.debug('Ion object: %s' % str(obj))
            results.append(obj)

        return results

    def find_by_association_doc(self, criteria=[], association="", datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        db = self.server[datastore_name]

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
            raise NotFound("Data store query for criteria %s failed" % str(criteria))
        if len(queryList) == 0:
            raise NotFound("Data store query for criteria %s returned no objects" % str(criteria))
        results = []
        for row in queryList:
            doc = row.doc
            results.append(doc)

        log.debug('Find results: %s' % str(results))
        return results

    def resolve_association(self, subject="", predicate="", object="", datastore_name=""):
        res_list = self.resolve_association_doc(subject, predicate, object, datastore_name)

        results = []
        # Convert each returned doc to its associated Ion object
        for item in res_list:
            subject_dict = item[0]
            object_dict = item[2]
            subject = self._persistence_dict_to_ion_object(subject_dict)
            log.debug('Subject Ion object: %s' % str(subject))
            object = self._persistence_dict_to_ion_object(object_dict)
            log.debug('Object Ion object: %s' % str(object))
            results.append([subject, item[1], object])

        return results

    def resolve_association_doc(self, subject="", predicate="", object="", datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        db = self.server[datastore_name]

        if subject == "":
            if predicate == "":
                if object == "":
                    # throw exception
                    raise BadRequest("Data store query does not specify subject, predicate or object")
                else:
                    # Find all subjects with any association to object
                    object_doc = self.read_doc(object, "", datastore_name)
                    res = []
                    all_doc_ids = self.list_objects(datastore_name)
                    for subject_doc_id in all_doc_ids:
                        if subject_doc_id == object:
                            continue
                        subject_doc = self.read_doc(subject_doc_id, "", datastore_name)
                        for key in subject_doc:
                            if isinstance(subject_doc[key], list):
                                if object in subject_doc[key]:
                                    res.append([subject_doc, key, object_doc])
                            else:
                                if object == subject_doc[key]:
                                    res.append([subject_doc, key, object_doc])

                    if len(res) == 0:
                        raise NotFound("Data store query for association %s/%s/%s returned no results" % (subject, predicate, object))
                    else:
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
                map_fun += object
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
                    raise NotFound("Data store query for association %s/%s/%s failed" % (subject, predicate, object))
                if len(queryList) == 0:
                    raise NotFound("Data store query for association %s/%s/%s returned no results" % (subject, predicate, object))
                res = []
                object_doc = self.read_doc(object, "", datastore_name)
                for row in queryList:
                    subject_doc = row.doc
                    res.append([subject_doc, predicate, object_doc])

                if len(res) == 0:
                    raise NotFound("Data store query for association %s/%s/%s returned no results" % (subject, predicate, object))
                else:
                    return res
        else:
            if predicate == "":
                if object == "":
                    # Find all objects with any association to subject
                    # TODO would need some way to indicate a key is an association predicate
                    pass
                else:
                    # Find all associations between subject and object
                    subject_doc = self.read_doc(subject, "", datastore_name)
                    object_doc = self.read_doc(object, "", datastore_name)
                    res = []
                    for key in subject_doc:
                        if isinstance(subject_doc[key], list):
                            if object in subject_doc[key]:
                                res.append([subject_doc, key, object_doc])
                        else:
                            if object == subject_doc[key]:
                                res.append([subject_doc, key, object_doc])

                    if len(res) == 0:
                        raise NotFound("Data store query for association %s/%s/%s returned no results" % (subject, predicate, object))
                    else:
                        return res
            else:
                if object == "":
                    # Find all associated objects
                    subject_doc = self.read_doc(subject, "", datastore_name)
                    res = []
                    if predicate in subject_doc:
                        for id in subject_doc[predicate]:
                            object_doc = self.read_doc(id, "", datastore_name)
                            res.append([subject_doc, predicate, object_doc])
                        return res
                    raise NotFound("Data store query for association %s/%s/%s returned no results" % (subject, predicate, object))
                else:
                    # Determine if association exists
                    subject_doc = self.read_doc(subject, "", datastore_name)
                    object_doc = self.read_doc(object, "", datastore_name)
                    if predicate in subject_doc:
                        if object in subject_doc[predicate]:
                            return [[subject_doc, predicate, object_doc]]
                    raise NotFound("Data store query for association %s/%s/%s returned no results" % (subject, predicate, object))

    def _ion_object_to_persistence_dict(self, ion_object):
        obj_dict = ion_object.__dict__.copy()
        obj_dict["type_"] = ion_object._def.type.name
        return obj_dict

    def _persistence_dict_to_ion_object(self, obj_dict):
        init_dict = obj_dict.copy()
        type = init_dict.pop("type_")
        ion_object = IonObject(type, init_dict)
        return ion_object
