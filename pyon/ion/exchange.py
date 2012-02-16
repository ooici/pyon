#!/usr/bin/env python

"""Exchange management classes."""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.net import messaging
from pyon.util.log import log
from pyon.core import bootstrap
from pyon.util.async import blocking_cb
from pyon.net.transport import BaseTransport, NamePair, AMQPTransport

ION_URN_PREFIX = "urn:ionx"

ION_ROOT_XS = "ioncore"

def valid_xname(name):
    return name and str(name).find(":") == -1 and str(name).find(" ") == -1

class ExchangeManager(object):
    """
    Manager object for the CC to manage Exchange related resources.
    """
    def __init__(self, container):
        log.debug("ExchangeManager initializing ...")
        self.container = container

        # Define the callables that can be added to Container public API
        self.container_api = [self.create_xs,
                              self.create_xp,
                              self.create_xn]

        # Add the public callables to Container
        for call in self.container_api:
            setattr(self.container, call.__name__, call)

        self.xs_by_name = {}
        self.default_xs = ExchangeSpace(self, ION_ROOT_XS)

        self._chan = None

        # TODO: Do more initializing here, not in container

    def start(self):
        log.debug("ExchangeManager starting ...")

        # Establish connection to broker
        # @TODO: raise error if sux
        node, ioloop = messaging.make_node()

        self._transport = AMQPTransport.get_instance()
        self._client    = self._get_channel(node)

        # Declare root exchange
        #self.default_xs.ensure_exists(self._get_channel())
        return node, ioloop

    def _get_channel(self, node):
        """
        Get a raw channel to be used by all the ensure_exists methods.
        """
        assert self.container

        # @TODO: needs lock, but so do all these methods
        if not self._chan:
            self._chan = blocking_cb(node.client.channel, 'on_open_callback')

        return self._chan

    def create_xs(self, name, exchange_type='topic', durable=False, auto_delete=True):
        log.debug("ExchangeManager.create_xs: %s", name)
        xs = ExchangeSpace(self, name, exchange_type=exchange_type, durable=durable, auto_delete=auto_delete)
        xs.declare()

        return xs

    def delete_xs(self, xs):
        """
        @type xs    ExchangeSpace
        """
        log.debug("ExchangeManager.delete_xs: %s", xs)
        xs.delete()

    def create_xp(self, xs, name, xptype):
        log.debug("ExchangeManager.create_xp: name=%s, xptype=%s", name, xptype)
        xp = ExchangePoint(self, xs, name, xptype)
        xp.declare()

        return xp

    def delete_xp(self, xp):
        log.debug("ExchangeManager.delete_xp: name=%s", xp.build_xname())
        xp.delete()

    def create_xn(self, xs, name, durable=False, auto_delete=True):
        log.debug("ExchangeManager.create_xn: name=%s, xs=%s", name, xs)
        xn = ExchangeName(self, xs, name, durable=durable, auto_delete=auto_delete)
        xn.declare()

        return xn

    def delete_xn(self, xn):
        log.debug("ExchangeManager.delete_xn: name=%s", xn.build_xlname())
        xn.delete()

    def stop(self, *args, **kwargs):
        log.debug("ExchangeManager stopping ...")

    # transport implementations - XOTransport objects call here
    def declare_exchange(self, exchange, exchange_type='topic', durable=False, auto_delete=True):
        log.info("ExchangeManager.declare_exchange")
        self._transport.declare_exchange_impl(self._client, exchange, exchange_type=exchange_type, durable=durable, auto_delete=auto_delete)
    def delete_exchange(self, exchange, **kwargs):
        log.info("ExchangeManager.delete_exchange")
        self._transport.delete_exchange_impl(self._client, exchange, **kwargs)
    def declare_queue(self, queue, durable=False, auto_delete=True):
        log.info("ExchangeManager.declare_queue")
        self._transport.declare_queue_impl(self._client, queue, durable=durable, auto_delete=auto_delete)
    def delete_queue(self, queue, **kwargs):
        log.info("ExchangeManager.delete_queue")
        self._transport.delete_queue_impl(self._client, queue, **kwargs)
    def bind(self, exchange, queue, binding):
        log.info("ExchangeManager.bind")
        self._transport.bind_impl(self._client, exchange, queue, binding)
    def unbind(self, exchange, queue, binding):
        log.info("ExchangeManager.unbind")
        self._transport.unbind_impl(self._client, exchange, queue, binding)

