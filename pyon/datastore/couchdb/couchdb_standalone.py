#!/usr/bin/env python

"""Standalone use utility methods for CouchDB"""

__author__ = 'Thomas R. Lennan, Michael Meisinger'


from uuid import uuid4
import couchdb
from couchdb.http import PreconditionFailed, ResourceConflict, ResourceNotFound

from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.util.containers import get_safe, SimpleLog, DictDiffer

log = SimpleLog("CouchDataStore", 0)

# Token for a most likely non-inclusive key range upper bound (end_key), for queries such as
# prefix <= keys < upper bound: e.g. ['some','value'] <= keys < ['some','value', END_MARKER]
# or "somestr" <= keys < "somestr"+END_MARKER for string prefix checking
# Note: Use highest ASCII characters here, not 8bit
#END_MARKER = "\x7f\x7f\x7f\x7f"
END_MARKER = "ZZZZZZ"


class CouchDataStore(object):
    """
    Data store implementation utilizing CouchDB to persist documents.
    For API info, see: http://packages.python.org/CouchDB/client.html
    """
    def __init__(self, datastore_name=None, host=None, port=None, username=None, password=None, config=None, newlog=None, **kwargs):
        """
        @param datastore_name  Name of datastore within server. Should be scoped by caller with sysname
        @param config  A standard config dict with connection params
        """
        global log
        if newlog:
            log = newlog

        self.datastore_name = datastore_name.lower() if datastore_name else None
        self.host = host or get_safe(config, 'server.couchdb.host') or 'localhost'
        self.port = port or get_safe(config, 'server.couchdb.port') or 5984
        self.username = username or get_safe(config, 'server.couchdb.username')
        self.password = password or get_safe(config, 'server.couchdb.password')
        if self.username and self.password:
            connection_str = "http://%s:%s@%s:%s" % (self.username, self.password, self.host, self.port)
            log.debug("Using username:password authentication to connect to datastore")
        else:
            connection_str = "http://%s:%s" % (self.host, self.port)

        # TODO: Potential security risk to emit password into log.
        log.info('Connecting to CouchDB server: %s' % connection_str)
        self.server = couchdb.Server(connection_str)

        self._datastore_cache = {}

        # Just to test existence of the datastore
        if self.datastore_name:
            ds, _ = self._get_datastore()

    def close(self):
        """
        Close any connections required for this datastore.
        """
        log.info("Closing connection to CouchDB")
        map(lambda x: map(lambda y: y.close(), x), self.server.resource.session.conns.values())
        self.server.resource.session.conns = {}     # just in case we try to reuse this, for some reason

    # -------------------------------------------------------------------------
    # Couch database operations

    def _get_datastore(self, datastore_name=None):
        datastore_name = datastore_name or self.datastore_name
        if not datastore_name:
            raise BadRequest("No data store name provided")

        if datastore_name in self._datastore_cache:
            return self._datastore_cache[datastore_name], datastore_name

        try:
            ds = self.server[datastore_name] #http lookup
            self._datastore_cache[datastore_name] = ds
            return ds, datastore_name
        except ResourceNotFound:
            raise NotFound("Data store '%s' does not exist" % datastore_name)
        except ValueError:
            raise BadRequest("Data store name '%s' invalid" % datastore_name)

    def create_datastore(self, datastore_name=None, **kwargs):
        """
        Create a data store with the given name.  This is
        equivalent to creating a database on a database server.
        """
        datastore_name = datastore_name or self.datastore_name
        try:
            self.server.create(datastore_name)
        except PreconditionFailed:
            raise BadRequest("Data store with name %s already exists" % datastore_name)
        except ValueError:
            raise BadRequest("Data store name %s invalid" % datastore_name)

    def delete_datastore(self, datastore_name=None):
        """
        Delete the data store with the given name.  This is
        equivalent to deleting a database from a database server.
        """
        datastore_name = datastore_name or self.datastore_name
        try:
            self.server.delete(datastore_name)
        except ResourceNotFound:
            raise NotFound('Data store %s does not exist' % datastore_name)
        except ValueError:
            raise BadRequest("Data store name %s invalid" % datastore_name)

    def list_datastores(self):
        """
        List all data stores within this data store server. This is
        equivalent to listing all databases hosted on a database server.
        """
        return list(self.server)

    def info_datastore(self, datastore_name=None):
        """
        List information about a data store.  Content may vary based
        on data store type.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        info = ds.info()
        return info

    def compact_datastore(self, datastore_name=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        return ds.compact()

    def exists_datastore(self, datastore_name=None):
        """
        Indicates whether named data store currently exists.
        """
        datastore_name = datastore_name or self.datastore_name
        try:
            ds = self.server[datastore_name]
            return True
        except ResourceNotFound:
            return False

    # -------------------------------------------------------------------------
    # Couch document operations

    def list_objects(self, datastore_name=None):
        """
        List all object types existing in the data store instance.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        return list(ds)

    def list_object_revisions(self, object_id, datastore_name=None):
        """
        Method for itemizing all the versions of a particular object
        known to the data store.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        gen = ds.revisions(object_id)
        res = [ent["_rev"] for ent in gen]
        return res

    def save_doc(self, doc, object_id=None, datastore_name=None):
        """
        Create or update document
        @param doc  A dict with a document to create or update
        @oaram object_id  The ID for the new document
        """
        ds, datastore_name = self._get_datastore(datastore_name)

        # Assign an id to doc (recommended in CouchDB documentation)
        if "_id" not in doc:
            doc["_id"] = object_id or uuid4().hex

        try:
            obj_id, version = ds.save(doc)
        except ResourceConflict:
            if "_rev" in doc:
                raise Conflict("Object with id %s revision conflict" % doc["_id"])
            else:
                raise BadRequest("Object with id %s already exists" % doc["_id"])

        return obj_id, version

    def create_doc(self, doc, object_id=None, datastore_name=None):
        """"
        Persist a new raw doc in the data store. An '_id' and initial
        '_rev' value will be added to the doc.
        """
        if object_id and '_id' in doc:
            raise BadRequest("Doc must not have '_id'")
        if '_rev' in doc:
            raise BadRequest("Doc must not have '_rev'")
        return self.save_doc(doc, object_id, datastore_name)

    def update_doc(self, doc, datastore_name=None):
        """
        Update an existing raw doc in the data store.  The '_rev' value
        must exist in the doc and must be the most recent known doc
        version. If not, a Conflict exception is thrown.
        """
        if '_id' not in doc:
            raise BadRequest("Doc must have '_id'")
        if '_rev' not in doc:
            raise BadRequest("Doc must have '_rev'")
        return self.save_doc(doc, datastore_name=datastore_name)

    def save_doc_mult(self, docs, object_ids=None, datastore_name=None):
        if type(docs) is not list:
            raise BadRequest("Invalid type for docs:%s" % type(docs))

        if object_ids:
            for doc, oid in zip(docs, object_ids):
                doc["_id"] = oid
        else:
            for doc in docs:
                if "_id" not in doc:
                    doc["_id"] = uuid4().hex

        ds, datastore_name = self._get_datastore(datastore_name)
        res = ds.update(docs)

        if not all([success for success, oid, rev in res]):
            errors = ["%s:%s" % (oid, rev) for success, oid, rev in res if not success]
            log.error('create_doc_mult had errors. Successful: %s, errors: %s' % (len(res) - len(errors), "\n".join(errors)))
        return res

    def create_doc_mult(self, docs, object_ids=None, datastore_name=None):
        """
        Create multiple raw docs.
        Returns list of (Success, Oid, rev)
        """
        if object_ids and any(["_id" in doc for doc in docs]):
            raise BadRequest("Docs must not have '_id'")
        if any(["_rev" in doc for doc in docs]):
            raise BadRequest("Docs must not have '_rev'")
        if object_ids and len(object_ids) != len(docs):
            raise BadRequest("Invalid object_ids length")

        return self.save_doc_mult(docs, object_ids, datastore_name=datastore_name)

    def update_doc_mult(self, docs, datastore_name=None):
        if not all(["_id" in doc for doc in docs]):
            raise BadRequest("Docs must have '_id'")
        if not all(["_rev" in doc for doc in docs]):
            raise BadRequest("Docs must have '_rev'")

        return self.save_doc_mult(docs, datastore_name=datastore_name)

    def read_doc(self, doc_id, rev_id=None, datastore_name=None):
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
            doc = ds.get(doc_id, rev=rev_id)
            if doc is None:
                raise NotFound('Object with id %s does not exist.' % doc_id)
        return doc

    def read_doc_mult(self, object_ids, datastore_name=None):
        """"
        Fetch a raw doc instances, HEAD rev.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        docs = ds.view("_all_docs", keys=object_ids, include_docs=True)
        # Check for docs not found
        notfound_list = ['Object with id %s does not exist.' % str(row.key) for row in docs if row.doc is None]
        if notfound_list:
            raise NotFound("\n".join(notfound_list))

        doc_list = [row.doc.copy() for row in docs]
        return doc_list

    def delete_doc(self, doc, datastore_name=None, **kwargs):
        """
        Remove all versions of specified raw doc from the data store.
        This method will check the '_rev' value to ensure that the doc
        provided is the most recent known doc version.  If not, a
        Conflict exception is thrown.
        If object id (str) is given instead of an object, deletes the
        object with the given id.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        doc_id = doc if type(doc) is str else doc["_id"]
        try:
            if type(doc) is str:
                del ds[doc_id]
            else:
                ds.delete(doc)
        except ResourceNotFound:
            raise NotFound('Object with id %s does not exist.' % doc_id)
        except ResourceConflict:
            raise Conflict("Object with id %s revision conflict" % doc["_id"])

    def delete_doc_mult(self, object_ids, datastore_name=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        obj_list = self.read_doc_mult(object_ids, datastore_name=datastore_name)
        for obj in obj_list:
            obj['_deleted'] = True
        self.save_doc_mult(obj_list, datastore_name=datastore_name)

    # -------------------------------------------------------------------------
    # Couch view operations

    def _get_design_name(self, design):
        return "_design/%s" % design

    def _get_view_name(self, design, name):
        return "_design/%s/_view/%s" % (design, name)

    def compact_views(self, design, datastore_name=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        return ds.compact(design)

    def define_profile_views(self, ds_views, datastore_name=None):
        for design, viewdef in ds_views.iteritems():
            self.define_views(design, viewdef, datastore_name=datastore_name)

    def define_views(self, design, viewdef, datastore_name=None):
        """
        Create or update a design document (set of views).
        If design exists, only updates if view definitions are different to prevent rebuild of indexes.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        doc_name = self._get_design_name(design)
        try:
            ds[doc_name] = dict(views=viewdef)
        except ResourceConflict:
            # View exists
            old_design = ds[doc_name]
            ddiff = DictDiffer(old_design.get("views", {}), viewdef)
            if ddiff.changed():
                old_design["views"] = viewdef
                ds.save(old_design)

    def refresh_views(self, design, datastore_name=None):
        """
        Triggers the rebuild of a design document (set of views).
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        doc_id = self._get_design_name(design)

        try:
            design_doc = ds[doc_id]
            view_name = design_doc["views"].keys()[0]
            rows = ds.view(self._get_view_name(design, view_name))
        except Exception, ex:
            log.exception("Problem with design %s/%s" ,datastore_name, doc_id)

    def delete_views(self, design, datastore_name=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        try:
            del ds[self._get_design_name(design)]
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


    def find_docs_by_view(self, design_name, view_name, key=None, keys=None, start_key=None, end_key=None,
                          id_only=True, **kwargs):
        """
        @brief Generic find function using an defined index
        @retval Returns a list of triples: (att_id, index_row, Attachment object or none)
        """
        log.debug("find_docs_by_view(%s/%s)",design_name, view_name)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        ds, datastore_name = self._get_datastore()

        view_args = self._get_view_args(kwargs)
        view_args['include_docs'] = (not id_only)
        view_doc = design_name if design_name == "_all_docs" else self._get_view_name(design_name, view_name)
        if keys:
            view_args['keys'] = keys
        view = ds.view(view_doc, **view_args)
        if key is not None:
            rows = view[key]
            log.info("find_docs_by_view(): key=%s" % key)
        elif keys:
            rows = view
            log.info("find_docs_by_view(): keys=%s" % keys)
        elif start_key and end_key:
            startkey = start_key or []
            endkey = list(end_key) or []
            endkey.append(END_MARKER)
            log.info("find_docs_by_view(): start_key=%s to end_key=%s" % (startkey, endkey))
            if view_args.get('descending', False):
                rows = view[endkey:startkey]
            else:
                rows = view[startkey:endkey]
        else:
            rows = view

        if id_only:
            res_rows = [(row['id'],row['key'], None) for row in rows]
        else:
            res_rows = [(row['id'],row['key'],row['doc']) for row in rows]

        log.info("find_docs_by_view() found %s objects" % (len(res_rows)))
        return res_rows
