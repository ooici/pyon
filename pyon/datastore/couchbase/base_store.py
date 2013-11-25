#!/usr/bin/env python

"""Standalone use datastore access methods for Couchbase Server"""

__author__ = 'Michael Meisinger, Seman Said'

import simplejson as json
import gevent
from gevent import sleep
import requests

try:
    import couchbase.client
    import couchbase.rest_client
    # Monkey patching
    couchbase.client.json = json
    couchbase.rest_client.json = json

    from couchbase.client import Couchbase, Bucket
    from couchbase.rest_client import RestHelper
    from couchbase.exception import BucketCreationException, BucketUnavailableException
    from couchbase.exception import MemcachedError
except ImportError:
    print "Couchbase driver not available!"

from pyon.datastore.couchdb.couch_common import AbstractCouchDataStore
from pyon.datastore.couchbase.views import get_couch_view_designs
from pyon.core.exception import BadRequest, Conflict, NotFound, ServerError
from pyon.util.containers import get_safe, DictDiffer

from ooi.logging import log


class CouchbaseDataStore(AbstractCouchDataStore):
    """
    Data store implementation utilizing Couchbase to persist documents.
    For API info, see: http://packages.python.org/CouchDB/client.html
    """
    def __init__(self, datastore_name=None, config=None, scope=None, profile=None, **kwargs):
        super(CouchbaseDataStore, self).__init__(datastore_name=datastore_name, config=config, scope=scope, profile=profile)

        if self.config.get("type", None) and self.config['type'] != "couchbase":
            raise BadRequest("Datastore server config is not couchbase: %s" % self.config)
        if self.datastore_name and self.datastore_name != self.datastore_name.lower():
            raise BadRequest("Invalid Couchbase datastore name: '%s'" % self.datastore_name)
        if self.scope and self.scope != self.scope.lower():
            raise BadRequest("Invalid Couchbase scope name: '%s'" % self.scope)

        # Connection
        self.username = self.username or ""
        self.password = self.password or ""
        if self.port == 5984:
            self.port = 8091
        self.api_port = get_safe(self.config, "api_port", "8092")

        connection_str = '%s:%s' % (self.host, self.port)
        log.info("Connecting to Couchbase server: %s (datastore_name=%s)", connection_str, self.datastore_name)
        self.server = Couchbase(connection_str, username=self.username, password=self.password)

        # Just to test existence of the datastore
        if self.datastore_name:
            try:
                ds, dsn = self._get_datastore()
            except NotFound:
                self.create_datastore()
                ds, _ = self._get_datastore()

    def close(self):
        log.debug("Closing connection to Couchbase")
        ##TODO:  is there a way to close the connection?


    # -------------------------------------------------------------------------
    # Couchbase database operations

    def _get_datastore(self, datastore_name=None):
        """
        Returns the couch datastore instance and datastore name.
        This caches the datastore instance to avoid an explicit lookup to save on http request.
        The consequence is that if another process deletes the datastore in the meantime, we will fail later.
        """
        ds_name = self._get_datastore_name(datastore_name)

        if ds_name in self._datastore_cache:
            return self._datastore_cache[ds_name], ds_name

        try:
            if not self.datastore_exists(datastore_name):
                raise NotFound("Datastore '%s' does not exist" % ds_name)

            ds = self.server[ds_name]   # Note: causes http lookup
            self._datastore_cache[ds_name] = ds
            return ds, ds_name
        except ValueError:
            raise BadRequest("Datastore name '%s' invalid" % ds_name)

    def _create_datastore(self, datastore_name):
        if self.datastore_exists(datastore_name):
            raise BadRequest("Datastore with name %s already exists" % datastore_name)
        bucket_password = get_safe(self.config, "bucket_password", "")
        ram_quota_mb = get_safe(self.config, "bucket_ram_quota_small_mb", "50")
        self._create_bucket(name=datastore_name, sasl_password=bucket_password, ram_quota_mb=ram_quota_mb)

    def _create_bucket(self, name, auth_type='sasl', bucket_type='couchbase',
                       parallel_db_and_view_compaction=False,
                       ram_quota_mb="128", replica_index='0', replica_number='0',
                       sasl_password=None, flush_enabled=False, proxy_port=11211):
        """
        If you set authType to "None", then you must specify a proxyPort number.
        If you set authType to "sasl", then you may optionally provide a "saslPassword" parameter.
           For Couchbase Sever 1.6.0, any SASL authentication-based access must go through a proxy at port 11211.
        """
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

        response = requests.post('http://%s:%s/pools/default/buckets' % (self.host, self.port), auth=(self.username, self.password), data=payload)
        if response.status_code != 202:
            log.error('Unable to create bucket %s on %s' % (name, self.host))
            raise BadRequest ('Couchbase error %d: %s' %(response.status_code, response.content))

        gevent.sleep(2)

        # Wait until datastore exists
        # retries = 0
        # ds_exists = self.datastore_exists(name)
        # while not ds_exists and retries < 20:
        #     gevent.sleep(0.1)
        #     ds_exists = self.datastore_exists(name)
        #     retries += 1
        # if not ds_exists:
        #     raise BadRequest("Could not create datastore %s in time" % name)

    def delete_datastore(self, datastore_name=None):
        try:
            super(CouchbaseDataStore, self).delete_datastore(datastore_name)
        except BucketUnavailableException as e:
            raise NotFound('Couchbase unable to delete bucket named %s on %s. Exception: %s ' % (
                datastore_name, e.parameters.get('host', None), e._message))
        # This was added due to Couchbase generating a JSON exception error when trying to delete non-existent bucket.
        except Exception:
            log.exception("Couchbase error")
            raise ServerError('Couchbase returned unknown error')

    def list_datastores(self):
        """
        List all data stores within this data store server. This is
        equivalent to listing all databases hosted on a database server.
        Returns scoped names.
        """
        rest = self.server._rest()
        buckets = rest.get_buckets()
        ds_list = [str(b.name) for b in buckets]
        return ds_list

    def info_datastore(self, datastore_name=None):
        """
        List information about a data store.  Content may vary based
        on data store type.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        # TODO is this correct?
        info = ds.stats
        return info

    def compact_datastore(self, datastore_name=None):
        raise NotImplementedError()

    def datastore_exists(self, datastore_name=None):
        """
        Indicates whether named datastore currently exists.
        """
        datastore_name = self._get_datastore_name(datastore_name)
        rest = RestHelper(self.server._rest())
        return rest.bucket_exists(datastore_name)


    # -------------------------------------------------------------------------
    # Couch document operations

    def list_objects(self, datastore_name=None):
        """
        List all object types existing in the data store instance.
        """
        ds, datastore_name = self._get_datastore(datastore_name)
        view = ds.view(self._get_view_name("association", "by_doc"), include_docs=False, stale="false" )
        row_ids = [row['id'] for row in view]
        return row_ids

    def list_object_revisions(self, object_id, datastore_name=None):
        raise NotImplementedError()


    def _save_doc(self, ds, doc):
        doc_id = doc["_id"]
        try:
            if isinstance(doc, dict):
                doc = json.dumps(doc)
            opaque, cas, msg = ds.set(doc_id, 0, 0, doc)
        except MemcachedError as ex:
            raise NotFound('Object %s could not be created: %s' % (doc_id, ex))
        return doc_id, cas

    def _save_doc_mult(self, ds, docs):
        res = [(True, id, cas) for opaque, cas, msg, id in [(ds.set(doc['_id'],0,0,doc) + (doc['_id'],)) for doc in docs]]
        return res

    # def _save_doc_mult(self, ds, docs):
    #     doc_list = [dict(meta=dict(id=doc["_id"], expiration=0, flags=0), json=doc) for doc in docs]
    #     payload = dict(docs=doc_list)
    #     payload = json.dumps(payload)
    #     api = 'http://%s:%s/%s/_bulk_docs' % (self.host, self.api_port, self.datastore_name)
    #     headers = {'Content-Type': 'application/json', 'Accept': '*/*'}
    #     response = requests.post(api, auth=(self.username, self.password), data=payload, headers=headers)
    #     if response.status_code != 202:
    #         raise BadRequest ('Couchbase error %d: %s' %(response.status_code, response.content))
    #
    #     res = [(True, doc["_id"], "") for doc in docs]
    #     return res

    def create_attachment(self, doc, attachment_name, data, content_type=None, datastore_name=""):
        """
        Assumes that the document already exists and creates attachment to it.
        @param doc can be either id or a document
        """
        if not isinstance(attachment_name, str):
            raise BadRequest("attachment name is not string")
        if not isinstance(data, str) and not isinstance(data, file):
            raise BadRequest("data to create attachment is not a str or file")

        ds, _ = self._get_datastore(datastore_name)
        # If doc is string, assume it is document id
        doc_id = doc if isinstance(doc, str) else doc.get('_id',None)
        if not doc_id:
            raise NotFound("document id is not found in the document for attachment")

        # Update the document to include the attachment id
        try:
            obj = self.read_doc(doc_id=doc_id,datastore_name=datastore_name)
        except:
            raise NotFound("Document could not found for attachment")
            # Make sure the attachment name is not already in the document
        attachment_id = self._get_attachment_id(doc, attachment_name, datastore_name)
        if attachment_id:
            raise BadRequest("Attachment name already in use: %s" % attachment_name)

        attachment_id = self._put_attachment(doc=doc, content=data, filename=attachment_name, content_type=content_type)

        if not obj.get(self.__attachment_string, False):
            obj[self.__attachment_string] = [[attachment_id, attachment_name]]
        else:
            obj[self.__attachment_string] += [[attachment_id, attachment_name]]

        # Update the document
        self.update_doc(obj)
        #TODO: if update fails, rollback and delete the attachment. Otherwise, there will be attachment without a parent document

        self._count(create_attachment=1)
        return attachment_id

    def _put_attachment(self, doc, content, filename, content_type, datastore_name=None):
        # Currently, doc, filename and content type is not used. Keep it for future use
        content_id =  self.get_unique_id()
        ds, _ = self._get_datastore(datastore_name)
        try:
            #content = json.dumps(content)
            ds.add(content_id, 0, 0, content)
        except MemcachedError as e:
            raise NotFound('Attachment could not be created. Id: %s - Exception: %s' % (content_id, e))

        return content_id

    def _update_doc(self, doc, datastore_name=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        try:
            key = str(doc['_id'])
            if isinstance(doc, dict):
                doc = json.dumps(doc)
            opaque, cas, msg = ds.replace(key, 0, 0, doc)
            self._count(update=1)
        except MemcachedError as e:
            raise NotFound('Object with id %s could not be updated. Exception: %s' % (key, e))
        log.debug('Update result: %s', str(key))
        return key, cas

    def update_attachment(self, doc, attachment_name, data, content_type=None, datastore_name=""):
        log.debug("updating attachment %s", attachment_name)
        attachment_id = self._get_attachment_id(doc, attachment_name, datastore_name)
        if not attachment_id:
            # if attachment not found, create it
            self.create_attachment(doc=doc, data=data, attachment_name=attachment_name, content_type=content_type, datastore_name=datastore_name)
        else:
            ds, _ = self._get_datastore(datastore_name)
            try:
                _, _, _ = ds.replace(attachment_id, 0, 0, data)
            except MemcachedError as e:
                raise NotFound('Attachment with with document id %s could not be updated. Exception: %s' % (attachment_id, e))
        log.debug("updated attachment %s", attachment_name)

    def read_doc(self, doc_id, rev_id=None, datastore_name=None, object_type=None):
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
                doc['_rev'] = cas
                doc['_id'] = str(doc['_id']) #doc_id
        else:
            raise NotImplementedError()
        return doc

    def read_doc_mult(self, object_ids, datastore_name=None):
        """"
        Fetch a number of raw doc instances, HEAD rev.
        """
        if not object_ids:
            return []
        ds, datastore_name = self._get_datastore(datastore_name)
        rows = ds.view("_all_docs", keys=object_ids, include_docs=True)

        # Check for docs not found
        notfound_list = ['Object with id %s does not exist.' % str(row.key)
                         for row in rows if row['doc'] is None]
        if notfound_list:
            raise NotFound("\n".join(notfound_list))

        doc_list = [row['doc']['json'] for row in rows]
        self._count(read_mult_call=1, read_mult_obj=len(doc_list))

        return doc_list

    def read_attachment(self, doc, attachment_name, datastore_name=""):
        if not isinstance(attachment_name, str):
            raise BadRequest("Attachment_name param is not str")
        ds, datastore_name = datastore_name or self._get_datastore(datastore_name)

        # Get attachment id from the document
        attachment_id = self._get_attachment_id(doc, attachment_name, datastore_name)
        if not attachment_id:
            raise NotFound ("Document doesn't have attachment")

        log.debug('Fetching attachment %s of document %s/%s', attachment_name, datastore_name, doc)
        attachment = self._get_attachment(attachment_id, attachment_name, datastore_name)

        if attachment is None:
            raise NotFound('Attachment %s does not exist in document %s.%s.', attachment_name, datastore_name, doc)
        else:
            log.debug('Reading attachment content: %s', attachment)

        if not isinstance(attachment, str):
            raise NotFound('Attachment read is not a string')

        log.debug('Read content of attachment: %s of document %s/%s', attachment_name, datastore_name, doc)

        self._count(read_attachment=1)
        return attachment

    def _get_attachment (self, doc_id, attachment_name, datastore_name=""):
        if not doc_id:
            raise BadRequest('Attachment id could not be found')
        ds, _  = self._get_datastore(datastore_name)
        try:
            status, cas, attachment = ds.get(doc_id)
        except MemcachedError as e:
            raise NotFound('Object with id %s could not be read. Exception: %s' % (doc_id, e.message))
        if attachment is None:
            raise NotFound('Object with id %s does not exist.' % str(doc_id))

        return attachment

    def _get_attachment_id (self, doc, attachment_name, datastore_name):
        doc_id = doc if isinstance(doc, str) else doc.get('_id',None)
        if not doc_id:
            raise BadRequest("document id is not found in the document ")
            # Gets attachment id from the document
        try:
            obj = self.read_doc(doc_id, datastore_name=datastore_name)
        except NotFound:
            raise NotFound ('Document could not be found for attachment read')

        if not obj.get(self.__attachment_string, False):
            attachment_id = None
        else:
            # Find the attachment id from the list
            #   "__attachments": [
            #    [
            #        "attachment id"
            #        "attachment name"
            #    ],
            #    [
            #        "attachment id"
            #        "attachment name"
            #    ]
            #  ],
            attachment_id = [attachment_meta_data[0] for attachment_meta_data in obj[self.__attachment_string] if attachment_meta_data[1] == attachment_name]
            attachment_id = attachment_id[0] if attachment_id else None

        return attachment_id

    #Todo: should this have datastore_name??
    def list_attachments(self, doc):
        """
        Returns the a list of attachments for the document, as a dict of dicts, key'ed by name with
        nested keys 'data' for the content and 'content-type'.
        @param doc  accepts either str (meaning an id) or dict (meaning a full document).
        """
        attachment_metadata = self._list_attachment_metadata(doc)
        attachments = None
        if attachment_metadata:
            # Todo: Currently content type is always empty
            attachments =[dict({'data' : self._get_attachment(attachment[0], attachment_name=attachment[1]), 'attachment_name':attachment[1], 'content-type':'' }) for attachment in attachment_metadata]

        return attachments

    def _list_attachment_metadata (self, doc):
        if isinstance(doc, dict):
            obj = self.read_doc(doc_id=doc["_id"])
        elif isinstance(doc, str):
            obj = self.read_doc(doc_id=doc)
        else:
            raise BadRequest("document id is not found in the document ")

        if not obj.get(self.__attachment_string, False):
            attachment_metadata = None
        else:
            attachment_metadata = [attachment_metadata for attachment_metadata in obj[self.__attachment_string]]

        return attachment_metadata

    def delete_doc(self, doc, datastore_name=None, object_type=None, **kwargs):
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

    def delete_doc_mult(self, object_ids, datastore_name=None, object_type=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        for oid in object_ids:
            try:
                ds.delete(oid)
            except Exception:
                log.warn("Could not delete %s" % oid)
        # Todo find other way to do bulk delete

    def delete_attachment(self, doc, attachment_name, datastore_name=""):
        """
        Deletes an attachment from a document.
        """
        if not isinstance(attachment_name, str):
            raise BadRequest("attachment_name is not a string")
        doc_id = doc if isinstance(doc, str) else doc.get('_id', None)

        attachment_id = self._get_attachment_id(doc_id, attachment_name, datastore_name)
        if not attachment_id:
            raise NotFound('Attachment could not be found for a document id: %s' % doc_id)

        ds, datastore_name = self._get_datastore(datastore_name)

        log.debug('Deleting attachment of document %s/%s' %(datastore_name, doc["_id"]))
        self.delete_doc(str(attachment_id))
        self._delete_attachment_meta_data(doc_id, attachment_name, datastore_name)
        log.debug('Deleted attachment: %s', attachment_name)
        self._count(delete_attachment=1)

    def _delete_attachment_meta_data(self, doc_id,attachment_name, datastore_name=""):
        """
        Removes attachment id and name from the document
        Assumes attachment id and name already in the document
        """
        if not type(doc_id) is str:
            raise BadRequest('doc_id must be string')
            # Get the document
        doc = self.read_doc(doc_id, datastore_name=datastore_name)
        # Remove attachment id and name from the document
        attachment_meta_data = [attachment_meta_data for attachment_meta_data in doc[self.__attachment_string] if attachment_meta_data[1] != attachment_name]
        doc[self.__attachment_string] = attachment_meta_data
        self.update_doc(doc, datastore_name=datastore_name)

    # -------------------------------------------------------------------------
    # View operations

    def compact_views(self, design, datastore_name=None):
        raise NotImplementedError()

    def define_profile_views(self, profile=None, datastore_name=None, keepviews=False):
        ds_views = get_couch_view_designs(profile)
        self._define_profile_views(ds_views, datastore_name=datastore_name, keepviews=keepviews)

    def define_viewset(self, design_name, design_doc, datastore_name=None, keepviews=False):
        ds, datastore_name = self._get_datastore(datastore_name)
        doc_name = self._get_design_name(design_name)

        if keepviews and design_name in ds.design_docs():
            return
        rest = self.server._rest()
        try:
            rest.delete_design_doc(bucket=datastore_name, design_doc=design_name)
        except Exception:
            pass
        design_doc_json = json.dumps(dict(views=design_doc))
        rest.create_design_doc(bucket=datastore_name, design_doc=design_name, function=design_doc_json)
        #ds[doc_name] = design_doc_json
        log.debug("Added design %s to datastore %s", doc_name, datastore_name)

    def refresh_views(self, datastore_name="", profile=None):
        """
        Triggers a refresh of all views (all designs) for this datastore's profile
        """
        profile = profile or self.profile
        ds_views = get_couch_view_designs(profile)
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
        view_args = super(CouchbaseDataStore, self)._get_view_args(all_args)
        if "state" not in view_args:
            view_args["stale"] = "false"
        return view_args

    def _get_row_doc(self, row):
        return row['doc']['json']