#
#class ExchangeSpace(object):
#    ION_DEFAULT_XS = "ioncore"
#
#    def __init__(self, name):
#        assert name, "Invalid XS name %s" % name
#        name = str(name)
#        if name.startswith(ION_URN_PREFIX):
#            name = name[len(ION_URN_PREFIX)+1:]
#        assert valid_xname(name), "Invalid XS name %s" % name
#        self.name = name
#        self.qname = self.build_qname()
#
#    def build_qname(self):
#        qname = "%s:%s:%s" % (ION_URN_PREFIX, bootstrap.sys_name, self.name)
#        return qname
#
#    def build_xname(self):
#        xname = "%s.ion.xs.%s" % (bootstrap.sys_name, self.name)
#        return xname
#
#    def ensure_exists(self, chan):
#        xname = self.build_xname()
#        log.debug("ExchangeSpace.ensure_exists() xname=%s", xname)
#
#        blocking_cb(chan.exchange_declare, 'callback', exchange=xname,
#                                                       type='topic',
#                                                       durable=False,
#                                                       auto_delete=True)
#
#        log.debug("ExchangeSpace (%s) created", xname)
#
#    def delete(self, chan):
#        xname = self.build_xname()
#        log.debug("ExchangeSpace.delete, xname: %s", xname)
#
#        blocking_cb(chan.exchange_delete, 'callback', exchange=xname)
#
#        log.debug("ExchangeSpace (%s) deleted", xname)
#
#    def __str__(self):
#        return self.name
#
#    def __repr__(self):
#        return "ExchangeSpace(%s)" % self.qname
#
#class ExchangeName(object):
#    """
#    Exchange names have the following format:
#    urn:ionx:<XS-Name>:<Name>
#    """
#    def __init__(self, name, xs=None):
#        assert name, "Invalid XS name %s" % name
#        name = str(name)
#        if name.startswith(ION_URN_PREFIX):
#            name = name[len(ION_URN_PREFIX)+1:]
#            xs, name = name.split(":")
#        assert xs, "XS not given"
#        assert valid_xname(name), "Invalid XN name %s" % name
#        self.xs = xs
#        self.name = str(name)
#        self.qname = self.build_qname()
#
#    def build_qname(self):
#        qname = "%s:%s:%s:%s" % (ION_URN_PREFIX, bootstrap.sys_name, str(self.xs), self.name)
#        return qname
#
#    def build_xlname(self):
#        xname = "%s.ion.xs.%s" % (bootstrap.sys_name, self.name)
#        return xname
#
#    def __str__(self):
#        return self.name
#
#    def __repr__(self):
#        return "ExchangeName(%s)" % self.qname
#
#class ExchangePoint(ExchangeName):
#    XPTYPES = {
#        'basic':'basic',
#        'ttree':'ttree',
#    }
#    def __init__(self, name, xs=None, xptype=None):
#        ExchangeName.__init__(self, name, xs)
#        self.xptype = xptype or 'basic'
#
#    def build_xname(self):
#        xname = "%s.xp.%s" % (self.xs.build_xname(), self.name)
#        return xname
#
#    def ensure_exists(self, chan):
#
#        xname = self.build_xname()
#        log.debug("ExchangePoint.ensure_exists, xname=%s", xname)
#
#        blocking_cb(chan.exchange_declare, 'callback', exchange=xname,
#                                                       type='topic',
#                                                       durable=False,
#                                                       auto_delete=True)
#
#        log.debug("ExchangePoint (%s) created", xname)
#
#    def delete(self, chan):
#        xname = self.build_xname()
#        log.debug("ExchangePoint.delete, xname: %s", xname)
#
#        blocking_cb(chan.exchange_delete, 'callback', exchange=xname)
#
#        log.debug("ExchangePoint (%s) deleted", xname)



