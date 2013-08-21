#!/usr/bin/env python
# 1,$s/t.complete_step('couchdb.%s.\([a-z_.]*\)'%\([a-z_.]*\))/self._complete_timing_step(t,\2,'\1')/
# 1,$s/stats.add_value('couchdb.%s.\([a-z_.]*\)'%\([a-z_.]*\),\(.*\))/self._save_stats_value(\2, '\1', \3)/

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from uuid import uuid4
import gevent
import hashlib

import couchdb
from couchdb.client import ViewResults, Row
from couchdb.http import PreconditionFailed, ResourceConflict, ResourceNotFound

from pyon.core.bootstrap import get_obj_registry, CFG
from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.core.object import IonObjectBase, IonObjectSerializer, IonObjectDeserializer
from pyon.datastore.datastore import DataStore
from pyon.datastore.couchdb.couchdb_config import get_couchdb_views
from pyon.ion.identifier import create_unique_association_id
from pyon.ion.resource import CommonResourceLifeCycleSM
from ooi.logging import log
from pyon.util.arg_check import validate_is_instance
from pyon.util.containers import get_ion_ts
from ooi.timer import Timer,Accumulator

stats = Accumulator(persist=True)

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
    doc_id = doc.pop('_id', None)
    doc_rev = doc.get('_rev', None)
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
        log.debug('__init__(host=%s, port=%s, datastore_name=%s, options=%s)', host, port, datastore_name, options)
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
        log.info('Connecting to CouchDB server: %s', connection_str)
        self.server = couchdb.Server(connection_str)

        # Datastore specialization (views)
        self.profile = profile

        # serializers
        self._io_serializer = IonObjectSerializer()
        # TODO: Not nice to have this class depend on ION objects
        self._io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
        self._datastore_cache = {}

    def close(self):
        log.trace("Closing connection to %s", self.datastore_name)
        map(lambda x: map(lambda y: y.close(), x), self.server.resource.session.conns.values())
        self.server.resource.session.conns = {}     # just in case we try to reuse this, for some reason

    def _get_datastore(self, datastore_name=None):
        datastore_name = datastore_name or self.datastore_name

        if datastore_name in self._datastore_cache:
            return (self._datastore_cache[datastore_name], datastore_name)

        try:
            ds = self.server[datastore_name]   # http lookup
            self._datastore_cache[datastore_name] = ds
            return ds, datastore_name
        except ResourceNotFound:
            raise BadRequest("Datastore '%s' does not exist" % datastore_name)
        except ValueError:
            raise BadRequest("Datastore name '%s' invalid" % datastore_name)

    def create_datastore(self, datastore_name="", create_indexes=True, profile=None):
        datastore_name = datastore_name or self.datastore_name
        profile = profile or self.profile
        log.info('Creating data store %s with profile=%s', datastore_name, profile)
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
        log.info('Deleting data store %s', datastore_name)
        try:
            self.server.delete(datastore_name)
        except ResourceNotFound:
            log.warn('deleting data store %s: does not exist', datastore_name)
        except ValueError:
            raise BadRequest("Data store name %s invalid" % datastore_name)

    def list_datastores(self):
        dbs = [db for db in self.server]
        log.debug('Data stores: %s', dbs)
        return dbs

    def info_datastore(self, datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        log.debug('Listing information about data store %s', datastore_name)
        info = ds.info()
        log.debug('Data store info: %s', info)
        return info

    def datastore_exists(self, datastore_name=""):
        for db in self.server:
            if db == datastore_name:
                return True
        return False

    def list_objects(self, datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        log.info('Listing all objects in data store %s', datastore_name)
        objs = [obj for obj in ds]
        return objs

    def list_object_revisions(self, object_id, datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        log.debug('Listing all versions of object %s/%s', datastore_name, object_id)
        gen = ds.revisions(object_id)
        res = [ent["_rev"] for ent in gen]
        return res

    def create(self, obj, object_id=None, attachments=None, datastore_name=""):
        """
        Converts ion objects to python dictionary before persisting them using the optional
        suggested identifier and creates attachments to the object.
        Returns an identifier and revision number of the object
        """
        if not isinstance(obj, IonObjectBase):
            raise BadRequest("Obj param is not instance of IonObjectBase")


        return self.create_doc(self._ion_object_to_persistence_dict(obj),
                               object_id=object_id, datastore_name=datastore_name,
                               attachments=attachments)

    def create_doc(self, doc, object_id=None, attachments=None, datastore_name=""):
        """
        Persists the document using the optionally suggested doc_id, and creates attachments to it.
        Returns the identifier and version number of the document
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        if '_id' in doc:
            raise BadRequest("Doc must not have '_id'")
        if '_rev' in doc:
            raise BadRequest("Doc must not have '_rev'")

        # Assign an id to doc (recommended in CouchDB documentation)
        doc["_id"] = object_id or uuid4().hex

        # Add the attachments if indicated
        if attachments is not None:
            pass   # Does not work with binary attachments
#            if isinstance(attachments, dict):
#                doc['_attachments'] = attachments
#            else:
#                raise BadRequest('Improper attachment given')
        t = self._get_timer()
        try:
            res = ds.save(doc)
            if t:
                self._complete_timing_step(t, datastore_name, 'create_doc.create')
        except ResourceConflict:
            raise BadRequest("Object with id %s already exist" % doc["_id"])
        obj_id, version = res
        if attachments is not None:
            # Need to iterate through attachments because couchdb_python does not support binary
            # content in db.save()
            sum_size = 0
            for att_name, att_value in attachments.iteritems():
                self.create_attachment(obj_id, att_name, att_value['data'], content_type=att_value.get('content_type', ''), datastore_name=datastore_name)
                sum_size += len(att_value['data'])
            if t:
                self._complete_timing_step(t, datastore_name, 'create_doc.attachments')
                self._save_stats_value(datastore_name, 'create_doc.attachments_count', len(attachments))
                self._save_stats_value(datastore_name, 'create_doc.attachments_size', sum_size)
        if t:
            stats.add(t)
        return obj_id, version

    def create_mult(self, objects, object_ids=None, allow_ids=False):
        if any([not isinstance(obj, IonObjectBase) for obj in objects]):
                raise BadRequest("Obj param is not instance of IonObjectBase")
        return self.create_doc_mult([self._ion_object_to_persistence_dict(obj) for obj in objects],
                                    object_ids, allow_ids=allow_ids)

    def create_doc_mult(self, docs, object_ids=None, allow_ids=False):
        if not allow_ids:
            if any(["_id" in doc for doc in docs]):
                raise BadRequest("Docs must not have '_id'")
            if any(["_rev" in doc for doc in docs]):
                raise BadRequest("Docs must not have '_rev'")
        if object_ids and len(object_ids) != len(docs):
            raise BadRequest("Invalid object_ids")
        if type(docs) is not list:
            raise BadRequest("Invalid type for docs:%s" % type(docs))

        if object_ids:
            for doc, oid in zip(docs, object_ids):
                doc["_id"] = oid
        else:
            for doc in docs:
                doc["_id"] = doc.get("_id", None) or uuid4().hex
                doc["_id"] = doc.get("_id", None) or uuid4().hex

        # Update docs.  CouchDB will assign versions to docs.
        db, _ = self._get_datastore()
        t = self._get_timer()
        res = db.update(docs)
        if t:
            self._complete_timing_step(t, None, 'create_doc_mult.update')
            self._save_stats_value(None, 'create_doc_mult.count', len(docs))
            stats.add(t)
        if not all([success for success, oid, rev in res]):
            errors = ["%s:%s" % (oid, rev) for success, oid, rev in res if not success]
            log.error('create_doc_mult had errors. Successful: %s, Errors: %s', len(res) - len(errors), "\n".join(errors))
        return res

    def update_doc_mult(self, docs):
        return self.create_doc_mult(docs, allow_ids=True)

    def create_attachment(self, doc, attachment_name, data, content_type=None, datastore_name=""):
        """
        Assumes that the document already exists and creates attachment to it.
        @param doc can be either id or a document
        """
        if not isinstance(attachment_name, str):
            raise BadRequest("attachment name is not string")
        if not isinstance(data, str) and not isinstance(data, file):
            raise BadRequest("data to create attachment is not a str or file")
        if isinstance(doc, str):
            doc = self.read_doc(doc_id=doc)
        ds, _ = self._get_datastore(datastore_name)
        ds.put_attachment(doc=doc, content=data, filename=attachment_name, content_type=content_type)

    def read(self, object_id, rev_id="", datastore_name=""):
        if not isinstance(object_id, str):
            raise BadRequest("Object id param is not string")
        doc = self.read_doc(object_id, rev_id, datastore_name)
        # Convert doc into Ion object
        obj = self._persistence_dict_to_ion_object(doc)
        return obj

    def read_doc(self, doc_id, rev_id="", datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        t = self._get_timer()
        if not rev_id:
            doc = ds.get(doc_id)
            if doc is None:
                raise NotFound('Object with id %s does not exist.' % str(doc_id))
        else:
            # doc = ds.get(doc_id, rev=rev_id)
            # Work around issue with couchdb_python 0.8 and concurrent use of this library
            # See https://code.google.com/p/couchdb-python/issues/detail?id=204
            # Fixed in client 0.9
            doc = None
            fixedit = False
            for i in range(3):
                try:
                    doc = ds.get(doc_id, rev=rev_id)
                    # If this passes we are good. Exit loop
                    fixedit = True
                    break
                except KeyError as ke:
                    log.warn("Couchdb_python 0.8 KeyError on read(%s) - try %s" % (doc_id, i))
                    gevent.sleep(0.05)
            if not fixedit:
                log.error("Couchdb_python 0.8 KeyError on read(%s) failed multiple retries" % doc_id)

            if doc is None:
                raise NotFound('Object with id %s does not exist.' % str(doc_id))
        if t:
#            self._complete_timing_step(t, datastore_name, 'create_doc.attachments')
#            self._save_stats_value(datastore_name, 'create_doc.attachments_count', len(attachments))
            self._complete_timing_step(t,datastore_name,'read_doc')
            stats.add(t)
        return doc

    def read_mult(self, object_ids, datastore_name="", _time=True):
        if any([not isinstance(object_id, str) for object_id in object_ids]):
            raise BadRequest("Object ids are not string: %s" % str(object_ids))
        docs = self.read_doc_mult(object_ids, datastore_name, _time=_time)
        # Convert docs into Ion objects
        obj_list = [self._persistence_dict_to_ion_object(doc) for doc in docs]
        return obj_list

    def read_doc_mult(self, object_ids, datastore_name="", _time=True):
        if not object_ids: return []
        ds, datastore_name = self._get_datastore(datastore_name)
        t = self._get_timer(condition=_time)
        docs = ds.view("_all_docs", keys=object_ids, include_docs=True)
        if t:
            self._complete_timing_step(t,datastore_name,'read_doc_mult.view')
        # Check for docs not found
        notfound_list = ['Object with id %s does not exist.' % str(row.key)
                         for row in docs if row.doc is None]
        if notfound_list:
            raise NotFound("\n".join(notfound_list))

        doc_list = [row.doc.copy() for row in docs]
        if t:
            self._complete_timing_step(t,datastore_name,'read_doc_mult.copy')
            stats.add(t)
            self._save_stats_value(datastore_name, 'read_doc_mult.count',  len(object_ids))
        return doc_list

    def read_attachment(self, doc, attachment_name, datastore_name=""):
        if not isinstance(attachment_name, str):
            raise BadRequest("Attachment_name param is not str")

        ds, datastore_name = self._get_datastore(datastore_name)

        attachment = ds.get_attachment(doc, attachment_name)

        if attachment is None:
            raise NotFound('Attachment %s does not exist in document %s.%s.',
                attachment_name, datastore_name, doc)
        else:
            attachment = attachment.read()

        if not isinstance(attachment, str):
            raise NotFound('Attachment read is not a string')
        return attachment

    def list_attachments(self, doc):
        """
        Returns the a list of attachments for the document, as a dict of dicts, key'ed by name with
        nested keys 'data' for the content and 'content-type'.
        @param doc  accepts either str (meaning an id) or dict (meaning a full document).
        """
        if isinstance(doc, dict) and '_attachments' not in doc:
            # Need to reread again, because it did not contain the _attachments
            doc = self.read_doc(doc_id=doc["_id"])
        elif isinstance(doc, str):
            doc = self.read_doc(doc_id=doc)

        return doc.get("_attachments", None)

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

        t = self._get_timer()
        try:
            res = ds.save(doc)
            if t:
                self._complete_timing_step(t,datastore_name,'update_doc.save')
                stats.add(t)
        except ResourceConflict:
            raise Conflict('Object not based on most current version')
        id, version = res
        return (id, version)

    def update_mult(self, objects):
        if any([not isinstance(obj, IonObjectBase) for obj in objects]):
            raise BadRequest("Obj param is not instance of IonObjectBase")
        return self.create_doc_mult([self._ion_object_to_persistence_dict(obj) for obj in objects], allow_ids=True)

    def update_attachment(self, doc, attachment_name, data, content_type=None, datastore_name=""):
        self.create_attachment(doc=doc, attachment_name=attachment_name, data=data,
            content_type=content_type,
            datastore_name=datastore_name)

    def delete(self, obj, datastore_name="", del_associations=False):
        if not isinstance(obj, IonObjectBase) and not isinstance(obj, str):
            raise BadRequest("Obj param is not instance of IonObjectBase or string id")
        if type(obj) is str:
            self.delete_doc(obj, datastore_name=datastore_name, del_associations=del_associations)
        else:
            if '_id' not in obj:
                raise BadRequest("Doc must have '_id'")
            if '_rev' not in obj:
                raise BadRequest("Doc must have '_rev'")
            self.delete_doc(self._ion_object_to_persistence_dict(obj), datastore_name=datastore_name, del_associations=del_associations)

    def delete_doc(self, doc, datastore_name="", del_associations=False):
        ds, datastore_name = self._get_datastore(datastore_name)
        doc_id = doc if type(doc) is str else doc["_id"]

        t = self._get_timer()
        assoc_ids = None
        if del_associations:
            assoc_ids = self.find_associations(anyside=doc_id, id_only=True)
            self.delete_doc_mult(assoc_ids, _time=False)
            if t:
                self._complete_timing_step(t,datastore_name,'delete_doc.associations')
#            for aid in assoc_ids:
#                self.delete(aid, datastore_name=datastore_name)
#            log.info("Deleted %n associations for object %s", len(assoc_ids), doc_id)

        else:
            warn_about_association = self._is_in_association(doc_id, datastore_name)
            if t:
                self._complete_timing_step(t,datastore_name,'delete_doc.check')
            if warn_about_association:
                bad_doc = self.read(doc_id)
                if doc:
                    log.warn("Attempt to delete %s object %s that still has associations", bad_doc.type_, doc_id)
                else:
                    log.warn("Attempt to delete object %s that still has associations", doc_id)
#           raise BadRequest("Object cannot be deleted until associations are broken")

        try:
            if type(doc) is str:
                del ds[doc_id]
                if t:
                    self._complete_timing_step(t,datastore_name,'delete_doc.byid')
            else:
                ds.delete(doc)
                if t:
                    self._complete_timing_step(t,datastore_name,'delete_doc.byobj')
            if t:
                stats.add(t)
                # track percentage deleted by ID vs Ion object
                self._save_stats_value(datastore_name, 'delete_doc.portion_byid',  1 if type(doc) is str else 0)
                if assoc_ids:
                    self._save_stats_value(datastore_name, 'delete_doc.association_count',  len(assoc_ids))
        except ResourceNotFound:
            raise NotFound('Object with id %s does not exist.' % doc_id)

    def delete_mult(self, object_ids, datastore_name=None):
        return self.delete_doc_mult(object_ids, datastore_name)

    def delete_doc_mult(self, object_ids, datastore_name=None, _time=True):
        ds, datastore_name = self._get_datastore(datastore_name)
        t = self._get_timer(condition=_time)
        obj_list = self.read_doc_mult(object_ids, datastore_name=datastore_name)
        if t:
            self._complete_timing_step(t,datastore_name,'delete_doc_mult.read')
        for obj in obj_list:
            obj['_deleted'] = True
        self.create_doc_mult(obj_list, allow_ids=True) # behind the scenes, calls ds.update()
        if t:
            self._complete_timing_step(t,datastore_name,'delete_doc_mult.update')
            stats.add(t)
            self._save_stats_value(datastore_name, 'delete_doc_mult.count',  len(object_ids))

    def delete_attachment(self, doc, attachment_name, datastore_name=""):
        """
        Deletes an attachment from a document.
        """
        if not isinstance(attachment_name, str):
            raise BadRequest("attachment_name is not a string")

        if isinstance(doc, str):
            doc = self.read_doc(doc_id=doc)

        ds, datastore_name = self._get_datastore(datastore_name)

        ds.delete_attachment(doc, attachment_name)

    def create_association(self, subject=None, predicate=None, obj=None, assoc_type=None):
        """
        Create an association between two IonObjects with a given predicate
        """
        #if assoc_type:
        #if assoc_type:
        #    raise BadRequest("assoc_type deprecated")
        if not (subject and predicate and obj):
            raise BadRequest("Association must have all elements set")

        t = self._get_timer()
        if type(subject) is str:
            subject_id = subject
            subject = self.read(subject_id)
            subject_type = subject._get_type()
        else:
            if "_id" not in subject or "_rev" not in subject:
                raise BadRequest("Subject id or rev not available")
            subject_id = subject._id
            subject_type = subject._get_type()

        if type(obj) is str:
            object_id = obj
            obj = self.read(object_id)
            object_type = obj._get_type()
        else:
            if "_id" not in obj or "_rev" not in obj:
                raise BadRequest("Object id or rev not available")
            object_id = obj._id
            object_type = obj._get_type()
        if t:
            self._complete_timing_step(t,self.datastore_name,'create_association.read')
        # Check that subject and object type are permitted by association definition
        # Note: Need import here, so that import orders are not screwed up
        from pyon.core.registry import getextends
        from pyon.ion.resource import Predicates
        from pyon.core.bootstrap import IonObject

        try:
            pt = Predicates.get(predicate)
        except AttributeError:
            raise BadRequest("Predicate unknown %s" % predicate)
        if not subject_type in pt['domain']:
            found_st = False
            for domt in pt['domain']:
                if subject_type in getextends(domt):
                    found_st = True
                    break
            if not found_st:
                raise BadRequest("Illegal subject type %s for predicate %s" % (subject_type, predicate))
        if not object_type in pt['range']:
            found_ot = False
            for rant in pt['range']:
                if object_type in getextends(rant):
                    found_ot = True
                    break
            if not found_ot:
                raise BadRequest("Illegal object type %s for predicate %s" % (object_type, predicate))

        # Finally, ensure this isn't a duplicate
        assoc_list = self.find_associations(subject, predicate, obj, id_only=False, _time=False)
        if t:
            self._complete_timing_step(t,self.datastore_name,'create_association.find')
        if len(assoc_list) != 0:
            assoc = assoc_list[0]
            raise BadRequest("Association between %s and %s with predicate %s already exists" % (subject, obj, predicate))

        assoc = IonObject("Association", s=subject_id, st=subject_type, p=predicate, o=object_id, ot=object_type, ts=get_ion_ts())
        out = self.create(assoc, create_unique_association_id())
        if t:
            self._complete_timing_step(t,self.datastore_name,'create_association.create')
            stats.add(t)
        return out

    def delete_association(self, association=''):
        """
        Delete an association between two IonObjects
        @param association  Association object, association id or 3-list of [subject, predicate, object]
        """
        if type(association) in (list, tuple) and len(association) == 3:
            subject, predicate, obj = association
            assoc_id_list = self.find_associations(subject=subject, predicate=predicate, obj=obj, id_only=True)
            success = True
            for aid in assoc_id_list:
                success = success and self.delete(aid)
            return success
        else:
            return self.delete(association)

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
            try:
                del ds[viewname]
            except ResourceNotFound:
                pass
            ds[viewname] = dict(views=viewdef)
        except Exception as ex:
            # In case this gets executed concurrently and 2 processes perform the same creates
            log.warn("Error defining datastore %s view %s (concurrent create?): %s", datastore_name, viewname, str(ex))

    def _update_views(self, datastore_name="", profile=None):
        ds, datastore_name = self._get_datastore(datastore_name)

        profile = profile or self.profile
        ds_views = get_couchdb_views(profile)

        for design, viewdef in ds_views.iteritems():
            for viewname in viewdef:
                try:
                    rows = ds.view("_design/%s/_view/%s" % (design, viewname))
                    #log.debug("View %s/_design/%s/_view/%s: %s rows", datastore_name, design, viewname, len(rows))
                except Exception, ex:
                    log.exception("Problem with view %s/_design/%s/_view/%s", datastore_name, design, viewname)

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
        view_args = dict((k, v) for k, v in all_args.iteritems() if k in ('descending', 'stale', 'skip', 'inclusive_end', 'update_seq') and v is not None)
        limit = int(all_args.get('limit', 0)) if all_args.get('limit', None) is not None else 0
        if limit > 0:
            view_args['limit'] = limit
        return view_args

    def _is_in_association(self, obj_id, datastore_name=""):
        if not obj_id:
            raise BadRequest("Must provide object id")
        ds, datastore_name = self._get_datastore(datastore_name)

        assoc_ids = self.find_associations(anyside=obj_id, id_only=True, limit=1)
        if assoc_ids:
            return True

        return False

    def find_objects_mult(self, subjects, id_only=False):
        """
        Returns a list of associations for a given list of subjects
        """
        ds, datastore_name = self._get_datastore()
        validate_is_instance(subjects, list, 'subjects is not a list of resource_ids')
        view_args = dict(keys=subjects, include_docs=True)
        t = self._get_timer()
        results = self.query_view(self._get_viewname("association", "by_bulk"), view_args)
        ids = [i['value'] for i in results]
        assocs = [i['doc'] for i in results]
        if t:
            self._complete_timing_step(t,self.datastore_name,'find_objects_mult.view.ids')
            stats.add(t)
        try:
            if id_only:
                return ids, assocs
            else:
                objs = self.read_mult(ids, _time=False)
                if t:
                    self._complete_timing_step(t,self.datastore_name,'find_objects_mult.view.objs')
                return objs, assocs
        finally:
            if t:
                stats.add(t)
                self._save_stats_value(self.datastore_name, 'find_objects_mult.count',  len(results))


    def find_subjects_mult(self, objects, id_only=False):
        """
        Returns a list of associations for a given list of objects
        """
        ds, datastore_name = self._get_datastore()
        validate_is_instance(objects, list, 'objects is not a list of resource_ids')
        view_args = dict(keys=objects, include_docs=True)
        t = self._get_timer()
        results = self.query_view(self._get_viewname("association", "by_subject_bulk"), view_args)
        ids = [i['value'] for i in results]
        assocs = [i['doc'] for i in results]
        if t:
            self._complete_timing_step(t,self.datastore_name,'find_subjects_mult.ids')
        try:
            if id_only:
                return ids, assocs
            else:
                objs = self.read_mult(ids, _time=False)
                if t:
                    self._complete_timing_step(t,self.datastore_name,'find_subjects_mult.objs')
                return objs, assocs
        finally:
            if t:
                stats.add(t)
                self._save_stats_value(self.datastore_name, 'find_subjects_mult.count',  len(results))

    def find_objects(self, subject, predicate=None, object_type=None, id_only=False, **kwargs):
        log.debug("find_objects(subject=%s, predicate=%s, object_type=%s, id_only=%s", subject, predicate, object_type, id_only)

        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not subject:
            raise BadRequest("Must provide subject")
        if object_type and not predicate:
            raise BadRequest("Cannot provide object type without a predictate")

        ds, datastore_name = self._get_datastore()

        if type(subject) is str:
            subject_id = subject
        else:
            if "_id" not in subject:
                raise BadRequest("Object id not available in subject")
            else:
                subject_id = subject._id

        t = self._get_timer()

        view_args = self._get_view_args(kwargs)
        view = ds.view(self._get_viewname("association", "by_sub"), **view_args)
        if t:
            self._complete_timing_step(t,datastore_name,'find_objects.view')
        key = [subject_id]
        if predicate:
            key.append(predicate)
            if object_type:
                key.append(object_type)
        endkey = self._get_endkey(key)
        rows = view[key:endkey]
        if t:
            self._complete_timing_step(t,datastore_name,'find_objects.rows')
            stats.add(t)
            self._save_stats_value(datastore_name, 'find_objects.row_count',  len(rows))
        obj_assocs = [self._persistence_dict_to_ion_object(row['value']) for row in rows]
        obj_ids = [assoc.o for assoc in obj_assocs]

        log.debug("find_objects() found %s objects", len(obj_ids))
        if id_only:
            return (obj_ids, obj_assocs)

        obj_list = self.read_mult(obj_ids)
        return (obj_list, obj_assocs)

    def find_subjects(self, subject_type=None, predicate=None, obj=None, id_only=False, **kwargs):
        log.debug("find_subjects(subject_type=%s, predicate=%s, object=%s, id_only=%s", subject_type, predicate, obj, id_only)

        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not obj:
            raise BadRequest("Must provide object")
        if subject_type and not predicate:
            raise BadRequest("Cannot provide subject type without a predicate")

        ds, datastore_name = self._get_datastore()

        if type(obj) is str:
            object_id = obj
        else:
            if "_id" not in obj:
                raise BadRequest("Object id not available in object")
            else:
                object_id = obj._id
        t = self._get_timer()

        view_args = self._get_view_args(kwargs)
        view = ds.view(self._get_viewname("association", "by_obj"), **view_args)
        if t:
            self._complete_timing_step(t,datastore_name,'find_subjects.view')
        key = [object_id]
        if predicate:
            key.append(predicate)
            if subject_type:
                key.append(subject_type)
        endkey = self._get_endkey(key)
        rows = view[key:endkey]
        if t:
            self._complete_timing_step(t,datastore_name,'find_subjects.rows')
            stats.add(t)
            self._save_stats_value(datastore_name, 'find_subjects.row_count',  len(rows))
        sub_assocs = [self._persistence_dict_to_ion_object(row['value']) for row in rows]
        sub_ids = [assoc.s for assoc in sub_assocs]

        log.debug("find_subjects() found %s subjects", len(sub_ids))
        if id_only:
            return (sub_ids, sub_assocs)

        sub_list = self.read_mult(sub_ids)
        return (sub_list, sub_assocs)

    def find_associations(self, subject=None, predicate=None, obj=None, assoc_type=None, id_only=True, anyside=None, _time=True, **kwargs):
        log.debug("find_associations(subject=%s, predicate=%s, object=%s, anyside=%s)", subject, predicate, obj, anyside)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not (subject or obj or predicate or anyside):
            raise BadRequest("Illegal parameters: No S/P/O or anyside")
        #if assoc_type:
        #    raise BadRequest("Illegal parameters: assoc_type deprecated")
        if anyside and (subject or obj):
            raise BadRequest("Illegal parameters: anyside cannot be combined with S/O")
        if anyside and predicate and type(anyside) in (list, tuple):
            raise BadRequest("Illegal parameters: anyside list cannot be combined with P")

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
        if anyside:
            if type(anyside) is str:
                anyside_ids = [anyside]
            elif type(anyside) in (list, tuple):
                if not all([type(o) in (str, list, tuple) for o in anyside]):
                    raise BadRequest("List of object ids or (object id, predicate) expected")
                anyside_ids = anyside
            else:
                if "_id" not in anyside:
                    raise BadRequest("Object id not available in anyside")
                else:
                    anyside_ids = [anyside._id]

        ds, datastore_name = self._get_datastore()
        view_args = self._get_view_args(kwargs)
        t = self._get_timer()

        if subject and obj:
            view_type = "by_match"
            view = ds.view(self._get_viewname("association", view_type), **view_args)
            key = [subject_id, object_id]
            if predicate:
                key.append(predicate)
            endkey = self._get_endkey(key)
            rows = view[key:endkey]
        elif subject:
            view_type = "by_sub"
            view = ds.view(self._get_viewname("association", view_type), **view_args)
            key = [subject_id]
            if predicate:
                key.append(predicate)
            endkey = self._get_endkey(key)
            rows = view[key:endkey]
        elif obj:
            view_type = "by_obj"
            view = ds.view(self._get_viewname("association", view_type), **view_args)
            key = [object_id]
            if predicate:
                key.append(predicate)
            endkey = self._get_endkey(key)
            rows = view[key:endkey]
        elif anyside:
            if predicate:
                view_type = "by_idpred"
                view = ds.view(self._get_viewname("association", view_type), **view_args)
                key = [anyside, predicate]
                endkey = self._get_endkey(key)
                rows = view[key:endkey]
            elif type(anyside_ids[0]) is str:
                view_type = "by_id"
                rows = ds.view(self._get_viewname("association", view_type), keys=anyside_ids, **view_args)
            else:
                view_type = "by_idpred"
                rows = ds.view(self._get_viewname("association", view_type), keys=anyside_ids, **view_args)
        elif predicate:
            view_type = "by_pred"
            view = ds.view(self._get_viewname("association", view_type), **view_args)
            key = [predicate]
            endkey = self._get_endkey(key)
            rows = view[key:endkey]
        else:
            raise BadRequest("Illegal arguments")

        if t:
            self._complete_timing_step(t,datastore_name,'find_associations.view')
            stats.add(t)
            self._save_stats_value(datastore_name, 'find_associations.count',  len(rows))

        if id_only:
            assocs = [row.id for row in rows]
        else:
            assocs = [self._persistence_dict_to_ion_object(row['value']) for row in rows]
        log.debug("find_associations() found %s associations", len(assocs))
        return assocs

    def find_resources(self, restype="", lcstate="", name="", id_only=True):
        return self.find_resources_ext(restype=restype, lcstate=lcstate, name=name, id_only=id_only)

    def find_resources_ext(self, restype="", lcstate="", name="",
                           keyword=None, nested_type=None,
                           attr_name=None, attr_value=None, alt_id=None, alt_id_ns=None,
                           limit=None, skip=None, descending=None, id_only=True):
        filter_kwargs = self._get_view_args(dict(limit=limit, skip=skip, descending=descending))
        if name:
            if lcstate:
                raise BadRequest("find by name does not support lcstate")
            return self.find_res_by_name(name, restype, id_only, filter=filter_kwargs)
        elif keyword:
            return self.find_res_by_keyword(keyword, restype, id_only, filter=filter_kwargs)
        elif alt_id or alt_id_ns:
            return self.find_res_by_alternative_id(alt_id, alt_id_ns, id_only, filter=filter_kwargs)
        elif nested_type:
            return self.find_res_by_nested_type(nested_type, restype, id_only, filter=filter_kwargs)
        elif restype and attr_name:
            return self.find_res_by_attribute(restype, attr_name, attr_value, id_only=id_only, filter=filter_kwargs)
        elif restype and lcstate:
            return self.find_res_by_lcstate(lcstate, restype, id_only, filter=filter_kwargs)
        elif restype:
            return self.find_res_by_type(restype, lcstate, id_only, filter=filter_kwargs)
        elif lcstate:
            return self.find_res_by_lcstate(lcstate, restype, id_only, filter=filter_kwargs)
        elif not restype and not lcstate and not name:
            return self.find_res_by_type(None, None, id_only, filter=filter_kwargs)

    def _prepare_find_return(self, rows, res_assocs=None, id_only=True, **kwargs):
        if id_only:
            res_ids = [row.id for row in rows]
            return (res_ids, res_assocs)
        else:
            res_docs = [self._persistence_dict_to_ion_object(row.doc) for row in rows]
            if [True for doc in res_docs if doc is None]:
                res_ids = [row.id for row in rows]
                log.error("Datastore returned None docs despite include_docs==True.\nids=%s\ndocs=%s\nassocs=%s", res_ids, res_docs, res_assocs)
            return (res_docs, res_assocs)

    def find_res_by_type(self, restype, lcstate=None, id_only=False, filter=None):
        log.debug("find_res_by_type(restype=%s, lcstate=%s)", restype, lcstate)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if lcstate:
            raise BadRequest('lcstate not supported anymore in find_res_by_type')
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("resource", "by_type"), include_docs=(not id_only), **filter)
        if restype:
            key = [restype]
            endkey = self._get_endkey(key)
            rows = view[key:endkey]   # Range query
        else:
            # Returns ALL documents, only limited by filter
            rows = view

        res_assocs = [dict(type=row['key'][0], name=row['key'][1], id=row.id) for row in rows]
        log.debug("find_res_by_type() found %s objects", len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_lcstate(self, lcstate, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_lcstate(lcstate=%s, restype=%s)", lcstate, restype)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if '_' in lcstate:
            log.warn("Search for compound lcstate restricted to maturity: %s", lcstate)
            lcstate,_ = lcstate.split("_", 1)
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("resource", "by_lcstate"), include_docs=(not id_only), **filter)
        key = [1, lcstate] if lcstate in CommonResourceLifeCycleSM.AVAILABILITY else [0, lcstate]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        rows = view[key:endkey]   # Range query

        res_assocs = [dict(lcstate=row['key'][1], type=row['key'][2], name=row['key'][3], id=row.id) for row in rows]
        log.debug("find_res_by_lcstate() found %s objects", len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_name(self, name, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_name(name=%s, restype=%s)", name, restype)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("resource", "by_name"), include_docs=(not id_only), **filter)
        key = [name]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        rows = view[key:endkey]   # Range query

        res_assocs = [dict(name=row['key'][0], type=row['key'][1], id=row.id) for row in rows]
        log.debug("find_res_by_name() found %s objects", len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_keyword(self, keyword, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_keyword(keyword=%s, restype=%s)", keyword, restype)
        if not keyword or type(keyword) is not str:
            raise BadRequest('Argument keyword illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("resource", "by_keyword"), include_docs=(not id_only), **filter)
        key = [keyword]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        rows = view[key:endkey]

        res_assocs = [dict(keyword=row['key'][0], type=row['key'][1], id=row.id) for row in rows]
        log.debug("find_res_by_keyword() found %s objects", len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_nested_type(self, nested_type, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_nested_type(nested_type=%s, restype=%s)", nested_type, restype)
        if not nested_type or type(nested_type) is not str:
            raise BadRequest('Argument nested_type illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("resource", "by_nestedtype"), include_docs=(not id_only), **filter)
        key = [nested_type]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        rows = view[key:endkey]

        res_assocs = [dict(nested_type=row['key'][0], type=row['key'][1], id=row.id) for row in rows]
        log.debug("find_res_by_nested_type() found %s objects", len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_attribute(self, restype, attr_name, attr_value=None, id_only=False, filter=None):
        log.debug("find_res_by_attribute(restype=%s, attr_name=%s, attr_value=%s)", restype, attr_name, attr_value)
        if not attr_name or type(attr_name) is not str:
            raise BadRequest('Argument attr_name illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("resource", "by_attribute"), include_docs=(not id_only), **filter)
        key = [restype, attr_name]
        if attr_value:
            key.append(attr_value)
        endkey = self._get_endkey(key)
        rows = view[key:endkey]

        res_assocs = [dict(type=row['key'][0], attr_name=row['key'][1], attr_value=row['key'][2], id=row.id) for row in rows]
        log.debug("find_res_by_attribute() found %s objects", len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_alternative_id(self, alt_id=None, alt_id_ns=None, id_only=False, filter=None):
        log.debug("find_res_by_alternative_id(restype=%s, alt_id_ns=%s)", alt_id, alt_id_ns)
        if alt_id and type(alt_id) is not str:
            raise BadRequest('Argument alt_id illegal')
        if alt_id_ns and type(alt_id_ns) is not str:
            raise BadRequest('Argument alt_id_ns illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        view = ds.view(self._get_viewname("resource", "by_altid"), include_docs=(not id_only), **filter)
        key = []
        if alt_id:
            key.append(alt_id)
            if alt_id_ns is not None:
                key.append(alt_id_ns)

        endkey = self._get_endkey(key)
        rows = view[key:endkey]

        if alt_id_ns and not alt_id:
            res_assocs = [dict(alt_id=row['key'][0], alt_id_ns=row['key'][1], id=row.id) for row in rows if row['key'][1] == alt_id_ns]
        else:
            res_assocs = [dict(alt_id=row['key'][0], alt_id_ns=row['key'][1], id=row.id) for row in rows]
        log.debug("find_res_by_alternative_id() found %s objects", len(res_assocs))
        if id_only:
            res_ids = [row['id'] for row in res_assocs]
            return (res_ids, res_assocs)
        else:
            if alt_id_ns and not alt_id:
                res_docs = [self._persistence_dict_to_ion_object(row.doc) for row in rows if row['key'][1] == alt_id_ns]
            else:
                res_docs = [self._persistence_dict_to_ion_object(row.doc) for row in rows]
            return (res_docs, res_assocs)

    def find_res_by_view(self, design_name, view_name, key=None, keys=None, start_key=None, end_key=None,
                     id_only=True, **kwargs):
        # TODO: Refactor common code out of above find functions
        pass

    def find_by_view(self, design_name, view_name, key=None, keys=None, start_key=None, end_key=None,
                           id_only=True, convert_doc=True, **kwargs):
        """
        @brief Generic find function using an defined index
        @retval Returns a list of triples: (object _id, index key, Document/object or None)
        """
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
            log.debug("find_by_view(%s): key=%s", view_doc, key)
        elif keys:
            rows = view
            log.debug("find_by_view(%s): keys=%s", view_doc, keys)
        elif start_key and end_key:
            startkey = start_key or []
            endkey = list(end_key) or []
            endkey.append(END_MARKER)
            log.debug("find_by_view(%s): start_key=%s to end_key=%s", view_doc, startkey, endkey)
            if view_args.get('descending', False):
                rows = view[endkey:startkey]
            else:
                rows = view[startkey:endkey]
        else:
            rows = view

        if id_only:
            if convert_doc:
                res_rows = [(row['id'], row['key'], self._persistence_dict_to_ion_object(row['value'])) for row in rows]
            else:
                res_rows = [(row['id'], row['key'], row['value']) for row in rows]
        else:
            if convert_doc:
                res_rows = [(row['id'], row['key'], self._persistence_dict_to_ion_object(row['doc'])) for row in rows]
            else:
                res_rows = [(row['id'], row['key'], row['doc']) for row in rows]

        log.debug("find_by_view() found %s objects", len(res_rows))
        return res_rows

    def _get_endkey(self, startkey):
        if startkey is None or type(startkey) is not list:
            raise BadRequest("Cannot create endkey for type %s" % type(startkey))
        endkey = list(startkey)
        endkey.append(END_MARKER)
        return endkey

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
        raise BadRequest('temporary views are not supported by bigcouch')
#        ds, datastore_name = self._get_datastore(datastore_name)
#        res = ds.query(map_fun, reduce_fun, **options)
#
#        return self._parse_results(res)

    def _parse_results(self, doc):
        ''' Parses a complex object and organizes it into basic types '''
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
        if isinstance(doc, Row):
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

        if isinstance(doc, list):
            ret = []
            for element in doc:
                ret.append(self._parse_results(element))
            return ret
        #-------------------------------
        # Handle a dic
        #-------------------------------
        # \_ Check to make sure it's not an IonObject
        # \_ Parse the key value structure for other objects
        if isinstance(doc, dict):
            if '_id' in doc:
                # IonObject
                return self._persistence_dict_to_ion_object(doc)

            for key, value in doc.iteritems():
                ret[key] = self._parse_results(value)
            return ret

        #-------------------------------
        # Primitive type
        #-------------------------------
        return doc


    #### helper methods to simplify creating unique names for timing and statistics
    #    timing steps should be: couchdb.$(DBNAME).$(OPERATION).$(STEP)
    #    for example: couchdb.events.create_doc_mult.save
    #    value stats should be: couchdb.$(DBNAME).$(OPERATION).$(VALUE)
    #    for example: couchdb.resources.create_doc_mult.count

    def _get_timer(self, condition=True):
        return Timer(logger=None) if condition and stats.is_log_enabled() else None

    def _format_timer(self, template, store):
        store_name = store or self.datastore_name
        parts = store_name.split('_')
        short_name = parts[-1]
        return template % short_name

    def _complete_timing_step(self, timer, store, step):
        name = self._format_timer('couchdb.%s.'+step, store)
        timer.complete_step(name)

    def _save_stats_value(self, store, step, value):
        name = self._format_timer('couchdb.%s.'+step, store)
        stats.add_value(name, value)
