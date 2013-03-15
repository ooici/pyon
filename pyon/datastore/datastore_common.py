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
    def get_datastore(cls, datastore_name=None, variant=DS_BASE, config=None, container=None, profile=None):
        CFG = None
        if config:
            CFG = config
        if container:
            if not CFG:
                CFG = container.CFG
        if not CFG:
            raise BadRequest("No config available to determine datastore")

        # Step 1: Get datastore server config
        server_cfg = cls.get_server_config(CFG)

        # Step 2: Find type specific implementation class
        server_types = get_safe(CFG, "container.datastore.server_types", None)
        if not server_types:
            raise BadRequest("Server types not configured!")

        server_type = server_cfg.get("type", "couchdb")
        type_cfg = server_types.get(server_type, None)
        if not type_cfg:
            raise BadRequest("Server type '%s' not configured!" % server_type)

        variant_store = type_cfg.get(variant, "base")

        # Step 3: Instantiate type specific implementation
        store_class = named_any(variant_store)
        store = store_class(datastore_name=datastore_name, config=server_cfg, profile=profile)

        return store

    @classmethod
    def get_server_config(cls, config=None):
        default_server = get_safe(config, "container.datastore.default_server", "couchdb")

        server_cfg = get_safe(config, "server.%s" % default_server, None)
        if not server_cfg:
            raise BadRequest("No datastore config available!")

        return server_cfg
