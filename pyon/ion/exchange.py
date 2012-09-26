#!/usr/bin/env python

"""Exchange management classes."""

__author__ = 'Michael Meisinger, Dave Foster'
__license__ = 'Apache 2.0'

from pyon.core import bootstrap
from pyon.core.bootstrap import CFG
from pyon.net import messaging
from pyon.net.transport import NameTrio, TransportError, ComposableTransport
from pyon.util.log import log
from pyon.ion.resource import RT
from pyon.core.exception import Timeout, ServiceUnavailable, ServerError

import gevent
import requests
import json
import time
import socket

from interface.objects import ExchangeName as ResExchangeName
from interface.objects import ExchangeSpace as ResExchangeSpace
from interface.objects import ExchangePoint as ResExchangePoint
from interface.services.coi.iexchange_management_service import ExchangeManagementServiceProcessClient
from interface.services.coi.iresource_registry_service import ResourceRegistryServiceProcessClient


ION_URN_PREFIX = "urn:ionx"

ION_ROOT_XS = "ioncore"

def valid_xname(name):
    return name and str(name).find(":") == -1 and str(name).find(" ") == -1

class ExchangeManagerError(StandardError):
    pass

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

        self.default_xs             = None
        self._xs_cache              = {}        # caching of xs names to RR objects
        self._default_xs_obj        = None      # default XS registry object
        self.org_id                 = None
        self._default_xs_declared   = False

        # mappings
        self.xs_by_name = {}                    # friendly named XS to XSO
        self.xn_by_name = {}                    # friendly named XN to XNO
        # xn by xs is a property

        # @TODO specify our own to_name here so we don't get auto-behavior - tricky chicken/egg
        self._ems_client    = ExchangeManagementServiceProcessClient(process=self.container)
        self._rr_client     = ResourceRegistryServiceProcessClient(process=self.container)

        # mapping of node/ioloop runner by connection name (in config, named via container.messaging.server keys)
        self._nodes     = {}
        self._ioloops   = {}

    def start(self):
        log.debug("ExchangeManager.start")

        total_count = 0

        def handle_failure(name, node):
            log.warn("Node %s could not be started", name)
            node.ready.set()        # let it fall out below

        # Establish connection(s) to broker
        for name, cfgkey in CFG.container.messaging.server.iteritems():
            if not cfgkey:
                continue

            if cfgkey not in CFG.server:
                raise ExchangeManagerError("Config key %s (name: %s) (from CFG.container.messaging.server) not in CFG.server" % (cfgkey, name))

            total_count += 1
            log.debug("Starting connection: %s", name)

            # start it with a zero timeout so it comes right back to us
            try:
                cfg_params = CFG.server[cfgkey]

                if cfg_params['type'] == 'zeromq':
                    node, ioloop = messaging.make_zmq_node(0, self.container.zmq_router)
                else:
                    node, ioloop = messaging.make_node(cfg_params, name, 0)

                # install a finished handler directly on the ioloop just for this startup period
                fail_handle = lambda _: handle_failure(name, node)
                ioloop.link(fail_handle)

                # wait for the node ready event, with a large timeout just in case
                node_ready = node.ready.wait(timeout=15)

                # remove the finished handler, we don't care about it here
                ioloop.unlink(fail_handle)

                # only add to our list if we started successfully
                if not node.running:
                    ioloop.kill()      # make sure ioloop dead
                else:
                    self._nodes[name]   = node
                    self._ioloops[name] = ioloop

            except socket.error as e:
                log.warn("Could not start connection %s due to socket error, continuing", name)

        fail_count = total_count - len(self._nodes)
        if fail_count > 0 or total_count == 0:
            if fail_count == total_count:
                raise ExchangeManagerError("No node connection was able to start (%d nodes attempted, %d nodes failed)" % (total_count, fail_count))

            log.warn("Some nodes could not be started, ignoring for now")   # @TODO change when ready

        # load interceptors into each
        map(lambda x: x.setup_interceptors(CFG.interceptor), self._nodes.itervalues())

        # prepare priviledged transport
        self._priviledged_transport = self.get_transport(self._nodes.get('priviledged', self._nodes.get('primary')))
        self._priviledged_transport.lock = True     # prevent any attempt to close

        self.default_xs         = ExchangeSpace(self, self._priviledged_transport, ION_ROOT_XS)
        self.xs_by_name[ION_ROOT_XS] = self.default_xs

        log.debug("Started %d connections (%s)", len(self._nodes), ",".join(self._nodes.iterkeys()))

    def stop(self, *args, **kwargs):
        # ##############
        # HACK HACK HACK
        #
        # It appears during shutdown that when a channel is closed, it's not FULLY closed by the pika connection
        # until the next round of _handle_events. We have to yield here to let that happen, in order to have close
        # work fine without blowing up.
        # ##############
        time.sleep(0.1)
        # ##############
        # /HACK
        # ##############

        log.debug("ExchangeManager.stopping (%d connections)", len(self._nodes))

        for name in self._nodes:
            self._nodes[name].stop_node()
            self._ioloops[name].kill()
            #self._nodes[name].client.ioloop.start()     # loop until connection closes

        self._priviledged_transport.lock = False
        self._priviledged_transport.close()

        # @TODO undeclare root xs??  need to know if last container
        #self.default_xs.delete()

    @property
    def default_node(self):
        """
        Returns the default node connection.
        """
        if 'primary' in self._nodes:
            return self._nodes['primary']
        elif len(self._nodes):
            log.warn("No primary connection, returning first available")
            return self._nodes.values()[0]

        return None

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

    def cleanup_xos(self):
        """
        Iterates the list of Exchange Objects and deletes them.

        Typically used for test cleanup.
        """

        xns = self.xn_by_name.values()  # copy as we're removing as we go

        for xn in xns:
            if isinstance(xn, ExchangePoint):   # @TODO ugh
                self.delete_xp(xn)
            else:
                self.delete_xn(xn)

        xss = self.xs_by_name.values()

        for xs in xss:
            if not (xs == self.default_xs and not self._default_xs_declared):
                self.delete_xs(xs)

        # reset xs map to initial state
        self._default_xs_declared = False
        self.xs_by_name = { ION_ROOT_XS: self.default_xs }      # friendly named XS to XSO

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

    def _ems_available(self):
        """
        Returns True if the EMS is (likely) available and the auto_register CFG entry is True.

        Has the side effect of bootstrapping the org_id and default_xs's id/rev from the RR.
        Therefore, cannot be a property.
        """
        if CFG.get_safe('container.exchange.auto_register', False):
            # ok now make sure it's in the directory
            service_list, _ = self.container.resource_registry.find_resources(restype="Service", name='exchange_management')
            if service_list is not None and len(service_list) > 0:
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

    def get_transport(self, node):
        """
        Get a transport to be used by operations here.
        """
        assert self.container

        with node._lock:
            transport = node._new_transport()
            return transport

    def create_xs(self, name, use_ems=True, exchange_type='topic', durable=False, auto_delete=True):
        log.debug("ExchangeManager.create_xs: %s", name)
        xs = ExchangeSpace(self,
                           self._priviledged_transport,
                           name,
                           exchange_type=exchange_type,
                           durable=durable,
                           auto_delete=auto_delete)

        self.xs_by_name[name] = xs

        if use_ems and self._ems_available():
            log.debug("Using EMS to create_xs")
            # create a RR object
            xso = ResExchangeSpace(name=name)
            xso_id = self._ems_client.create_exchange_space(xso, self.org_id)

            log.debug("Created RR XS object, id: %s", xso_id)
        else:
            self._ensure_default_declared()
            xs.declare()

        return xs

    def delete_xs(self, xs, use_ems=True):
        """
        @type xs    ExchangeSpace
        """
        log.debug("ExchangeManager.delete_xs: %s", xs)

        name = xs._exchange     # @TODO this feels wrong
        self.xs_by_name.pop(name, None) # EMS may be running on the same container, which touches this same dict
                                        # so delete in the safest way possible
                                        # @TODO: does this mean we need to sync xs_by_name and friends in the datastore?

        if use_ems and self._ems_available():
            log.debug("Using EMS to delete_xs")
            xso = self._get_xs_obj(name)
            self._ems_client.delete_exchange_space(xso._id)
            del self._xs_cache[name]
        else:
            try:
                xs.delete()
            except TransportError as ex:
                log.warn("Could not delete XS (%s): %s", name, ex)

    def create_xp(self, name, xs=None, use_ems=True, **kwargs):
        log.debug("ExchangeManager.create_xp: %s", name)
        xs = xs or self.default_xs
        xp = ExchangePoint(self,
                           self._priviledged_transport,
                           name,
                           xs,
                           **kwargs)

        # put in xn_by_name anyway
        self.xn_by_name[name] = xp

        if use_ems and self._ems_available():
            log.debug("Using EMS to create_xp")
            # create an RR object
            xpo = ResExchangePoint(name=name, topology_type=xp._xptype)
            xpo_id = self._ems_client.create_exchange_point(xpo, self._get_xs_obj(xs._exchange)._id)        # @TODO: _exchange is wrong
        else:
            self._ensure_default_declared()
            xp.declare()

        return xp

    def delete_xp(self, xp, use_ems=True):
        log.debug("ExchangeManager.delete_xp: name=%s", 'TODO') #xp.build_xname())

        name = xp._exchange # @TODO: not right
        self.xn_by_name.pop(name, None) # EMS may be running on the same container, which touches this same dict
                                        # so delete in the safest way possible
                                        # @TODO: does this mean we need to sync xs_by_name and friends in the datastore?

        if use_ems and self._ems_available():
            log.debug("Using EMS to delete_xp")
            # find the XP object via RR
            xpo_ids = self._rr_client.find_resources(RT.ExchangePoint, name=name, id_only=True)
            if not (len(xpo_ids) and len(xpo_ids[0]) == 1):
                log.warn("Could not find XP in RR with name of %s", name)

            xpo_id = xpo_ids[0][0]
            self._ems_client.delete_exchange_point(xpo_id)
        else:
            try:
                xp.delete()
            except TransportError as ex:
                log.warn("Could not delete XP (%s): %s", name, ex)

    def _create_xn(self, xn_type, name, xs=None, use_ems=True, **kwargs):
        xs = xs or self.default_xs
        log.debug("ExchangeManager._create_xn: type: %s, name=%s, xs=%s, kwargs=%s", xn_type, name, xs, kwargs)

        if xn_type == "service":
            xn = ExchangeNameService(self,
                                     self._priviledged_transport,
                                     name,
                                     xs,
                                     **kwargs)
        elif xn_type == "process":
            xn = ExchangeNameProcess(self,
                                     self._priviledged_transport,
                                     name,
                                     xs,
                                     **kwargs)
        elif xn_type == "queue":
            xn = ExchangeNameQueue(self,
                                   self._priviledged_transport,
                                   name,
                                   xs,
                                   **kwargs)
        else:
            raise StandardError("Unknown XN type: %s" % xn_type)

        self.xn_by_name[name] = xn

        if use_ems and self._ems_available():
            log.debug("Using EMS to create_xn")
            xno = ResExchangeName(name=name, xn_type=xn.xn_type)
            self._ems_client.declare_exchange_name(xno, self._get_xs_obj(xs._exchange)._id)     # @TODO: exchange is wrong
        else:
            self._ensure_default_declared()
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
        self.xn_by_name.pop(name, None) # EMS may be running on the same container, which touches this same dict
                                        # so delete in the safest way possible
                                        # @TODO: does this mean we need to sync xs_by_name and friends in the datastore?

        if use_ems and self._ems_available():
            log.debug("Using EMS to delete_xn")
            # find the XN object via RR?
            xno_ids = self._rr_client.find_resources(RT.ExchangeName, name=name, id_only=True)
            if not (len(xno_ids) and len(xno_ids[0]) == 1):
                log.warn("Could not find XN in RR with name of %s", name)

            xno_id = xno_ids[0][0]

            self._ems_client.undeclare_exchange_name(xno_id)        # "canonical name" currently understood to be RR id
        else:
            try:
                xn.delete()
            except TransportError as ex:
                log.warn("Could not delete XN (%s): %s", name, ex)

    def _ensure_default_declared(self):
        """
        Ensures we declared the default exchange space.
        Needed by most exchange object calls, so each one calls here.
        """
        if not self._default_xs_declared:
            log.debug("ExchangeManager._ensure_default_declared, declaring default xs")
            self._default_xs_declared = True
            self.default_xs.declare()

    def get_definitions(self):
        """
        Rabbit HTTP management API call to get all defined objects on a broker.

        Returns users, vhosts, queues, exchanges, bindings, rabbit_version, and permissions.
        """
        url = self._get_management_url("definitions")
        raw_defs = self._call_management(url)

        return raw_defs

    def list_nodes(self):
        """
        Rabbit HTTP management API call to get all nodes in a cluster.
        """
        url = self._get_management_url("nodes")
        nodes = self._call_management(url)

        return nodes

    def list_connections(self):
        """
        Rabbit HTTP management API call to get all connections to a broker.
        """
        url = self._get_management_url("connections")
        conns = self._call_management(url)

        return conns

    def list_channels(self):
        """
        Rabbit HTTP management API call to get channels opened on the broker.
        """
        url = self._get_management_url("channels")
        chans = self._call_management(url)

        return chans

    def list_exchanges(self):
        """
        Rabbit HTTP management API call to list exchanges on the broker.

        Returns a list of exchange names. If you want the full set of properties for each,
        use _list_exchanges.
        """
        raw_exchanges = self._list_exchanges()
        exchanges = [x['name'] for x in raw_exchanges]

        return exchanges

    def _list_exchanges(self):
        """
        Rabbit HTTP management API call to list exchanges with full properties.

        This is used by list_exchanges to get a list of names, but does not filter anything.
        """
        url = self._get_management_url("exchanges", "%2f")
        raw_exchanges = self._call_management(url)

        return raw_exchanges

    def list_queues(self, name=None):
        """
        Rabbit HTTP management API call to list names of queues on the broker.

        Returns a list of queue names. If you want the full properties for each,
        use _list_queues.

        @param  name    If set, filters the list by only including queues with name in them.
        """
        raw_queues = self._list_queues()

        nl = lambda x: (name is None) or (name is not None and name in x)

        queues = [x['name'] for x in raw_queues if nl(x['name'])]

        return queues

    def _list_queues(self):
        """
        Rabbit HTTP management API call to list queues with full properties.

        This is used by list_queues to get a list of names, but does not filter anything.
        """
        url = self._get_management_url("queues", "%2f")
        raw_queues = self._call_management(url)

        return raw_queues

    def get_queue_info(self, queue):
        """
        Rabbit HTTP management API call to get full properties of a single queue.
        """
        url = self._get_management_url("queues", "%2f", queue)
        queue_info = self._call_management(url)

        return queue_info

    def list_bindings(self, exchange=None, queue=None):
        """
        Rabbit HTTP management API call to list bindings.

        Returns a list of tuples formatted as (exchange, queue, routing_key, properties_key aka binding id).
        This method can optionally filter queues or exchanges (or both) by specifying strings to
        exchange/queue keyword arguments. If you want the full list of properties unfiltered, call
        _list_bindings instead.

        The properties_key is used to delete a binding.

        If you want to get the bindings on a specific queue or exchange, don't use the filters here, but
        call the specific list_bindings_for_queue or list_bindings_for_exchange, as they will not result
        in a large result from the management API.

        @param  exchange    If set, filters the list by only including bindings with exchanges that have the
                            passed value in them.
        @param  queue       If set, filters the list by only including bindings with queues that have the
                            passed value in them.
        """
        raw_binds = self._list_bindings()

        ql = lambda x: (queue is None) or (queue is not None and queue in x)
        el = lambda x: (exchange is None) or (exchange is not None and exchange in x)

        binds = [(x['source'], x['destination'], x['routing_key'], x['properties_key']) for x in raw_binds if x['destination_type'] == 'queue' and x['source'] != '' and ql(x['destination']) and el(x['source'])]
        return binds

    def _list_bindings(self):
        """
        Rabbit HTTP management API call to list bindings with full properties.

        This is used by list_bindings to get a list of binding tuples, but does not filter anything.
        """
        url = self._get_management_url("bindings", "%2f")
        raw_binds = self._call_management(url)

        return raw_binds

    def list_bindings_for_queue(self, queue):
        """
        Rabbit HTTP management API call to list bindings for a queue.

        Returns a list of tuples formatted as (exchange, queue, routing_key, properties_key aka binding id).
        If you want the full list of properties for all the bindings, call _list_bindings_for_queue instead.

        This method is much more efficient than calling list_bindings with a filter. 

        @param  queue   The name of the queue you want bindings for.
        """
        raw_binds = self._list_bindings_for_queue(queue)

        binds = [(x['source'], x['destination'], x['routing_key'], x['properties_key']) for x in raw_binds if x['source'] != '']
        return binds

    def _list_bindings_for_queue(self, queue):
        """
        Rabbit HTTP management API call to list bindings on a queue with full properties.

        This is used by list_bindings_for_queue to get a list of binding tuples, but does not filter
        anything.
        """
        url = self._get_management_url("queues", "%2f", queue, "bindings")
        raw_binds = self._call_management(url)

        return raw_binds

    def list_bindings_for_exchange(self, exchange):
        """
        Rabbit HTTP management API call to list bindings for an exchange.

        Returns a list of tuples formatted as (exchange, queue, routing_key, properties_key aka binding id).
        If you want the full list of properties for all the bindings, call _list_bindings_for_exchange instead.

        This method is much more efficient than calling list_bindings with a filter. 

        @param  exchange    The name of the exchange you want bindings for.
        """
        raw_binds = self._list_bindings_for_exchange(exchange)

        binds = [(x['source'], x['destination'], x['routing_key'], x['properties_key']) for x in raw_binds if x['source'] != '']
        return binds

    def _list_bindings_for_exchange(self, exchange):
        """
        Rabbit HTTP management API call to list bindings for an exchange with full properties.

        This is used by list_bindings_for_exchange to get a list of binding tuples, but does not filter
        anything.
        """
        url = self._get_management_url("exchanges", "%2f", exchange, "bindings", "source")
        raw_binds = self._call_management(url)

        return raw_binds

    def delete_binding(self, exchange, queue, binding_prop_key):
        """
        Rabbit HTTP management API call to delete a binding.

        You may also use delete_binding_tuple to directly pass the tuples returned by
        any of the list binding calls.
        """

        # have to urlencode the %, even though it is already urlencoded - rabbit needs this.
        url = self._get_management_url("bindings", "%2f", "e", exchange, "q", queue, binding_prop_key.replace("%", "%25"))
        self._call_management_delete(url)

        return True

    def delete_binding_tuple(self, binding_tuple):
        """
        Rabbit HTTP management API call to delete a binding using a tuple from our list binding methods.
        """
        return self.delete_binding(binding_tuple[0], binding_tuple[1], binding_tuple[3])

    def purge_queue(self, queue):
        """
        Rabbit HTTP management API call to purge a queue.
        """
        url = self._get_management_url("queues", "%2f", queue, "contents")
        self._call_management_delete(url)

        return True

    def _get_management_url(self, *feats):
        """
        Builds a URL to be used with the Rabbit HTTP management API.
        """
        node = self._nodes.get('priviledged', self._nodes.values()[0])
        host = node.client.parameters.host

        url = "http://%s:%s/api/%s" % (host, CFG.get_safe("container.exchange.management.port", "55672"), "/".join(feats))

        return url

    def _call_management(self, url):
        """
        Makes a GET HTTP request to the Rabbit HTTP management API.

        This method will raise an exception if a non-200 HTTP status code is returned.

        @param  url     A URL to be used, build one with _get_management_url.
        """
        return self._make_management_call(url)

    def _call_management_delete(self, url):
        """
        Makes an HTTP DELETE request to the Rabbit HTTP management API.

        This method will raise an exception if a non-200 HTTP status code is returned.

        @param  url     A URL to be used, build one with _get_management_url.
        """
        return self._make_management_call(url, method="delete")

    def _make_management_call(self, url, use_ems=True, method="get"):
        """
        Makes a call to the Rabbit HTTP management API using the passed in HTTP method.
        """
        log.debug("Calling rabbit API management (%s): %s", method, url)

        if use_ems and self._ems_available():
            log.debug("Directing call to EMS")
            content = self._ems_client.call_management(url, method)
        else:
            meth = getattr(requests, method)

            try:
                username = CFG.get_safe("container.exchange.management.username", "guest")
                password = CFG.get_safe("container.exchange.management.password", "guest")

                with gevent.timeout.Timeout(10):
                    r = meth(url, auth=(username, password))
                r.raise_for_status()

                if not r.content == "":
                    content = json.loads(r.content)
                else:
                    content = None

            except gevent.timeout.Timeout as ex:
                raise Timeout(str(ex))
            except requests.exceptions.Timeout as ex:
                raise Timeout(str(ex))
            except (requests.exceptions.ConnectionError, socket.error) as ex:
                raise ServiceUnavailable(str(ex))
            except requests.exceptions.RequestException as ex:
                # the generic base exception all requests' exceptions inherit from, raise our
                # general server error too.
                raise ServerError(str(ex))

        return content

