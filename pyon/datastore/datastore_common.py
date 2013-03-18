#!/usr/bin/env python

"""Common datastore definitions"""

__author__ = 'Michael Meisinger'

from pyon.core.exception import BadRequest
from pyon.util.containers import get_safe, named_any


class DataStore(object):
    """Base class for all compliant datastores"""
    def __init__(self, datastore_name=None, profile=None, config=None, container=None, **kwargs):
        pass


class DatastoreFactory(object):
    """Helps to create instances of datastores"""

    DS_BASE = "base"    # A standalone variant
    DS_FULL = "full"    # A datastore that requires pyon initialization

    @classmethod
    def get_datastore(cls, datastore_name=None, variant=DS_BASE, config=None, container=None, profile=None, scope=None):
        # Step 1: Get datastore server config
        if not config and container:
            config = container.CFG
        if config:
            if "container" in config:
                server_cfg = cls.get_server_config(config)
            else:
                server_cfg = config
                config = None

        if not server_cfg:
            raise BadRequest("No config available to determine datastore")

        # Step 2: Find type specific implementation class
        if config:
            server_types = get_safe(config, "container.datastore.server_types", None)
            if not server_types:
                # Some tests fudge the CFG - make it more lenient
                #raise BadRequest("Server types not configured!")
                variant_store = cls.get_datastore_class(server_cfg, variant=variant)

            else:
                server_type = server_cfg.get("type", "couchdb")
                type_cfg = server_types.get(server_type, None)
                if not type_cfg:
                    raise BadRequest("Server type '%s' not configured!" % server_type)

                variant_store = type_cfg.get(variant, cls.DS_BASE)
        else:
            # Fallback in case a server config was given (NOT NICE)
            variant_store = cls.get_datastore_class(server_cfg, variant=variant)

        # Step 3: Instantiate type specific implementation
        store_class = named_any(variant_store)
        store = store_class(datastore_name=datastore_name, config=server_cfg, profile=profile, scope=scope)

        return store

    @classmethod
    def get_datastore_class(cls, server_cfg, variant=None):
        server_type = server_cfg.get('type', 'couchdb')
        if server_type == 'couchdb':
            if variant == cls.DS_BASE:
                store_cls = "pyon.datastore.couchdb.base_store.CouchDataStore"
            else:
                store_cls = "pyon.datastore.couchdb.datastore.CouchPyonDataStore"
        elif server_type == 'couchbase':
            store_cls = "pyon.datastore.couchbase.base_store.CouchbaseDataStore"
        else:
            raise BadRequest("Unknown datastore server type: %s" % server_type)
        return store_cls

    @classmethod
    def get_server_config(cls, config=None):
        default_server = get_safe(config, "container.datastore.default_server", "couchdb")

        server_cfg = get_safe(config, "server.%s" % default_server, None)
        if not server_cfg:
            raise BadRequest("No datastore config available!")

        return server_cfg