class XOTransport(BaseTransport):
    def __init__(self, exchange_manager):
        self._exchange_manager = exchange_manager

    def declare_exchange_impl(self, client, exchange, **kwargs):
        return self._exchange_manager.declare_exchange(exchange, **kwargs)

    def delete_exchange_impl(self, client, exchange, **kwargs):
        return self._exchange_manager.delete_exchange(exchange, **kwargs)

    def declare_queue_impl(self, client, queue, **kwargs):
        return self._exchange_manager.declare_queue(queue, **kwargs)

    def delete_queue_impl(self, client, queue, **kwargs):
        return self._exchange_manager.delete_queue(queue, **kwargs)

    def bind_impl(self, client, exchange, queue, binding):
        return self._exchange_manager.bind(exchange, queue, binding)

    def unbind_impl(self, client, exchange, queue, binding):
        return self._exchange_manager.unbind(exchange, queue, binding)

#    # friendly versions?
#    def declare_exchange(self, exchange, **kwargs):
#        return self.declare_exchange_impl(None, exchange, **kwargs)
#
#        # etc etc

class ExchangeSpace(XOTransport, NamePair):

    ION_DEFAULT_XS = "ioncore"

    def __init__(self, exchange_manager, exchange, exchange_type='topic', durable=False, auto_delete=True):
        XOTransport.__init__(self, exchange_manager=exchange_manager)
        NamePair.__init__(self, exchange=exchange)

        self._xs_exchange_type = exchange_type
        self._xs_durable       = durable
        self._xs_auto_delete   = auto_delete

    @property
    def exchange(self):
        return "%s.ion.xs.%s" % (bootstrap.get_sys_name(), self._exchange)

    def declare(self):
        self.declare_exchange_impl(None, self.exchange,
                                         exchange_type=self._xs_exchange_type,
                                         durable=self._xs_durable,
                                         auto_delete=self._xs_auto_delete)

    def delete(self):
        self.delete_exchange_impl(None, self.exchange)

class ExchangeName(XOTransport, NamePair):
    def __init__(self, exchange_manager, xs, name, durable=False, auto_delete=True):
        XOTransport.__init__(self, exchange_manager=exchange_manager)
        NamePair.__init__(self, exchange=None, queue=name)
        self._xs = xs

        self._xn_durable        = durable
        self._xn_auto_delete    = auto_delete

    @property
    def exchange(self):
        return self._xs.exchange

    @property
    def queue(self):
        # make sure prefixed with sysname?
        queue = self._queue
        if self._queue and not self.exchange in self._queue:
            queue = ".".join([self.exchange, self._queue])

        return queue

    def declare(self):
        return self.declare_queue_impl(None, self.queue, durable=self._xn_durable, auto_delete=self._xn_auto_delete)

    def delete(self):
        self.delete_queue_impl(None, self.queue)

    def bind(self, binding_key):
        self.bind_impl(None, self.exchange, self.queue, binding_key)

    def unbind(self, binding_key):
        self.unbind_impl(None, self.exchange, self.queue, binding_key)

class ExchangePoint(ExchangeName):
    """
    @TODO is this really an ExchangeName? seems more inline with XS
    @TODO a nameable ExchangePoint - to be able to create a named queue that receives routed
            messages from the XP.
    """
    XPTYPES = {
        'basic':'basic',
        'ttree':'ttree',
        }

    def __init__(self, exchange_manager, xs, name, xptype):
        XOTransport.__init__(self, exchange_manager=exchange_manager)
        NamePair.__init__(self, exchange=name)

        self._xs = xs
        self._xptype = xptype or 'ttree'

    @property
    def exchange(self):
        return "%s.xp.%s" % (self._xs.exchange, self._exchange)

    @property
    def queue(self):
        return None     # @TODO: correct?

    def declare(self):
        self.declare_exchange_impl(None, self.exchange)

    def delete(self):
        self.delete_exchange_impl(None, self.exchange)






# @TODO: these are first class objects yes?
class ProcessExchangeName(ExchangeName):
    pass

class ServiceExchangeName(ExchangeName):
    pass

#class ExchangePoint(ExchangeName):
#    pass

class QueueExchangeName(ExchangeName):
    pass