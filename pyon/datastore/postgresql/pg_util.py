#!/usr/bin/env python

"""Common utilities for PostgreSQL datastore. SIDE EFFECT: Gevent monkey patching"""

__author__ = 'Michael Meisinger'

import contextlib
import gevent
from gevent.queue import Queue
from gevent.socket import wait_read, wait_write
import time
import sys
import simplejson as json

try:
    import psycopg2
    from psycopg2 import OperationalError, ProgrammingError, DatabaseError, IntegrityError, extensions
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    from psycopg2.extensions import connection as _connection
    from psycopg2.extensions import cursor as _cursor
    from psycopg2.extras import register_default_json
except ImportError:
    print "PostgreSQL imports not available!"


# Gevent Monkey patching
def gevent_wait_callback(conn, timeout=None):
    """A wait callback useful to allow gevent to work with Psycopg."""
    while 1:
        state = conn.poll()
        if state == extensions.POLL_OK:
            break
        elif state == extensions.POLL_READ:
            wait_read(conn.fileno(), timeout=timeout)
        elif state == extensions.POLL_WRITE:
            wait_write(conn.fileno(), timeout=timeout)
        else:
            raise OperationalError(
                "Bad result from poll: %r" % state)

extensions.set_wait_callback(gevent_wait_callback)
# End Gevent Monkey patching

# Set JSON to Pyon default simplejson to get str instead of unicode in deserialization
register_default_json(None, globally=True, loads=json.loads)


class DatabaseConnectionPool(object):
    """Gevent compliant database connection pool"""

    def __init__(self, maxsize=100):
        if not isinstance(maxsize, (int, long)):
            raise TypeError('Expected integer, got %r' % (maxsize, ))
        self.maxsize = maxsize  # Maximum connections (pool + checkout out)
        self.pool = Queue()     # Open connection pool
        self.size = 0           # Number of open connections

    def get(self):
        pool = self.pool
        if self.size >= self.maxsize or pool.qsize():
            return pool.get()
        else:
            self.size += 1
            try:
                new_item = self.create_connection()
            except:
                self.size -= 1
                raise
            return new_item

    def put(self, item):
        self.pool.put(item)

    def closeall(self):
        while not self.pool.empty():
            conn = self.pool.get_nowait()
            try:
                conn.close()
                self.size -= 1
            except Exception:
                pass

    @contextlib.contextmanager
    def connection(self, isolation_level=None):
        conn = self.get()
        try:
            if isolation_level is not None:
                if conn.isolation_level == isolation_level:
                    isolation_level = None
                else:
                    conn.set_isolation_level(isolation_level)
            yield conn
        except:
            if conn.closed:
                conn = None
                self.closeall()
            else:
                conn = self._rollback(conn)
            raise
        else:
            if conn.closed:
                raise OperationalError("Cannot commit because connection was closed: %r" % (conn, ))
            conn.commit()
        finally:
            if conn is not None and not conn.closed:
                if isolation_level is not None:
                    conn.set_isolation_level(isolation_level)
                self.put(conn)

    @contextlib.contextmanager
    def cursor(self, *args, **kwargs):
        isolation_level = kwargs.pop('isolation_level', None)
        conn = self.get()
        try:
            if isolation_level is not None:
                if conn.isolation_level == isolation_level:
                    isolation_level = None
                else:
                    conn.set_isolation_level(isolation_level)
            tracer = kwargs.pop("tracer", None)
            cur = conn.cursor(*args, **kwargs)
            if isinstance(cur, TracingCursor):
                cur._tracer = tracer
            yield cur
        except:
            if conn.closed:
                conn = None
                self.closeall()
            else:
                conn = self._rollback(conn)
            raise
        else:
            if conn.closed:
                raise OperationalError("Cannot commit because connection was closed: %r" % (conn, ))
            conn.commit()
        finally:
            if conn is not None and not conn.closed:
                if isolation_level is not None:
                    conn.set_isolation_level(isolation_level)
                self.put(conn)

    def _rollback(self, conn):
        try:
            conn.rollback()
        except:
            gevent.get_hub().handle_error(conn, *sys.exc_info())
            return
        return conn

    def execute(self, *args, **kwargs):
        with self.cursor(**kwargs) as cursor:
            cursor.execute(*args)
            return cursor.rowcount

    def fetchone(self, *args, **kwargs):
        with self.cursor(**kwargs) as cursor:
            cursor.execute(*args)
            return cursor.fetchone()

    def fetchall(self, *args, **kwargs):
        with self.cursor(**kwargs) as cursor:
            cursor.execute(*args)
            return cursor.fetchall()

    def fetchiter(self, *args, **kwargs):
        with self.cursor(**kwargs) as cursor:
            cursor.execute(*args)
            while True:
                items = cursor.fetchmany()
                if not items:
                    break
                for item in items:
                    yield item


