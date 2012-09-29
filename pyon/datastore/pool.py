""" general pooling mechanism, although slightly tailored to DB connections """

from threading import Lock
from pyon.core.exception import ServerError, BadRequest
from pyon.util.log import log


class Pool(object):
    def __init__(self, name, factory_method=None, expected_connections=5, max_connections=10):
        """ create a new pool that uses the callable factory_method to create new connections
            will emit warnings if more than expected_connections are active,
            will fail if request would cause more than max_connections to be active.
        """
        self._name = name
        self._lock = Lock()
        self._create_object = factory_method or self.create_object
        self._expected = expected_connections
        self._max = max_connections
        self._unused = []
        self._used = []
        self._close = None

    def check_out(self):
        """ check a connection out of the pool or create one if necessary """
        self._lock.acquire()
        try:
            if self._close:
                raise ServerError('system shutting down')
            if len(self._unused):
                out = self._unused[0]
                del self._unused[0]
            else:
                count = len(self._used)
                if count >= self._max:
                    raise BadRequest('already have max connections for ' + self._name)
                elif count > self._expected:
                    log.warn('exceeding expected number of DB connections for ' + self._name + ': ' + str(count))
                out = self._create_object(self._name)
            self._used.append(out)
            return out
        finally:
            self._lock.release()

    def check_in(self, obj):
        """ return a connection to the pool """
        self._lock.acquire()
        try:
            self._used.remove(obj)
            if self._close:
                try:
                    self._close(obj)
                except:
                    log.warn('exception in close operation', exc_info=True)
            else:
                self._unused.append(obj)
        finally:
            self._lock.release()

    def create_object(self, obj):
        raise NotImplementedError('should be implemented by subclass')

    def destroy_object(self, obj):
        """ return a connection, but don't allow it to be reused (ie- connection has been closed) """
        self._lock.acquire()
        try:
            self._used.remove(obj)
        finally:
            self._lock.release()

    def shut_down(self, op=None, interrupt=False):
        """ allow no more objects to be created, invoke op on all objects now or wait for check_in """
        self._close = op
        if interrupt:
            # make copy so checkins won't update list while iterating
            for o in [ o for o in self._used ]:
                try:
                    op(o)
                except:
                    log.warn('exception in close operation', exc_info=True)
