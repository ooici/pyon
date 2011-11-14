#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from uuid import uuid4

from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.datastore.datastore import DataStore
from pyon.util.log import log

class MockDB_DataStore(DataStore):
    """
    Data store implementation utilizing in-memory dict of dicts
    to persist documents.
    """

    def __init__(self, datastore_name='prototype'):
        self.datastore_name = datastore_name
        log.debug('Creating in-memory dict of dicts that will simulate data stores')
        self.root = {}

    def create_datastore(self, datastore_name="", create_indexes=True):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Creating data store %s' % datastore_name)
        if datastore_name not in self.root:
            self.root[datastore_name] = {}
        return True

    def delete_datastore(self, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Deleting data store %s' % datastore_name)
        if datastore_name in self.root:
            del self.root[datastore_name]
        return True

    def list_datastores(self):
        log.debug('Listing all data stores')
        dsList = self.root.keys()
        log.debug('Data stores: %s' % str(dsList))
        return dsList

    def info_datastore(self, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Listing information about data store %s' % datastore_name)
        if datastore_name in self.root:
            info = 'Data store exists'
        else:
            info = 'Data store does not exist'
        log.debug('Data store info: %s' % str(info))
        return info

    def datastore_exists(self, datastore_name=""):
        return datastore_name in self.root

    def list_objects(self, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Listing all objects in data store %s' % datastore_name)
        objs = []
        for key, value in self.root[datastore_name].items():
            if key.find('_version_counter') == -1 and key.find('_version_') == -1:
                objs.append(key)
        log.debug('Objects: %s' % str(objs))
        return objs

    def list_object_revisions(self, object_id, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        log.debug('Listing all versions of object %s/%s' % (datastore_name, str(object_id)))
        res = []
        for key, value in self.root[datastore_name].items():
            if (key.find('_version_counter') == -1
                and (key.find(object_id + '_version_') == 0)):
                res.append(key)
        log.debug('Versions: %s' % str(res))
        return res

    def create(self, object, object_id=None, datastore_name=""):
        return self.create_doc(self._ion_object_to_persistence_dict(object), object_id=object_id, datastore_name=datastore_name)

    def create_doc(self, doc, object_id=None, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        # Assign an id to doc
        doc["_id"] = object_id or uuid4().hex
        object_id = doc["_id"]
        log.debug('Creating new object %s/%s' % (datastore_name, object_id))

        # Create key for version counter entry.  Will be used
        # on update to increment version number easily.
        versionCounterKey = '__' + object_id + '_version_counter'
        versionCounter = 1

        # Assign initial version to doc
        doc["_rev"] = versionCounter

        # Write HEAD, version and version counter dicts
        datastore_dict[object_id] = doc
        datastore_dict[versionCounterKey] = versionCounter
        datastore_dict[object_id + '_version_' + str(versionCounter)] = doc

        # Return list that identifies the id of the new doc and its version
        res = [object_id, str(versionCounter)]
        log.debug('Create result: %s' % str(res))
        return res

    def read(self, object_id, rev_id="", datastore_name=""):
        doc = self.read_doc(object_id, rev_id, datastore_name)

        # Convert doc into Ion object
        obj = self._persistence_dict_to_ion_object(doc)
        log.debug('Ion object: %s' % str(obj))
        return obj

    def read_doc(self, object_id, rev_id="", datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        try:
            key = object_id
            if rev_id == "":
                log.debug('Reading head version of object %s/%s' % (datastore_name, str(object_id)))
            else:
                log.debug('Reading version %s of object %s/%s' % (str(rev_id), datastore_name, str(object_id)))
                key += '_version_' + str(rev_id)
            doc = datastore_dict[key]
        except KeyError:
            raise NotFound('Object with id %s does not exist.' % str(object_id))
        log.debug('Read result: %s' % str(doc))
        return doc

    def update(self, object, datastore_name=""):
        return self.update_doc(self._ion_object_to_persistence_dict(object))

    def update_doc(self, doc, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        try:
            object_id = doc["_id"]

            # Find the next doc version
            versionCounterKey = '__' + object_id + '_version_counter'
            baseVersion = doc["_rev"]
            versionCounter = datastore_dict[versionCounterKey] + 1
            if baseVersion != versionCounter - 1:
                raise Conflict('Object not based on most current version')
        except KeyError:
            raise BadRequest("Object missing required _id and/or _rev values")

        log.debug('Saving new version of object %s/%s' % (datastore_name, doc["_id"]))
        doc["_rev"] = versionCounter

        # Overwrite HEAD and version counter dicts, add new version dict
        datastore_dict[object_id] = doc
        datastore_dict[versionCounterKey] = versionCounter
        datastore_dict[object_id + '_version_' + str(versionCounter)] = doc
        res = [object_id, str(versionCounter)]
        log.debug('Update result: %s' % str(res))
        return res

    def delete(self, object, datastore_name=""):
        return self.delete_doc(self._ion_object_to_persistence_dict(object))

    def delete_doc(self, doc, datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        object_id = doc["_id"]
        log.debug('Deleting object %s/%s' % (datastore_name, doc["_id"]))
        try:
            if object_id in datastore_dict.keys():
                # Find all version dicts and delete them
                for key in datastore_dict.keys():
                    if key.find(object_id + '_version_') == 0:
                        del datastore_dict[key]
                # Delete the HEAD dict
                del datastore_dict[object_id]
                # Delete the version counter dict
                del datastore_dict['__' + object_id + '_version_counter']
        except KeyError:
            raise NotFound('Object ' + object_id + ' does not exist.')
        log.debug('Delete result: True')
        return True

    def find(self, criteria=[], datastore_name=""):
        docList = self.find_doc(criteria, datastore_name)

        results = []
        # Convert each returned doc to its associated Ion object
        for doc in docList:
            obj = self._persistence_dict_to_ion_object(doc)
            log.debug('Ion object: %s' % str(obj))
            results.append(obj)

        return results

    def find_doc(self, criteria=[], datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        results = []
        log_string = "Searching for objects matching criteria list: " + str(criteria)
        log.debug(log_string)

        # Traverse entire data store, checking each HEAD version for equality
        # with specified criterion
        for obj_id in self.list_objects(datastore_name):
            try:
                doc = self.read_doc(obj_id, rev_id="", datastore_name=datastore_name)
                log.debug("Doc: %s" % str(doc))
                if len(criteria) == 0:
                    results.append(doc)
                else:
                    criteria_satisfied = False
                    for criterion in criteria:
                        if isinstance(criterion, list):
                            key = criterion[0]
                            logical_operation = criterion[1]
                            value = criterion[2]
                            if key in doc:
                                if logical_operation == DataStore.EQUAL:
                                    if doc[key] == value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                                elif logical_operation == DataStore.NOT_EQUAL:
                                    if doc[key] != value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                                elif logical_operation == DataStore.GREATER_THAN:
                                    if doc[key] > value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                                elif logical_operation == DataStore.GREATER_THAN_OR_EQUAL:
                                    if doc[key] >= value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                                elif logical_operation == DataStore.LESS_THAN:
                                    if doc[key] < value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                                elif logical_operation == DataStore.LESS_THAN_OR_EQUAL:
                                    if doc[key] <= value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                        else:
                            if criterion == DataStore.AND:
                                # Can shortcut the query at this point if the
                                # previous criterion failed
                                if criteria_satisfied == False:
                                    break

                    if criteria_satisfied:
                        results.append(doc)
                
            except KeyError:
                pass

        log.debug('Find results: %s' % str(results))

        if len(results) == 0:
            raise NotFound('No objects matched criteria %s' % criteria)

        return results

    def find_by_idref(self, criteria=[], association="", datastore_name=""):
        doc_list = self.find_by_idref_doc(criteria, association, datastore_name)

        results = []
        # Convert each returned doc to its associated Ion object
        for doc in doc_list:
            obj = self._persistence_dict_to_ion_object(doc)
            log.debug('Ion object: %s' % str(obj))
            results.append(obj)

        return results

    def find_by_idref_doc(self, criteria=[], association="", datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        ids = []
        log_string = "Searching for objects matching criteria list: " + str(criteria)
        log.debug(log_string)

        # Traverse entire data store, checking each HEAD version for equality
        # with specified criterion
        for obj_id in self.list_objects(datastore_name):
            try:
                doc = self.read_doc(obj_id, rev_id="", datastore_name=datastore_name)
                log.debug("Doc: %s" % str(doc))
                if len(criteria) == 0:
                    if association in doc:
                        for id in doc[association]:
                            ids.append(id)
                else:
                    criteria_satisfied = False
                    for criterion in criteria:
                        if isinstance(criterion, list):
                            key = criterion[0]
                            logical_operation = criterion[1]
                            value = criterion[2]
                            if key in doc:
                                if logical_operation == DataStore.EQUAL:
                                    if doc[key] == value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                                elif logical_operation == DataStore.NOT_EQUAL:
                                    if doc[key] != value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                                elif logical_operation == DataStore.GREATER_THAN:
                                    if doc[key] > value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                                elif logical_operation == DataStore.GREATER_THAN_OR_EQUAL:
                                    if doc[key] >= value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                                elif logical_operation == DataStore.LESS_THAN:
                                    if doc[key] < value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                                elif logical_operation == DataStore.LESS_THAN_OR_EQUAL:
                                    if doc[key] <= value:
                                        criteria_satisfied = True
                                    else:
                                        criteria_satisfied = False
                        else:
                            if criterion == DataStore.AND:
                                # Can shortcut the query at this point if the
                                # previous criterion failed
                                if criteria_satisfied == False:
                                    break

                    if criteria_satisfied:
                        if association in doc:
                            for id in doc[association]:
                                ids.append(id)

            except KeyError:
                pass

        results = []
        for id in ids:
            doc = self.read_doc(id, "", datastore_name)
            results.append(doc)

        log.debug('Find results: %s' % str(results))

        if len(results) == 0:
            raise NotFound('No objects matched criteria %s' % criteria)

        return results

    def resolve_idref(self, subject="", predicate="", object="", datastore_name=""):
        res_list = self.resolve_idref_doc(subject, predicate, object, datastore_name)

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

    def resolve_idref_doc(self, subject="", predicate="", object="", datastore_name=""):
        if datastore_name == "":
            datastore_name = self.datastore_name
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

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
                        raise NotFound("Data store query for association %s/%s/%s failed" % (subject, predicate, object))
                    else:
                        return res
            else:
                # Find all subjects with association to object
                object_doc = self.read_doc(object, "", datastore_name)
                res = []
                all_doc_ids = self.list_objects(datastore_name)
                for subject_doc_id in all_doc_ids:
                    if subject_doc_id == object:
                        continue
                    subject_doc = self.read_doc(subject_doc_id, "", datastore_name)
                    if predicate in subject_doc:
                        if object in subject_doc[predicate]:
                            res.append([subject_doc, predicate, object_doc])

                if len(res) == 0:
                    raise NotFound("Data store query for association %s/%s/%s failed" % (subject, predicate, object))
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
                        raise NotFound("Data store query for association %s/%s/%s failed" % (subject, predicate, object))
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
                    raise NotFound("Data store query for association %s/%s/%s failed" % (subject, predicate, object))
                else:
                    # Determine if association exists
                    subject_doc = self.read_doc(subject, "", datastore_name)
                    object_doc = self.read_doc(object, "", datastore_name)
                    if predicate in subject_doc:
                        if object in subject_doc[predicate]:
                            return [[subject_doc, predicate, object_doc]]
                    raise NotFound("Data store query for association %s/%s/%s failed" % (subject, predicate, object))

    def _ion_object_to_persistence_dict(self, ion_object):
        obj_dict = ion_object.__dict__.copy()
        obj_dict["type_"] = ion_object._def.type.name
        return obj_dict

    def _persistence_dict_to_ion_object(self, obj_dict):
        init_dict = obj_dict.copy()
        type = init_dict.pop("type_")
        ion_object = IonObject(type, init_dict)
        return ion_object
