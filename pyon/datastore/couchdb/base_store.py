#!/usr/bin/env python

"""Standalone use utility methods for CouchDB"""

__author__ = 'Thomas R. Lennan, Michael Meisinger'


from uuid import uuid4
import couchdb
from couchdb.http import PreconditionFailed, ResourceConflict, ResourceNotFound, ServerError
import gevent

from pyon.datastore.couchdb.couch_common import AbstractCouchDataStore
from pyon.datastore.couchdb.views import get_couchdb_view_designs
from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.util.containers import get_safe, DictDiffer

from ooi.logging import log


class CouchDataStore(AbstractCouchDataStore):
    """
    Datastore implementation utilizing CouchDB to persist documents.
    For API info, see: http://packages.python.org/CouchDB/client.html.
    A base datastore knows how to manage datastores, CRUD documents (dict) and access generic indexes.
    """
    def __init__(self, datastore_name=None, config=None, scope=None, profile=None, **kwargs):
        super(CouchDataStore, self).__init__(datastore_name=datastore_name, config=config, scope=scope, profile=profile)

        if self.config.get("type", None) and self.config['type'] != "couchdb":
            raise BadRequest("Datastore server config is not couchdb: %s" % self.config)
        if self.datastore_name and self.datastore_name != self.datastore_name.lower():
            raise BadRequest("Invalid CouchDB datastore name: '%s'" % self.datastore_name)
        if self.scope and self.scope != self.scope.lower():
            raise BadRequest("Invalid CouchDB scope name: '%s'" % self.scope)

        # Connection
        if self.username and self.password:
            connection_str = "http://%s:%s@%s:%s" % (self.username, self.password, self.host, self.port)
            log_connection_str = "http://%s:%s@%s:%s" % ("username", "password", self.host, self.port)
            log.debug("Using username:password authentication to connect to datastore")
        else:
            connection_str = "http://%s:%s" % (self.host, self.port)
            log_connection_str = connection_str

        log.info("Connecting to CouchDB server: %s", log_connection_str)
        self.server = couchdb.Server(connection_str)

        self._id_factory = None   # TODO

        # Just to test existence of the datastore
        if self.datastore_name:
            try:
                ds, _ = self._get_datastore()
            except NotFound:
                self.create_datastore()
                ds, _ = self._get_datastore()

    def close(self):
        """
        Close any connections required for this datastore.
        """
        log.trace("Closing connection to %s", self.datastore_name)
        # Compatiblity between couchdb client 0.8 and 0.9
        if hasattr(self.server.resource.session, 'conns'):
            conns = self.server.resource.session.conns
            self.server.resource.session.conns = {}     # just in case we try to reuse this, for some reason
        else:
            conns = self.server.resource.session.connection_pool.conns
            self.server.resource.session.connection_pool.conns = {}     # just in case we try to reuse this, for some reason
        map(lambda x: map(lambda y: y.close(), x), conns.values())


    # -------------------------------------------------------------------------
    # Couch database operations

    def _get_datastore(self, datastore_name=None):
        """
        Returns the couch datastore instance and datastore name.
        This caches the datastore instance to avoid an explicit lookup to save on http request.
        The consequence is that if another process deletes the datastore in the meantime, we will fail later.
        """
        datastore_name = self._get_datastore_name(datastore_name)

        if datastore_name in self._datastore_cache:
            return self._datastore_cache[datastore_name], datastore_name

        try:
            ds = self.server[datastore_name]   # Note: causes http lookup
            self._datastore_cache[datastore_name] = ds
            return ds, datastore_name
        except ResourceNotFound:
            raise NotFound("Datastore '%s' does not exist" % datastore_name)
        except ValueError:
            raise BadRequest("Datastore name '%s' invalid" % datastore_name)
        except ServerError as se:
            raise BadRequest("Data store name %s invalid" % datastore_name)

    def _create_datastore(self, datastore_name):
        try:
            self.server.create(datastore_name)
        except PreconditionFailed:
            raise BadRequest("Datastore with name %s already exists" % datastore_name)
        except ValueError:
            raise BadRequest("Datastore name %s invalid" % datastore_name)
        except ServerError as se:
            if se.message[1][0] == 'illegal_database_name':
                raise BadRequest("Data store name %s invalid" % datastore_name)
            else:
                raise

    def delete_datastore(self, datastore_name=None):
        try:
            super(CouchDataStore, self).delete_datastore(datastore_name)
        except ResourceNotFound:
            raise NotFound('Datastore %s does not exist' % datastore_name)
        except ValueError:
            raise BadRequest("Datastore name %s invalid" % datastore_name)
        except ServerError as se:
            if se.message[1][0] == 'illegal_database_name':
                raise BadRequest("Data store name %s invalid" % datastore_name)
            else:
                raise

    def list_datastores(self):
        """
        List all datastores within this datastore server. This is
        equivalent to listing all databases hosted on a database server.
        Returns scoped names.
        """
        return list(self.server)

    def info_datastore(self, datastore_name=None):
        """
        List information about a datastore.  Content may vary based
        on datastore type.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        info = ds.info()
        return info

    def compact_datastore(self, datastore_name=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        return ds.compact()

    def datastore_exists(self, datastore_name=None):
        """
        Indicates whether named datastore currently exists.
        """
        datastore_name = self._get_datastore_name(datastore_name)
        try:
            self.server[datastore_name]
            return True
        except ResourceNotFound:
            return False


    # -------------------------------------------------------------------------
    # Couch document operations

    def list_objects(self, datastore_name=None):
        """
        List all object types existing in the datastore instance.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        return list(ds)

    def list_object_revisions(self, object_id, datastore_name=None):
        """
        Method for itemizing all the versions of a particular object
        known to the datastore.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        gen = ds.revisions(object_id)
        res = [ent["_rev"] for ent in gen]
        return res


    def _save_doc(self, ds, doc):
        try:
            obj_id, version = ds.save(doc)
        except ResourceConflict:
            if "_rev" in doc:
                raise Conflict("Object with id %s revision conflict" % doc["_id"])
            else:
                raise BadRequest("Object with id %s already exists" % doc["_id"])

        return obj_id, version

    def _save_doc_mult(self, ds, docs):
        res = ds.update(docs)
        return res

    def create_doc(self, doc, object_id=None, attachments=None, datastore_name=None):
        if '_rev' in doc:
            raise BadRequest("Doc must not have '_rev'")
        return super(CouchDataStore, self).create_doc(doc, object_id=object_id, attachments=attachments, datastore_name=datastore_name)

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
        self._count(create_attachment=1)

    def update_doc(self, doc, datastore_name=None):
        if '_rev' not in doc:
            raise BadRequest("Doc must have '_rev'")
        return super(CouchDataStore, self).update_doc(doc, datastore_name=datastore_name)

    def update_doc_mult(self, docs, datastore_name=None):
        if not all(["_rev" in doc for doc in docs]):
            raise BadRequest("Docs must have '_rev'")

        return super(CouchDataStore, self).update_doc_mult(docs, datastore_name=datastore_name)

    def update_attachment(self, doc, attachment_name, data, content_type=None, datastore_name=""):
        self.create_attachment(doc=doc, attachment_name=attachment_name, data=data,
                               content_type=content_type,
                               datastore_name=datastore_name)
        self._count(update_attachment=1)

    def read_doc(self, doc_id, rev_id=None, datastore_name=None, object_type=None):
        """"
        Fetch a raw doc instance.  If rev_id is specified, an attempt
        will be made to return that specific doc version.  Otherwise,
        the HEAD version is returned.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        if not rev_id:
            doc = ds.get(doc_id)
            if doc is None:
                raise NotFound('Object with id %s does not exist.' % doc_id)
        else:
            # There was an issue with couchdb_python 0.8 and concurrent use of this library
            # See https://code.google.com/p/couchdb-python/issues/detail?id=204
            # Fixed in client 0.9
            doc = ds.get(doc_id, rev=rev_id)
            if doc is None:
                raise NotFound('Object with id %s does not exist.' % doc_id)
        self._count(read=1)

        return doc

    def read_doc_mult(self, object_ids, datastore_name=None, strict=True):
        """"
        Fetch a number of raw doc instances, HEAD rev.
        """
        if not object_ids:
            return []
        ds, datastore_name = self._get_datastore(datastore_name)
        rows = ds.view("_all_docs", keys=object_ids, include_docs=True)

        if strict:
            # Check for docs not found
            notfound_list = ['Object with id %s does not exist.' % str(row.key)
                             for row in rows if row.doc is None]
            if notfound_list:
                raise NotFound("\n".join(notfound_list))

        doc_list = [row.doc.copy() if row.doc is not None else None for row in rows]   # TODO: Is copy() necessary?
        self._count(read_mult_call=1, read_mult_obj=len(doc_list))

        return doc_list

    def read_attachment(self, doc, attachment_name, datastore_name=""):
        if not isinstance(attachment_name, str):
            raise BadRequest("Attachment_name param is not str")

        ds, datastore_name = self._get_datastore(datastore_name)

        attachment = ds.get_attachment(doc, attachment_name)

        if attachment is None:
            raise NotFound('Attachment %s does not exist in document %s.%s.',
                           attachment_name, datastore_name, doc)

        attachment_content = attachment.read()
        if not isinstance(attachment_content, str):
            raise NotFound('Attachment read is not a string')

        self._count(read_attachment=1)

        return attachment_content

    def list_attachments(self, doc):
        """
        Returns the a list of attachments for the document, as a dict of dicts, key'ed by name with
        nested keys 'data' for the content and 'content-type'.
        @param doc  accepts either str (meaning an id) or dict (a full document).
        """
        if isinstance(doc, dict) and '_attachments' not in doc:
            # Need to reread again, because it did not contain the _attachments
            doc = self.read_doc(doc_id=doc["_id"])
        elif isinstance(doc, str):
            doc = self.read_doc(doc_id=doc)

        attachment_list = doc.get("_attachments", None)
        return attachment_list

    def delete_doc(self, doc, datastore_name=None, object_type=None, **kwargs):
        """
        Remove all versions of specified raw doc from the datastore.
        This method will check the '_rev' value to ensure that the doc
        provided is the most recent known doc version.  If not, a
        Conflict exception is thrown.
        If object id (str) is given instead of an object, deletes the
        object with the given id.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        doc_id = doc if type(doc) is str else doc["_id"]
        log.debug('Deleting object %s/%s', datastore_name, doc_id)
        try:
            if type(doc) is str:
                del ds[doc_id]
            else:
                ds.delete(doc)
        except ResourceNotFound:
            raise NotFound('Object with id %s does not exist.' % doc_id)
        except ResourceConflict:
            raise Conflict("Object with id %s revision conflict" % doc["_id"])

    def delete_doc_mult(self, object_ids, datastore_name=None, object_type=None):
        obj_list = self.read_doc_mult(object_ids, datastore_name=datastore_name)
        for obj in obj_list:
            obj['_deleted'] = True
        self.update_doc_mult(obj_list, datastore_name=datastore_name)
        self._count(delete_mult_call=1, delete_mult_obj=len(obj_list))

    def delete_attachment(self, doc, attachment_name, datastore_name=""):
        """
        Deletes an attachment from a document.
        """
        if not isinstance(attachment_name, str):
            raise BadRequest("attachment_name is not a string")

        if isinstance(doc, str):
            doc = self.read_doc(doc_id=doc, datastore_name=datastore_name)

        ds, datastore_name = self._get_datastore(datastore_name)

        log.debug('Delete attachment %s of document %s', attachment_name, doc["_id"])
        ds.delete_attachment(doc, attachment_name)
        self._count(delete_attachment=1)


    # -------------------------------------------------------------------------
    # View operations

    def compact_views(self, design, datastore_name=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        return ds.compact(design)

    def define_profile_views(self, profile=None, datastore_name=None, keepviews=False):
        profile = profile or self.profile
        ds_views = get_couchdb_view_designs(profile)
        self._define_profile_views(ds_views, datastore_name=datastore_name, keepviews=keepviews)

    def define_viewset(self, design_name, design_doc, datastore_name=None, keepviews=False):
        """
        Create or update a design document (i.e. a set of views).
        If design exists, only updates if view definitions are different to prevent rebuild of indexes.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        doc_name = self._get_design_name(design_name)
        try:
            ds[doc_name] = dict(views=design_doc)
        #except ResourceConflict:
        except Exception:
            # View exists
            old_design = ds[doc_name]
            if not keepviews:
                try:
                    try:
                        del ds[doc_name]
                    except ResourceNotFound:
                        pass
                    ds[doc_name] = dict(views=design_doc)
                except Exception as ex:
                    # In case this gets executed concurrently and 2 processes perform the same creates
                    log.warn("Error defining datastore %s view %s (concurrent create?): %s", datastore_name, doc_name, str(ex))
            else:
                ddiff = DictDiffer(old_design.get("views", {}), design_doc)
                if ddiff.changed():
                    old_design["views"] = design_doc
                    ds.save(old_design)

    def refresh_views(self, datastore_name="", profile=None):
        """
        Triggers a refresh of all views (all designs) for this datastore's profile
        """
        profile = profile or self.profile
        ds_views = get_couchdb_view_designs(profile)
        for design_name, design_doc in ds_views.iteritems():
            self.refresh_viewset(design_name, datastore_name=datastore_name)

    def refresh_viewset(self, design, datastore_name=None):
        """
        Triggers the rebuild of a design document (set of views).
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        doc_id = self._get_design_name(design)
        try:
            design_doc = ds[doc_id]
            view_name = design_doc["views"].keys()[0]
            ds.view(self._get_view_name(design, view_name))
        except Exception:
            log.exception("Problem with design %s/%s", datastore_name, doc_id)

    def delete_views(self, design, datastore_name=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        try:
            del ds[self._get_design_name(design)]
        except ResourceNotFound:
            pass

