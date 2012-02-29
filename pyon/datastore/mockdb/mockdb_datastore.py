#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from uuid import uuid4

from pyon.core.bootstrap import obj_registry
from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.core.object import IonObjectBase, IonObjectSerializer, IonObjectDeserializer
from pyon.datastore.datastore import DataStore
from pyon.ion.resource import CommonResourceLifeCycleSM
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

        # serializers
        self._io_serializer     = IonObjectSerializer()
        self._io_deserializer   = IonObjectDeserializer(obj_registry=obj_registry)

    def create_datastore(self, datastore_name="", create_indexes=True):
        if not datastore_name:
            datastore_name = self.datastore_name
        log.info('Creating data store %s' % datastore_name)
        if self.datastore_exists(datastore_name):
            raise BadRequest("Data store with name %s already exists" % datastore_name)
        if datastore_name not in self.root:
            self.root[datastore_name] = {}

    def delete_datastore(self, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        log.info('Deleting data store %s' % datastore_name)
        if datastore_name in self.root:
            del self.root[datastore_name]
        else:
            log.info('Data store %s does not exist' % datastore_name)

    def list_datastores(self):
        log.debug('Listing all data stores')
        dsList = self.root.keys()
        log.debug('Data stores: %s' % str(dsList))
        return dsList

    def info_datastore(self, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        log.debug('Listing information about data store %s' % datastore_name)
        if datastore_name in self.root:
            info = 'Data store exists'
        else:
            raise BadRequest("Data store with name %s does not exist" % datastore_name)
        log.debug('Data store info: %s' % str(info))
        return info

    def datastore_exists(self, datastore_name=""):
        return datastore_name in self.root

    def list_objects(self, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        log.debug('Listing all objects in data store %s' % datastore_name)
        objs = []
        for key, value in self.root[datastore_name].items():
            if key.find('_version_counter') == -1 and key.find('_version_') == -1:
                objs.append(key)
        log.debug('Objects: %s' % str(objs))
        return objs

    def list_object_revisions(self, object_id, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        log.debug('Listing all versions of object %s/%s' % (datastore_name, str(object_id)))
        res = []
        for key, value in self.root[datastore_name].items():
            if (key.find('_version_counter') == -1
                and (key.find(object_id + '_version_') == 0)):
                res.append(key)
        log.debug('Versions: %s' % str(res))
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
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        if object_id:
            if object_id in datastore_dict:
                raise BadRequest("Object with id %s already exist" % object_id)

        # Assign an id to doc
        doc["_id"] = object_id or uuid4().hex
        object_id = doc["_id"]

        log.debug('Creating new object %s/%s' % (datastore_name, object_id))

        # Create key for version counter entry.  Will be used
        # on update to increment version number easily.
        version_counter_key = '__' + object_id + '_version_counter'
        version_counter = 1

        # Assign initial version to doc
        doc["_rev"] = str(version_counter)

        # Write HEAD, version and version counter dicts
        datastore_dict[object_id] = doc
        datastore_dict[version_counter_key] = version_counter
        datastore_dict[object_id + '_version_' + str(version_counter)] = doc

        # Return list that identifies the id of the new doc and its version
        res = [object_id, str(version_counter)]
        log.debug('Create result: %s' % str(res))
        return res

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

        res = []
        for doc, oid in zip(docs, object_ids):
            oid,rev = self.create_doc(doc, oid)
            res.append((True,oid,rev))
        return res

    def read(self, object_id, rev_id="", datastore_name=""):
        if not isinstance(object_id, str):
            raise BadRequest("Object id param is not string")
        doc = self.read_doc(object_id, rev_id, datastore_name)

        # Convert doc into Ion object
        obj = self._persistence_dict_to_ion_object(doc)
        log.debug('Ion object: %s' % str(obj))
        return obj

    def read_doc(self, object_id, rev_id="", datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        try:
            key = object_id
            if rev_id != None and rev_id != "":
                log.debug('Reading version %s of object %s/%s' % (str(rev_id), datastore_name, str(object_id)))
                key += '_version_' + str(rev_id)
            else:
                log.debug('Reading head version of object %s/%s' % (datastore_name, str(object_id)))
            doc = datastore_dict[key]
        except KeyError:
            raise NotFound('Object with id %s does not exist.' % str(object_id))
        log.debug('Read result: %s' % str(doc))
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
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        doc_list = []
        try:
            for object_id in object_ids:
                log.debug('Reading head version of object %s/%s' % (datastore_name, str(object_id)))
                doc = datastore_dict[object_id]

                doc_list.append(doc.copy())
        except KeyError:
            raise NotFound('Object with id %s does not exist.' % str(object_id))
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
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        try:
            object_id = doc["_id"]

            # Find the next doc version
            version_counter_key = '__' + object_id + '_version_counter'
            baseVersion = doc["_rev"]
            version_counter = datastore_dict[version_counter_key] + 1
            if baseVersion != str(version_counter - 1):
                raise Conflict('Object not based on most current version')
        except KeyError:
            raise BadRequest("Object missing required _id and/or _rev values")

        log.debug('Saving new version of object %s/%s' % (datastore_name, doc["_id"]))
        doc["_rev"] = str(version_counter)

        # Overwrite HEAD and version counter dicts, add new version dict
        datastore_dict[object_id] = doc
        datastore_dict[version_counter_key] = version_counter
        datastore_dict[object_id + '_version_' + str(version_counter)] = doc
        res = [object_id, str(version_counter)]
        log.debug('Update result: %s' % str(res))
        return res

    def delete(self, obj, datastore_name=""):
        if not isinstance(obj, IonObjectBase) and not isinstance(obj, str):
            raise BadRequest("Obj param is not instance of IonObjectBase or string id")
        if type(obj) is str:
            return self.delete_doc(obj, datastore_name=datastore_name)
        return self.delete_doc(self._ion_object_to_persistence_dict(obj), datastore_name=datastore_name)

    def delete_doc(self, doc, datastore_name=""):
        if not datastore_name:
            datastore_name = self.datastore_name
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        if type(doc) is str:
            object_id = doc
        else:
            object_id = doc["_id"]
        
        log.info('Deleting object %s/%s' % (datastore_name, object_id))
        if object_id in datastore_dict.keys():

            if self._is_in_association(object_id, datastore_name):
                obj = self.read(object_id, "", datastore_name)
                log.warn("XXXXXXX Attempt to delete object %s that still has associations" % str(obj))
#                raise BadRequest("Object cannot be deleted until associations are broken")

            # Find all version dicts and delete them
            for key in datastore_dict.keys():
                if key.find(object_id + '_version_') == 0:
                    del datastore_dict[key]
            # Delete the HEAD dict
            del datastore_dict[object_id]
            # Delete the version counter dict
            del datastore_dict['__' + object_id + '_version_counter']
        else:
            raise NotFound('Object with id ' + object_id + ' does not exist.')
        log.info('Delete result: True')

    def _is_in_association(self, obj_id, datastore_name=""):
        log.debug("_is_in_association(%s)" % obj_id)
        if not obj_id:
            raise BadRequest("Must provide object id")

        if not datastore_name:
            datastore_name = self.datastore_name
        try:
            datastore_dict = self.root[datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + datastore_name + ' does not exist.')

        for objname,obj in datastore_dict.iteritems():
            if (objname.find('_version_')>0) or (not type(obj) is dict): continue
            if 'type_' in obj and obj['type_'] == "Association":
                association = obj
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
        try:
            datastore_dict = self.root[self.datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + self.datastore_name + ' does not exist.')

        if type(subject) is str:
            subject_id = subject
        else:
            if "_id" not in subject:
                raise BadRequest("Object id not available in subject")
            else:
                subject_id = subject._id
        assoc_list = []
        target_id_list = []
        target_list = []
        for objname,obj in datastore_dict.iteritems():
            if (objname.find('_version_')>0) or (not type(obj) is dict): continue
            if 'type_' in obj and obj['type_'] == "Association":
                if obj['s'] == subject_id:
                    if predicate and obj['p'] == predicate:
                        if (object_type and obj['ot'] == object_type) or not object_type:
                            assoc_list.append(obj)
                            target_id_list.append(obj['o'])
                            target_list.append(self.read(obj['o']))
                    elif not predicate:
                        assoc_list.append(obj)
                        target_id_list.append(obj['o'])
                        target_list.append(self.read(obj['o']))

        log.debug("find_objects() found %s objects" % (len(target_list)))
        if id_only:
            return (target_id_list, assoc_list)
        else:
            return (target_list, assoc_list)

    def find_subjects(self, subject_type=None, predicate=None, obj=None, id_only=False):
        log.debug("find_subjects(subject_type=%s, predicate=%s, object=%s, id_only=%s" % (subject_type, predicate, obj, id_only))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not obj:
            raise BadRequest("Must provide object")
        try:
            datastore_dict = self.root[self.datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + self.datastore_name + ' does not exist.')

        if type(obj) is str:
            object_id = obj
        else:
            if "_id" not in obj:
                raise BadRequest("Object id not available in object")
            else:
                object_id = obj._id
        assoc_list = []
        target_id_list = []
        target_list = []
        for objname,obj in datastore_dict.iteritems():
            if (objname.find('_version_')>0) or (not type(obj) is dict): continue
            if 'type_' in obj and obj['type_'] == "Association":
                if obj['o'] == object_id:
                    if predicate and obj['p'] == predicate:
                        if (subject_type and obj['st'] == subject_type) or not subject_type:
                            assoc_list.append(obj)
                            target_id_list.append(obj['s'])
                            target_list.append(self.read(obj['s']))
                    elif not predicate:
                        assoc_list.append(obj)
                        target_id_list.append(obj['s'])
                        target_list.append(self.read(obj['s']))

        log.debug("find_subjects() found %s subjects" % (len(target_list)))
        if id_only:
            return (target_id_list, assoc_list)
        else:
            return (target_list, assoc_list)

    def find_associations(self, subject=None, predicate=None, obj=None, assoc_type=None, id_only=True):
        log.debug("find_associations(subject=%s, predicate=%s, object=%s, assoc_type=%s)" % (subject, predicate, obj, assoc_type))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if subject and obj or predicate:
            pass
        else:
            raise BadRequest("Illegal parameters")
        try:
            datastore_dict = self.root[self.datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + self.datastore_name + ' does not exist.')

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
            target_list = []
            for objname,obj in datastore_dict.iteritems():
                if (objname.find('_version_')>0) or (not type(obj) is dict): continue
                if 'type_' in obj and obj['type_'] == "Association":
                    if obj['s'] == subject_id and obj['o'] == object_id:
                        if assoc_type:
                            if obj['at'] == assoc_type:
                                target_list.append(obj)
                        else:
                            target_list.append(obj)
        else:
            target_list = []
            for objname,obj in datastore_dict.iteritems():
                if (objname.find('_version_')>0) or (not type(obj) is dict): continue
                if 'type_' in obj and obj['type_'] == "Association":
                    if obj['p'] == predicate:
                        target_list.append(obj)

        if id_only:
            assocs = [row['_id'] for row in target_list]
        else:
            assocs = [self._persistence_dict_to_ion_object(row) for row in target_list]
        log.debug("find_associations() found %s associations" % (len(assocs)))
        return assocs
        
    def find_res_by_type(self, restype, lcstate=None, id_only=False):
        log.debug("find_res_by_type(restype=%s, lcstate=%s)" % (restype, lcstate))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        try:
            datastore_dict = self.root[self.datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + self.datastore_name + ' does not exist.')

        assoc_list = []
        target_id_list = []
        target_list = []
        for objname,obj in datastore_dict.iteritems():
            if (objname.find('_version_')>0) or (not type(obj) is dict): continue
            if 'type_' in obj and (obj['type_'] == restype or (not restype and obj['type_'] != "Association")):
                if (lcstate and 'lcstate' in obj and obj['lcstate'] == lcstate) or not lcstate or not restype:
                    target_id_list.append(obj['_id'])
                    target_list.append(self._persistence_dict_to_ion_object(obj))
                    assoc_list.append([])

        log.debug("find_res_by_type() found %s resources" % (len(target_list)))
        if id_only:
            return (target_id_list, assoc_list)
        else:
            return (target_list, assoc_list)

    def find_res_by_lcstate(self, lcstate, restype=None, id_only=False):
        log.debug("find_res_by_type(lcstate=%s, restype=%s)" % (lcstate, restype))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        try:
            datastore_dict = self.root[self.datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + self.datastore_name + ' does not exist.')

        if lcstate in CommonResourceLifeCycleSM.STATE_ALIASES:
            lcstate_match = CommonResourceLifeCycleSM.STATE_ALIASES[lcstate]
        else:
            lcstate_match = [lcstate]
        assoc_list = []
        target_id_list = []
        target_list = []
        for objname,obj in datastore_dict.iteritems():
            if (objname.find('_version_')>0) or (not type(obj) is dict): continue
            if 'lcstate' in obj and obj['lcstate'] in lcstate_match:
                if (restype and obj['type_'] == restype) or not restype:
                    target_id_list.append(obj['_id'])
                    target_list.append(self._persistence_dict_to_ion_object(obj))
                    assoc_list.append([])

        log.debug("find_res_by_lcstate() found %s resources" % (len(target_list)))
        if id_only:
            return (target_id_list, assoc_list)
        else:
            return (target_list, assoc_list)

    def _pass(self):
        pass

    def find_res_by_name(self, name, restype=None, id_only=False):
        log.debug("find_res_by_name(name=%s, restype=%s)" % (name, restype))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        try:
            datastore_dict = self.root[self.datastore_name]
        except KeyError:
            raise BadRequest('Data store ' + self.datastore_name + ' does not exist.')

        assoc_list = []
        target_id_list = []
        target_list = []
        for objname,obj in datastore_dict.iteritems():
            if (objname.find('_version_')>0) or (not type(obj) is dict): continue
            if 'name' in obj and obj['name'] == name:
                if (restype and obj['type_'] == restype) or not restype:
                    target_id_list.append(obj['_id'])
                    target_list.append(self._persistence_dict_to_ion_object(obj))
                    assoc_list.append([])

        log.debug("find_res_by_name() found %s resources" % (len(target_list)))
        if id_only:
            return (target_id_list, assoc_list)
        else:
            return (target_list, assoc_list)

    def find_dir_entries(self, qname):
        raise NotImplementedError()

    def _ion_object_to_persistence_dict(self, ion_object):
        if ion_object is None: return None

        obj_dict = self._io_serializer.serialize(ion_object)
        return obj_dict

    def _persistence_dict_to_ion_object(self, obj_dict):
        if obj_dict is None: return None

        ion_object = self._io_deserializer.deserialize(obj_dict)
        return ion_object
