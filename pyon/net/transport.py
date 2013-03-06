#!/usr/bin/env python

"""
Transport layer abstractions

TODOS:
- split listen() into two subcalls (for StreamSubscriber)
"""

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.log import log
from pyon.util.containers import DotDict
from gevent.event import AsyncResult, Event
from gevent.queue import Queue
from gevent import coros, sleep
from gevent.timeout import Timeout
from gevent.pool import Pool
from contextlib import contextmanager
import os
from pika import BasicProperties
from pyon.util.async import spawn
from pyon.util.pool import IDPool
from uuid import uuid4
from collections import defaultdict


class TransportError(StandardError):
    pass


class BaseTransport(object):
    def declare_exchange_impl(self, exchange, **kwargs):
        raise NotImplementedError()

    def delete_exchange_impl(self, exchange, **kwargs):
        raise NotImplementedError()

    def declare_queue_impl(self, queue, **kwargs):
        raise NotImplementedError()

    def delete_queue_impl(self, queue, **kwargs):
        raise NotImplementedError()

    def bind_impl(self, exchange, queue, binding):
        raise NotImplementedError()

    def unbind_impl(self, exchange, queue, binding):
        raise NotImplementedError()

    def ack_impl(self, delivery_tag):
        raise NotImplementedError()

    def reject_impl(self, delivery_tag, requeue=False):
        raise NotImplementedError()

    def start_consume_impl(self, callback, queue, no_ack=False, exclusive=False):
        raise NotImplementedError()

    def stop_consume_impl(self, consumer_tag):
        raise NotImplementedError()

    def setup_listener(self, binding, default_cb):
        raise NotImplementedError()

    def get_stats_impl(self, queue):
        raise NotImplementedError()

    def purge_impl(self, queue):
        raise NotImplementedError()

    def qos_impl(self, prefetch_size=0, prefetch_count=0, global_=False):
        raise NotImplementedError()

    def publish_impl(self, exchange, routing_key, body, properties, immediate=False, mandatory=False, durable_msg=False):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    @property
    def channel_number(self):
        raise NotImplementedError()

    @property
    def active(self):
        raise NotImplementedError()

    def add_on_close_callback(self, cb):
        raise NotImplementedError()


