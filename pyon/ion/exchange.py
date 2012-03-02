#!/usr/bin/env python

"""Exchange management classes."""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.net import messaging
from pyon.util.log import log
from pyon.core import bootstrap
from pyon.util.async import blocking_cb
from pyon.net.transport import BaseTransport, NameTrio, AMQPTransport
from interface.objects import ExchangeName as ResExchangeName
from interface.objects import ExchangeSpace as ResExchangeSpace
from interface.objects import ExchangePoint as ResExchangePoint
from interface.services.coi.iexchange_management_service import ExchangeManagementServiceProcessClient
from interface.services.coi.iresource_registry_service import ResourceRegistryServiceProcessClient
from pyon.util.config import CFG
from pyon.ion.resource import RT

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
        # @TODO: remove
        self.container_api = [self.create_xs,
                              self.create_xp,
                              self.create_xn_service,
                              self.create_xn_process,
                              self.create_xn_queue]

        # Add the public callables to Container
        for call in self.container_api:
            setattr(self.container, call.__name__, call)

        self.default_xs         = ExchangeSpace(self, ION_ROOT_XS)
        self._xs_cache          = {}        # caching of xs names to RR objects
        self._default_xs_obj    = None      # default XS registry object
        self.org_id             = None

        # mappings
        self.xs_by_name = { ION_ROOT_XS: self.default_xs }      # friendly named XS to XSO
        self.xn_by_name = {}                                    # friendly named XN to XNO
        # xn by xs is a property

        self._chan = None

        # @TODO specify our own to_name here so we don't get auto-behavior - tricky chicken/egg
        self._ems_client    = ExchangeManagementServiceProcessClient(process=self.container)
        self._rr_client     = ResourceRegistryServiceProcessClient(process=self.container)

        # TODO: Do more initializing here, not in container

    @property
    def xn_by_xs(self):
        """
        Get a list of XNs associated by XS (friendly name).
        """
        ret = {}
        for xnname, xn in self.xn_by_name.iteritems():
            xsn = xn._xs._exchange
            if not xsn in ret:
                ret[xsn] = []
            ret[xsn].append(xn)

        return ret

    def _get_xs_obj(self, name=ION_ROOT_XS):
        """
        Gets a resource-registry represented XS, either via cache or RR request.
        """
        if name in self._xs_cache:
            return self._xs_cache[name]

        xs_objs, _ = self._rr_client.find_resources(RT.ExchangeSpace, name=name)
        if not len(xs_objs) == 1:
            log.warn("Could not find RR XS object with name: %s", name)
            return None

        self._xs_cache[name] = xs_objs[0]
        return xs_objs[0]

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

    def _ems_available(self):
        """
        Returns True if the EMS is (likely) available and the auto_register CFG entry is True.

        Has the side effect of bootstrapping the org_id and default_xs's id/rev from the RR.
        Therefore, cannot be a property.
        """
        if CFG.container.get('exchange', {}).get('auto_register', False):
            # ok now make sure it's in the directory
            svc_de = self.container.directory.lookup('/Services/exchange_management')
            if svc_de is not None:
                if not self.org_id:
                    # find the default Org
                    org_ids = self._rr_client.find_resources(RT.Org, id_only=True)
                    if not (len(org_ids) and len(org_ids[0]) == 1):
                        log.warn("EMS available but could not find Org")
                        return False

                    self.org_id = org_ids[0][0]
                    log.debug("Bootstrapped Container exchange manager with org id: %s", self.org_id)
                return True

        return False

    def _get_channel(self, node):
        """
        Get a raw channel to be used by all the ensure_exists methods.
        """
        assert self.container

        # @TODO: needs lock, but so do all these methods
        if not self._chan:
            self._chan = blocking_cb(node.client.channel, 'on_open_callback')

        return self._chan

    def create_xs(self, name, use_ems=True, exchange_type='topic', durable=False, auto_delete=True):
        log.debug("ExchangeManager.create_xs: %s", name)
        xs = ExchangeSpace(self, name, exchange_type=exchange_type, durable=durable, auto_delete=auto_delete)

        self.xs_by_name[name] = xs

        if use_ems and self._ems_available():
            log.debug("Using EMS to create_xs")
            # create a RR object
            xso = ResExchangeSpace(name=name)
            xso_id = self._ems_client.create_exchange_space(xso, self.org_id)

            log.debug("Created RR XS object, id: %s", xso_id)
        else:
            xs.declare()

        return xs

    def delete_xs(self, xs, use_ems=True):
        """
        @type xs    ExchangeSpace
        """
        log.debug("ExchangeManager.delete_xs: %s", xs)

        name = xs._exchange     # @TODO this feels wrong
        del self.xs_by_name[name]

        if use_ems and self._ems_available():
            log.debug("Using EMS to delete_xs")
            xso = self._get_xs_obj(name)
            self._ems_client.delete_exchange_space(xso._id)
            del self._xs_cache[name]
        else:
            xs.delete()

    def create_xp(self, name, xs=None, use_ems=True, **kwargs):
        log.debug("ExchangeManager.create_xp: %s", name)
        xs = xs or self.default_xs
        xp = ExchangePoint(self, name, xs, **kwargs)

        # put in xn_by_name anyway
        self.xn_by_name[name] = xp

        if use_ems and self._ems_available():
            log.debug("Using EMS to create_xp")
            # create an RR object
            xpo = ResExchangePoint(name=name, topology_type=xp._xptype)
            xpo_id = self._ems_client.create_exchange_point(xpo, self._get_xs_obj(xs._exchange)._id)        # @TODO: _exchange is wrong
        else:
            xp.declare()

        return xp

    def delete_xp(self, xp, use_ems=True):
        log.debug("ExchangeManager.delete_xp: name=%s", 'TODO') #xp.build_xname())

        name = xp._exchange # @TODO: not right
        del self.xn_by_name[name]

        if use_ems and self._ems_available():
            log.debug("Using EMS to delete_xp")
            # find the XP object via RR
            xpo_ids = self._rr_client.find_resources(RT.ExchangePoint, name=name, id_only=True)
            if not (len(xpo_ids) and len(xpo_ids[0]) == 1):
                log.warn("Could not find XP in RR with name of %s", name)

            xpo_id = xpo_ids[0][0]
            self._ems_client.delete_exchange_point(xpo_id)
        else:
            xp.delete()

    def _create_xn(self, xn_type, name, xs=None, use_ems=True, **kwargs):
        xs = xs or self.default_xs
        log.debug("ExchangeManager._create_xn: type: %s, name=%s, xs=%s, kwargs=%s", xn_type, name, xs, kwargs)

        if xn_type == "service":
            xn = ExchangeNameService(self, name, xs, **kwargs)
        elif xn_type == "process":
            xn = ExchangeNameProcess(self, name, xs, **kwargs)
        elif xn_type == "queue":
            xn = ExchangeNameQueue(self, name, xs, **kwargs)
        else:
            raise StandardError("Unknown XN type: %s" % xn_type)

        self.xn_by_name[name] = xn

        if use_ems and self._ems_available():
            log.debug("Using EMS to create_xn")
            xno = ResExchangeName(name=name, xn_type=xn.xn_type)
            self._ems_client.declare_exchange_name(xno, self._get_xs_obj(xs._exchange)._id)     # @TODO: exchange is wrong
        else:
            xn.declare()

        return xn

    def create_xn_service(self, name, xs=None, **kwargs):
        return self._create_xn('service', name, xs=xs, **kwargs)

    def create_xn_process(self, name, xs=None, **kwargs):
        return self._create_xn('process', name, xs=xs, **kwargs)

    def create_xn_queue(self, name, xs=None, **kwargs):
        return self._create_xn('queue', name, xs=xs, **kwargs)

    def delete_xn(self, xn, use_ems=False):
        log.debug("ExchangeManager.delete_xn: name=%s", "TODO") #xn.build_xlname())

        name = xn._queue                # @TODO feels wrong
        del self.xn_by_name[name]

        if use_ems and self._ems_available():
            log.debug("Using EMS to delete_xn")
            # find the XN object via RR?
            xno_ids = self._rr_client.find_resources(RT.ExchangeName, name=name, id_only=True)
            if not (len(xno_ids) and len(xno_ids[0]) == 1):
                log.warn("Could not find XN in RR with name of %s", name)

            xno_id = xno_ids[0][0]

            self._ems_client.undeclare_exchange_name(xno_id)        # "canonical name" currently understood to be RR id
        else:
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
        return self._transport.declare_queue_impl(self._client, queue, durable=durable, auto_delete=auto_delete)
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

    def setup_listener(self, binding, default_cb):
        log.debug("XOTransport passing on setup_listener")
        pass

