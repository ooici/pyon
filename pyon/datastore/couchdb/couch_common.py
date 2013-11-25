#!/usr/bin/env python

"""Common datastore abstract base for both CouchDB/BigCouch and Couchbase"""

__author__ = 'Michael Meisinger'


from uuid import uuid4

from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.util.containers import get_safe, DictDiffer
from pyon.util.stats import StatsCounter

from ooi.logging import log

# Token for a most likely non-inclusive key range upper bound (end_key), for queries such as
# prefix <= keys < upper bound: e.g. ['some','value'] <= keys < ['some','value', END_MARKER]
# or "somestr" <= keys < "somestr"+END_MARKER for string prefix checking
# Note: Use highest ASCII characters here, not 8bit
#END_MARKER = "\x7f\x7f\x7f\x7f"
END_MARKER = "ZZZZZZ"


class AbstractCouchDataStore(object):
    """
    Base class common to both CouchDB and Couchbase datastores.
    """
    _stats = StatsCounter()

    def __init__(self, datastore_name=None, config=None, scope=None, profile=None):
        """
        @param datastore_name  Name of datastore within server. May be scoped to sysname
        @param config  A server config dict with connection params
        @param scope  Prefix for the datastore name (e.g. sysname) to separate multiple systems
        """
        self.config = config
        if not self.config:
            self.config = {}

        # Connection basics
        self.host = self.config.get('host', None) or 'localhost'
        self.port = self.config.get('port', None) or 5984
        self.username = self.config.get('username', None)
        self.password = self.config.get('password', None)

        self.profile = profile
        self.datastore_name = datastore_name

        self._datastore_cache = {}
        self.server = None

        # Datastore (couch database) handling. Scope with given scope (sysname) and make all lowercase
        self.scope = scope
        if self.scope:
            self.datastore_name = ("%s_%s" % (self.scope, datastore_name)).lower() if datastore_name else None
        else:
            self.datastore_name = datastore_name.lower() if datastore_name else None


    # -------------------------------------------------------------------------
    # Couch database operations

    def _get_datastore_name(self, datastore_name=None):
        """
        Computes a name for the datastore to work on. If name is given, uses the lower case
        version of this name. If this instance was initialized with a scope, the name is additionally
        scoped. If no name was given, the instance defaults will be returned.
        """
        if datastore_name and self.scope:
            datastore_name = "%s_%s" % (self.scope, datastore_name)
        elif datastore_name:
            #datastore_name = datastore_name.lower()
            pass
        elif self.datastore_name:
            datastore_name = self.datastore_name
        else:
            raise BadRequest("No datastore name provided")
        return datastore_name


    def create_datastore(self, datastore_name=None, create_indexes=True, profile=None):
        """
        Create a datastore with the given name.  This is
        equivalent to creating a database on a database server.
        @param datastore_name  Datastore to work on. Will be scoped if scope was provided.
        @param create_indexes  If True create indexes according to profile
        @param profile  The profile used to determine indexes
        """
        ds_name = self._get_datastore_name(datastore_name)
        profile = profile or self.profile
        log.info('Creating datastore %s (create_indexes=%s, profile=%s)' % (ds_name, create_indexes, profile))

        self._create_datastore(ds_name)

        if create_indexes and profile:
            log.info('Creating indexes for datastore %s with profile=%s' % (ds_name, profile))
            self.define_profile_views(profile=profile, datastore_name=datastore_name, keepviews=True)

    def _create_datastore(self, datastore_name):
        raise NotImplementedError()

    def delete_datastore(self, datastore_name=None):
        """
        Delete the datastore with the given name.  This is
        equivalent to deleting a database from a database server.
        """
        if datastore_name is None:
            if self.datastore_name:
                datastore_name = self._get_datastore_name(datastore_name)
            else:
                raise BadRequest("Not datastore_name provided")
        elif not datastore_name.startswith(self.scope or ""):
            datastore_name = self._get_datastore_name(datastore_name)
        log.info('Deleting datastore %s' % datastore_name)

        self.server.delete(datastore_name)
        if datastore_name in self._datastore_cache:
            del self._datastore_cache[datastore_name]


    # -------------------------------------------------------------------------
    # Couch document operations

    def save_doc(self, doc, object_id=None, datastore_name=None):
        """
        Create or update document
        @param doc  A dict with a document to create or update
        @oaram object_id  The ID for the new document
        """
        ds, datastore_name = self._get_datastore(datastore_name)

        create = False
        # Assign an id to doc
        if "_id" not in doc:
            create = True
            object_id = object_id or self.get_unique_id()
            doc["_id"] = object_id

        if create:
            log.debug('Create document id=%s', doc['_id'])
        else:
            log.debug('Update document id=%s', doc['_id'])

        return self._save_doc(ds, doc)

    def _save_doc(self, ds, doc):
        raise NotImplementedError()

    def save_doc_mult(self, docs, object_ids=None, datastore_name=None):
        if type(docs) is not list:
            raise BadRequest("Invalid type for docs: %s" % type(docs))
        if not docs:
            return []

        if object_ids:
            for doc, oid in zip(docs, object_ids):
                doc["_id"] = oid
        else:
            for doc in docs:
                doc["_id"] = doc.get("_id", None) or self.get_unique_id()

        ds, datastore_name = self._get_datastore(datastore_name)
        res = self._save_doc_mult(ds, docs)

        self._count(create_mult_call=1, create_mult_obj=len(docs))
        if not all([success for success, oid, rev in res]):
            errors = ["%s:%s" % (oid, rev) for success, oid, rev in res if not success]
            log.error('create_doc_mult had errors. Successful: %s, Errors: %s'
                      % (len(res) - len(errors), "\n".join(errors)))
        else:
            log.debug('create_doc_mult successfully created %s documents', len(res))

        return res

    def _save_doc_mult(self, ds, docs):
        raise NotImplementedError()

    def create_doc(self, doc, object_id=None, attachments=None, datastore_name=None):
        """"
        Persists a document using the optionally provided object_id.
        Optionally creates attachments to the new document.
        Returns a tuple of identifier and revision number of the document
        """
        if object_id and '_id' in doc:
            raise BadRequest("Doc must not have '_id'")
        if '_rev' in doc:
            raise BadRequest("Doc must not have '_rev'")

        # Add the attachments if indicated
        if attachments is not None:
            pass   # Does not work with binary attachments
            # if isinstance(attachments, dict):
            #     doc['_attachments'] = attachments
            # else:
            #     raise BadRequest('Improper attachment given')

        obj_id, version = self.save_doc(doc, object_id, datastore_name=datastore_name)
        self._count(create=1)

        if attachments is not None:
            # Need to iterate through attachments because couchdb_python does not support binary
            # content in db.save()
            for att_name, att_value in attachments.iteritems():
                self.create_attachment(obj_id, att_name, att_value['data'],
                                       content_type=att_value.get('content_type', ''), datastore_name=datastore_name)

        return obj_id, version

    def create_doc_mult(self, docs, object_ids=None, datastore_name=None):
        """
        Create multiple raw docs.
        Returns list of (Success True/False, document_id, rev)
        """
        if type(docs) is not list:
            raise BadRequest("Invalid type for docs:%s" % type(docs))
        if object_ids and len(object_ids) != len(docs):
            raise BadRequest("Invalid object_ids")

        res = self.save_doc_mult(docs, object_ids, datastore_name=datastore_name)
        self._count(create_mult_call=1, create_mult_obj=len(docs))

        return res

    def create_attachment(self, doc, attachment_name, data, content_type=None, datastore_name=""):
        raise NotImplementedError()

    def update_doc(self, doc, datastore_name=None):
        """
        Update an existing raw doc in the datastore.  The '_rev' value
        must exist in the doc and must be the most recent known doc
        version. If not, a Conflict exception is thrown.
        """
        if '_id' not in doc:
            raise BadRequest("Doc must have '_id'")

        return self._update_doc(doc, datastore_name)

    def _update_doc(self, doc, datastore_name=None):
        obj_id, version = self.save_doc(doc, datastore_name=datastore_name)
        self._count(update=1)

        return obj_id, version

    def update_doc_mult(self, docs, datastore_name=None):
        """
        Update multiple raw docs.
        Returns list of (Success True/False, document_id, rev)
        """
        if type(docs) is not list:
            raise BadRequest("Invalid type for docs:%s" % type(docs))
        if not all(["_id" in doc for doc in docs]):
            raise BadRequest("Docs must have '_id'")

        res = self.save_doc_mult(docs, datastore_name=datastore_name)
        self._count(update_mult_call=1, update_mult_obj=len(docs))

        return res

    # -------------------------------------------------------------------------
    # View operations

    def _get_design_name(self, design):
        return "_design/%s" % design

    def _get_view_name(self, design, name):
        return "_design/%s/_view/%s" % (design, name)

    def get_unique_id(self):
        return uuid4().hex

    def _get_endkey(self, startkey):
        if startkey is None or type(startkey) is not list:
            raise BadRequest("Cannot create endkey for type %s" % type(startkey))
        endkey = list(startkey)
        endkey.append(END_MARKER)
        return endkey

    def _define_profile_views(self, ds_views, datastore_name=None, keepviews=False):
        for design_name, design_doc in ds_views.iteritems():
            self.define_viewset(design_name, design_doc, datastore_name=datastore_name, keepviews=keepviews)

    def define_viewset(self, design_name, design_doc, datastore_name=None, keepviews=False):
        raise NotImplementedError()

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

    def find_docs_by_view(self, design_name, view_name, key=None, keys=None, start_key=None, end_key=None,
                          id_only=True, **kwargs):
        """
        Generic find function using a defined index
        @param design_name  design document
        @param view_name  view name
        @param key  specific key to find
        @param keys  list of keys to find
        @param start_key  find range start value
        @param end_key  find range end value
        @param id_only  if True, the 4th element of each triple is the document
        @retval Returns a list of 4-tuples: (document id, index key, index value, document)
        """
        #log.debug("find_docs_by_view(%s/%s)",design_name, view_name)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        ds, datastore_name = self._get_datastore()

        view_args = self._get_view_args(kwargs)
        view_args['include_docs'] = (not id_only)
        view_doc = design_name if design_name == "_all_docs" else self._get_view_name(design_name, view_name)
        if key is not None:
            rows = ds.view(view_doc, key=key, **view_args)
        elif keys:
            rows = ds.view(view_doc, keys=keys, **view_args)
        elif start_key and end_key:
            startkey = start_key or []
            if end_key is None:
                end_key = []
            elif not isinstance(end_key, list):
                end_key = list(end_key)
            endkey = self._get_endkey(end_key)
            if view_args.get('descending', False):
                rows = ds.view(view_doc, start_key=endkey, end_key=startkey, **view_args)
            else:
                rows = ds.view(view_doc, start_key=startkey, end_key=endkey, **view_args)
        else:
            rows = ds.view(view_doc, **view_args)

        if id_only:
            res_rows = [(row['id'], row['key'], row.get('value', None)) for row in rows]
        else:
            res_rows = [(row['id'], row['key'], self._get_row_doc(row)) for row in rows]

        self._count(find_by_view_call=1, find_by_view_obj=len(res_rows))

        return res_rows

    def query_view(self, view_name='', opts=None, datastore_name=''):
        """
        query_view is a straight through method for querying a view in CouchDB. query_view provides us the interface
        to the view structure in couch, in lieu of implementing a method for every type of query we could want, we
        now have the capability for clients to make queries to couch in a straight-through manner.
        """
        if opts is None:
            opts = {}
        ds, datastore_name = self._get_datastore(datastore_name)

        # Actually obtain the results and place them in rows
        rows = ds.view(view_name, **opts)

        # Parse the results and convert the results into ionobjects and python types.
        result = self._parse_results(rows)

        return result

    def custom_query(self, map_fun, reduce_fun=None, datastore_name='', **options):
        """
        custom_query sets up a temporary view in couchdb, the map_fun is a string consisting
        of the javascript map function

        Warning: Please note that temporary views are not suitable for use in production,
        as they are really slow for any database with more than a few dozen documents.
        You can use a temporary view to experiment with view functions, but switch to a
        permanent view before using them in an application.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        res = ds.query(map_fun, reduce_fun, **options)

        return self._parse_results(res)

    def _parse_results(self, doc):
        raise NotImplementedError()

    def _get_row_doc(self, row):
        return row['doc']

    def _count(self, datastore=None, **kwargs):
        datastore = datastore or self.datastore_name
        self._stats.count(namespace=datastore, **kwargs)