class XOTransport(ComposableTransport):
    def __init__(self, exchange_manager, priviledged_transport):
        self._exchange_manager = exchange_manager
        ComposableTransport.__init__(self, priviledged_transport, None, *ComposableTransport.common_methods)

    def setup_listener(self, binding, default_cb):
        log.debug("XOTransport passing on setup_listener")
        pass

class ExchangeSpace(XOTransport, NameTrio):

    ION_DEFAULT_XS = "ioncore"

    def __init__(self, exchange_manager, priviledged_transport, exchange, exchange_type='topic', durable=False, auto_delete=True):
        XOTransport.__init__(self, exchange_manager=exchange_manager, priviledged_transport=priviledged_transport)
        NameTrio.__init__(self, exchange=exchange)

        self._xs_exchange_type = exchange_type
        self._xs_durable       = durable
        self._xs_auto_delete   = auto_delete

    @property
    def exchange(self):
        return "%s.ion.xs.%s" % (bootstrap.get_sys_name(), self._exchange)

    def declare(self):
        self.declare_exchange_impl(self.exchange,
                                   exchange_type=self._xs_exchange_type,
                                   durable=self._xs_durable,
                                   auto_delete=self._xs_auto_delete)

    def delete(self):
        self.delete_exchange_impl(self.exchange)