class ComposableTransport(BaseTransport):
    """
    A Transport that has its methods composed of two or more transports.

    This is used for ExchangeObjects, where we want to compose the container's ex_manager authoritative
    transport with a self transport unique to the XO, needed for the following methods:
        - ack_impl
        - reject_impl
        - start_consume_impl
        - stop_consume_impl
        - qos_impl
        - get_stats_impl
        - publish_impl      (solely for publish rates, not needed for identity in protocol)
    """
    common_methods = ['ack_impl',
                      'reject_impl',
                      'start_consume_impl',
                      'stop_consume_impl',
                      'qos_impl',
                      'get_stats_impl',
                      'publish_impl']

    def __init__(self, left, right, *methods):
        self._transports = [left]

        log.debug("ComposableTransport.__init__(%s) %s %s", self.channel_number, type(left), left)

        self._methods = { 'declare_exchange_impl': left.declare_exchange_impl,
                          'delete_exchange_impl' : left.delete_exchange_impl,
                          'declare_queue_impl'   : left.declare_queue_impl,
                          'delete_queue_impl'    : left.delete_queue_impl,
                          'bind_impl'            : left.bind_impl,
                          'unbind_impl'          : left.unbind_impl,
                          'ack_impl'             : left.ack_impl,
                          'reject_impl'          : left.reject_impl,
                          'start_consume_impl'   : left.start_consume_impl,
                          'stop_consume_impl'    : left.stop_consume_impl,
                          'setup_listener'       : left.setup_listener,
                          'get_stats_impl'       : left.get_stats_impl,
                          'purge_impl'           : left.purge_impl,
                          'qos_impl'             : left.qos_impl,
                          'publish_impl'         : left.publish_impl, }

        if right is not None:
            self.overlay(right, *methods)
        self._close_callbacks = []

    def overlay(self, transport, *methods):
        for m in methods:
            self._methods[m] = getattr(transport, m)

        log.debug("ComposableTransport.overlay(%s) %s %s (%s)", self.channel_number, type(transport), transport, transport.channel_number)

        self._transports.append(transport)

    def declare_exchange_impl(self, exchange, **kwargs):
        m = self._methods['declare_exchange_impl']
        return m(exchange, **kwargs)

    def delete_exchange_impl(self, exchange, **kwargs):
        m = self._methods['delete_exchange_impl']
        return m(exchange, **kwargs)

    def declare_queue_impl(self, queue, **kwargs):
        m = self._methods['declare_queue_impl']
        return m(queue, **kwargs)

    def delete_queue_impl(self, queue, **kwargs):
        m = self._methods['delete_queue_impl']
        return m(queue, **kwargs)

    def bind_impl(self, exchange, queue, binding):
        m = self._methods['bind_impl']
        return m(exchange, queue, binding)

    def unbind_impl(self, exchange, queue, binding):
        m = self._methods['unbind_impl']
        return m(exchange, queue, binding)

    def ack_impl(self, delivery_tag):
        m = self._methods['ack_impl']
        return m(delivery_tag)

    def reject_impl(self, delivery_tag, requeue=False):
        m = self._methods['reject_impl']
        return m(delivery_tag, requeue=requeue)

    def start_consume_impl(self, callback, queue, no_ack=False, exclusive=False):
        m = self._methods['start_consume_impl']
        return m(callback, queue, no_ack=no_ack, exclusive=exclusive)

    def stop_consume_impl(self, consumer_tag):
        m = self._methods['stop_consume_impl']
        return m(consumer_tag)

    def setup_listener(self, binding, default_cb):
        m = self._methods['setup_listener']
        return m(binding, default_cb)

    def get_stats_impl(self, queue):
        m = self._methods['get_stats_impl']
        return m(queue)

    def purge_impl(self, queue):
        m = self._methods['purge_impl']
        return m(queue)

    def qos_impl(self, prefetch_size=0, prefetch_count=0, global_=False):
        m = self._methods['qos_impl']
        return m(prefetch_size=prefetch_size, prefetch_count=prefetch_count, global_=global_)

    def publish_impl(self, exchange, routing_key, body, properties, immediate=False, mandatory=False, durable_msg=False):
        m = self._methods['publish_impl']
        return m(exchange, routing_key, body, properties, immediate=immediate, mandatory=mandatory, durable_msg=durable_msg)

    def close(self):
        for t in self._transports:
            t.close()

        for cb in self._close_callbacks:
            cb(self, 200, "Closed OK")    # @TODO where to get real value

    @property
    def channel_number(self):
        return self._transports[-1].channel_number

    def add_on_close_callback(self, cb):
        self._close_callbacks.append(cb)

    @property
    def active(self):
        return all(map(lambda x: x.active, self._transports))


