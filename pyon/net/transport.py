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
import os

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

    def ack_impl(self, client, delivery_tag):
        raise NotImplementedError()
    def reject_impl(self, client, delivery_tag, requeue=False):
        raise NotImplementedError()

    def start_consume_impl(self, client, callback, queue, no_ack=False, exclusive=False):
        raise NotImplementedError()
    def stop_consume_impl(self, client, consumer_tag):
        raise NotImplementedError()

    def setup_listener(self, binding, default_cb):
        raise NotImplementedError()

    def get_stats_impl(self, client, queue):
        raise NotImplementedError()

    def purge_impl(self, client, queue):
        raise NotImplementedError()

    def qos_impl(self, client, prefetch_size=0, prefetch_count=0, global_=False):
        raise NotImplementedError()

    def publish_impl(self, client, exchange, routing_key, body, properties, immediate=False, mandatory=False): 
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
        log.debug("AMQPTransport.declare_exchange_impl(%s): %s, T %s, D %s, AD %s", client.channel_number, exchange, exchange_type, durable, auto_delete)
        arguments = {}

        if os.environ.get('QUEUE_BLAME', None) is not None:
            testid = os.environ['QUEUE_BLAME']
            arguments.update({'created-by':testid})

        self._sync_call(client, client.exchange_declare, 'callback',
                                             exchange=exchange,
                                             type=exchange_type,
                                             durable=durable,
                                             auto_delete=auto_delete,
                                             arguments=arguments)

    def delete_exchange_impl(self, client, exchange, **kwargs):
        log.debug("AMQPTransport.delete_exchange_impl(%s): %s", client.channel_number, exchange)
        self._sync_call(client, client.exchange_delete, 'callback', exchange=exchange)

    def declare_queue_impl(self, client, queue, durable=False, auto_delete=True):
        log.debug("AMQPTransport.declare_queue_impl(%s): %s, D %s, AD %s", client.channel_number, queue, durable, auto_delete)
        arguments = {}

        if os.environ.get('QUEUE_BLAME', None) is not None:
            testid = os.environ['QUEUE_BLAME']
            arguments.update({'created-by':testid})

        frame = self._sync_call(client, client.queue_declare, 'callback',
                                queue=queue or '',
                                auto_delete=auto_delete,
                                durable=durable,
                                arguments=arguments)

        return frame.method.queue

    def delete_queue_impl(self, client, queue, **kwargs):
        log.debug("AMQPTransport.delete_queue_impl(%s): %s", client.channel_number, queue)
        self._sync_call(client, client.queue_delete, 'callback', queue=queue)

    def bind_impl(self, client, exchange, queue, binding):
        log.debug("AMQPTransport.bind_impl(%s): EX %s, Q %s, B %s", client.channel_number, exchange, queue, binding)
        self._sync_call(client, client.queue_bind, 'callback',
                                        queue=queue,
                                        exchange=exchange,
                                        routing_key=binding)

    def unbind_impl(self, client, exchange, queue, binding):
        log.debug("AMQPTransport.unbind_impl(%s): EX %s, Q %s, B %s", client.channel_number, exchange, queue, binding)
        self._sync_call(client, client.queue_unbind, 'callback', queue=queue,
                                                     exchange=exchange,
                                                     routing_key=binding)

    def ack_impl(self, client, delivery_tag):
        """
        Acks a message.
        """
        client.basic_ack(delivery_tag)

    def reject_impl(self, client, delivery_tag, requeue=False):
        """
        Rejects a message.
        """
        client.basic_reject(delivery_tag, requeue=requeue)

    def start_consume_impl(self, client, callback, queue, no_ack=False, exclusive=False):
        """
        Starts consuming on a queue.
        Will asynchronously deliver messages to the callback method supplied.

        @return A consumer tag to be used when stop_consume_impl is called.
        """
        log.debug("AMQPTransport.start_consume_impl(%s): %s", client.channel_number, queue)
        consumer_tag = client.basic_consume(callback,
                                            queue=queue,
                                            no_ack=no_ack,
                                            exclusive=exclusive)
        return consumer_tag

    def stop_consume_impl(self, client, consumer_tag):
        """
        Stops consuming by consumer tag.
        """
        log.debug("AMQPTransport.stop_consume_impl(%s): %s", client.channel_number, consumer_tag)
        self._sync_call(client, client.basic_cancel, 'callback', consumer_tag)

    def setup_listener(self, binding, default_cb):
        """
        Calls setup listener via the default callback passed in.
        """
        return default_cb(self, binding)

    def get_stats_impl(self, client, queue):
        """
        Gets a tuple of number of messages, number of consumers on a queue.
        """
        log.debug("AMQPTransport.get_stats_impl(%s): Q %s", client.channel_number, queue)
        frame = self._sync_call(client, client.queue_declare, 'callback',
                                        queue=queue or '',
                                        passive=True)
        return frame.method.message_count, frame.method.consumer_count

    def purge_impl(self, client, queue):
        """
        Purges a queue.
        """
        log.debug("AMQPTransport.purge_impl(%s): Q %s", client.channel_number, queue)
        self._sync_call(client, client.queue_purge, 'callback', queue=queue)

    def qos_impl(self, client, prefetch_size=0, prefetch_count=0, global_=False):
        """
        Adjusts quality of service for a channel.
        """
        log.debug("AMQPTransport.qos_impl(%s): pf_size %s, pf_count %s, global_ %s", client.channel_number, prefetch_size, prefetch_count, global_)
        self._sync_call(client, client.basic_qos, 'callback', prefetch_size=prefetch_size, prefetch_count=prefetch_count, global_=global_)

    def publish_impl(self, client, exchange, routing_key, body, properties, immediate=False, mandatory=False):
        """
        Publishes a message on an exchange.
        """
        client.basic_publish(exchange=exchange, #todo
                             routing_key=routing_key, #todo
                             body=body,
                             properties=properties,
                             immediate=immediate, #todo
                             mandatory=mandatory) #todo

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