class PostgresConnectionPool(DatabaseConnectionPool):

    def __init__(self, *args, **kwargs):
        self.connect = kwargs.pop('connect', psycopg2.connect)
        self.tracer = kwargs.pop('tracer', None)
        maxsize = kwargs.pop('maxsize', None)
        self.args = args
        self.kwargs = kwargs
        if self.tracer:
            self.kwargs.setdefault("connection_factory", TracingConnection)
        DatabaseConnectionPool.__init__(self, maxsize)

    def create_connection(self):
        conn = self.connect(*self.args, **self.kwargs)
        if self.tracer:
            conn.set_tracer(self.tracer)
        return conn


def psycopg2_connect(dsn=None, *args, **kwargs):
    if dsn is None:
        c_host = kwargs.pop("c_host", None) or "localhost"
        c_port = kwargs.pop("c_port", None) or "5432"
        c_dbname = kwargs.pop("c_dbname", None) or "postgres"
        c_user = kwargs.pop("c_user", None) or ""
        c_password = kwargs.pop("c_password", None) or ""
        dsn = "host=%s port=%s dbname=%s user=%s password=%s" % (c_host, c_port, c_dbname, c_user, c_password)
    tracer = kwargs.pop("tracer", None)
    trace_stmt = kwargs.pop("trace_stmt", None)
    if tracer:
        conn = psycopg2.connect(dsn, *args, connection_factory=TracingConnection, **kwargs)
        conn.set_tracer(tracer, trace_stmt)
    else:
        conn = psycopg2.connect(dsn, *args, **kwargs)
    return conn


class TracingConnection(_connection):
    """A connection that logs all queries to a file or logger__ object."""
    def set_tracer(self, tracer, trace_stmt=None):
        self._tracer = tracer
        self._trace_stmt = trace_stmt

    def cursor(self, *args, **kwargs):
        kwargs.setdefault('cursor_factory', TracingCursor)
        return super(TracingConnection, self).cursor(*args, **kwargs)


class TracingCursor(_cursor):
    """A cursor that logs queries using its connection logging facilities."""

    def __init__(self, *args, **kwargs):
        self._tracer = kwargs.pop("_tracer", None)
        self._trace_stmt = kwargs.pop("_trace_stmt", None)
        _cursor.__init__(self, *args, **kwargs)
        self._tracer = self._tracer or getattr(self.connection, "_tracer", None)
        self._trace_stmt = self._trace_stmt or getattr(self.connection, "_trace_stmt", None)

    def execute(self, query, vars=None):
        query_time = 0
        try:
            t_begin = time.time()
            res = super(TracingCursor, self).execute(query, vars)
            query_time = time.time() - t_begin
            return res
        finally:
            if self._tracer:
                self._log_call(self._tracer, trace_stmt=self._trace_stmt, query_time=query_time)

    def callproc(self, procname, vars=None):
        query_time = 0
        try:
            t_begin = time.time()
            res = super(TracingCursor, self).callproc(procname, vars)
            query_time = time.time() - t_begin
            return res
        finally:
            if self._tracer:
                self._log_call(self._tracer, trace_stmt=self._trace_stmt, query_time=query_time)

    def fetchall(self):
        query_time = 0
        try:
            t_begin = time.time()
            res = super(TracingCursor, self).fetchall()
            query_time = time.time() - t_begin
            return res
        finally:
            log_entry = getattr(self, "_current_entry", None)
            if log_entry and log_entry.get("statement", "") == self.query and "statement_time" in log_entry:
                log_entry["statement_time"] += query_time

    def _log_call(self, tracer, trace_stmt=None, query_time=None):
        statement = trace_stmt or self.query
        status = self.rowcount
        log_entry = dict(
            statement=statement,
            status=status,
        )
        if query_time is not None:
            log_entry["statement_time"] = query_time
        tracer.log_call(log_entry, include_stack=True)
        self._current_entry = log_entry
        return log_entry


class StatementBuilder(object):
    def __init__(self):
        self.statement = None
        self.st_frag = []
        self.statement_args = {}

    def append(self, *fragments):
        self.st_frag.extend(fragments)

    def append_value(self, fragment, valkey, value, count):
        if count:
            self.st_frag.append(",")
        self.st_frag.append(fragment)
        self.statement_args[valkey+str(count)] = value

    def build(self):
        self.statement = "".join(self.st_frag)
        return self.statement, self.statement_args