class AMQPTransport(BaseTransport):
    """
    A transport adapter around a Pika channel.
    """

    def __init__(self, amq_chan):
        """
        Creates an AMQPTransport, bound to an underlying Pika channel.
        """
        #log.info("AMQPTransport(%d)", amq_chan.channel_number)
        self._client = amq_chan
        self._client.add_on_close_callback(self._on_underlying_close)

        self._close_callbacks = []
        self.lock = False

    def _on_underlying_close(self, code, text):
        logmeth = log.debug
        if not (code == 0 or code == 200):
            logmeth = log.error
        logmeth("AMQPTransport.underlying closed:\n\tchannel number: %s\n\tcode: %d\n\ttext: %s", self.channel_number, code, text)

        # PIKA BUG: in v0.9.5, this amq_chan instance will be left around in the callbacks
        # manager, and trips a bug in the handler for on_basic_deliver. We attempt to clean
        # up for Pika here so we don't goof up when reusing a channel number.

        # this appears to be fixed in 3050d116899aced2392def2e3e66ca30c93334ac
        # https://github.com/pika/pika/commit/e93c7ebae2c57b798977ba2992602310deb4758b
        self._client.callbacks.remove(self._client.channel_number, 'Basic.GetEmpty')
        self._client.callbacks.remove(self._client.channel_number, 'Channel.Close')
        self._client.callbacks.remove(self._client.channel_number, '_on_basic_deliver')
        self._client.callbacks.remove(self._client.channel_number, '_on_basic_get')

        # uncomment these lines to see the full callback list that Pika maintains
        #stro = pprint.pformat(callbacks._callbacks)
        #log.error(str(stro))

        for cb in self._close_callbacks:
            cb(self, code, text)

    @property
    def active(self):
        if self._client is not None:
            if self._client.closing is None:
                return True

        return False

    def close(self):

        if self.lock:
            return

        self._client.close()

    @property
    def channel_number(self):
        return self._client.channel_number

    def add_on_close_callback(self, cb):
        self._close_callbacks.append(cb)

    @contextmanager
    def _push_close_cb(self, callback):
        self._client.add_on_close_callback(callback)
        try:
            yield callback
        finally:
            # PIKA BUG: v0.9.5, we need to specify the callback as a dict - this is fixed in git HEAD (13 Feb 2012)
            de = {'handle': callback, 'one_shot': True}
            self._client.callbacks.remove(self._client.channel_number, '_on_channel_close', de)

    def _sync_call(self, func, cb_arg, *args, **kwargs):
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
        with self._push_close_cb(eb):
            func(*args, **kwargs)
            ret_vals = ar.get(timeout=10)

        if isinstance(ret_vals, TransportError):

            # mark this channel as poison, do not use again!
            # don't test for type here, we don't want to have to import PyonSelectConnection
            if hasattr(self._client.transport, 'connection') and hasattr(self._client.transport.connection, 'mark_bad_channel'):
                self._client.transport.connection.mark_bad_channel(self._client.channel_number)
            else:
                log.warn("Could not mark channel # (%s) as bad, Pika could be corrupt", self._client.channel_number)

            raise ret_vals

        if len(ret_vals) == 0:
            return None
        elif len(ret_vals) == 1:
            return ret_vals[0]
        return tuple(ret_vals)

    def declare_exchange_impl(self, exchange, exchange_type='topic', durable=False, auto_delete=True):
        log.debug("AMQPTransport.declare_exchange_impl(%s): %s, T %s, D %s, AD %s", self._client.channel_number, exchange, exchange_type, durable, auto_delete)
        arguments = {}

        if os.environ.get('QUEUE_BLAME', None) is not None:
            testid = os.environ['QUEUE_BLAME']
            arguments.update({'created-by': testid})

        self._sync_call(self._client.exchange_declare, 'callback',
                                             exchange=exchange,
                                             type=exchange_type,
                                             durable=durable,
                                             auto_delete=auto_delete,
                                             arguments=arguments)

    def delete_exchange_impl(self, exchange, **kwargs):
        log.debug("AMQPTransport.delete_exchange_impl(%s): %s", self._client.channel_number, exchange)
        self._sync_call(self._client.exchange_delete, 'callback', exchange=exchange)

    def declare_queue_impl(self, queue, durable=False, auto_delete=True):
        log.debug("AMQPTransport.declare_queue_impl(%s): %s, D %s, AD %s", self._client.channel_number, queue, durable, auto_delete)
        arguments = {}

        if os.environ.get('QUEUE_BLAME', None) is not None:
            testid = os.environ['QUEUE_BLAME']
            arguments.update({'created-by': testid})

        frame = self._sync_call(self._client.queue_declare, 'callback',
                                queue=queue or '',
                                auto_delete=auto_delete,
                                durable=durable,
                                arguments=arguments)

        return frame.method.queue

    def delete_queue_impl(self, queue, **kwargs):
        log.debug("AMQPTransport.delete_queue_impl(%s): %s", self._client.channel_number, queue)
        self._sync_call(self._client.queue_delete, 'callback', queue=queue)

    def bind_impl(self, exchange, queue, binding):
        log.debug("AMQPTransport.bind_impl(%s): EX %s, Q %s, B %s", self._client.channel_number, exchange, queue, binding)
        self._sync_call(self._client.queue_bind, 'callback',
                                        queue=queue,
                                        exchange=exchange,
                                        routing_key=binding)

    def unbind_impl(self, exchange, queue, binding):
        log.debug("AMQPTransport.unbind_impl(%s): EX %s, Q %s, B %s", self._client.channel_number, exchange, queue, binding)
        self._sync_call(self._client.queue_unbind, 'callback', queue=queue,
                                                     exchange=exchange,
                                                     routing_key=binding)

    def ack_impl(self, delivery_tag):
        """
        Acks a message.
        """
        log.debug("AMQPTransport.ack(%s): %s", self._client.channel_number, delivery_tag)
        self._client.basic_ack(delivery_tag)

    def reject_impl(self, delivery_tag, requeue=False):
        """
        Rejects a message.
        """
        self._client.basic_reject(delivery_tag, requeue=requeue)

    def start_consume_impl(self, callback, queue, no_ack=False, exclusive=False):
        """
        Starts consuming on a queue.
        Will asynchronously deliver messages to the callback method supplied.

        @return A consumer tag to be used when stop_consume_impl is called.
        """
        log.debug("AMQPTransport.start_consume_impl(%s): %s", self._client.channel_number, queue)
        consumer_tag = self._client.basic_consume(callback,
                                            queue=queue,
                                            no_ack=no_ack,
                                            exclusive=exclusive)
        return consumer_tag

    def stop_consume_impl(self, consumer_tag):
        """
        Stops consuming by consumer tag.
        """
        log.debug("AMQPTransport.stop_consume_impl(%s): %s", self._client.channel_number, consumer_tag)
        self._sync_call(self._client.basic_cancel, 'callback', consumer_tag)

        # PIKA 0.9.5 / GEVENT interaction problem here
        # we get called back too early, the basic_cancel hasn't really finished processing yet. we need
        # to wait until our consumer tag is removed from the pika channel's consumers dict.
        # See: https://gist.github.com/3751870

        attempts = 5
        while attempts > 0:
            if consumer_tag not in self._client._consumers:
                break
            else:
                log.debug("stop_consume_impl waiting for ctag to be removed from consumers, attempts rem: %s", attempts)

            attempts -= 1
            sleep(1)

        if consumer_tag in self._client._consumers:
            raise TransportError("stop_consume_impl did not complete in the expected amount of time, transport may be compromised")

    def setup_listener(self, binding, default_cb):
        """
        Calls setup listener via the default callback passed in.
        """
        return default_cb(self, binding)

    def get_stats_impl(self, queue):
        """
        Gets a tuple of number of messages, number of consumers on a queue.
        """
        log.debug("AMQPTransport.get_stats_impl(%s): Q %s", self._client.channel_number, queue)
        frame = self._sync_call(self._client.queue_declare, 'callback',
                                        queue=queue or '',
                                        passive=True)
        return frame.method.message_count, frame.method.consumer_count

    def purge_impl(self, queue):
        """
        Purges a queue.
        """
        log.debug("AMQPTransport.purge_impl(%s): Q %s", self._client.channel_number, queue)
        self._sync_call(self._client.queue_purge, 'callback', queue=queue)

    def qos_impl(self, prefetch_size=0, prefetch_count=0, global_=False):
        """
        Adjusts quality of service for a channel.
        """
        log.debug("AMQPTransport.qos_impl(%s): pf_size %s, pf_count %s, global_ %s", self._client.channel_number, prefetch_size, prefetch_count, global_)
        self._sync_call(self._client.basic_qos, 'callback', prefetch_size=prefetch_size, prefetch_count=prefetch_count, global_=global_)

    def publish_impl(self, exchange, routing_key, body, properties, immediate=False, mandatory=False, durable_msg=False):
        """
        Publishes a message on an exchange.
        """
        log.debug("AMQPTransport.publish(%s): ex %s key %s", self._client.channel_number, exchange, routing_key)

        if durable_msg:
            delivery_mode = 2
        else:
            delivery_mode = None

        props = BasicProperties(headers=properties,
                                delivery_mode=delivery_mode)

        self._client.basic_publish(exchange=exchange,       # todo
                                   routing_key=routing_key, # todo
                                   body=body,
                                   properties=props,
                                   immediate=immediate,     # todo
                                   mandatory=mandatory)     # todo


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
            self._exchange, self._queue, self._binding = list(exchange) + ([None] * (3 - len(exchange)))
        elif isinstance(queue, tuple):
            self._exchange, self._queue, self._binding = list(queue) + ([None] * (3 - len(queue)))
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


