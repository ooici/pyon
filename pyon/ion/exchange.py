#!/usr/bin/env python

"""Exchange management classes."""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.net import messaging
from pyon.util.log import log
from pyon.core import bootstrap
from pyon.util.async import blocking_cb

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
        self.default_xs = ExchangeSpace(ION_ROOT_XS)

        self._chan = None

        # TODO: Do more initializing here, not in container

    def start(self):
        log.debug("ExchangeManager starting ...")

        # Establish connection to broker
        # @TODO: raise error if sux
        node, ioloop = messaging.make_node()

        # Declare root exchange
        #self.default_xs.ensure_exists(self._get_channel())
        return node, ioloop

    def _get_channel(self):
        """
        Get a raw channel to be used by all the ensure_exists methods.
        """
        assert self.container and self.container.node

        # @TODO: needs lock, but so do all these methods
        if not self._chan:
            self._chan = blocking_cb(self.container.node.client.channel, 'on_open_callback')

        return self._chan

    def create_xs(self, name):
        log.debug("ExchangeManager.create_xs: %s", name)
        xs = ExchangeSpace(name)
        xs.ensure_exists(self._get_channel())

        return xs

    def create_xp(self, xs, name, xptype):
        log.debug("ExchangeManager.create_xp: name=%s, xptype=%s", name, xptype)
        xp = ExchangePoint(name, xs=xs, xptype=xptype)
        xp.ensure_exists(self._get_channel())

        return xp

    def create_xn(self, xs, name):
        log.debug("ExchangeManager.create_xn: name=%s, xs=%s", name, xs)
        xn = ExchangeName(name, xs)
        #xn.ensure_exists(self._get_channel())

        return xn

    def stop(self, *args, **kwargs):
        log.debug("ExchangeManager stopping ...")


class ExchangeSpace(object):
    ION_DEFAULT_XS = "ioncore"

    def __init__(self, name):
        assert name, "Invalid XS name %s" % name
        name = str(name)
        if name.startswith(ION_URN_PREFIX):
            name = name[len(ION_URN_PREFIX)+1:]
        assert valid_xname(name), "Invalid XS name %s" % name
        self.name = name
        self.qname = self.build_qname()

    def build_qname(self):
        qname = "%s:%s:%s" % (ION_URN_PREFIX, bootstrap.sys_name, self.name)
        return qname

    def build_xname(self):
        xname = "%s.ion.xs.%s" % (bootstrap.sys_name, self.name)
        return xname

    def ensure_exists(self, chan):
        xname = self.build_xname()
        log.debug("ExchangeSpace.ensure_exists() xname=%s", xname)

        blocking_cb(chan.exchange_declare, 'callback', exchange=xname,
                                                       type='topic',
                                                       durable=False,
                                                       auto_delete=True)

        log.debug("ExchangeSpace (%s) created", xname)

    def __str__(self):
        return self.name

    def __repr__(self):
        return "ExchangeSpace(%s)" % self.qname

class ExchangeName(object):
    """
    Exchange names have the following format:
    urn:ionx:<XS-Name>:<Name>
    """
    def __init__(self, name, xs=None):
        assert name, "Invalid XS name %s" % name
        name = str(name)
        if name.startswith(ION_URN_PREFIX):
            name = name[len(ION_URN_PREFIX)+1:]
            xs, name = name.split(":")
        assert xs, "XS not given"
        assert valid_xname(name), "Invalid XN name %s" % name
        self.xs = xs
        self.name = str(name)
        self.qname = self.build_qname()

    def build_qname(self):
        qname = "%s:%s:%s:%s" % (ION_URN_PREFIX, bootstrap.sys_name, str(self.xs), self.name)
        return qname

    def build_xlname(self):
        xname = "%s.ion.xs.%s" % (bootstrap.sys_name, self.name)
        return xname

    def __str__(self):
        return self.name

    def __repr__(self):
        return "ExchangeName(%s)" % self.qname

class ExchangePoint(ExchangeName):
    XPTYPES = {
        'basic':'basic',
        'ttree':'ttree',
    }
    def __init__(self, name, xs=None, xptype=None):
        ExchangeName.__init__(self, name, xs)
        self.xptype = xptype or 'basic'

    def build_xname(self):
        xname = "%s.xp.%s" % (self.xs.build_xname(), self.name)
        return xname

    def ensure_exists(self, chan):

        xname = self.build_xname()
        log.debug("ExchangePoint.ensure_exists, xname=%s", xname)

        blocking_cb(chan.exchange_declare, 'callback', exchange=xname,
                                                       type='topic',
                                                       durable=False,
                                                       auto_delete=True)

        log.debug("ExchangePoint (%s) created", xname)