#    # friendly versions?
#    def declare_exchange(self, exchange, **kwargs):
#        return self.declare_exchange_impl(None, exchange, **kwargs)
#
#        # etc etc

class ExchangeSpace(XOTransport, NameTrio):

    ION_DEFAULT_XS = "ioncore"

    def __init__(self, exchange_manager, exchange, exchange_type='topic', durable=False, auto_delete=True):
        XOTransport.__init__(self, exchange_manager=exchange_manager)
        NameTrio.__init__(self, exchange=exchange)

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

class ExchangeName(XOTransport, NameTrio):

    xn_type = "XN_BASE"

    _xn_durable     = False
    _xn_auto_delete = True

    def __init__(self, exchange_manager, name, xs, durable=None, auto_delete=None):
        XOTransport.__init__(self, exchange_manager=exchange_manager)
        NameTrio.__init__(self, exchange=None, queue=name)

        self._xs = xs

        if durable:     self._xn_durable        = durable
        if auto_delete: self._xn_auto_delete    = auto_delete

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

    def setup_listener(self, binding, default_cb):
        log.debug("ExchangeName.setup_listener: B %s", binding)

        # make sure we've bound (idempotent action)
        self.bind(binding)


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

    xn_type = "XN_XP"

    def __init__(self, exchange_manager, name, xs, xptype=None):
        xptype = xptype or 'ttree'

        XOTransport.__init__(self, exchange_manager=exchange_manager)
        NameTrio.__init__(self, exchange=name)

        self._xs        = xs
        self._xptype    = xptype

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



class ExchangeNameProcess(ExchangeName):
    xn_type = "XN_PROCESS"
    pass

class ExchangeNameService(ExchangeName):
    xn_type = "XN_SERVICE"
    _xn_auto_delete = False
    pass

class ExchangeNameQueue(ExchangeName):
    xn_type = "XN_QUEUE"
    def queue(self):
        return None