class TopicTrie(object):
    """
    Support class for building a routing device to do amqp-like pattern matching.

    Used for events/pubsub in our system with the local transport. Efficiently stores all registered
    subscription topic trees in a trie structure, handling wildcards * and #.

    See:
        http://www.zeromq.org/whitepapers:message-matching      (doesn't handle # so scrapped)
        http://www.rabbitmq.com/blog/2010/09/14/very-fast-and-scalable-topic-routing-part-1/
        http://www.rabbitmq.com/blog/2011/03/28/very-fast-and-scalable-topic-routing-part-2/
    """

    class Node(object):
        """
        Internal node of a trie.

        Stores two data points: a token (literal string, '*', or '#', or None if used as root element),
                                and a set of "patterns" aka a ref to an object representing a bind.
        """
        def __init__(self, token, patterns=None):
            self.token = token
            self.patterns = patterns or []
            self.children = {}

        def get_or_create_child(self, token):
            """
            Returns a child node with the given token.

            If it doesn't already exist, it is created, otherwise the existing one is returned.
            """
            if token in self.children:
                return self.children[token]

            new_node = TopicTrie.Node(token)
            self.children[token] = new_node

            return new_node

        def get_all_matches(self, topics):
            """
            Given a list of topic tokens, returns all patterns stored in child nodes/self that match the topic tokens.

            This is a depth-first search pruned by token, with special handling for both wildcard types.
            """
            results = []

            if len(topics) == 0:
                # terminal point, return any pattern we have here
                return self.patterns

            cur_token = topics[0]
            rem_tokens = topics[1:]     # will always be a list, even if empty or 1-len
            #log.debug('get_all_matches(%s): cur_token %s, rem_tokens %s', self.token, cur_token, rem_tokens)

            # child node direct matching
            if cur_token in self.children:
                results.extend(self.children[cur_token].get_all_matches(rem_tokens))

            # now '*' wildcard
            if '*' in self.children:
                results.extend(self.children['*'].get_all_matches(rem_tokens))

            # '#' means any number of tokens - naive method of descent, we'll feed it nothing to start. Then chop the full
            # topics all the way down, put the results in a set to remove duplicates, and also any patterns on self.
            if '#' in self.children:
                # keep popping off and descend, make a set out of results
                all_wild_childs = set()
                for i in xrange(len(topics)):
                    res = self.children['#'].get_all_matches(topics[i:])
                    map(all_wild_childs.add, res)

                results.extend(all_wild_childs)
                results.extend(self.children['#'].patterns)     # any patterns defined in # are legal too

            return results

    def __init__(self):
        """
        Creates a dummy root node that all topic trees hang off of.
        """
        self.root = self.Node(None)

    def add_topic_tree(self, topic_tree, pattern):
        """
        Splits a string topic_tree into tokens (by .) and recursively adds them to the trie.

        Adds the pattern at the terminal node for later retrieval.
        """
        topics = topic_tree.split(".")

        curnode = self.root

        for topic in topics:
            curnode = curnode.get_or_create_child(topic)

        if not pattern in curnode.patterns:
            curnode.patterns.append(pattern)

    def remove_topic_tree(self, topic_tree, pattern):
        """
        Splits a string topic_tree into tokens (by .) and removes the pattern from the terminal node.

        @TODO should remove empty nodes
        """
        topics = topic_tree.split(".")

        curnode = self.root

        for topic in topics:
            curnode = curnode.get_or_create_child(topic)

        if pattern in curnode.patterns:
            curnode.patterns.remove(pattern)

    def get_all_matches(self, topic_tree):
        """
        Returns a list of all matches for a given topic tree string.

        Creates a set out of the matching patterns, so multiple binds matching on the same pattern only
        return once.
        """
        topics = topic_tree.split(".")
        return set(self.root.get_all_matches(topics))