class ExchangeName(XOTransport, NameTrio):

    xn_type = "XN_BASE"

    _xn_durable     = False
    _xn_auto_delete = False
    _declared_queue = None

    def __init__(self, exchange_manager, priviledged_transport, name, xs, durable=None, auto_delete=None):
        XOTransport.__init__(self, exchange_manager=exchange_manager, priviledged_transport=priviledged_transport)
        NameTrio.__init__(self, exchange=None, queue=name)

        self._xs = xs

        if durable is not None:     self._xn_durable        = durable
        if auto_delete is not None: self._xn_auto_delete    = auto_delete

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
        self._declared_queue = self.declare_queue_impl(self.queue, durable=self._xn_durable, auto_delete=self._xn_auto_delete)
        return self._declared_queue

    def delete(self):
        self.delete_queue_impl(self.queue)
        self._declared_queue = None

    def bind(self, binding_key, xs_or_xp=None):
        exchange = self.exchange
        if xs_or_xp is not None:
            exchange = xs_or_xp.exchange

        self.bind_impl(exchange, self.queue, binding_key)

    def unbind(self, binding_key, xs_or_xp=None):
        exchange = self.exchange
        if xs_or_xp is not None:
            exchange = xs_or_xp.exchange

        self.unbind_impl(exchange, self.queue, binding_key)

    def setup_listener(self, binding, default_cb):
        log.debug("ExchangeName.setup_listener: B %s", binding)

        # make sure we've bound (idempotent action)
        self.bind(binding)

    def get_stats(self):
        return self.get_stats_impl(self.queue)

    def purge(self):
        return self.purge_impl(self.queue)

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

    def __init__(self, exchange_manager, priviledged_transport, name, xs, xptype=None):
        xptype = xptype or 'ttree'

        XOTransport.__init__(self, exchange_manager=exchange_manager, priviledged_transport=priviledged_transport)
        NameTrio.__init__(self, exchange=name)

        self._xs        = xs
        self._xptype    = xptype

    @property
    def exchange(self):
        return "%s.xp.%s" % (self._xs.exchange, self._exchange)

    @property
    def queue(self):
        if self._queue:
            return self._queue
        return None     # @TODO: correct?

    def declare(self):
        self.declare_exchange_impl(self.exchange)

    def delete(self):
        self.delete_exchange_impl(self.exchange)

    def create_route(self, name):
        """
        Returns an ExchangePointRoute used for sending messages to an exchange point.
        """
        return ExchangePointRoute(self._exchange_manager, self._transports[0], name, self)

    def get_stats(self):
        raise NotImplementedError("get_stats not implemented for XP")

    def purge(self):
        raise NotImplementedError("purge not implemented for XP")

class ExchangePointRoute(ExchangeName):
    """
    Used for sending messages to an exchange point via a Publisher.

    This object is created via ExchangePoint.create_route
    """

    def __init__(self, exchange_manager, priviledged_transport, name, xp):
        ExchangeName.__init__(self, exchange_manager, priviledged_transport, name, xp)     # xp goes to xs param

    def declare(self):
        raise StandardError("ExchangePointRoute does not support declare")

    def delete(self):
        raise StandardError("ExchangePointRoute does not support delete")

class ExchangeNameProcess(ExchangeName):
    xn_type = "XN_PROCESS"
    pass

class ExchangeNameService(ExchangeName):
    xn_type = "XN_SERVICE"
    _xn_auto_delete = False
    pass

class ExchangeNameQueue(ExchangeName):
    xn_type = "XN_QUEUE"
    @property
    def queue(self):
        if self._declared_queue:
            return self._declared_queue
        return ExchangeName.queue.fget(self)

    def setup_listener(self, binding, default_cb):
        log.debug("ExchangeQueue.setup_listener: passing on binding")

