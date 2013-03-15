#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from uuid import uuid4

import hashlib

from couchbase.client import Couchbase, Bucket
from couchbase.rest_client import RestHelper
from couchbase.exception import BucketCreationException, BucketUnavailableException, MemcachedTimeoutException
import requests
from pyon.datastore.couchdb.views import get_couchdb_views

from couchdb.client import ViewResults, Row
from couchdb.http import PreconditionFailed, ResourceConflict, ResourceNotFound

from pyon.core.bootstrap import get_obj_registry, CFG
from pyon.core.exception import BadRequest, Conflict, NotFound, ServerError
from pyon.core.object import IonObjectBase, IonObjectSerializer, IonObjectDeserializer
from pyon.datastore.datastore import DataStore
from pyon.ion.identifier import create_unique_association_id
from pyon.ion.resource import CommonResourceLifeCycleSM
from pyon.util.log import log
from pyon.util.arg_check import validate_is_instance
from pyon.util.containers import get_ion_ts
from pyon.util.stats import StatsCounter
import simplejson as json
from couchbase.exception import MemcachedError
from requests.exceptions import ConnectionError
from gevent import sleep

import inspect


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


class CouchDataStore(DataStore):
    """
    Data store implementation utilizing CouchDB to persist documents.
    For API info, see: http://packages.python.org/CouchDB/client.html
    """
    _stats = StatsCounter()
    def __init__(self, host=None, port=None, datastore_name='default', options="", profile=DataStore.DS_PROFILE.BASIC):
        log.debug('__init__(host=%s, port=%s, datastore_name=%s, options=%s)', host, port, datastore_name, options)
        self.host = host or CFG.server.couchbase.host
        self.port = port or CFG.server.couchbase.port
        self.datastore_name = datastore_name
        self.__attachment_string = '__attachments'  # Attachment string name that will be used in Couchbase
        try:
            if CFG.server.couchbase.username and CFG.server.couchbase.password:
                log.debug("Using username:password authentication to connect to datastore")
        except AttributeError:
            log.error("Couchbase username:password not configured correctly ")
            raise BadRequest ("Couchbase username:password not configured correctly ")
        except ConnectionError:
            log.error("Couchbase error: could not be connected to Couchbase.")
            raise BadRequest ("Couchbase error: could not be connected to Couchbase.")

        self.username = CFG.server.couchbase.username
        self.password = CFG.server.couchbase.password
        connection_str = '%s:%s' %(self.host, self.port)
        log.info('Connecting to Couchbase server: username:%s password:%s  "http://%s:%s"  ' % (self.username, self.password, self.host, self.port))

        self.server = Couchbase(connection_str, username=self.username, password=self.password)
        self.profile = profile


        # serializers
        self._io_serializer = IonObjectSerializer()
        # TODO: Not nice to have this class depend on ION objects
        self._io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
        self._datastore_cache = {}

    def close(self):
        log.debug("Closing connection to Couchbase")
        ##TODO:  is there a way to close connection
        '''
        ds, _ = self._get_datastore()
        del ds
        del self.server
        '''

    def _get_datastore(self, datastore_name=None):
        datastore_name = datastore_name or self.datastore_name

        if datastore_name in self._datastore_cache:
            return (self._datastore_cache[datastore_name], datastore_name)

        try:
            ds = self.server[datastore_name]
            self._datastore_cache[datastore_name] = ds
            return ds, datastore_name
        except ResourceNotFound:
            raise BadRequest("Datastore '%s' does not exist" % datastore_name)
        except ValueError:
            raise BadRequest("Datastore name '%s' invalid" % datastore_name)

    def create_datastore(self, datastore_name="", create_indexes=True, profile=None):
        datastore_name = datastore_name or self.datastore_name
        profile = profile or self.profile
        bucket_password = CFG.server.couchbase.bucket_password,
        ram_quota_mb =   CFG.server.couchbase.bucket_ram_quota_samll_mb
        log.info('Creating data store %s with profile=%s' % (datastore_name, profile))
        if self.datastore_exists(datastore_name):
            raise BadRequest("Data store with name %s already exists" % datastore_name)
        self._create_bucket(name=datastore_name, sasl_password=bucket_password, ram_quota_mb=ram_quota_mb)
        if create_indexes:
            self._define_views(datastore_name, profile)

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
            # 400 means the document is already created
            log.error('Unable to create bucket %s on %')
            raise BadRequest ('Couchbase returned error - status code:%d bucket name:%s - error_string from Couchbase: %s' %(response.status_code, name, response.content))
        sleep(3)


    def delete_datastore(self, datastore_name=''):
        datastore_name = datastore_name or self.datastore_name
        log.info('Deleting data store %s' % datastore_name)
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
        dbs = [db.name for db in self.server]
        log.debug('Data stores: %s', str(dbs[0]))
        return dbs

    def info_datastore(self, datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        log.debug('Listing information about data store %s', datastore_name)
        ## Review
        ## TODO ds.stats??
        info = ds.stats
        log.debug('\n\n\nData store info: %s\n\n\n', str(info))
        return info

    def datastore_exists(self, datastore_name=""):
        ## TODO Review
        rest = RestHelper(self.server._rest())
        return rest.bucket_exists(datastore_name)
        '''
        for db in self.server:
            if db == datastore_name:
                return True
        return False
        '''

    def _list_objects (self, ds, filter=None):
        view = ds.view(self._get_viewname("association", "by_doc"), include_docs=False, stale="false" )
        row_ids = [row['id'] for row in view]
        return row_ids

    ## Todo review
    ## Right now it only returns ids
    def list_objects(self, datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        log.warning('Listing all objects in data store %s' % datastore_name)
        #objs = [obj for obj in ds]
        objs = self._list_objects(ds)
        log.debug('Objects: %s', str(objs))
        return objs

    def list_object_revisions(self, object_id, datastore_name=""):
        raise NotImplemented ("List object revisions is not implemented")


    def create(self, obj, object_id=None, attachments=None, datastore_name=""):
        """
        Converts ion objects to python dictionary before persisting them using the optional
        suggested identifier and creates attachments to the object.
        Returns an identifier and revision number of the object
        """
        if not isinstance(obj, IonObjectBase):
            raise BadRequest("Obj param is not instance of IonObjectBase: The type is:" + str(type(obj)))

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
        ##doc["_id"] = object_id or self.get_unique_id()
        doc_id =  object_id or self.get_unique_id()
        log.debug('Creating new object %s/%s' % (datastore_name, doc_id))
        log.debug('create doc contents: %s', doc)

        try:
            ###
            doc['_id'] = doc_id
            if isinstance(doc, dict):
                doc = json.dumps(doc)
                #TODO should this be add or set?
            ###opaque, cas, msg = ds.add(doc_id, 0, 0, doc)
            opaque, cas, msg = ds.set(doc_id, 0, 0, doc)
            self._count(create=1)
        except MemcachedError as e:
            raise NotFound('Object could not be created. Id: %s - Datastore: %s - Exception: %s' % (doc_id, datastore_name, e))
        except MemcachedTimeoutException as e:
            raise NotFound('create_doc: Couchbase server timeout:\nId: %s - Datastore: %s - \nException: %s \ndoc: %s' % (doc_id, datastore_name, e, doc))

        # Add the attachments if indicated
        if attachments is not None:
            for att_name, att_value in attachments.iteritems():
                self.create_attachment(doc_id, att_name, att_value['data'], content_type=att_value.get('content_type', ''), datastore_name=datastore_name)
        log.debug('Create result: %s', str(doc_id))
        obj_id, version = doc_id, cas

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
            #object_ids = [doc.get("_id", None) or self.get_unique_id() for doc in docs]
            for doc in docs:
                doc["_id"] = doc.get("_id", None) or self.get_unique_id()
        '''
        ### TODO
        if not object_ids:
            object_ids = []
            for doc in docs:
                doc_id = doc.get("_id", None)
                if not doc_id:
                    doc_id = self.get_unique_id()
                else:
                    del doc['_id']
                object_ids.append(doc_id)
        '''


        ds, _ = self._get_datastore()
        #res = db.update(docs)
        ## Todo. Find other way to do bulk insert
        ##             opaque, cas, msg = ds.add(doc_id, 0, 0, doc)
        ###res = [(True, id, cas) for opaque, cas, msg, id in [(ds.set(oid,0,0,doc) + (oid,)) for doc, oid in zip(docs, object_ids)]]
        res = [(True, id, cas) for opaque, cas, msg, id in [(ds.set(doc['_id'],0,0,doc) + (doc['_id'],)) for doc in docs]]

        self._count(create_mult_call=1, create_mult_obj=len(docs))
        if not all([success for success, oid, rev in res]):
            errors = ["%s:%s" % (oid, rev) for success, oid, rev in res if not success]
            log.error('create_doc_mult had errors. Successful: %s, Errors: %s'
                      % (len(res) - len(errors), "\n".join(errors)))
        else:
            log.debug('create_doc_mult result: %s', str(res))

        return res


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

    def read(self, object_id, rev_id="", datastore_name=""):
        if not isinstance(object_id, str):
            raise BadRequest("Object id param is not string. It is %s" % type(object_id) )
        if rev_id:
            raise BadRequest("Couchbase doesn't support revision based read")
        doc = self.read_doc(object_id, rev_id, datastore_name)

        # Convert doc into Ion object
        obj = self._persistence_dict_to_ion_object(doc)
        log.debug('Ion object: %s', str(obj))

        return obj

    def read_doc(self, doc_id, rev_id="", datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        if not rev_id:
            log.debug('Reading head version of object %s/%s', datastore_name, doc_id)
            try:
                status, cas, doc = ds.get(doc_id)
            except MemcachedError as e:
                raise NotFound('Object can not be read. ID: %s - Datastore Name: %s. Exception: %s' % (doc_id, datastore_name, e.message))
            if doc is None:
                raise NotFound('Object with id %s does not exist.' % str(doc_id))
            else:
                ## review
                doc = json.loads(doc)
                doc['_rev'] = cas
                doc['_id'] = str(doc['_id']) #doc_id
        else:
            raise NotImplemented ("Read with rev_id is not supported")
        log.debug('read doc contents: %s', doc)
        self._count(read=1)
        return doc

    def read_mult(self, object_ids, datastore_name=""):
        if any([not isinstance(object_id, str) for object_id in object_ids]):
            raise BadRequest("Object ids are not string: %s" % str(object_ids))
            #docs = self.read_doc_mult(object_ids, datastore_name)
        # Convert docs into Ion objects
        return self.read_doc_mult(object_ids, datastore_name=datastore_name)

    def read_doc_mult(self, object_ids, datastore_name=""):
        ## TODO: find other way to do bulk read
        if not object_ids:
            return []
        data, not_found_list = self._read_doc_mult(object_ids,datastore_name)
        if not_found_list:
            raise NotFound("\n".join(not_found_list))

        return data

    def _read_doc_mult(self, object_ids, datastore_name=""):
        datastore_name = datastore_name or self.datastore_name
        data = json.dumps({"keys": object_ids})
        #todo remove port number
        response = requests.post('http://%s:%s/%s/_all_docs?include_docs=true&stale=false' %(self.host, '8092', datastore_name), auth=(self.username, self.password), data=data)
        obj = []
        notfound_list = []
        if response.status_code == 404:
            uri = 'http://%s:%s/%s/_all_docs?include_docs=true' % (self.host, self.port, datastore_name)
            data = str(data)
            print ("Couchbase server returned an error. \n Returned code: %d \n Returned content:%s \n URI: %s \n Data:%s " %(response.status_code, response.content, uri, data))
            log.error("Couchbase server returned an error. \n Returned code: %d \n Returned content:%s \n URI: %s \n Data:%s " %(response.status_code, response.content, uri, data))
            notfound_list.append('Object id does not exist.')
        elif response.status_code == 200:
            rows = json.loads(response.content)
            for row in rows['rows']:
                if 'doc' in row and 'json' in row['doc']:
                    obj.append(self._persistence_dict_to_ion_object(row['doc']['json']))
                elif 'error' in row:
                    obj.append(None)
                    notfound_list.append('Object with id %s does not exist.' % row['key'])
        else:
            uri = 'http://%s:%s/%s/_all_docs?include_docs=true' % (self.host, self.port, datastore_name)
            data = str(data)
            raise ServerError("Couchbase server returned an error. \n Returned code: %d \n Returned content:%s \n URI: %s \n Data:%s " %(response.status_code, response.content, uri, data))

        return obj, notfound_list


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

    def update(self, obj, datastore_name=""):
        if not isinstance(obj, IonObjectBase):
            raise BadRequest("Obj param is not instance of IonObjectBase. The type is: " + str(type(obj)))
        return self.update_doc(self._ion_object_to_persistence_dict(obj))

    def update_doc(self, doc, datastore_name=""):
        ds, datastore_name = self._get_datastore(datastore_name)
        if '_id' not in doc:
            raise BadRequest("Doc must have '_id'")
            ## Review
        #if '_rev' not in doc:
        #    raise BadRequest("Doc must have '_rev'")

        log.debug('update doc contents: %s', doc)
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

    def delete(self, obj, datastore_name="", del_associations=False):
        if not isinstance(obj, IonObjectBase) and not isinstance(obj, str):
            raise BadRequest("Obj param is not instance of IonObjectBase or string id")
        if type(obj) is str:
            self.delete_doc(obj, datastore_name=datastore_name, del_associations=del_associations)
        else:
            if '_id' not in obj:
                raise BadRequest("Doc must have '_id'")
                #if '_rev' not in obj:
            #    raise BadRequest("Doc must have '_rev'")
            self.delete_doc(self._ion_object_to_persistence_dict(obj), datastore_name=datastore_name, del_associations=del_associations)

    def delete_doc(self, doc, datastore_name="", del_associations=False):
        ds, datastore_name = self._get_datastore(datastore_name)
        doc_id = doc if type(doc) is str else doc["_id"]
        log.debug('Deleting object %s/%s', datastore_name, doc_id)

        if del_associations:
            assoc_ids = self.find_associations(anyside=doc_id, id_only=True)
            self.delete_doc_mult(assoc_ids)
        #            for aid in assoc_ids:
        #                self.delete(aid, datastore_name=datastore_name)
        #            log.info("Deleted %n associations for object %s", len(assoc_ids), doc_id)

        elif self._is_in_association(doc_id, datastore_name):
            bad_doc = self.read(doc_id)
            if doc:
                log.warn("XXXXXXX Attempt to delete %s object %s that still has associations" % (bad_doc.type_, doc_id))
            else:
                log.warn("XXXXXXX Attempt to delete object %s that still has associations" % doc_id)
                #           raise BadRequest("Object cannot be deleted until associations are broken")

        try:
            ds.delete(doc_id)
            self._count(delete=1)
        except MemcachedError as e:
            raise NotFound('Object with id %s could not be deleted. Exception: %s' % (doc_id, e))

    def delete_mult(self, object_ids, datastore_name=None):
        return self.delete_doc_mult(object_ids, datastore_name)

    def delete_doc_mult(self, object_ids, datastore_name=None):
        ds, datastore_name = self._get_datastore(datastore_name)
        # Todo find other way to do bulk delete
        return [ds.delete(id) for id in object_ids]

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


    def create_association(self, subject=None, predicate=None, obj=None, assoc_type=None):
        """
        Create an association between two IonObjects with a given predicate
        """
        #if assoc_type:
        #if assoc_type:
        #    raise BadRequest("assoc_type deprecated")
        if not (subject and predicate and obj):
            raise BadRequest("Association must have all elements set")
        if type(subject) is str:
            subject_id = subject
            subject = self.read(subject_id)
            subject_type = subject._get_type()
        else:
            #if "_id" not in subject or "_rev" not in subject:
            if "_id" not in subject:
                raise BadRequest("Subject id or rev not available")
            subject_id = subject._id
            subject_type = subject._get_type()

        if type(obj) is unicode:
            obj = str(obj)
        if type(obj) is str:
            object_id = obj
            obj = self.read(object_id)
            object_type = obj._get_type()
        else:
            #if "_id" not in obj or "_rev" not in obj:
            if "_id" not in obj:
                raise BadRequest("Object id or rev not available")
            object_id = obj._id
            object_type = obj._get_type()

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
        assoc_list = self.find_associations(subject, predicate, obj, id_only=False)
        if len(assoc_list) != 0:
            assoc = assoc_list[0]
            raise BadRequest("Association between %s and %s with predicate %s already exists" % (subject, obj, predicate))

        assoc = IonObject("Association",
                          s=subject_id, st=subject_type,
                          p=predicate,
                          o=object_id, ot=object_type,
                          ts=get_ion_ts())
        self._count(_create_assoc=1)
        return self.create(assoc, create_unique_association_id())

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
            self._count(_delete_assoc=1)
            return success
        else:
            self._count(_delete_assoc=1)
            return self.delete(association)

    def _get_viewname(self, design, name):
        return "_design/%s/_view/%s" % (design, name)

    def _define_views(self, datastore_name=None, profile=None, keepviews=False):
        datastore_name = datastore_name or self.datastore_name
        profile = profile or self.profile
        log.debug('Define views datastore: %s profile: %s' %(datastore_name,profile))

        ds_views = get_couchdb_views(profile)
        for design, viewdef in ds_views.iteritems():
            self._define_view(design, viewdef, datastore_name=datastore_name, keepviews=keepviews)

    def _get_view_names(self,design_name,  datastore_name=None) :
        ds, datastore_name = self._get_datastore(datastore_name)
        design_path = "_design/%s" % design_name
        design_doc = ds[design_path]
        return [view.name for view in design_doc.views()]


    def _define_view(self, design, viewdef, datastore_name=None, keepviews=False):
        ds, datastore_name = self._get_datastore(datastore_name)
        viewname = "_design/%s" % design

        if keepviews and viewname in ds.design_docs():
        #if keepviews and viewname in self._get_view_names(design, datastore_name):
            return
        try:
            ##TODO review this
            ### del ds[viewname]
            rest = self.server._rest()
            rest.delete_design_doc(bucket=datastore_name, design_doc=design)
        except:
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
                    log.debug("View %s/_design/%s/_view/%s: %s rows", datastore_name, design, viewname, len(rows))
                except Exception, ex:
                    log.exception("Problem with view %s/_design/%s/_view/%s", datastore_name, design, viewname)

    _refresh_views = _update_views

    def _delete_views(self, datastore_name="", profile=None):
        ds, datastore_name = self._get_datastore(datastore_name)

        profile = profile or self.profile
        ds_views = get_couchdb_views(profile)

        for design, viewdef in ds_views.iteritems():
            try:
                #TODO: review
                ###del ds["_design/%s" % design]
                rest = self.server._rest()
                rest.delete_design_doc(bucket=datastore_name, design_doc=design)
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
        log.debug("_is_in_association(%s)", obj_id)
        if not obj_id:
            raise BadRequest("Must provide object id")

        assoc_ids = self.find_associations(anyside=obj_id, id_only=True, limit=1)
        if assoc_ids:
            log.debug("Object found as object in associations: %s", assoc_ids)
            return True

        return False



    def find_objects_mult(self, subjects, id_only=False):
        """
        Returns a list of associations for a given list of subjects
        """
        ds, datastore_name = self._get_datastore()
        validate_is_instance(subjects, list, 'subjects is not a list of resource_ids')
        view_args = dict(keys=subjects, include_docs=True)
        results = self.query_view(self._get_viewname("association", "by_bulk"), view_args)
        ids = [i['value'] for i in results]
        assocs = [i['doc'] for i in results]
        self._count(find_assocs_mult_call=1, find_assocs_mult_obj=len(ids))
        if id_only:
            return ids, assocs
        else:
            return self.read_mult(ids), assocs

    def find_subjects_mult(self, objects, id_only=False):
        """
        Returns a list of associations for a given list of objects
        """
        ds, datastore_name = self._get_datastore()
        validate_is_instance(objects, list, 'objects is not a list of resource_ids')
        view_args = dict(keys=objects, include_docs=True)
        results = self.query_view(self._get_viewname("association", "by_subject_bulk"), view_args)
        ids = [i['value'] for i in results]
        assocs = [i['doc'] for i in results]
        self._count(find_assocs_mult_call=1, find_assocs_mult_obj=len(ids))
        if id_only:
            return ids, assocs
        else:
            return self.read_mult(ids), assocs


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

        view_args = self._get_view_args(kwargs)
        #view = ds.view(self._get_viewname("association", "by_sub"), **view_args)
        key = [subject_id]
        if predicate:
            key.append(predicate)
            if object_type:
                key.append(object_type)
        endkey = self._get_endkey(key)
        #rows = view[key:endkey]
        rows = ds.view(self._get_viewname("association", "by_sub"), start_key=key, end_key=endkey, stale="false", **view_args)

        '''
        import pprint
        print "\n\n view objects: ", self._get_viewname("association", "by_sub"), " key:", key, " endkey", endkey
        print pprint.pformat(rows)
        print "\n\n"
        '''

        obj_assocs = [self._persistence_dict_to_ion_object((row['value'])) for row in rows]
        obj_ids = [str(assoc.o) for assoc in obj_assocs]                                       ## Review added str()
        self._count(find_objects_call=1, find_objects_obj=len(obj_assocs))

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

        view_args = self._get_view_args(kwargs)
        key = [object_id]
        if predicate:
            key.append(predicate)
            if subject_type:
                key.append(subject_type)
        endkey = self._get_endkey(key)
        #rows = view[key:endkey]
        rows = ds.view(self._get_viewname("association", "by_obj"), start_key=key, end_key=endkey, stale="false", **view_args)

        sub_assocs = [self._persistence_dict_to_ion_object(row['value']) for row in rows]
        sub_ids = [str(assoc.s) for assoc in sub_assocs]                                    ## Review str()
        self._count(find_subjects_call=1, find_subjects_obj=len(sub_assocs))

        log.debug("find_subjects() found %s subjects", len(sub_ids))
        if id_only:
            return (sub_ids, sub_assocs)

        sub_list = self.read_mult(sub_ids)
        return (sub_list, sub_assocs)

    def find_associations(self, subject=None, predicate=None, obj=None, assoc_type=None, id_only=True, anyside=None, **kwargs):
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

        if subject and obj:
            key = [subject_id, object_id]
            if predicate:
                key.append(predicate)
            endkey = self._get_endkey(key)
            rows = ds.view(self._get_viewname("association", "by_match"), start_key=key, end_key=endkey, stale="false", **view_args)
        elif subject:
            key = [subject_id]
            if predicate:
                key.append(predicate)
            endkey = self._get_endkey(key)
            rows = ds.view(self._get_viewname("association", "by_sub"), start_key=key, end_key=endkey, stale="false", **view_args)
        elif obj:
            key = [object_id]
            if predicate:
                key.append(predicate)
            endkey = self._get_endkey(key)
            rows = ds.view(self._get_viewname("association", "by_obj"), start_key=key, end_key=endkey, stale="false", **view_args)
        elif anyside:
            if predicate:
                key = [anyside, predicate]
                endkey = self._get_endkey(key)
                rows = ds.view(self._get_viewname("association", "by_idpred"), start_key=key, end_key=endkey, stale="false", **view_args)
            elif type(anyside_ids[0]) is str:
                anyside_ids = json.dumps(anyside_ids)
                rows = ds.view(self._get_viewname("association", "by_id"), keys=anyside_ids, **view_args)
            else:
                ## Review json dumps
                anyside_ids = json.dumps(anyside_ids)
                rows = ds.view(self._get_viewname("association", "by_idpred"), keys=anyside_ids, **view_args)
        elif predicate:
            key = [predicate]
            endkey = self._get_endkey(key)
            rows = ds.view(self._get_viewname("association", "by_pred"), start_key=key, end_key=endkey, stale="false", **view_args)
        else:
            raise BadRequest("Illegal arguments")

        if id_only:
            assocs = [row['id'] for row in rows]
        else:
            assocs = [self._persistence_dict_to_ion_object(row['value']) for row in rows]
        log.debug("find_associations() found %s associations", len(assocs))
        self._count(find_assocs_call=1, find_assocs_obj=len(assocs))
        return assocs

    def _prepare_find_return(self, rows, res_assocs=None, id_only=True, **kwargs):
        if id_only:
            res_ids = [row['id'] for row in rows]
            return res_ids, res_assocs
        else:
            res_docs = [self._persistence_dict_to_ion_object(row['doc']['json']) for row in rows]
            return res_docs, res_assocs


    def find_resources(self, restype="", lcstate="", name="", id_only=True):
        return self.find_resources_ext(restype=restype, lcstate=lcstate, name=name, id_only=id_only)
        '''
        res1,res2 = self.find_resources_ext(restype=restype, lcstate=lcstate, name=name, id_only=id_only)
        import pprint
        print "\n\n find_resources", restype, lcstate, name, id_only
        if id_only:
            pprint.pprint(res1)
        else:
            pprint.pprint([obj.__dict__ for obj in res1])
        pprint.pprint(res2)
        return res1,res2
        '''


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

    def find_res_by_type(self, restype, lcstate=None, id_only=False, filter=None):
        log.debug("find_res_by_type(restype=%s, lcstate=%s)", restype, lcstate)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if lcstate:
            raise BadRequest('lcstate not supported anymore in find_res_by_type')

        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        ##view = ds.view(self._get_viewname("resource", "by_type"), include_docs=(not id_only), **filter)
        if restype:
            key = [restype]
            endkey = self._get_endkey(key)
            ##rows = view[key:endkey]
            rows = ds.view(self._get_viewname("resource", "by_type"), include_docs=(not id_only), start_key=key, end_key=endkey, stale="false", **filter)
        else:
            # Returns ALL documents, only limited by filter
            ##rows = view
            rows = ds.view(self._get_viewname("resource", "by_type"), include_docs=(not id_only), **filter)

        #res_assocs = [dict(type=row['key'][0], lcstate=row['key'][1], name=row['key'][2], id=row['id']) for row in rows]
        res_assocs = [dict(type=row['key'][0], name=row['key'][1], id=row['id']) for row in rows]
        log.debug("find_res_by_type() found %s objects", len(res_assocs))
        self._count(find_res_by_type_call=1, find_res_by_type_obj=len(res_assocs))
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
        ##view = ds.view(self._get_viewname("resource", "by_lcstate"), include_docs=(not id_only), **filter)
        key = [1, lcstate] if lcstate in CommonResourceLifeCycleSM.AVAILABILITY else [0, lcstate]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        ##rows = view[key:endkey]
        rows = ds.view(self._get_viewname("resource", "by_lcstate"), include_docs=(not id_only),  start_key=key, end_key=endkey, stale="false", **filter)

        res_assocs = [dict(lcstate=row['key'][1], type=row['key'][2], name=row['key'][3], id=row['id']) for row in rows]

        log.debug("find_res_by_lcstate() found %s objects", len(res_assocs))
        self._count(find_res_by_lcstate_call=1, find_res_by_lcstate_obj=len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_name(self, name, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_name(name=%s, restype=%s)", name, restype)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        ##view = ds.view(self._get_viewname("resource", "by_name"), include_docs=(not id_only), **filter)
        key = [name]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        #rows = view[key:endkey]
        rows = ds.view(self._get_viewname("resource", "by_name"), include_docs=(not id_only), start_key=key, end_key=endkey, stale="false", **filter)

        #res_assocs = [dict(name=row['key'][0], type=row['key'][1], lcstate=row['key'][2], id=row['id']) for row in rows]
        res_assocs = [dict(name=row['key'][0], type=row['key'][1], id=row['id']) for row in rows]
        log.debug("find_res_by_name() found %s objects", len(res_assocs))
        self._count(find_res_by_name_call=1, find_res_by_name_obj=len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_keyword(self, keyword, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_keyword(keyword=%s, restype=%s)", keyword, restype)
        if not keyword or type(keyword) is not str:
            raise BadRequest('Argument keyword illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        ##view = ds.view(self._get_viewname("resource", "by_keyword"), include_docs=(not id_only), **filter)
        key = [keyword]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        ##rows = view[key:endkey]
        rows = ds.view(self._get_viewname("resource", "by_keyword"), include_docs=(not id_only), start_key=key, end_key=endkey, stale="false", **filter)

        res_assocs = [dict(keyword=row['key'][0], type=row['key'][1], id=row['id']) for row in rows]
        log.debug("find_res_by_keyword() found %s objects", len(res_assocs))
        self._count(find_res_by_kw_call=1, find_res_by_kw_obj=len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_nested_type(self, nested_type, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_nested_type(nested_type=%s, restype=%s)", nested_type, restype)
        if not nested_type or type(nested_type) is not str:
            raise BadRequest('Argument nested_type illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        ##view = ds.view(self._get_viewname("resource", "by_nestedtype"), include_docs=(not id_only), **filter)
        key = [nested_type]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        #rows = view[key:endkey]
        rows = ds.view(self._get_viewname("resource", "by_nestedtype"), include_docs=(not id_only), start_key=key, end_key=endkey, stale="false", **filter)

        res_assocs = [dict(nested_type=row['key'][0], type=row['key'][1], id=row['id']) for row in rows]
        log.debug("find_res_by_nested_type() found %s objects", len(res_assocs))
        self._count(find_res_by_nested_call=1, find_res_by_nested_obj=len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_attribute(self, restype, attr_name, attr_value=None, id_only=False, filter=None):
        log.debug("find_res_by_attribute(restype=%s, attr_name=%s, attr_value=%s)", restype, attr_name, attr_value)
        if not attr_name or type(attr_name) is not str:
            raise BadRequest('Argument attr_name illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        ##view = ds.view(self._get_viewname("resource", "by_attribute"), include_docs=(not id_only), **filter)
        key = [restype, attr_name]
        if attr_value:
            key.append(attr_value)
        endkey = self._get_endkey(key)
        ##rows = view[key:endkey]
        rows = ds.view(self._get_viewname("resource", "by_attribute"), include_docs=(not id_only), start_key=key, end_key=endkey, stale="false", **filter)

        res_assocs = [dict(type=row['key'][0], attr_name=row['key'][1], attr_value=row['key'][2], id=row['id']) for row in rows]
        log.debug("find_res_by_attribute() found %s objects", len(res_assocs))
        self._count(find_res_by_attribute_call=1, find_res_by_attribute_obj=len(res_assocs))
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
        ##view = ds.view(self._get_viewname("resource", "by_altid"), include_docs=(not id_only), **filter)
        key = []
        if alt_id:
            key.append(alt_id)
            if alt_id_ns is not None:
                key.append(alt_id_ns)

        endkey = self._get_endkey(key)
        ##rows = view[key:endkey]
        rows = ds.view(self._get_viewname("resource", "by_altid"), include_docs=(not id_only), start_key=key, end_key=endkey, stale="false", **filter)

        if alt_id_ns and not alt_id:
            res_assocs = [dict(alt_id=row['key'][0], alt_id_ns=row['key'][1], id=row['id']) for row in rows if row['key'][1] == alt_id_ns]
        else:
            res_assocs = [dict(alt_id=row['key'][0], alt_id_ns=row['key'][1], id=row['id']) for row in rows]
        log.debug("find_res_by_alternative_id() found %s objects", len(res_assocs))
        self._count(find_res_by_altid_call=1, find_res_by_altid_obj=len(res_assocs))
        if id_only:
            res_ids = [row['id'] for row in res_assocs]
            return (res_ids, res_assocs)
        else:
            if alt_id_ns and not alt_id:
                res_docs = [self._persistence_dict_to_ion_object(row['doc']['json']) for row in rows if row['key'][1] == alt_id_ns]
            else:
                #res_docs = [self._persistence_dict_to_ion_object(row.doc) for row in rows]
                ###res_docs = [self._persistence_dict_to_ion_object(dict(_id=row['id'], **row['doc']['json'])) for row in rows]
                res_docs = [self._persistence_dict_to_ion_object(row['doc']['json']) for row in rows]
            return (res_docs, res_assocs)

    def find_res_by_view(self, design_name, view_name, key=None, keys=None, start_key=None, end_key=None,
                         id_only=True, **kwargs):
        # TODO: Refactor common code out of above find functions
        pass

    ## Need to do more tests
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
        ##if keys:
        ##    view_args['keys'] = keys
        #@view = ds.view(view_doc, **view_args)
        if key is not None:
            rows = ds.view(view_doc, key=key,  **view_args)
            log.info("find_by_view(%s): key=%s", view_doc, key)
        elif keys:
            #rows = view
            rows = ds.view(view_doc, keys=keys,  **view_args)
            log.info("find_by_view(%s): keys=%s", view_doc, str(keys))
        elif start_key and end_key:
            startkey = start_key or []
            endkey = list(end_key) or []
            endkey.append(END_MARKER)
            log.info("find_by_view(%s): start_key=%s to end_key=%s", view_doc, startkey, endkey)
            if view_args.get('descending', False):
                ##rows = view[endkey:startkey]
                rows = ds.view(view_doc,  start_key=endkey, end_key=startkey, stale="false", **view_args)
            else:
                ##rows = view[startkey:endkey]
                rows = ds.view(view_doc,  start_key=key, end_key=endkey, stale="false", **view_args)
        else:
            #rows = view
            rows = ds.view(view_doc, **view_args)

        ###rows = [self._persistence_dict_to_ion_object(dict(_id=row['id'], **row)) for row in rows]
        rows = [self._persistence_dict_to_ion_object(row) for row in rows]

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

        self._count(find_by_view_call=1, find_by_view_obj=len(res_rows))

        log.info("find_by_view() found %s objects" % (len(res_rows)))
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
        ds, datastore_name = self._get_datastore(datastore_name)
        res = ds.query(map_fun, reduce_fun, **options)

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


    def _count(self, datastore=None, **kwargs):
        datastore = datastore or self.datastore_name
        self._stats.count(namespace=datastore, **kwargs)

    def get_unique_id(self):
        return uuid4().hex