class LocalRouter(object):
    """
    A RabbitMQ-like routing device implemented with gevent mechanisms for an in-memory broker.

    Using LocalTransport, can handle topic-exchange-like communication in ION within the context
    of a single container.
    """

    class ConsumerClosedMessage(object):
        """
        Dummy object used to exit queue get looping greenlets.
        """
        pass

    def __init__(self, sysname):
        self._sysname = sysname
        self.ready = Event()

        # exchange/queues/bindings
        self._exchanges = {}                            # names -> { subscriber, topictrie(queue name) }
        self._queues = {}                               # names -> gevent queue
        self._bindings_by_queue = defaultdict(list)     # queue name -> [(ex, binding)]
        self._lock_declarables = coros.RLock()          # exchanges, queues, bindings, routing method

        # consumers
        self._consumers = defaultdict(list)             # queue name -> [ctag, channel._on_deliver]
        self._consumers_by_ctag = {}                    # ctag -> queue_name ??
        self._ctag_pool = IDPool()                      # pool of consumer tags
        self._lock_consumers = coros.RLock()            # lock for interacting with any consumer related attrs

        # deliveries
        self._unacked = {}                              # dtag -> (ctag, msg)
        self._lock_unacked = coros.RLock()              # lock for interacting with unacked field

        self._gl_msgs = None
        self._gl_pool = Pool()
        self.gl_ioloop = None

        self.errors = []

    @property
    def _connect_addr(self):
        return "inproc://%s" % self._sysname

    def start(self):
        """
        Starts all internal greenlets of this router device.
        """
        self._queue_incoming = Queue()
        self._gl_msgs = self._gl_pool.spawn(self._run_gl_msgs)
        self._gl_msgs.link_exception(self._child_failed)

        self.gl_ioloop = spawn(self._run_ioloop)

    def stop(self):
        self._gl_msgs.kill()    # @TODO: better
        self._gl_pool.join(timeout=5, raise_error=True)

    def _run_gl_msgs(self):
        self.ready.set()
        while True:
            ex, rkey, body, props = self._queue_incoming.get()
            try:
                with self._lock_declarables:
                    self._route(ex, rkey, body, props)
            except Exception as e:
                self.errors.append(e)
                log.exception("Routing message")

    def _route(self, exchange, routing_key, body, props):
        """
        Delivers incoming messages into queues based on known routes.

        This entire method runs in a lock (likely pretty slow).
        """
        assert exchange in self._exchanges, "Unknown exchange %s" % exchange

        queues = self._exchanges[exchange].get_all_matches(routing_key)
        log.debug("route: ex %s, rkey %s,  matched %s routes", exchange, routing_key, len(queues))

        # deliver to each queue
        for q in queues:
            assert q in self._queues
            log.debug("deliver -> %s", q)
            self._queues[q].put((exchange, routing_key, body, props))

    def _child_failed(self, gproc):
        """
        Handler method for when any child worker thread dies with error.

        Aborts the "ioloop" greenlet.
        """
        log.error("Child (%s) failed with an exception: %s", gproc, gproc.exception)

        if self.gl_ioloop:
            self.gl_ioloop.kill(exception=gproc.exception, block=False)

    def _run_ioloop(self):
        """
        An "IOLoop"-like greenlet - sits and waits until the pool is finished.

        Fits with the AMQP node.
        """
        self._gl_pool.join()

    def publish(self, exchange, routing_key, body, properties, immediate=False, mandatory=False):
        self._queue_incoming.put((exchange, routing_key, body, properties))
        sleep(0.0001)      # really wish switch would work instead of a sleep, seems wrong

    def declare_exchange(self, exchange, **kwargs):
        with self._lock_declarables:
            if not exchange in self._exchanges:
                self._exchanges[exchange] = TopicTrie()

    def delete_exchange(self, exchange, **kwargs):
        with self._lock_declarables:
            if exchange in self._exchanges:
                del self._exchanges[exchange]

    def declare_queue(self, queue, **kwargs):

        with self._lock_declarables:
            # come up with new queue name if none specified
            if queue is None or queue == '':
                while True:
                    proposed = "q-%s" % str(uuid4())[0:10]
                    if proposed not in self._queues:
                        queue = proposed
                        break

            if not queue in self._queues:
                self._queues[queue] = Queue()

            return queue

    def delete_queue(self, queue, **kwargs):
        with self._lock_declarables:
            if queue in self._queues:
                del self._queues[queue]

                # kill bindings
                for ex, binding in self._bindings_by_queue[queue]:
                    if ex in self._exchanges:
                        self._exchanges[ex].remove_topic_tree(binding, queue)

                self._bindings_by_queue.pop(queue)

    def bind(self, exchange, queue, binding):
        log.info("Bind: ex %s, q %s, b %s", exchange, queue, binding)
        with self._lock_declarables:
            assert exchange in self._exchanges, "Missing exchange %s in list of exchanges" % str(exchange)
            assert queue in self._queues

            tt = self._exchanges[exchange]

            tt.add_topic_tree(binding, queue)
            self._bindings_by_queue[queue].append((exchange, binding))

    def unbind(self, exchange, queue, binding):
        with self._lock_declarables:
            assert exchange in self._exchanges
            assert queue in self._queues

            self._exchanges[exchange].remove_topic_tree(binding, queue)
            for i, val in enumerate(self._bindings_by_queue[queue]):
                ex, b = val
                if ex == exchange and b == binding:
                    self._bindings_by_queue[queue].pop(i)
                    break

    def start_consume(self, callback, queue, no_ack=False, exclusive=False):
        assert queue in self._queues

        with self._lock_consumers:
            new_ctag = self._generate_ctag()
            assert new_ctag not in self._consumers_by_ctag

            with self._lock_declarables:
                gl = self._gl_pool.spawn(self._run_consumer, new_ctag, queue, self._queues[queue], callback)
                gl.link_exception(self._child_failed)
            self._consumers[queue].append((new_ctag, callback, no_ack, exclusive, gl))
            self._consumers_by_ctag[new_ctag] = queue

            return new_ctag

    def stop_consume(self, consumer_tag):
        assert consumer_tag in self._consumers_by_ctag

        with self._lock_consumers:
            queue = self._consumers_by_ctag[consumer_tag]
            self._consumers_by_ctag.pop(consumer_tag)

            for i, consumer in enumerate(self._consumers[queue]):
                if consumer[0] == consumer_tag:

                    # notify consumer greenlet that we want to stop
                    if queue in self._queues:
                        self._queues[queue].put(self.ConsumerClosedMessage())
                    consumer[4].join(timeout=5)
                    consumer[4].kill()

                    # @TODO reject any unacked messages

                    self._consumers[queue].pop(i)
                    break

            self._return_ctag(consumer_tag)

    def _run_consumer(self, ctag, queue_name, gqueue, callback):
        cnt = 0
        while True:
            m = gqueue.get()
            if isinstance(m, self.ConsumerClosedMessage):
                break
            exchange, routing_key, body, props = m

            # create method frame
            method_frame = DotDict()
            method_frame['consumer_tag']    = ctag
            method_frame['redelivered']     = False     # @TODO
            method_frame['exchange']        = exchange
            method_frame['routing_key']     = routing_key

            # create header frame
            header_frame = DotDict()
            header_frame['headers'] = props.copy()

            # make delivery tag for ack/reject later
            dtag = self._generate_dtag(ctag, cnt)
            cnt += 1

            with self._lock_unacked:
                self._unacked[dtag] = (ctag, queue_name, m)

            method_frame['delivery_tag'] = dtag

            # deliver to callback
            try:
                callback(self, method_frame, header_frame, body)
            except Exception:
                log.exception("delivering to consumer, ignore!")

    def _generate_ctag(self):
        return "zctag-%s" % self._ctag_pool.get_id()

    def _return_ctag(self, ctag):
        self._ctag_pool.release_id(int(ctag.split("-")[-1]))

    def _generate_dtag(self, ctag, cnt):
        """
        Generates a unique delivery tag for each consumer.

        Greenlet-safe, no need to lock.
        """
        return "%s-%s" % (ctag, cnt)

    def ack(self, delivery_tag):
        assert delivery_tag in self._unacked

        with self._lock_unacked:
            del self._unacked[delivery_tag]

    def reject(self, delivery_tag, requeue=False):
        assert delivery_tag in self._unacked

        with self._lock_unacked:
            _, queue, m = self._unacked.pop(delivery_tag)
            if requeue:
                log.warn("REQUEUE: EXPERIMENTAL %s", delivery_tag)
                self._queues[queue].put(m)

    def transport_close(self, transport):
        log.warn("LocalRouter.transport_close: %s TODO", transport)
        # @TODO reject all messages in unacked spot

        # turn off any consumers from this transport

    def get_stats(self, queue):
        """
        Returns a 2-tuple of (# msgs, # consumers) on a given queue.
        """
        assert queue in self._queues

        consumers = 0
        if queue in self._consumers:
            consumers = len(self._consumers[queue])

        # the queue qsize gives you number of undelivered messages, which i think is what AMQP does too
        return (self._queues[queue].qsize(), consumers)

    def purge(self, queue):
        """
        Deletes all contents of a queue.

        @TODO could end up in a race with an infinite producer
        """
        assert queue in self._queues

        with Timeout(5):
            while not self._queues[queue].empty():
                self._queues[queue].get_nowait()

