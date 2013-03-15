    #!/usr/bin/env python

"""Common datastore abstract base for both CouchDB/BigCouch and Couchbase"""

__author__ = 'Michael Meisinger'


from uuid import uuid4

from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.util.containers import get_safe, DictDiffer

from ooi.logging import log


class AbstractCouchDataStore(object):
    """
    Base class common to both CouchDB and Couchbase datastores.
    """

    def __init__(self, datastore_name=None, config=None, scope=None, newlog=None):
        """
        @param datastore_name  Name of datastore within server. May be scoped to sysname
        @param config  A server config dict with connection params
        @param scope  Prefix for the datastore name (e.g. sysname) to separate multiple systems
        @param newlog  Override for the logging system
        """
        global log
        if newlog:
            log = newlog

        self.config = config
        if not self.config:
            self.config = {}

        # Connection basics
        self.host = self.config.get('host', 'localhost')
        self.port = self.config.get('port', 5984)
        self.username = self.config.get('username', None)
        self.password = self.config.get('password', None)

        self.datastore_name = datastore_name

        # Datastore (couch database) handling. Scope with given scope (sysname) and make all lowercase
        self.scope = scope
        if self.scope:
            self.datastore_name = ("%s_%s" % (self.scope, datastore_name)).lower() if datastore_name else None
        else:
            self.datastore_name = datastore_name.lower() if datastore_name else None
