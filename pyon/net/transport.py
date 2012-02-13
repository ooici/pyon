#!/usr/bin/env python

"""
Transport layer abstractions

TODOS:
- port _sync_call from Channel layer for better error flow, add close callback to channel/client
- split listen() into two subcalls (for StreamSubscriber)
"""

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.async import blocking_cb
from pyon.util.log import log
from gevent.event import AsyncResult

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

    def declare_exchange_impl(self, client, exchange, exchange_type='topic', durable=False, auto_delete=True):
        log.debug("AMQPTransport.declare_exchange_impl: %s, T %s, D %s, AD %s", exchange, exchange_type, durable, auto_delete)
        blocking_cb(client.exchange_declare, 'callback',
                                             exchange=exchange,
                                             type=exchange_type,
                                             durable=durable,
                                             auto_delete=auto_delete)

    def delete_exchange_impl(self, client, exchange, **kwargs):
        log.debug("AMQPTransport.delete_exchange_impl: %s", exchange)
        blocking_cb(client.exchange_delete, 'callback', exchange=exchange)

    def declare_queue_impl(self, client, queue, durable=False, auto_delete=True):
        log.debug("AMQPTransport.declare_queue_impl: %s, D %s, AD %s", queue, durable, auto_delete)
        frame = blocking_cb(client.queue_declare, 'callback',
                                queue=queue or '',
                                auto_delete=auto_delete,
                                durable=durable)
        return frame.method.queue

    def delete_queue_impl(self, client, queue, **kwargs):
        log.debug("AMQPTransport.delete_queue_impl: %s", queue)
        blocking_cb(client.queue_delete, 'callback', queue=queue)

    def bind_impl(self, client, exchange, queue, binding):
        log.debug("AMQPTransport.bind_impl: EX %s, Q %s, B %s", exchange, queue, binding)
        blocking_cb(client.queue_bind, 'callback',
                                        queue=queue,
                                        exchange=exchange,
                                        routing_key=binding)

    def unbind_impl(self, client, exchange, queue, binding):
        log.debug("AMQPTransport.unbind_impl: EX %s, Q %s, B %s", exchange, queue, binding)
        blocking_cb(client.queue_unbind, 'callback', queue=queue,
                                                     exchange=exchange,
                                                     routing_key=binding)