class LocalTransport(BaseTransport):
    def __init__(self, broker, ch_number):
        self._broker = broker
        self._ch_number = ch_number

        self._active = True

        self._close_callbacks = []

    def declare_exchange_impl(self, exchange, **kwargs):
        self._broker.declare_exchange(exchange, **kwargs)

    def delete_exchange_impl(self, exchange, **kwargs):
        self._broker.delete_exchange(exchange, **kwargs)

    def declare_queue_impl(self, queue, **kwargs):
        return self._broker.declare_queue(queue, **kwargs)

    def delete_queue_impl(self, queue, **kwargs):
        self._broker.delete_queue(queue, **kwargs)

    def bind_impl(self, exchange, queue, binding):
        self._broker.bind(exchange, queue, binding)

    def unbind_impl(self, exchange, queue, binding):
        self._broker.unbind(exchange, queue, binding)

    def publish_impl(self, exchange, routing_key, body, properties, immediate=False, mandatory=False, durable_msg=False):
        self._broker.publish(exchange, routing_key, body, properties, immediate=immediate, mandatory=mandatory)

    def start_consume_impl(self, callback, queue, no_ack=False, exclusive=False):
        return self._broker.start_consume(callback, queue, no_ack=no_ack, exclusive=exclusive)

    def stop_consume_impl(self, consumer_tag):
        self._broker.stop_consume(consumer_tag)

    def ack_impl(self, delivery_tag):
        self._broker.ack(delivery_tag)

    def reject_impl(self, delivery_tag, requeue=False):
        self._broker.reject(delivery_tag, requeue=requeue)

    def close(self):
        self._broker.transport_close(self)
        self._active = False

        for cb in self._close_callbacks:
            cb(self, 200, "Closed ok")         # @TODO should come elsewhere

    def add_on_close_callback(self, cb):
        self._close_callbacks.append(cb)

    @property
    def active(self):
        return self._active

    @property
    def channel_number(self):
        return self._ch_number

    def qos_impl(self, prefetch_size=0, prefetch_count=0, global_=False):
        log.info("TODO: QOS")

    def get_stats_impl(self, queue):
        return self._broker.get_stats(queue)

    def purge_impl(self, queue):
        return self._broker.purge(queue)

