#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from pyon.core.bootstrap import get_obj_registry, CFG
from pyon.core.object import IonObjectBase, IonObjectSerializer, IonObjectDeserializer
from pyon.datastore.datastore import DataStore
from pyon.datastore.couchdb.base_store import CouchDataStore
from pyon.datastore.couchdb.pyon_store import PyonCouchDataStoreMixin
from pyon.util.log import log


class CouchPyonDataStore(CouchDataStore, PyonCouchDataStoreMixin):
    """
    Pyon specialization of CouchDB datastore.
    This class adds IonObject handling to the underlying base datastore.
    """
    def __init__(self, datastore_name=None, profile=None, config=None, scope=None, **kwargs):
        log.debug('__init__(datastore_name=%s, profile=%s, config=%s)', datastore_name, profile, config)

        CouchDataStore.__init__(self, datastore_name=datastore_name,
                                 config=config or CFG.get_safe("server.couchdb"),
                                 profile=profile or DataStore.DS_PROFILE.BASIC,
                                 scope=scope)

        # IonObject Serializers
        self._io_serializer = IonObjectSerializer()
        self._io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
