#!/usr/bin/env python

"""Standalone use utility methods for CouchDB"""

__author__ = 'Thomas R. Lennan, Michael Meisinger'


from uuid import uuid4
from couchbase.client import Couchbase, Bucket
from couchbase.rest_client import RestHelper

from pyon.core.exception import BadRequest, Conflict, NotFound, ServerError
from pyon.util.containers import get_safe, DictDiffer
from couchbase.exception import BucketCreationException, BucketUnavailableException
from pyon.core.bootstrap import get_obj_registry, CFG
from couchbase.exception import MemcachedError
import json
from gevent import sleep
from ooi.logging import log
import requests

import couchbase.client
import couchbase.rest_client
couchbase.client.json = json
couchbase.rest_client.json = json

# Token for a most likely non-inclusive key range upper bound (end_key), for queries such as
# prefix <= keys < upper bound: e.g. ['some','value'] <= keys < ['some','value', END_MARKER]
# or "somestr" <= keys < "somestr"+END_MARKER for string prefix checking
# Note: Use highest ASCII characters here, not 8bit
#END_MARKER = "\x7f\x7f\x7f\x7f"
END_MARKER = "ZZZZZZ"

class CouchbaseDataStore(object):
    """
    Data store implementation utilizing CouchDB to persist documents.
    For API info, see: http://packages.python.org/CouchDB/client.html
    """
    def __init__(self, datastore_name=None, host=None, port=None, username=None, password=None,
                 config=None, newlog=None, scope=None, **kwargs):
        """
        @param datastore_name  Name of datastore within server. Should be scoped by caller with sysname
        @param config  A standard config dict with connection params
        @param scope  Identifier to prefix the datastore name (e.g. sysname)
        """
        global log
        if newlog:
            log = newlog

        # Connection
        self.host = host or get_safe(config, 'server.couchbase.host') or 'localhost'
        self.port = port or get_safe(config, 'server.couchbase.port') or 8091
        self.username = username or get_safe(config, 'server.couchbase.username')
        self.password = password or get_safe(config, 'server.couchbase.password')
        self.config = config

        connection_str = '%s:%s' %(self.host, self.port)


        # TODO: Potential security risk to emit password into log.
        self.server = Couchbase(connection_str, username=self.username, password=self.password)

        self._datastore_cache = {}

        # Datastore (couch database) handling. Scope with given scope (sysname) and make all lowercase
        self.scope = scope
        if self.scope:
            self.datastore_name = ("%s_%s" % (self.scope, datastore_name)).lower() if datastore_name else None
        else:
            self.datastore_name = datastore_name.lower() if datastore_name else None

        log.info('Connecting to Couchbase standalone server: %s, username: %s datastore: %s' % (connection_str, self.username, self.datastore_name))
        # Just to test existence of the datastore
        if self.datastore_name:
            ####print "\n\n datastore name is set\n\n"
            if not self.exists_datastore(self.datastore_name):
                ####print "\n\n try creating datastore ", self.datastore_name, "\n\n\n"
                self.create_datastore()
                ds, _ = self._get_datastore()

        log.info('done connection')
    def close(self):
        log.debug("Closing connection to Couchbase")
        '''
        ds, _ = self._get_datastore()
        del ds
        del self.server
        ##TODO:  is there a way to close connection
        '''
        pass


    def _get_datastore_name(self, datastore_name=None):
        """
        Computes a name for the datastore to work on. If name is given, uses the lower case
        version of this name. If this instance was initialized with a scope, the name is additionally
        scoped. If no name was given, the instance defaults will be returned.
        """
        if datastore_name and self.scope:
            datastore_name = ("%s_%s" % (self.scope, datastore_name)).lower()
        elif datastore_name:
            datastore_name = datastore_name.lower()
        elif self.datastore_name:
            datastore_name = self.datastore_name
        else:
            raise BadRequest("No data store name provided")
            ####print "\n\n get_data_name 2", datastore_name
        return datastore_name

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
        except ValueError:
            raise BadRequest("Data store name '%s' invalid" % datastore_name)

    def create_datastore(self, datastore_name=None, **kwargs):
        """
        Create a data store with the given name.  This is
        equivalent to creating a database on a database server.
        @param datastore_name  Datastore to work on. Will be scoped if scope was provided.
        """
        datastore_name = self._get_datastore_name(datastore_name)
        log.debug("Create datastore name: %s" %datastore_name)
        ####print "\n\n\n create datastore  ", datastore_name, "\n\n"

        bucket_password = get_safe(self.config, 'server.couchbase.bucket_password') or None
        ram_quota_mb = get_safe(self.config, 'server.couchbase.bucket_ram_quota_samll_mb') or None
        if not self.exists_datastore(datastore_name):
            self._create_bucket(name=datastore_name, sasl_password=bucket_password, ram_quota_mb=ram_quota_mb)

    def _create_bucket(self, name, auth_type='sasl', bucket_type='couchbase', parallel_db_and_view_compaction='false',
                       ram_quota_mb="128", replica_index='0', replica_number='1', sasl_password=None, flush_enabled=False, proxy_port=11211):
        '''
        If you set authType to "none", then you must specify a proxyPort number.
        If you set authType to "sasl", then you may optionally provide a "saslPassword" parameter.
           For Couchbase Sever 1.6.0, any SASL authentication-based access must go through a proxy at port 11211.
        '''

        payload = dict()
        payload['name'] = name
        payload['authType'] = auth_type
        payload['bucketType'] = bucket_type
        if flush_enabled:
            payload['flushEnabled'] = '1'
        if parallel_db_and_view_compaction:
            payload['parallelDBAndViewCompaction'] = parallel_db_and_view_compaction
            payload['proxyPort'] = proxy_port
        payload['ramQuotaMB'] = ram_quota_mb
        if replica_index:
            payload['replicaIndex'] = replica_index
        if replica_number:
            payload['replicaNumber'] = replica_number
        if sasl_password:
            payload['saslPassword'] = sasl_password
        response = requests.post('http://%s:%s/pools/default/buckets' %(self.host, self.port), auth=(self.username, self.password), data=payload)
        if response.status_code != 202:
            log.error('Unable to create bucket %s on %s' % (name, self.host))
            raise BadRequest ('Couchbase returned error - status code:%d - error_string from Couchbase: %s' %(response.status_code, response.content))
        sleep(2)

    def delete_datastore(self, datastore_name=None):
        """
        Delete the data store with the given name.  This is
        equivalent to deleting a database from a database server.
        """
        log.debug("Delete datastore name: %s" % datastore_name)
        datastore_name = self._get_datastore_name(datastore_name)
        try:
            if datastore_name in self._datastore_cache:
                del self._datastore_cache[datastore_name]
            self.server.delete(datastore_name)
        except BucketUnavailableException as e:
            raise NotFound('Couchbase unable to delete bucket named %s on %s. Exception: %s ' %(datastore_name, e.parameters.get('host', None), e._message))
        # This was added due to Couchbase generating a JSON exception error when trying to delete non-existent bucket.
        except:
            raise ServerError('Couchbase returned unknown error')

    def list_datastores(self):
        """
        List all data stores within this data store server. This is
        equivalent to listing all databases hosted on a database server.
        Returns scoped names.
        """
        dsn = [str(db.name) for db in self.server]
        log.debug("List datastore: %s" % str(dsn))
        return dsn

    def info_datastore(self, datastore_name=None):
        """
        List information about a data store.  Content may vary based
        on data store type.
        """
        log.debug("List datastore")
        ds, datastore_name = self._get_datastore(datastore_name)
        # TODO is this correct?
        info = ds.stats
        return info

    def compact_datastore(self, datastore_name=None):
        #ds, datastore_name = self._get_datastore(datastore_name)
        #return ds.compact()

        raise NotImplemented('Currently, compact is not supported')

    def exists_datastore(self, datastore_name=None):
        log.debug("Exists datastore %s" % datastore_name)
        rest = RestHelper(self.server._rest())
        return rest.bucket_exists(datastore_name)
        """
        Indicates whether named data store currently exists.
        datastore_name = self._get_datastore_name(datastore_name)
        ## Review
        try:
            self.server[datastore_name]
            return True
        except BucketUnavailableException:
            return False
        """

    def list_objects(self, datastore_name=None):
        """
        List all object types existing in the data store instance.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        view = ds.view(self._get_viewname("association", "by_doc"), include_docs=False, stale="false" )
        row_ids = [row['id'] for row in view]
        log.debug("list objects %s" % datastore_name)
        return row_ids

    def list_object_revisions(self, object_id, datastore_name=None):
        """
        Method for itemizing all the versions of a particular object
        known to the data store.
        """
        raise NotImplemented('Currently, not supported')

    def save_doc(self, doc, object_id=None, datastore_name=None):
        """
        Create or update document
        @param doc  A dict with a document to create or update
        @oaram object_id  The ID for the new document
        """
        ds, datastore_name = self._get_datastore(datastore_name)

        # Assign an id to doc (recommended in CouchDB documentation)
        if "_id" not in doc:
            object_id = object_id or self.get_unique_id()
            doc["_id"] = object_id
        else:
            object_id = doc["_id"]

        try:
            if isinstance(doc, dict):
                doc = json.dumps(doc)
            opaque, cas, msg = ds.set(object_id, 0, 0, doc)
        except MemcachedError as e:
            raise NotFound('Object could not be created. Id: %s - Exception: %s' % (doc_id, e))
        version = cas

        return object_id, version

    def create_doc(self, doc, object_id=None, datastore_name=None):
        """"
        Persist a new raw doc in the data store. An '_id' and initial
        '_rev' value will be added to the doc.
        """
        if object_id and '_id' in doc:
            raise BadRequest("Doc must not have '_id'")
        return self.save_doc(doc, object_id, datastore_name=datastore_name)

    def update_doc(self, doc, datastore_name=None):
        """
        Update an existing raw doc in the data store.  The '_rev' value
        must exist in the doc and must be the most recent known doc
        version. If not, a Conflict exception is thrown.
        """
        if '_id' not in doc:
            raise BadRequest("Doc must have '_id'")
        return self.save_doc(doc, datastore_name=datastore_name)

    def save_doc_mult(self, docs, object_ids=None, datastore_name=None):
        if type(docs) is not list:
            raise BadRequest("Invalid type for docs:%s" % type(docs))
        if object_ids and len(object_ids) != len(docs):
            raise BadRequest("Invalid object_ids")

        if object_ids:
            for doc, oid in zip(docs, object_ids):
                doc["_id"] = oid
        else:
            for doc in docs:
                if "_id" not in doc:
                    doc["_id"] = self.get_unique_id()

        ds, datastore_name = self._get_datastore(datastore_name)
        ##res = ds.update(docs)
        res = [(True, id, cas) for opaque, cas, msg, id in [(ds.set(doc['_id'],0,0,doc) + (doc['_id'],)) for doc in docs]]

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
        if object_ids and len(object_ids) != len(docs):
            raise BadRequest("Invalid object_ids length")

        return self.save_doc_mult(docs, object_ids, datastore_name=datastore_name)

    def read_doc(self, doc_id, rev_id=None, datastore_name=None):
        """"
        Fetch a raw doc instance.  If rev_id is specified, an attempt
        will be made to return that specific doc version.  Otherwise,
        the HEAD version is returned.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        if not rev_id:
            try:
                status, cas, doc = ds.get(doc_id)
            except MemcachedError as e:
                raise NotFound('Object with id %s could not be read. Exception: %s' % (doc_id, e.message))
            if doc is None:
                raise NotFound('Object with id %s does not exist.' % str(doc_id))
            else:
                ## review
                doc = json.loads(doc)
                doc['_id'] = doc_id
        else:
            raise NotImplemented ("Read with rev_id is not supported")
        return doc

    def read_doc_mult(self, object_ids, datastore_name=None):
        ## TODO: review
        return [self.read_doc(id) for id in object_ids]

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
            ds.delete(doc_id)
        except MemcachedError as e:
            raise NotFound('Object with id %s could not be deleted. Exception: %s' % (doc_id, e))

    def delete_doc_mult(self, object_ids, datastore_name=None):
        ds, _ = self._get_datastore(datastore_name)
        # Todo review
        return [ds.delete(id) for id in object_ids]

    # -------------------------------------------------------------------------
    # Couch view operations

    def _get_design_name(self, design):
        return "_design/%s" % design

    def _get_view_name(self, design, name):
        return "_design/%s/_view/%s" % (design, name)

    def compact_views(self, design, datastore_name=None):
        raise NotImplemented ('Compact is not supported')
        #ds, datastore_name = self._get_datastore(datastore_name)
        #return ds.compact(design)

    def define_profile_views(self, profile, datastore_name=None):
        from pyon.datastore.couchdb.views import get_couchdb_view_designs
        ds_views = get_couchdb_view_designs(profile)
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
        except Exception:
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
            #view_name = design_doc["views"].keys()[0]
            #view_name = design_doc.views()[0].name
            for view in design_doc.views():
                ds.view(self._get_view_name(design, view.name))
        except Exception:
            log.exception("Problem with design %s/%s", datastore_name, doc_id)

    def delete_views(self, design, datastore_name=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        try:
            rest = self.server._rest()
            rest.delete_design_doc(bucket=datastore_name, design_doc=design)
        except Exception:
            pass

    def _get_view_args(self, all_args):
        """
        @brief From given all_args dict, extract all entries that are valid CouchDB view options.
        @see http://wiki.apache.org/couchdb/HTTP_view_API
        """
        view_args = dict((k, v) for k, v in all_args.iteritems() if k in ('descending', 'stale', 'skip', 'inclusive_end', 'update_seq'))
        limit = int(all_args.get('limit', 0))
        if limit > 0:
            view_args['limit'] = limit
        return view_args

    def query(self, map):
        ds, datastore_name = self._get_datastore()
        return ds.query(map)

    def find_docs_by_view(self, design_name, view_name, key=None, keys=None, start_key=None, end_key=None,
                          id_only=True, **kwargs):
        """
        @brief Generic find function using an defined index
        @retval Returns a list of triples: (att_id, index_row, Attachment object or none)
        """
        #log.debug("find_docs_by_view(%s/%s)",design_name, view_name)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        ds, datastore_name = self._get_datastore()

        view_args = self._get_view_args(kwargs)
        view_args['include_docs'] = (not id_only)
        view_doc = design_name if design_name == "_all_docs" else self._get_view_name(design_name, view_name)
        #if keys:
        #    view_args['keys'] = keys
        #view = ds.view(view_doc, **view_args)
        if key is not None:
            rows = ds.view(view_doc, key=key,  **view_args)
            #log.info("find_docs_by_view(): key=%s" % key)
        elif keys:
            rows = ds.view(view_doc, keys=keys,  **view_args)
            #log.info("find_docs_by_view(): keys=%s" % keys)
        elif start_key and end_key:
            startkey = start_key or []
            endkey = list(end_key) or []
            endkey.append(END_MARKER)
            #log.info("find_docs_by_view(): start_key=%s to end_key=%s" % (startkey, endkey))
            if view_args.get('descending', False):
                #rows = view[endkey:startkey]
                rows = ds.view(view_doc,  start_key=endkey, end_key=startkey, stale="false", **view_args)
            else:
                #rows = view[startkey:endkey]
                rows = ds.view(view_doc,  start_key=key, end_key=endkey, stale="false", **view_args)
        else:
            #rows = view
            rows = ds.view(view_doc, **view_args)

        if id_only:
            res_rows = [(row['id'], row['key'], row.get('value', None)) for row in rows]
        else:
            res_rows = [(row['id'], row['key'], row['doc']) for row in rows]

        #log.info("find_docs_by_view() found %s objects" % (len(res_rows)))
        return res_rows

    def get_unique_id(self):
        return uuid4().hex