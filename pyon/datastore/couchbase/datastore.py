#!/usr/bin/env python

__author__ = 'Michael Meisinger, Seman Said'

from pyon.core.bootstrap import get_obj_registry, CFG
from pyon.core.object import IonObjectBase, IonObjectSerializer, IonObjectDeserializer
from pyon.datastore.datastore import DataStore
from pyon.datastore.couchdb.pyon_store import PyonCouchDataStoreMixin
from pyon.datastore.couchbase.base_store import CouchbaseDataStore
from pyon.util.log import log


class CouchbasePyonDataStore(CouchbaseDataStore, PyonCouchDataStoreMixin):
    """
    Pyon specialization of Couchbase datastore.
    This class adds IonObject handling to the underlying base datastore.
    """
    def __init__(self, datastore_name=None, profile=None, config=None, scope=None, **kwargs):
        log.debug('__init__(datastore_name=%s, profile=%s, config=%s)', datastore_name, profile, config)

        CouchbaseDataStore.__init__(self, datastore_name=datastore_name,
                                         config=config or CFG.get_safe("server.couchdb"),
                                         profile=profile or DataStore.DS_PROFILE.BASIC,
                                         scope=scope)

        # IonObject Serializers
        self._io_serializer = IonObjectSerializer()
        self._io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
