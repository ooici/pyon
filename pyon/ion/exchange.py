#!/usr/bin/env python

"""Exchange management classes."""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.net import messaging
from pyon.util.log import log
from pyon.util.state_object import  LifecycleStateMixin

ION_URN_PREFIX = "urn:ionx"

ION_ROOT_XS = "ioncore"

def valid_xname(name):
    return name and str(name).find(":") == -1 and str(name).find(" ") == -1

class ExchangeManager(LifecycleStateMixin):
    """
    Manager object for the CC to manage Exchange related resources.
    """
    def on_init(self, container, *args, **kwargs):
        log.debug("ExchangeManager: init")
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

    def on_start(self, *args, **kwargs):
        # Establish connection to broker
        #self.container.node, self.container.ioloop = messaging.make_node() # TODO: shortcut hack

        # Declare root exchange
        #self.default_xs.ensure_exists(self.container.node)
        log.debug("ExchangeManager: start")

    def create_xs(self, name):
        pass

    def create_xp(self, xs, name, xptype):
        pass

    def create_xn(self, xs, name):
        pass

    def on_quit(self, *args, **kwargs):
        log.debug("ExchangeManager: quit")


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
        qname = "%s:%s" % (ION_URN_PREFIX, self.name)
        return qname

    def build_xname(self):
        xname = "ion.xs.%s" % (self.name)
        return xname

    def ensure_exists(self, node):
        xname = self.build_xname()
        log.debug("ExchangeSpace.ensure_exists() xname=%" % xname)
        #ch = node.basic_channel()
        #log.debug("ExchangeSpace.ensure_exists. Got basic channel %s" % ch)


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
        qname = "%s:%s:%s" % (ION_URN_PREFIX, str(self.xs), self.name)
        return qname

    def build_xlname(self):
        xname = "ion.xs.%s" % (self.name)
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
        xname = "ion.xs.%s.xp.%s" % (self.xs, self.name)
        return xname

