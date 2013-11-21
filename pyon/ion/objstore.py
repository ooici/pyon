#!/usr/bin/env python

"""General purpose Object store implementation"""

__author__ = 'Michael Meisinger'


from pyon.core import bootstrap
from pyon.datastore.datastore import DataStore
from pyon.util.containers import recursive_encode


class ObjectStore(object):
    """
    Class that uses a data store to provide a general purpose key-value store.
    Values can be either dict or IonObject.
    """
    def __init__(self, datastore_manager=None, container=None):
        self.container = container or bootstrap.container_instance

        # Get an instance of datastore configured as resource registry.
        datastore_manager = datastore_manager or self.container.datastore_manager
        self.obj_store = datastore_manager.get_datastore("objects", DataStore.DS_PROFILE.OBJECTS)
        self.name = 'container_object_store'
        self.id = 'container_object_store'

    def start(self):
        pass

    def stop(self):
        self.close()

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.obj_store.close()


    def create(self, obj, object_id=None):
        return self.obj_store.create(obj, object_id=object_id)

    def create_doc(self, doc, object_id=None):
        return self.obj_store.create_doc(doc, object_id=object_id)

    def create_mult(self, objects, object_ids=None):
        return self.obj_store.create_mult(objects, object_ids=object_ids)

    def create_doc_mult(self, docs, object_ids=None):
        return self.obj_store.create_doc_mult(docs, object_ids=object_ids)


    def update(self, obj):
        return self.obj_store.update(obj)

    def update_doc(self, doc):
        return self.obj_store.update_doc(doc)

    def update_mult(self, objects):
        return self.obj_store.update_mult(objects)

    def update_doc_mult(self, docs):
        return self.obj_store.update_doc_mult(docs)


    def delete(self, obj):
        return self.obj_store.delete(obj)

    def delete_doc(self, doc):
        return self.obj_store.delete_doc(doc)

    def delete_mult(self, object_ids):
        return self.obj_store.delete_mult(object_ids)

    def delete_doc_mult(self, object_ids):
        return self.obj_store.delete_doc_mult(object_ids)


    def read(self, object_id):
        return self.obj_store.read(object_id)

    def read_doc(self, doc_id):
        obj = self.obj_store.read_doc(doc_id)
        obj = obj.copy()
        recursive_encode(obj)
        return obj

    def read_mult(self, object_ids, strict=True):
        return self.obj_store.read_mult(object_ids, strict=strict)

    def read_doc_mult(self, object_ids, strict=True):
        objs = self.obj_store.read_doc_mult(object_ids, strict=strict)
        objs = [recursive_encode(obj) if obj is not None else None for obj in objs]
        return objs
