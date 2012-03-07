#!/usr/bin/env python

"""
Transport layer abstractions

TODOS:
- split listen() into two subcalls (for StreamSubscriber)
"""

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from gevent.event import AsyncResult
from contextlib import contextmanager

class TransportError(StandardError):
    pass

class BaseTransport(object):
    def declare_exchange_impl(self, client, exchange, **kwargs):
        raise NotImplementedError()
    def delete_exchange_impl(self, client, exchange, **kwargs):
        raise NotImplementedError()

    def declare_queue_impl(self, client, queue, **kwargs):
        raise NotImplementedError()
    def delete_queue_impl(self, client, queue, **kwargs):
        raise NotImplementedError()

    def bind_impl(self, client, exchange, queue, binding):
        raise NotImplementedError()
    def unbind_impl(self, client, exchange, queue, binding):
        raise NotImplementedError()

    def setup_listener(self, binding, default_cb):
        raise NotImplementedError()

class AMQPTransport(BaseTransport):
    """
    This is STATELESS. You can make instances of it, but no need to (true singleton).
    """
    __instance = None

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = AMQPTransport()
        return cls.__instance

    @contextmanager
    def _push_close_cb(self, client, callback):
        client.add_on_close_callback(callback)
        try:
            yield callback
        finally:
            # PIKA BUG: v0.9.5, we need to specify the callback as a dict - this is fixed in git HEAD (13 Feb 2012)
            de = {'handle': callback, 'one_shot': True}
            client.callbacks.remove(client.channel_number, '_on_channel_close', de)

    def _sync_call(self, client, func, cb_arg, *args, **kwargs):
        """
        Functionally similar to the generic blocking_cb but with error support that's Channel specific.
        """
        ar = AsyncResult()

        def cb(*args, **kwargs):
            ret = list(args)
            if len(kwargs): ret.append(kwargs)
            ar.set(ret)

        eb = lambda ch, *args: ar.set(TransportError("_sync_call could not complete due to an error (%s)" % args))

        kwargs[cb_arg] = cb
        with self._push_close_cb(client, eb):
            func(*args, **kwargs)
            ret_vals = ar.get(timeout=10)

        if isinstance(ret_vals, TransportError):

            # mark this channel as poison, do not use again!
            # don't test for type here, we don't want to have to import PyonSelectConnection
            if hasattr(client.transport, 'connection') and hasattr(client.transport.connection, 'mark_bad_channel'):
                client.transport.connection.mark_bad_channel(client.channel_number)
            else:
                log.warn("Could not mark channel # (%s) as bad, Pika could be corrupt", client.channel_number)

            raise ret_vals

        if len(ret_vals) == 0:
            return None
        elif len(ret_vals) == 1:
            return ret_vals[0]
        return tuple(ret_vals)


    def declare_exchange_impl(self, client, exchange, exchange_type='topic', durable=False, auto_delete=True):
        log.debug("AMQPTransport.declare_exchange_impl: %s, T %s, D %s, AD %s", exchange, exchange_type, durable, auto_delete)
        self._sync_call(client, client.exchange_declare, 'callback',
                                             exchange=exchange,
                                             type=exchange_type,
                                             durable=durable,
                                             auto_delete=auto_delete)

    def delete_exchange_impl(self, client, exchange, **kwargs):
        log.debug("AMQPTransport.delete_exchange_impl: %s", exchange)
        self._sync_call(client, client.exchange_delete, 'callback', exchange=exchange)

    def declare_queue_impl(self, client, queue, durable=False, auto_delete=True):
        log.debug("AMQPTransport.declare_queue_impl: %s, D %s, AD %s", queue, durable, auto_delete)
        frame = self._sync_call(client, client.queue_declare, 'callback',
                                queue=queue or '',
                                auto_delete=auto_delete,
                                durable=durable)
        return frame.method.queue

    def delete_queue_impl(self, client, queue, **kwargs):
        log.debug("AMQPTransport.delete_queue_impl: %s", queue)
        self._sync_call(client, client.queue_delete, 'callback', queue=queue)

    def bind_impl(self, client, exchange, queue, binding):
        log.debug("AMQPTransport.bind_impl: EX %s, Q %s, B %s", exchange, queue, binding)
        self._sync_call(client, client.queue_bind, 'callback',
                                        queue=queue,
                                        exchange=exchange,
                                        routing_key=binding)

    def unbind_impl(self, client, exchange, queue, binding):
        log.debug("AMQPTransport.unbind_impl: EX %s, Q %s, B %s", exchange, queue, binding)
        self._sync_call(client, client.queue_unbind, 'callback', queue=queue,
                                                     exchange=exchange,
                                                     routing_key=binding)

    def setup_listener(self, binding, default_cb):
        """
        Calls setup listener via the default callback passed in.
        """
        return default_cb(self, binding)


class NameTrio(object):
    """
    Internal representation of a name/queue/binding (optional).
    Created and used at the Endpoint layer and sometimes Channel layer.
    """
    def __init__(self, exchange=None, queue=None, binding=None):
        """
        Creates a NameTrio.

        If either exchange or queue is a tuple, it will use that as a (exchange, queue, binding (optional)) triple.

        @param  exchange    An exchange name. You would typically use the sysname for that.
        @param  queue       Queue name.
        @param  binding     A binding/routing key (used for both recv and send sides). Optional,
                            and if not specified, defaults to the *internal* queue name.
        """
        if isinstance(exchange, tuple):
            self._exchange, self._queue, self._binding = list(exchange) + ([None] *(3-len(exchange)))
        elif isinstance(queue, tuple):
            self._exchange, self._queue, self._binding = list(queue) + ([None] *(3-len(queue)))
        else:
            self._exchange  = exchange
            self._queue     = queue
            self._binding   = binding

    @property
    def exchange(self):
        return self._exchange

    @property
    def queue(self):
        return self._queue

    @property
    def binding(self):
        return self._binding or self._queue

    def __str__(self):
        return "NP (%s,%s,B: %s)" % (self.exchange, self.queue, self.binding)
