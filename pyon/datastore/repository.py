"""

"""

from pyon.core.exception import IonException, ServerError, BadRequest
from pyon.core.object import IonObjectBase
from pyon.datastore.id_factory import SaltedTimeIDFactory
from pyon.ion.resource import AT
from pyon.util.log import log
from pyon.datastore.representation import IonSerializerDictionaryRepresentation


class Repository(object):

    def __init__(self, pools, representation=None):
        self._pool = pools
        if representation:
            self._representation = representation
        else:
            self._id_factory = SaltedTimeIDFactory()
            self._representation = IonSerializerDictionaryRepresentation(id_factory=self._id_factory)

    def close(self):
        for pool in self._pool.values():
            pool.close(op=self._close_connection)

    def _close_connection(self, connection):
        connection.close()

    #############################

    def _validate_object(self, arg):
        ''' check that arg is IonObject or list of IonObjects '''
        if isinstance(arg, IonObjectBase):
            return
        if isinstance(arg, list) and len(arg) and all([isinstance(o, IonObjectBase) for o in arg]):
            return
        raise BadRequest('invalid repository entry type ' + arg.__class__.__name__ + ': ' + repr(arg))

    def _validate_object_or_id(self, arg):
        ''' collection of IDs is valid, otherwise check for valid IonObject(s) '''
        if isinstance(arg, str):
            return
        if isinstance(arg, list) and len(arg) and all([isinstance(id, str) for id in arg]):
            return
        self._validate_object(arg)

    def _is_id(self, arg):
        return isinstance(arg, str) or (isinstance(arg, list) and isinstance(arg[0], str))

    #############################
    #
    # CRUD operations delegate to datastore
    # all use _perform for consistency:
    # - check argument for allowed types argect, id, list of objects or list of ids
    # - get pooled datastore instance
    # - perform operation, notify of any non-application exceptions
    # - return connection to pool

    def insert(self, store, arg, _connection=None, **kw):
        """ insert one or more IonObjects into the DB
            return value is one/list of triples (success, id, exception)
                   indicating success or failure per insert
        """
        if not _connection:
            self._validate_object(arg)
            encoded = self._encode(arg, add_id=True)
            return self._perform(self.insert, store, encoded)
        return _connection.insert(arg, **kw)

    def update(self, store, arg, _connection=None, **kw):
        """ update one or more IonObjects
            return value is one/list of triples (success, id, exception)
                   indicating success or failure per insert
        """
        if not _connection:
            self._validate_object(arg)
            return self._perform(self.update, store, self._encode(arg))
        return _connection.update(arg, **kw)

    def read(self, store, arg, _connection=None, **kw):
        """ read one or more IonObjects from the DB
            arg may be IonObject(s) (which will be updated)
                or if type is provided, id(s)
            returns one/list of tuples (success, id, IonObject or exception)
        """
        if not _connection:
            self._validate_object_or_id(arg)
            return self._perform(self.read, store, self._encode_or_id(arg))
        return self._decode(_connection.read(arg, **kw))

    def delete(self, store, arg, _connection=None, **kw):
        """ delete one or more objects from the DB
            arg may be IonObject(s), or if type is provided, id(s)
            return value is one/list of triples (success, id, exception)
                   indicating success or failure per insert
        """
        if not _connection:
            self._validate_object_or_id(arg)
            return self._perform(self.delete, store, self._encode_or_id(arg))
        return _connection.delete(arg, **kw)

    def _encode_or_id(self, arg):
        if self._is_id(arg):
            return arg
        else:
            return self._encode(arg)

    def _encode(self, arg, add_id=False):
        if isinstance(arg, list):
            return [self._encode(o, add_id=add_id) for o in arg]
        return self._representation.encode(arg, add_id=add_id)

    def _decode(self, arg):
        if isinstance(arg, list):
            return [self._decode(d) for d in arg]
        if isinstance(arg, tuple):
            return arg[0], arg[1], self._decode(arg[2])
        if isinstance(arg, Exception):
            return arg
        return self._representation.decode(arg)

    def _perform(self, op, store, *args, **kwargs):
        """ re-invoke the calling operation with a pooled DB connection """
        pool = self._pool[store]
        connection = pool.check_out()
        if not connection:
            raise ServerError('failed to get a connection for store: ' + store)
        try:
            return op(store, *args, _connection=connection, **kwargs)
        except IonException:
            raise
        except:
            # should have been rethrown as application exception by store, find and fix these occurrences...
            log.error('unexpected exception from datastore', exc_info=True)
            raise
        finally:
            pool.check_in(connection)

    #############################
    #
    # NOT YET IMPLEMENTED
    def create_association(self, subject=None, predicate=None, arg=None, assoc_type=AT.H2H):
        pass

    def delete_association(self, association=''):
        pass

    def find_objects(self, subject, predicate="", object_type="", id_only=False):
        pass

    def find_subjects(self, subject_type="", predicate="", obj="", id_only=False):
        pass

    def find_associations(self, subject="", predicate="", obj="", assoc_type=AT.H2H, id_only=True):
        pass

    def find_resources(self, restype="", lcstate="", name="", id_only=True):
        pass
