#!/usr/bin/env python

"""Common datastore definitions"""

__author__ = 'Michael Meisinger'

from ooi.logging import log

from pyon.core.exception import BadRequest
from pyon.util.containers import get_safe, named_any, DotDict


class DataStore(object):
    """
    Common definitions and base class for data stores
    """
    # Constants for common datastore names
    DS_RESOURCES = "resources"
    DS_OBJECTS = "objects"
    DS_EVENTS = "events"
    DS_DIRECTORY = DS_RESOURCES
    DS_STATE = "state"
    DS_CONVERSATIONS = "conversations"
    DS_COVERAGE = "coverage"

    # Enumeration of index profiles for datastores
    DS_PROFILE_LIST = ['OBJECTS', 'RESOURCES', 'DIRECTORY', 'STATE', 'EVENTS', 'CONV', 'FILESYSTEM', 'BASIC', 'SCIDATA', 'COVERAGE']
    DS_PROFILE = DotDict(zip(DS_PROFILE_LIST, DS_PROFILE_LIST))
    DS_PROFILE.lock()

    # Maps common datastore logical names to index profiles
    DS_PROFILE_MAPPING = {
        DS_RESOURCES: DS_PROFILE.RESOURCES,
        DS_OBJECTS: DS_PROFILE.OBJECTS,
        DS_EVENTS: DS_PROFILE.EVENTS,
        DS_STATE: DS_PROFILE.STATE,
        DS_CONVERSATIONS: DS_PROFILE.OBJECTS,
        DS_COVERAGE: DS_PROFILE.COVERAGE,
        }

    def __init__(self, datastore_name=None, profile=None, config=None, container=None, scope=None, **kwargs):
        pass


class DatastoreFactory(object):
    """Helps to create instances of datastores"""

    DS_BASE = "base"    # A standalone variant                                    of
    DS_FULL = "full"    # A datastore that requires pyon initialization

    @classmethod
    def get_datastore(cls, datastore_name=None, variant=DS_BASE, config=None, container=None, profile=None, scope=None):
        #log.info("get_datastore(%s, variant=%s, profile=%s, scope=%s, config=%s)", datastore_name, variant, profile, scope, "")

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
                server_type = server_cfg.get("type", "postgresql")
                type_cfg = server_types.get(server_type, None)
                if not type_cfg:
                    raise BadRequest("Server type '%s' not configured!" % server_type)

                variant_store = type_cfg.get(variant, cls.DS_BASE)
        else:
            # Fallback in case a server config was given (NOT NICE)
            variant_store = cls.get_datastore_class(server_cfg, variant=variant)


        # Step 3: Instantiate type specific implementation
        store_class = named_any(variant_store)
        profile = profile or DataStore.DS_PROFILE_MAPPING.get(datastore_name, DataStore.DS_PROFILE.BASIC)
        log.debug("get_datastore(%s, profile=%s, scope=%s, variant=%s) -> %s", datastore_name, profile, scope, variant, store_class.__name__)
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
        elif server_type == 'postgresql':
            store_cls = "pyon.datastore.postgresql.base_store.PostgresDataStore"
        else:
            raise BadRequest("Unknown datastore server type: %s" % server_type)
        return store_cls

    @classmethod
    def get_server_config(cls, config=None):
        default_server = get_safe(config, "container.datastore.default_server", "postgresql")

        server_cfg = get_safe(config, "server.%s" % default_server, None)
        if not server_cfg:
            # Support tests that mock out the CFG
            pg_cfg = get_safe(config, "server.postgresql", None)
            if pg_cfg:
                server_cfg = pg_cfg
            else:
                raise BadRequest("No datastore config available!")
                # server_cfg = dict(
                #     type='postgresql',
                #     host='localhost',
                #     port=5432,
                #     username='ion',
                #     password=None,
                #     admin_username=None,
                #     admin_password=None,
                #     default_database='postgres',
                #     database='ion',
                #     connection_pool_max=5)
        else:
            # HACK for CEI system start compliance:
            # If couchdb password is set and current is empty, use couchdb password instead
            couch_cfg = get_safe(config, "server.couchdb", None)
            if couch_cfg and get_safe(couch_cfg, "password") and not get_safe(server_cfg, "password"):
                server_cfg["admin_username"] = couch_cfg["username"]
                server_cfg["admin_password"] = couch_cfg["password"]
                server_cfg["password"] = couch_cfg["password"]
                if get_safe(couch_cfg, "host") == "couchdb.dev.oceanobservatories.org":
                    server_cfg["host"] = "pg-dev02.oceanobservatories.org"
                log.warn("Substituted username/password using couchdb. New config: %s", server_cfg)

        return server_cfg