class LocalBroker(object):

    def __init__(self):
        self._exchanges = {}
        self._queues = {}
        self._binds = []        # list of tuples: exchange, queue, routing_key, who to call


        self._lock = coros.RLock()

    def incoming(self, exchange, routing_key, body, properties, immediate=False, mandatory=False):

        def binding_key_matches(bkey, rkey):
            return bkey == rkey # @TODO expand obv

        # find all matching calls
        matching_binds = [x for x in self._binds if x[0] == exchange and binding_key_matches(x[2], routing_key)]

        # make calls
        for bind in matching_binds:
            try:
                method_frame = DotDict()
                header_frame = DotDict()
                bind[3](self, method_frame, header_frame, body)
            except Exception as ex:
                log.exception("Error in local message routing, continuing")

        return True

    def declare_exchange(self, exchange, exchange_type='topic', durable=False, auto_delete=True):
        if exchange in self._exchanges:
            exrec = self._exchanges[exchange]

            assert exrec['type'] == exchange_type and exrec['durable'] == durable and exrec['auto_delete'] == auto_delete

        else:
            assert exchange_type == 'topic', "Topic only supported"

            self._exchanges[exchange] = { 'exchange': exchange,
                                          'type' : exchange_type,
                                          'durable' : durable,
                                          'auto_delete' : auto_delete }

        return True





class LocalTransport(BaseTransport):

    def __init__(self, broker):
        self._broker = broker

    def publish_impl(self, client, exchange, routing_key, body, properties, immediate=False, mandatory=False):
        return self._broker.incoming(exchange, routing_key, body, properties, immediate=immediate, mandatory=mandatory)

    def declare_exchange_impl(self, client, exchange, exchange_type='topic', durable=False, auto_delete=True):
        return self._broker.declare_exchange(exchange, exchange_type=exchange_type, durable=durable, auto_delete=auto_delete)



