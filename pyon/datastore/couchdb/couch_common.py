    #!/usr/bin/env python

"""Common datastore abstract base for both CouchDB/BigCouch and Couchbase"""

__author__ = 'Michael Meisinger'


from uuid import uuid4

from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.util.containers import get_safe, DictDiffer
from pyon.util.stats import StatsCounter

from ooi.logging import log

# Token for a most likely non-inclusive key range upper bound (end_key), for queries such as
# prefix <= keys < upper bound: e.g. ['some','value'] <= keys < ['some','value', END_MARKER]
# or "somestr" <= keys < "somestr"+END_MARKER for string prefix checking
# Note: Use highest ASCII characters here, not 8bit
#END_MARKER = "\x7f\x7f\x7f\x7f"
END_MARKER = "ZZZZZZ"


class AbstractCouchDataStore(object):
    """
    Base class common to both CouchDB and Couchbase datastores.
    """
    _stats = StatsCounter()

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

    def _get_datastore_name(self, datastore_name=None):
        """
        Computes a name for the datastore to work on. If name is given, uses the lower case
        version of this name. If this instance was initialized with a scope, the name is additionally
        scoped. If no name was given, the instance defaults will be returned.
        """
        if datastore_name and self.scope:
            datastore_name = ("%s_%s" % (self.scope, datastore_name)).lower()
        elif datastore_name:
            datastore_name = datastore_name.lower()
        elif self.datastore_name:
            datastore_name = self.datastore_name
        else:
            raise BadRequest("No data store name provided")
        return datastore_name

    def _get_design_name(self, design):
        return "_design/%s" % design

    def _get_view_name(self, design, name):
        return "_design/%s/_view/%s" % (design, name)

    def _get_endkey(self, startkey):
        if startkey is None or type(startkey) is not list:
            raise BadRequest("Cannot create endkey for type %s" % type(startkey))
        endkey = list(startkey)
        endkey.append(END_MARKER)
        return endkey

    def _count(self, datastore=None, **kwargs):
        datastore = datastore or self.datastore_name
        self._stats.count(namespace=datastore, **kwargs)
