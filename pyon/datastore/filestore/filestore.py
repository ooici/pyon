#!/usr/bin/env python

"""File system based datastore with limited functionality (CRUD)."""

__author__ = 'Michael Meisinger'

import simplejson as json
import base64
import os
from uuid import uuid4

from pyon.core import bootstrap
from pyon.core.bootstrap import get_obj_registry, CFG
from pyon.core.exception import BadRequest, NotFound, Inconsistent
from pyon.core.object import IonObjectBase
from pyon.ion.event import EventPublisher
from pyon.ion.identifier import create_unique_resource_id
from pyon.ion.resource import LCS, LCE, PRED, RT, AS, get_restype_lcsm, is_resource, ExtendedResourceContainer, lcstate, lcsplit
from pyon.util.containers import get_ion_ts
from pyon.util.log import log
from pyon.core.object import IonObjectBase, IonObjectSerializer, IonObjectDeserializer
from pyon.util.file_sys import FileSystem, FS

from interface.objects import Attachment, AttachmentType, ResourceModificationType


class FileDataStore(object):
    def __init__(self, container, datastore_name=""):
        self.container = container
        self.datastore_name = datastore_name

        # Object serialization/deserialization
        self._io_serializer = IonObjectSerializer()
        self._io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())

    def start(self):
        if self.container.has_capability(self.container.CCAP.FILE_SYSTEM):
            self.datastore_dir = FileSystem.get_url(FS.FILESTORE, self.datastore_name)
        else:
            self.datastore_dir = "./tmp/%s" % self.datastore_name

    def stop(self):
        pass

    def _get_filename(self, object_id):
        return "%s/%s" % (self.datastore_dir, object_id)

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
        if '_id' in doc:
            raise BadRequest("Doc must not have '_id'")

        # Assign an id to doc (recommended in CouchDB documentation)
        doc["_id"] = object_id or uuid4().hex
        log.debug('Creating new object %s/%s' % (datastore_name, doc["_id"]))
        log.debug('create doc contents: %s', doc)

        filename = self._get_filename(doc["_id"])
        doc_json = json.dumps(doc)
        with open(filename, "w") as f:
            f.write(doc_json)

        return doc["_id"], 1

    def update(self, obj, datastore_name=""):
        if not isinstance(obj, IonObjectBase):
            raise BadRequest("Obj param is not instance of IonObjectBase")
        return self.update_doc(self._ion_object_to_persistence_dict(obj))

    def update_doc(self, doc, datastore_name=""):
        if '_id' not in doc:
            raise BadRequest("Doc must have '_id'")

        log.debug('update doc contents: %s', doc)
        filename = self._get_filename(doc["_id"])
        doc_json = json.dumps(doc)
        with open(filename, "w") as f:
            f.write(doc_json)

        return doc["_id"], 2

    def read(self, object_id, rev_id="", datastore_name=""):
        if not isinstance(object_id, str):
            raise BadRequest("Object id param is not string")
        doc = self.read_doc(object_id, rev_id, datastore_name)

        # Convert doc into Ion object
        obj = self._persistence_dict_to_ion_object(doc)
        log.debug('Ion object: %s', str(obj))
        return obj

    def read_doc(self, doc_id, rev_id="", datastore_name=""):
        log.debug('Reading head version of object %s/%s', datastore_name, doc_id)
        filename = self._get_filename(doc_id)
        doc = None
        with open(filename, "r") as f:
            doc_json = f.read()
            doc = json.loads(doc_json)
        if doc is None:
            raise NotFound('Object with id %s does not exist.' % str(doc_id))
        log.debug('read doc contents: %s', doc)
        return doc

    def delete(self, obj, datastore_name="", del_associations=False):
        if not isinstance(obj, IonObjectBase) and not isinstance(obj, str):
            raise BadRequest("Obj param is not instance of IonObjectBase or string id")
        if type(obj) is str:
            self.delete_doc(obj, datastore_name=datastore_name, del_associations=del_associations)
        else:
            if '_id' not in obj:
                raise BadRequest("Doc must have '_id'")
            self.delete_doc(self._ion_object_to_persistence_dict(obj), datastore_name=datastore_name, del_associations=del_associations)

    def delete_doc(self, doc, datastore_name="", del_associations=False):
        doc_id = doc if type(doc) is str else doc["_id"]
        log.debug('Deleting object %s/%s', datastore_name, doc_id)
        filename = self._get_filename(doc_id)

        try:
            os.remove(filename)
        except OSError:
            raise NotFound('Object with id %s does not exist.' % doc_id)

    def _ion_object_to_persistence_dict(self, ion_object):
        if ion_object is None: return None

        obj_dict = self._io_serializer.serialize(ion_object)
        return obj_dict

    def _persistence_dict_to_ion_object(self, obj_dict):
        if obj_dict is None: return None

        ion_object = self._io_deserializer.deserialize(obj_dict)
        return ion_object
