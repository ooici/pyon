from pyon.core.bootstrap import get_sys_name
from pyon.datastore.couchdb.couch_store import CouchStore
from pyon.datastore.pool import Pool

class CouchDBPoolDict(dict):
    """ acts like a dictionary of Pool, but creates new Pools dynamically as needed """
    def __init__(self, prefix=get_sys_name()+'_', expected_connections=None, max_connections=None, **kw):
        super(CouchDBPoolDict,self).__init__()
        self.prefix = prefix
        # split keyword args between those passed to Pool()
        self.pool_args = {}
        if expected_connections:
            self.pool_args['expected_connections']=expected_connections
        if max_connections:
            self.pool_args['max_connections']=max_connections
        # and those passed to CouchStore()
        self.db_args = kw

    def __getitem__(self, name):
        if name in self.keys():
            return super(CouchDBPoolDict,self).__getitem__(name)
        factory_method=lambda name: CouchStore(self.prefix+name, **self.db_args)
        pool = Pool(name, factory_method=factory_method, **self.pool_args)
        self.__setitem__(name, pool)
        return pool