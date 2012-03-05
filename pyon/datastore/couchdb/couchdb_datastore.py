#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from uuid import uuid4
import hashlib

import couchdb
from couchdb.client import ViewResults, Row
from couchdb.http import PreconditionFailed, ResourceConflict, ResourceNotFound

from pyon.core.bootstrap import obj_registry
from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.core.object import IonObjectBase, IonObjectSerializer, IonObjectDeserializer
from pyon.datastore.datastore import DataStore
from pyon.datastore.couchdb.couchdb_config import get_couchdb_views
from pyon.ion.resource import CommonResourceLifeCycleSM
from pyon.util.log import log
from pyon.core.bootstrap import CFG

# Token for a most likely non-inclusive key range upper bound (end_key), for queries such as
# prefix <= keys < upper bound: e.g. ['some','value'] <= keys < ['some','value', END_MARKER]
# or "somestr" <= keys < "somestr"+END_MARKER for string prefix checking
# Note: Use highest ASCII characters here, not 8bit
#END_MARKER = "\x7f\x7f\x7f\x7f"
END_MARKER = "ZZZZZZ"

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
        log.debug('__init__(host=%s, port=%s, datastore_name=%s, options=%s)' % (host, port, datastore_name, options))
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

        # Datastore specialization (views)
        self.profile = profile

        # serializers
        self._io_serializer     = IonObjectSerializer()
        # TODO: Not nice to have this class depend on ION objects
        self._io_deserializer   = IonObjectDeserializer(obj_registry=obj_registry)

    def close(self):
        log.info("Closing connection to CouchDB")
        map(lambda x: map(lambda y: y.close(), x), self.server.resource.session.conns.values())
        self.server.resource.session.conns = {}     # just in case we try to reuse this, for some reason

    def _get_datastore(self, datastore_name=None):
        datastore_name = datastore_name or self.datastore_name
        try:
            ds = self.server[datastore_name]
            return ds, datastore_name
        except ResourceNotFound:
            raise BadRequest("Datastore '%s' does not exist" % datastore_name)
        except ValueError:
            raise BadRequest("Datastore name '%s' invalid" % datastore_name)

    def create_datastore(self, datastore_name="", create_indexes=True, profile=None):
        datastore_name = datastore_name or self.datastore_name
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
        datastore_name = datastore_name or self.datastore_name
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
        ds, datastore_name = self._get_datastore(datastore_name)
        log.debug('Listing information about data store %s' % datastore_name)
        info = ds.info()
        log.debug('Data store info: %s' % str(info))
        return info

    def datastore_exists(self, datastore_name=""):
        for db in self.server:
            if db == datastore_name:
                return True
        return False

    def list_objects(self, datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        log.warning('Listing all objects in data store %s' % datastore_name)
        objs = [obj for obj in ds]
        log.debug('Objects: %s' % str(objs))
        return objs

    def list_object_revisions(self, object_id, datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        log.debug('Listing all versions of object %s/%s' % (datastore_name, object_id))
        gen = ds.revisions(object_id)
        res = [ent["_rev"] for ent in gen]
        log.debug('Object versions: %s' % str(res))
        return res

    def create(self, obj, object_id=None, datastore_name=""):
        if not isinstance(obj, IonObjectBase):
            raise BadRequest("Obj param is not instance of IonObjectBase")
        return self.create_doc(self._ion_object_to_persistence_dict(obj),
                               object_id=object_id, datastore_name=datastore_name)

    def create_doc(self, doc, object_id=None, datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        if '_id' in doc:
            raise BadRequest("Doc must not have '_id'")
        if '_rev' in doc:
            raise BadRequest("Doc must not have '_rev'")

        if object_id:
            try:
                self.read(object_id, '', datastore_name)
                raise BadRequest("Object with id %s already exists" % object_id)
            except NotFound:
                pass

        # Assign an id to doc (recommended in CouchDB documentation)
        doc["_id"] = object_id or uuid4().hex
        log.info('Creating new object %s/%s' % (datastore_name, doc["_id"]))
        log.debug('create doc contents: %s', doc)

        # Save doc.  CouchDB will assign version to doc.
        try:
            res = ds.save(doc)
        except ResourceConflict:
            raise BadRequest("Object with id %s already exist" % doc["_id"])
        log.debug('Create result: %s' % str(res))
        id, version = res
        return (id, version)


    def _preload_create_doc(self, doc):
        ds, datastore_name = self._get_datastore()
        log.debug('Preloading object %s/%s' % (datastore_name, doc["_id"]))
        log.debug('create doc contents: %s', doc)

        # Save doc.  CouchDB will assign version to doc.
        try:
            res = ds.save(doc)
        except ResourceConflict:
            raise BadRequest("Object with id %s already exist" % doc["_id"])
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
        ds, datastore_name = self._get_datastore(datastore_name)
        if not rev_id:
            log.debug('Reading head version of object %s/%s' % (datastore_name, doc_id))
            doc = ds.get(doc_id)
            if doc is None:
                raise NotFound('Object with id %s does not exist.' % str(doc_id))
        else:
            log.debug('Reading version %s of object %s/%s' % (rev_id, datastore_name, doc_id))
            doc = ds.get(doc_id, rev=rev_id)
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
        ds, datastore_name = self._get_datastore(datastore_name)
        log.info('Reading head version of objects %s/%s' % (datastore_name, object_ids))
        docs = ds.view("_all_docs", keys=object_ids, include_docs=True)
        # Check for docs not found
        notfound_list = ['Object with id %s does not exist.' % str(row.key) for row in docs if row.doc is None]
        if notfound_list:
            raise NotFound("\n".join(notfound_list))

        doc_list = [row.doc.copy() for row in docs]
        return doc_list
    
    def update(self, obj, datastore_name=""):
        if not isinstance(obj, IonObjectBase):
            raise BadRequest("Obj param is not instance of IonObjectBase")
        return self.update_doc(self._ion_object_to_persistence_dict(obj))

    def update_doc(self, doc, datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
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
            res = ds.save(doc)
        except ResourceConflict:
            raise Conflict('Object not based on most current version')
        log.debug('Update result: %s' % str(res))
        id, version = res
        return (id, version)

    def delete(self, obj, datastore_name="", del_associations=False):
        if not isinstance(obj, IonObjectBase) and not isinstance(obj, str):
            raise BadRequest("Obj param is not instance of IonObjectBase or string id")
        if type(obj) is str:
            self.delete_doc(obj, datastore_name=datastore_name)
        else:
            if '_id' not in obj:
                raise BadRequest("Doc must have '_id'")
            if '_rev' not in obj:
                raise BadRequest("Doc must have '_rev'")
            self.delete_doc(self._ion_object_to_persistence_dict(obj), datastore_name=datastore_name, del_associations=del_associations)

    def delete_doc(self, doc, datastore_name="", del_associations=False):
        ds, datastore_name = self._get_datastore(datastore_name)
        doc_id = doc if type(doc) is str else doc["_id"]
        log.debug('Deleting object %s/%s' % (datastore_name, doc_id))

        if del_associations:
            assoc_ids = self.find_associations(anyobj=doc_id, id_only=True)
            for aid in assoc_ids:
                self.delete(aid, datastore_name=datastore_name)
            log.debug("Deleted %n associations for object %s" % (len(assoc_ids), doc_id))

        elif self._is_in_association(doc_id, datastore_name):
            log.warn("XXXXXXX Attempt to delete object %s that still has associations" % doc_id)
#           raise BadRequest("Object cannot be deleted until associations are broken")

        try:
            if type(doc) is str:
                del ds[doc_id]
            else:
                ds.delete(doc)
        except ResourceNotFound:
            raise NotFound('Object with id %s does not exist.' % doc_id)

    def _get_viewname(self, design, name):
        return "_design/%s/_view/%s" % (design, name)

    def _define_views(self, datastore_name=None, profile=None, keepviews=False):
        datastore_name = datastore_name or self.datastore_name
        profile = profile or self.profile

        ds_views = get_couchdb_views(profile)
        for design, viewdef in ds_views.iteritems():
            self._define_view(design, viewdef, datastore_name=datastore_name, keepviews=keepviews)

    def _define_view(self, design, viewdef, datastore_name=None, keepviews=False):
        ds, datastore_name = self._get_datastore(datastore_name)
        viewname = "_design/%s" % design
        if keepviews and viewname in ds:
            return
        try:
            del ds[viewname]
        except ResourceNotFound:
            pass
        ds[viewname] = dict(views=viewdef)

    def _update_views(self, datastore_name="", profile=None):
        ds, datastore_name = self._get_datastore(datastore_name)

        profile = profile or self.profile
        ds_views = get_couchdb_views(profile)

        for design, viewdef in ds_views.iteritems():
            for viewname in viewdef:
                try:
                    rows = ds.view("_design/%s/_view/%s" % (design, viewname))
                    log.debug("View %s/_design/%s/_view/%s: %s rows" % (datastore_name, design, viewname, len(rows)))
                except Exception, ex:
                    log.exception("Problem with view %s/_design/%s/_view/%s" % (datastore_name, design, viewname))

    _refresh_views = _update_views

    def _delete_views(self, datastore_name="", profile=None):
        ds, datastore_name = self._get_datastore(datastore_name)

        profile = profile or self.profile
        ds_views = get_couchdb_views(profile)

        for design, viewdef in ds_views.iteritems():
            try:
                del ds["_design/%s" % design]
            except ResourceNotFound:
                pass

    def _get_view_args(self, all_args):
        """
        @brief From given all_args dict, extract all entries that are valid CouchDB view options.
        @see http://wiki.apache.org/couchdb/HTTP_view_API
        """
        view_args = dict((k, v) for k,v in all_args.iteritems() if k in ('descending', 'stale', 'skip', 'inclusive_end', 'update_seq'))
        limit = int(all_args.get('limit', 0))
        if limit>0:
            view_args['limit'] = limit
        return view_args

    def _is_in_association(self, obj_id, datastore_name=""):
        log.debug("_is_in_association(%s)" % obj_id)
        if not obj_id:
            raise BadRequest("Must provide object id")
        ds, datastore_name = self._get_datastore(datastore_name)

        assoc_ids = self.find_associations(anyobj=obj_id, id_only=True, limit=1)
        if assoc_ids:
            log.debug("Object found as object in associations: First is %s" % assoc_ids)
            return True

        return False

    def find_objects(self, subject, predicate=None, object_type=None, id_only=False, **kwargs):
        log.debug("find_objects(subject=%s, predicate=%s, object_type=%s, id_only=%s" % (subject, predicate, object_type, id_only))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not subject:
            raise BadRequest("Must provide subject")
        ds, datastore_name = self._get_datastore()

        if type(subject) is str:
            subject_id = subject
        else:
            if "_id" not in subject:
                raise BadRequest("Object id not available in subject")
            else:
                subject_id = subject._id

        view_args = self._get_view_args(kwargs)
        view = ds.view(self._get_viewname("association","by_sub"), **view_args)
        key = [subject_id]
        if predicate:
            key.append(predicate)
            if object_type:
                key.append(object_type)
        endkey = list(key)
        endkey.append(END_MARKER)
        rows = view[key:endkey]

        obj_assocs = [self._persistence_dict_to_ion_object(row['value']) for row in rows]
        obj_ids = [assoc.o for assoc in obj_assocs]

        log.debug("find_objects() found %s objects" % (len(obj_ids)))
        if id_only:
            return (obj_ids, obj_assocs)

        obj_list = self.read_mult(obj_ids)
        return (obj_list, obj_assocs)

    def find_subjects(self, subject_type=None, predicate=None, obj=None, id_only=False, **kwargs):
        log.debug("find_subjects(subject_type=%s, predicate=%s, object=%s, id_only=%s" % (subject_type, predicate, obj, id_only))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not obj:
            raise BadRequest("Must provide object")
        ds, datastore_name = self._get_datastore()

        if type(obj) is str:
            object_id = obj
        else:
            if "_id" not in obj:
                raise BadRequest("Object id not available in object")
            else:
                object_id = obj._id

        view_args = self._get_view_args(kwargs)
        view = ds.view(self._get_viewname("association","by_obj"), **view_args)
        key = [object_id]
        if predicate:
            key.append(predicate)
            if subject_type:
                key.append(subject_type)
        endkey = list(key)
        endkey.append(END_MARKER)
        rows = view[key:endkey]

        sub_assocs = [self._persistence_dict_to_ion_object(row['value']) for row in rows]
        sub_ids = [assoc.s for assoc in sub_assocs]

        log.debug("find_subjects() found %s subjects" % (len(sub_ids)))
        if id_only:
            return (sub_ids, sub_assocs)

        sub_list = self.read_mult(sub_ids)
        return (sub_list, sub_assocs)

    def find_associations(self, subject=None, predicate=None, obj=None, assoc_type=None, id_only=True, anyobj=None, **kwargs):
        log.debug("find_associations(subject=%s, predicate=%s, object=%s)" % (subject, predicate, obj))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not (subject and obj or predicate or anyobj):
            raise BadRequest("Illegal parameters")
        if assoc_type and not predicate:
            raise BadRequest("Illegal parameters")

        # Support
        if subject is None and obj is None and anyobj:
            subject = anyobj

        if subject:
            if type(subject) is str:
                subject_id = subject
            else:
                if "_id" not in subject:
                    raise BadRequest("Object id not available in subject")
                else:
                    subject_id = subject._id
        if obj:
            if type(obj) is str:
                object_id = obj
            else:
                if "_id" not in obj:
                    raise BadRequest("Object id not available in object")
                else:
                    object_id = obj._id

        ds, datastore_name = self._get_datastore()
        view_args = self._get_view_args(kwargs)

        if subject and obj:
            view = ds.view(self._get_viewname("association","by_ids"), **view_args)
            key = [subject_id, object_id]
            if predicate:
                key.append(predicate)
            if assoc_type:
                key.append(assoc_type)
            endkey = list(key)
            endkey.append(END_MARKER)
            rows = view[key:endkey]
        elif subject:
            view = ds.view(self._get_viewname("association","by_id"), **view_args)
            key = [subject_id]
            if predicate:
                key.append(predicate)
            if assoc_type:
                key.append(assoc_type)
            endkey = list(key)
            endkey.append(END_MARKER)
            rows = view[key:endkey]
        elif predicate:
            view = ds.view(self._get_viewname("association","by_pred"), **view_args)
            key = [predicate]
            endkey = list(key)
            endkey.append(END_MARKER)
            rows = view[key:endkey]
        else:
            raise BadRequest("Illegal arguments")

        if id_only:
            assocs = [row.id for row in rows]
        else:
            assocs = [self._persistence_dict_to_ion_object(row['value']) for row in rows]
        log.debug("find_associations() found %s associations" % (len(assocs)))
        return assocs

    def find_res_by_type(self, restype, lcstate=None, id_only=False):
        log.debug("find_res_by_type(restype=%s, lcstate=%s)" % (restype, lcstate))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("resource","by_type"), include_docs=(not id_only))
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
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("resource","by_lcstate"), include_docs=(not id_only))
        is_hierarchical = (lcstate in CommonResourceLifeCycleSM.STATE_ALIASES)
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
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("resource","by_name"), include_docs=(not id_only))
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
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("directory","by_path"))
        key = str(qname).split('/')[1:]
        endkey = list(key)
        endkey.append(END_MARKER)
        if qname == '/': del endkey[0]
        rows = view[key:endkey]
        res_entries = [self._persistence_dict_to_ion_object(row.value) for row in rows]
        log.debug("find_dir_entries() found %s objects" % (len(res_entries)))
        return res_entries

    def find_by_view(self, design_name, view_name, key=None, keys=None, start_key=None, end_key=None,
                           id_only=True, convert_doc=True, **kwargs):
        """
        @brief Generic find function using an defined index
        @retval Returns a list of triples: (att_id, index_row, Attachment object or none)
        """
        log.debug("find_by_view(%s/%s)" % (design_name, view_name))
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        ds, datastore_name = self._get_datastore()

        view_args = self._get_view_args(kwargs)
        view_args['include_docs'] = (not id_only)
        view_doc = design_name if design_name == "_all_docs" else self._get_viewname(design_name, view_name)
        if keys:
            view_args['keys'] = keys
        view = ds.view(view_doc, **view_args)
        if key is not None:
            rows = view[key]
            log.info("find_by_view(): key=%s" % key)
        elif keys:
            rows = view
            log.info("find_by_view(): keys=%s" % keys)
        elif start_key and end_key:
            startkey = start_key or []
            endkey = list(end_key) or []
            endkey.append(END_MARKER)
            log.info("find_by_view(): start_key=%s to end_key=%s" % (startkey, endkey))
            if view_args.get('descending', False):
                rows = view[endkey:startkey]
            else:
                rows = view[startkey:endkey]
        else:
            rows = view

        if id_only:
            res_rows = [(row['id'],row['key'], None) for row in rows]
        else:
            if convert_doc:
                res_rows = [(row['id'],row['key'],self._persistence_dict_to_ion_object(row['doc'])) for row in rows]
            else:
                res_rows = [(row['id'],row['key'],row['doc']) for row in rows]

        log.info("find_by_view() found %s objects" % (len(res_rows)))
        return res_rows

    def _ion_object_to_persistence_dict(self, ion_object):
        if ion_object is None: return None

        obj_dict = self._io_serializer.serialize(ion_object)
        return obj_dict

    def _persistence_dict_to_ion_object(self, obj_dict):
        if obj_dict is None: return None

        ion_object = self._io_deserializer.deserialize(obj_dict)
        return ion_object

    def query_view(self, view_name='', opts={}, datastore_name=''):
        '''
        query_view is a straight through method for querying a view in CouchDB. query_view provides us the interface
        to the view structure in couch, in lieu of implementing a method for every type of query we could want, we
        now have the capability for clients to make queries to couch in a straight-through manner.
        '''
        ds, datastore_name = self._get_datastore(datastore_name)

        # Actually obtain the results and place them in rows
        rows = ds.view(view_name, **opts)

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
        ds, datastore_name = self._get_datastore(datastore_name)
        res = ds.query(map_fun,reduce_fun,**options)

        return self._parse_results(res)


    def _parse_results(self, doc):
        ''' Parses a complex object and organizes it into basic types
        '''
        ret = {}

        #-------------------------------
        # Handle ViewResults type (CouchDB type)
        #-------------------------------
        # \_ Ignore the meta data and parse the rows only
        if isinstance(doc, ViewResults):
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

