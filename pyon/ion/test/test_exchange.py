#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'

from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
from examples.service.hello_service import HelloService
from interface.services.examples.hello.ihello_service import HelloServiceClient
from pyon.net.endpoint import RPCServer, Subscriber, Publisher
from pyon.util.async import spawn
import unittest
from pyon.ion.exchange import ExchangeManager, ION_ROOT_XS, ExchangeNameProcess, ExchangeSpace, ExchangePoint, ExchangeNameService, ExchangeName, ExchangeNameQueue, ExchangeManagerError
from mock import Mock, sentinel, patch, call
from pyon.net.transport import BaseTransport, TransportError, AMQPTransport
from pyon.core.bootstrap import get_sys_name
from pyon.net.channel import RecvChannel
from pyon.core.bootstrap import CFG
from pyon.util.containers import DotDict
from gevent.queue import Queue
import os
import time

def _make_server_cfg(**kwargs):
    ddkwargs = DotDict(**kwargs)
    return DotDict(CFG.container, messaging=DotDict(CFG.container.messaging, server=ddkwargs))

@attr('UNIT', group='COI')
@patch('pyon.ion.exchange.messaging')
class TestExchangeManager(PyonTestCase):
    def setUp(self):
        self.container = Mock()
        self.ex_manager = ExchangeManager(self.container)
        self.ex_manager._get_channel = Mock()

    def test_verify_service(self, mockmessaging):
        PyonTestCase.test_verify_service(self)

    @patch.dict('pyon.ion.exchange.CFG', container=_make_server_cfg())
    def test_start_with_no_connections(self, mockmessaging):
        self.assertRaises(ExchangeManagerError, self.ex_manager.start)

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp':sentinel.amqp}, container=_make_server_cfg(primary='amqp'))
    def test_start_with_one_connection(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop
        self.ex_manager.start()

        mockmessaging.make_node.assert_called_once_with(sentinel.amqp, 'primary', 0)
        self.assertIn('primary', self.ex_manager._nodes)
        self.assertIn('primary', self.ex_manager._ioloops)
        self.assertEquals(self.ex_manager._nodes['primary'], mockmessaging.make_node.return_value[0])
        self.assertEquals(self.ex_manager._ioloops['primary'], mockmessaging.make_node.return_value[1])

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp':sentinel.amqp, 'amqp_again':sentinel.amqp_again}, container=_make_server_cfg(primary='amqp', secondary='amqp_again'))
    def test_start_with_multi_connections(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop
        self.ex_manager.start()

        mockmessaging.make_node.assert_calls(call(sentinel.amqp, 'primary', 0), call(sentinel.amqp_again, 'secondary', 0))

        self.assertIn('primary', self.ex_manager._nodes)
        self.assertIn('primary', self.ex_manager._ioloops)
        self.assertEquals(self.ex_manager._nodes['primary'], mockmessaging.make_node.return_value[0])
        self.assertEquals(self.ex_manager._ioloops['primary'], mockmessaging.make_node.return_value[1])

        self.assertIn('secondary', self.ex_manager._nodes)
        self.assertIn('secondary', self.ex_manager._ioloops)
        self.assertEquals(self.ex_manager._nodes['secondary'], mockmessaging.make_node.return_value[0])
        self.assertEquals(self.ex_manager._ioloops['secondary'], mockmessaging.make_node.return_value[1])

    @patch.dict('pyon.ion.exchange.CFG', server={}, container=_make_server_cfg(primary='idontexist'))
    def test_start_with_non_existing_connection_in_server(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop

        self.assertRaises(ExchangeManagerError, self.ex_manager.start)
        self.assertFalse(mockmessaging.make_node.called)

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp':sentinel.amqp, 'amqp_fail':sentinel.amqp_fail}, container=_make_server_cfg(primary='amqp', secondary='amqp_fail'))
    def test_start_with_working_and_failing_connection(self, mockmessaging):

        # set up return values - first is amqp (Working) second is amqp_fail (not working)
        nodemock = Mock()
        nodemock.running = False
        iomock = Mock()
        def ret_vals(conf, name, timeout):
            if name == 'secondary':
                return (nodemock, iomock)
            return (Mock(), Mock())

        mockmessaging.make_node.side_effect = ret_vals

        self.ex_manager.start()

        self.assertEquals(len(self.ex_manager._nodes), 1)
        iomock.kill.assert_called_once_with()

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp_fail':sentinel.amqp_fail}, container=_make_server_cfg(primary='amqp_fail'))
    def test_start_with_only_failing_connections(self, mockmessaging):
        nodemock = Mock()
        nodemock.running = False
        iomock = Mock()

        mockmessaging.make_node.return_value = (nodemock, iomock)

        self.assertRaises(ExchangeManagerError, self.ex_manager.start)
        iomock.kill.assert_called_once_with()

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp':sentinel.amqp}, container=_make_server_cfg(primary='amqp'))
    def test_start_stop(self, mockmessaging):
        nodemock = Mock()
        iomock = Mock()
        mockmessaging.make_node.return_value = (nodemock, iomock)

        self.ex_manager.start()
        self.ex_manager.stop()

        nodemock.stop_node.assert_called_once_with()
        iomock.kill.assert_called_once_with()

    def test_default_node_no_connections(self, mockmessaging):
        self.assertIsNone(self.ex_manager.default_node)

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp_not_default':sentinel.amqp_not_default}, container=_make_server_cfg(secondary='amqp_not_default'))
    def test_default_node_no_default_name(self, mockmessaging):
        nodemock = Mock()
        mockmessaging.make_node.return_value = (nodemock, Mock())     # node, ioloop

        self.ex_manager.start()

        self.assertEquals(self.ex_manager.default_node, nodemock)

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp':sentinel.amqp, 'amqp_again':sentinel.amqp_again}, container=_make_server_cfg(primary='amqp', secondary='amqp_again'))
    def test_default_node(self, mockmessaging):

        # set up return values - amqp returns this named version, amqp_again does not
        nodemock = Mock()
        iomock = Mock()
        def ret_vals(conf, name, timeout):
            if name == 'primary':
                return (nodemock, iomock)
            return (Mock(), Mock())

        mockmessaging.make_node.side_effect = ret_vals
        self.ex_manager.start()

        self.assertEquals(self.ex_manager.default_node, nodemock)

@attr('INT', group='COI')
class TestExchangeManagerInt(IonIntegrationTestCase):

    fail_bad_user_cfg = {
        'type':'amqp91',
        'host':CFG.server.amqp.host,
        'port':CFG.server.amqp.port,
        'username':'THIS_SHOULD_NOT_EXIST',
        'password':'REALLY_DOESNT_MATTER',
        'vhost': '/',
        'heartbeat':30,
    }

    fail_bad_port_cfg = {
        'type':'amqp91',
        'host':CFG.server.amqp.host,
        'port':CFG.server.amqp.port + 10,
        'username':CFG.server.amqp.username,
        'password':CFG.server.amqp.password,
        'vhost': '/',
        'heartbeat':30,
    }

    fail_bad_host_cfg = {
        'type':'amqp91',
        'host':'nowaydoesthisexistatall.badtld',
        'port':CFG.server.amqp.port,
        'username':CFG.server.amqp.username,
        'password':CFG.server.amqp.password,
        'vhost': '/',
        'heartbeat':30,
    }

    def setUp(self):
        pass

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp':CFG.server.amqp, 'couchdb':CFG.server.couchdb}, container=_make_server_cfg(primary='amqp'))
    def test_start_stop(self):
        self._start_container()

        self.assertEquals(self.container.node, self.container.ex_manager.default_node)
        self.assertEquals(len(self.container.ex_manager._nodes), 1)

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp':CFG.server.amqp, 'couchdb':CFG.server.couchdb, 'amqp_fail':fail_bad_user_cfg}, container=_make_server_cfg(primary='amqp', secondary='amqp_fail'))
    def test_start_stop_with_one_success_and_one_failure(self):
        self._start_container()

        self.assertEquals(len(self.container.ex_manager._nodes), 1)
        self.assertIn('primary', self.container.ex_manager._nodes)
        self.assertNotIn('secondary', self.container.ex_manager._nodes)

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp':CFG.server.amqp, 'couchdb':CFG.server.couchdb, 'amqp_fail':fail_bad_user_cfg, 'amqp_fail2':fail_bad_port_cfg}, container=_make_server_cfg(primary='amqp', secondary='amqp_fail', thirdly='amqp_fail2'))
    def test_start_stop_with_one_success_and_multiple_failures(self):
        self._start_container()

        self.assertEquals(len(self.container.ex_manager._nodes), 1)
        self.assertIn('primary', self.container.ex_manager._nodes)
        self.assertNotIn('secondary', self.container.ex_manager._nodes)

    @patch.dict('pyon.ion.exchange.CFG', server={'couchdb':CFG.server.couchdb, 'amqp':fail_bad_user_cfg}, container=_make_server_cfg())
    def test_start_stop_with_no_connections(self):
        self.assertRaises(ExchangeManagerError, self._start_container)

    @patch.dict('pyon.ion.exchange.CFG', server={'couchdb':CFG.server.couchdb, 'amqp_bad':fail_bad_port_cfg}, container=_make_server_cfg(primary='amqp_bad'))
    def test_start_stop_with_bad_port_failure(self):
        self.assertRaises(ExchangeManagerError, self._start_container)

    @patch.dict('pyon.ion.exchange.CFG', server={'couchdb':CFG.server.couchdb, 'amqp_bad':fail_bad_host_cfg}, container=_make_server_cfg(primary='amqp_bad'))
    def test_start_stop_with_bad_host_failure(self):
        self.assertRaises(ExchangeManagerError, self._start_container)


@attr('UNIT', group='exchange')
@patch.dict('pyon.ion.exchange.CFG', {'container':{'exchange':{'auto_register': False}}})
class TestExchangeObjects(PyonTestCase):
    def setUp(self):
        self.ex_manager = ExchangeManager(Mock())
        self.ex_manager._transport  = Mock(BaseTransport)
        self.ex_manager._client     = Mock()
        # all exchange level operations are patched out via the _transport

    def test_exchange_by_name(self):
        # defaults: Root XS, no XNs
        self.assertIn(ION_ROOT_XS, self.ex_manager.xs_by_name)
        self.assertIn(self.ex_manager.default_xs, self.ex_manager.xs_by_name.itervalues())
        self.assertEquals(len(self.ex_manager.xn_by_name), 0)

        # create another XS
        xs = self.ex_manager.create_xs('exchange')
        self.assertIn('exchange', self.ex_manager.xs_by_name)
        self.assertIn(xs, self.ex_manager.xs_by_name.values())
        self.assertEquals(len(self.ex_manager.xn_by_name), 0)

        # now create some XNs underneath default exchange
        xn1 = self.ex_manager.create_xn_process('xn1')
        self.assertEquals(xn1._xs, self.ex_manager.default_xs)
        self.assertIn('xn1', self.ex_manager.xn_by_name)
        self.assertIn(xn1, self.ex_manager.xn_by_name.values())
        self.assertEquals(xn1, self.ex_manager.xn_by_name['xn1'])
        self.assertIsInstance(xn1, ExchangeNameProcess)

        self.assertEquals({ION_ROOT_XS:[xn1]}, self.ex_manager.xn_by_xs)

        xn2 = self.ex_manager.create_xn_service('xn2')
        self.assertIn('xn2', self.ex_manager.xn_by_name)
        self.assertIn(xn2, self.ex_manager.xn_by_xs[ION_ROOT_XS])
        self.assertEquals(xn2.xn_type, 'XN_SERVICE')

        # create one under our second xn3
        xn3 = self.ex_manager.create_xn_queue('xn3', xs)
        self.assertIn('xn3', self.ex_manager.xn_by_name)
        self.assertIn(xn3, self.ex_manager.xn_by_xs['exchange'])
        self.assertNotIn(xn3, self.ex_manager.xn_by_xs[ION_ROOT_XS])

    def test_create_xs(self):
        xs      = self.ex_manager.create_xs(sentinel.xs)
        exstr   = '%s.ion.xs.%s' % (get_sys_name(), str(sentinel.xs))     # what we expect the exchange property to return

        self.assertEquals(xs._exchange, sentinel.xs)
        self.assertEquals(xs.exchange, exstr)
        self.assertEquals(xs.queue, None)
        self.assertEquals(xs.binding, None)

        self.assertEquals(xs._xs_exchange_type, 'topic')
        self.assertEquals(xs._xs_durable, False)
        self.assertEquals(xs._xs_auto_delete, True)

        # should be in our map too
        self.assertIn(sentinel.xs, self.ex_manager.xs_by_name)
        self.assertEquals(self.ex_manager.xs_by_name[sentinel.xs], xs)

        # should've tried to declare
        self.ex_manager._transport.declare_exchange_impl.assert_called_with(self.ex_manager._client, exstr, auto_delete=True, durable=False, exchange_type='topic')

    def test_create_xs_with_params(self):
        xs      = self.ex_manager.create_xs(sentinel.xs, exchange_type=sentinel.ex_type, durable=True)
        exstr   = '%s.ion.xs.%s' % (get_sys_name(), str(sentinel.xs))     # what we expect the exchange property to return

        self.assertEquals(xs._xs_durable, True)
        self.assertEquals(xs._xs_exchange_type, sentinel.ex_type)

        # declaration?
        self.ex_manager._transport.declare_exchange_impl.assert_called_with(self.ex_manager._client, exstr, auto_delete=True, durable=True, exchange_type=sentinel.ex_type)

    def test_delete_xs(self):
        # need an XS first
        xs      = self.ex_manager.create_xs(sentinel.delete_me)
        exstr   = '%s.ion.xs.%s' % (get_sys_name(), str(sentinel.delete_me))     # what we expect the exchange property to return

        self.assertIn(sentinel.delete_me, self.ex_manager.xs_by_name)

        self.ex_manager.delete_xs(xs)

        self.assertNotIn(sentinel.delete_me, self.ex_manager.xs_by_name)

        # call to broker
        self.ex_manager._transport.delete_exchange_impl.assert_called_once_with(self.ex_manager._client, exstr)

    def test_delete_xs_without_creating_it_first(self):
        xsmock = Mock(ExchangeSpace)
        xsmock._exchange = sentinel.fake

        self.assertRaises(KeyError, self.ex_manager.delete_xs, xsmock)

    def test_create_xp(self):
        xp      = self.ex_manager.create_xp(sentinel.xp)
        exstr   = "%s.ion.xs.%s.xp.%s" % (get_sys_name(), self.ex_manager.default_xs._exchange, str(sentinel.xp))

        self.assertEquals(xp._exchange, sentinel.xp)
        self.assertEquals(xp._xs, self.ex_manager.default_xs)
        self.assertEquals(xp._xptype, 'ttree')
        self.assertEquals(xp._queue, None)
        self.assertEquals(xp._binding, None)

        self.assertEquals(xp.exchange, exstr)

        # declaration
        self.ex_manager._transport.declare_exchange_impl.assert_called_with(self.ex_manager._client, exstr, auto_delete=True, durable=False, exchange_type='topic')

    def test_create_xp_with_params(self):
        xp = self.ex_manager.create_xp(sentinel.xp, xptype=sentinel.xptype)
        self.assertEquals(xp._xptype, sentinel.xptype)

    def test_create_xp_with_different_xs(self):
        xs = self.ex_manager.create_xs(sentinel.xs)
        xs_exstr = '%s.ion.xs.%s' % (get_sys_name(), str(sentinel.xs))     # what we expect the exchange property to return

        xp = self.ex_manager.create_xp(sentinel.xp, xs)
        xp_exstr = '%s.xp.%s' % (xs_exstr, str(sentinel.xp))

        # check mappings
        self.assertIn(sentinel.xp, self.ex_manager.xn_by_name)
        self.assertIn(xp, self.ex_manager.xn_by_xs[sentinel.xs])

        self.assertEquals(xp.exchange, xp_exstr)

    def test_delete_xp(self):
        xp      = self.ex_manager.create_xp(sentinel.xp)
        exstr   = "%s.ion.xs.%s.xp.%s" % (get_sys_name(), self.ex_manager.default_xs._exchange, str(sentinel.xp))

        self.assertIn(sentinel.xp, self.ex_manager.xn_by_name)

        self.ex_manager.delete_xp(xp)

        self.assertNotIn(sentinel.xp, self.ex_manager.xn_by_name)

        # deletion
        self.ex_manager._transport.delete_exchange_impl.assert_called_once_with(self.ex_manager._client, exstr)

    def test_delete_xp_without_creating_it_first(self):
        xpmock = Mock(ExchangePoint)
        xpmock._exchange = sentinel.delete_me

        self.assertRaises(KeyError, self.ex_manager.delete_xp, xpmock)

    def test__create_xn_unknown_type(self):
        self.assertRaises(StandardError, self.ex_manager._create_xn, sentinel.unknown)

    def test_create_xn_service(self):
        xn      = self.ex_manager.create_xn_service('servicename')
        qstr    = '%s.%s' % (xn.exchange, 'servicename')        # what we expect the queue name to look like

        self.assertIsInstance(xn, ExchangeName)
        self.assertIsInstance(xn, ExchangeNameService)

        # exclusive attrs to XN
        self.assertEquals(xn._xs, self.ex_manager.default_xs)
        self.assertEquals(xn._xn_auto_delete, ExchangeNameService._xn_auto_delete)
        self.assertEquals(xn._xn_durable, ExchangeNameService._xn_durable)
        self.assertEquals(xn.xn_type, 'XN_SERVICE')

        # underlying attrs
        self.assertEquals(xn._exchange, None)
        self.assertEquals(xn._queue, 'servicename')
        self.assertEquals(xn._binding, None)

        # top level props
        self.assertEquals(xn.exchange, self.ex_manager.default_xs.exchange)
        self.assertEquals(xn.queue, qstr)
        self.assertEquals(xn.binding, 'servicename')

        # should be in mapping
        self.assertIn('servicename', self.ex_manager.xn_by_name)
        self.assertIn(xn, self.ex_manager.xn_by_xs[ION_ROOT_XS])

        # declaration
        self.ex_manager._transport.declare_queue_impl.assert_called_once(self.ex_manager._client, qstr, durable=ExchangeNameService._xn_durable, auto_delete=ExchangeNameService._xn_auto_delete)

    def test_create_xn_process(self):
        xn = self.ex_manager.create_xn_process('procname')

        self.assertIsInstance(xn, ExchangeName)
        self.assertIsInstance(xn, ExchangeNameProcess)

    def test_create_xn_queue(self):
        xn = self.ex_manager.create_xn_queue('queuename')

        self.assertIsInstance(xn, ExchangeName)
        self.assertIsInstance(xn, ExchangeNameQueue)

    def test_create_xn_with_different_xs(self):
        xs = self.ex_manager.create_xs(sentinel.xs)
        xs_exstr = '%s.ion.xs.%s' % (get_sys_name(), str(sentinel.xs))     # what we expect the exchange property to return

        xn      = self.ex_manager.create_xn_service('servicename', xs)
        qstr    = '%s.%s' % (xn.exchange, 'servicename')        # what we expect the queue name to look like

        # check mappings
        self.assertIn('servicename', self.ex_manager.xn_by_name)
        self.assertIn(xn, self.ex_manager.xn_by_xs[sentinel.xs])

        self.assertEquals(xn.queue, qstr)

    def test_delete_xn(self):
        xn      = self.ex_manager.create_xn_process('procname')
        qstr    = '%s.%s' % (xn.exchange, 'procname')

        self.assertIn('procname', self.ex_manager.xn_by_name)

        self.ex_manager.delete_xn(xn)

        self.assertNotIn('procname', self.ex_manager.xn_by_name)

        # call to broker
        self.ex_manager._transport.delete_queue_impl.assert_called_once_with(self.ex_manager._client, qstr)

    def test_xn_setup_listener(self):
        xn      = self.ex_manager.create_xn_service('servicename')
        qstr    = '%s.%s' % (xn.exchange, 'servicename')        # what we expect the queue name to look like

        xn.setup_listener(sentinel.binding, None)

        self.ex_manager._transport.bind_impl.assert_called_once_with(self.ex_manager._client, xn.exchange, qstr, sentinel.binding)

    def test_xn_bind(self):
        xn      = self.ex_manager.create_xn_service('servicename')

        xn.bind(sentinel.bind)

        self.ex_manager._transport.bind_impl.assert_called_once_with(self.ex_manager._client, xn.exchange, xn.queue, sentinel.bind)

    def test_xn_unbind(self):
        xn      = self.ex_manager.create_xn_service('servicename')

        xn.unbind(sentinel.bind)

        self.ex_manager._transport.unbind_impl.assert_called_once_with(self.ex_manager._client, xn.exchange, xn.queue, sentinel.bind)


@attr('INT', group='exchange')
@patch.dict('pyon.ion.exchange.CFG', {'container':{'exchange':{'auto_register': False}}})
@unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False),'Test reaches into container, doesn\'t work with CEI')
class TestExchangeObjectsInt(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()

    def test_rpc_with_xn(self):
        # get an xn to use for send/recv
        xn = self.container.ex_manager.create_xn_service('hello')

        # create an RPCServer for a hello service
        hs = HelloService()
        rpcs = RPCServer(from_name=xn, service=hs)

        # spawn the listener, kill on test exit (success/fail/error should cover?)
        gl_listen = spawn(rpcs.listen)
        self.addCleanup(gl_listen.kill)

        # ok, now create a client using same xn
        hsc = HelloServiceClient(to_name=xn)

        # try to message it!
        ret = hsc.hello('hi there')

        # did we get back what we expected?
        self.assertEquals(ret, 'BACK:hi there')

        # clean xn up
        xn.delete()

    def test_pubsub_with_xp(self):
        raise unittest.SkipTest("not done yet")

    def test_consume_one_message_at_a_time(self):
        # see also pyon.net.test.test_channel:TestChannelInt.test_consume_one_message_at_a_time

        pub3 = Publisher(to_name=(self.container.ex_manager.default_xs.exchange, 'routed.3'))
        pub5 = Publisher(to_name=(self.container.ex_manager.default_xs.exchange, 'routed.5'))

        #
        # SETUP COMPLETE, BEGIN TESTING OF EXCHANGE OBJECTS
        #

        xq = self.container.ex_manager.create_xn_queue('random_queue')
        self.addCleanup(xq.delete)

        # recv'd messages from the subscriber
        self.recv_queue = Queue()

        sub = Subscriber(from_name=xq, callback=lambda m,h: self.recv_queue.put((m, h)))
        sub.prepare_listener()

        # publish 10 messages - we're not bound yet, so they'll just dissapear
        for x in xrange(10):
            pub3.publish("3,%s" % str(x))

        # no messages yet
        self.assertFalse(sub.get_one_msg(timeout=0))

        # now, we'll bind the xq
        xq.bind('routed.3')

        # even tho we are consuming, there are no messages - the previously published ones all dissapeared
        self.assertFalse(sub.get_one_msg(timeout=0))

        # publish those messages again
        for x in xrange(10):
            pub3.publish("3,%s" % str(x))

        # NOW we have messages!
        for x in xrange(10):
            self.assertTrue(sub.get_one_msg(timeout=0))
            m,h = self.recv_queue.get(timeout=0)
            self.assertEquals(m, "3,%s" % str(x))

        # we've cleared it all
        self.assertFalse(sub.get_one_msg(timeout=0))

        # bind a wildcard and publish on both
        xq.bind('routed.*')

        for x in xrange(10):
            time.sleep(0.3)
            pub3.publish("3,%s" % str(x))
            time.sleep(0.3)
            pub5.publish("5,%s" % str(x))

        # should get all 20, interleaved
        for x in xrange(10):
            self.assertTrue(sub.get_one_msg(timeout=0))
            m, h = self.recv_queue.get(timeout=0)
            self.assertEquals(m, "3,%s" % str(x))

            self.assertTrue(sub.get_one_msg(timeout=0))
            m, h = self.recv_queue.get(timeout=0)
            self.assertEquals(m, "5,%s" % str(x))

        # add 5 binding, remove all other bindings
        xq.bind('routed.5')
        xq.unbind('routed.3')
        xq.unbind('routed.*')

        # try publishing to 3, shouldn't arrive anymore
        pub3.publish("3")

        self.assertFalse(sub.get_one_msg(timeout=0))

        # let's turn off the consumer and let things build up a bit
        sub._chan.stop_consume()

        for x in xrange(10):
            pub5.publish("5,%s" % str(x))

        # 10 messages in the queue, no consumers
        self.assertTupleEqual((10, 0), sub._chan.get_stats())

        # drain queue
        sub._chan.start_consume()
        time.sleep(1)       # yield to allow delivery

        for x in xrange(10):
            self.assertTrue(sub.get_one_msg(timeout=0))
            self.recv_queue.get(timeout=0)

        sub.close()

@attr('INT', group='exchange')
@patch.dict('pyon.ion.exchange.CFG', {'container':{'exchange':{'auto_register': False}}})
class TestExchangeObjectsCreateDelete(IonIntegrationTestCase):
    """
    Tests creation and deletion of things on the broker.

    We're intentionally trying to declare things and have them blow up and catch them.
    This could very well leave things in a bad state on the broker, but the tests should
    still be able to run again and again.

    We need a better way of inspecting the broker.
    https://github.com/auser/alice is a good option, but looks like we need to use a community fork
    on github to make it work on a modern rabbit: https://github.com/paukul/alice/commit/3c984a8b88d00f61a65516b16a66d5174782820b
    """
    def setUp(self):
        self._start_container()

    def test_create_xs(self):
        xs = self.container.ex_manager.create_xs('test_xs')
        self.addCleanup(xs.delete)

        # TEST SPECIFIC: make sure we can't declare exchange (already exists with diff params)
        # get a RecvChannel, mess with the settings to purposely mismatch
        ch = self.container.node.channel(RecvChannel)
        ch._exchange_auto_delete = not xs._xs_auto_delete

        self.assertRaises(TransportError, ch._declare_exchange, xs.exchange)

    def test_create_xp(self):
        xp = self.container.ex_manager.create_xp('test_xp')
        self.addCleanup(xp.delete)

        # TEST SPECIFIC: make sure we can't declare exchange (already exists with diff params)
        # get a RecvChannel, mess with the settings to purposely mismatch
        ch = self.container.node.channel(RecvChannel)
        ch._exchange_auto_delete = not xp._xs._xs_auto_delete

        self.assertRaises(TransportError, ch._declare_exchange, xp.exchange)

    def test_create_xn(self):
        xn = self.container.ex_manager.create_xn_service('test_service')
        self.addCleanup(xn.delete)

        # TEST SPECIFIC: make sure we can't declare queue (already exists with diff params)
        # get a RecvChannel, mess with the settings to purposely mismatch
        ch = self.container.node.channel(RecvChannel)
        ch._queue_auto_delete = not xn._xn_auto_delete

        # must set recv_name (declare queue demands it)
        ch._recv_name = xn

        self.assertRaises(TransportError, ch._declare_queue, xn.queue)

    def test_delete_xs(self):
        # we get interesting here.  we have to create or xs, try to declare again to prove it is there,
        # then delete, then declare to prove we CAN create, then make sure to clean it up.  whew.
        xs = self.container.ex_manager.create_xs('test_xs')

        # prove XS is declared already (can't declare the same named one with diff params)
        ch = self.container.node.channel(RecvChannel)
        ch._exchange_auto_delete = not xs._xs_auto_delete

        self.assertRaises(TransportError, ch._declare_exchange, xs.exchange)

        # now let's delete via ex manager
        self.container.ex_manager.delete_xs(xs)

        # grab another channel and declare (should work fine this time)
        ch = self.container.node.channel(RecvChannel)
        ch._exchange_auto_delete = not xs._xs_auto_delete

        ch._declare_exchange(xs.exchange)

        # cool, now cleanup (we don't expose this via Channel)
        at = AMQPTransport.get_instance()
        at.delete_exchange_impl(ch._amq_chan, xs.exchange)

    def test_delete_xp(self):
        # same as test_delete_xs
        xp = self.container.ex_manager.create_xp('test_xp')

        # prove XS is declared already (can't declare the same named one with diff params)
        ch = self.container.node.channel(RecvChannel)
        ch._exchange_auto_delete = not xp._xs._xs_auto_delete

        self.assertRaises(TransportError, ch._declare_exchange, xp.exchange)

        # now let's delete via ex manager
        self.container.ex_manager.delete_xp(xp)

        # grab another channel and declare (should work fine this time)
        ch = self.container.node.channel(RecvChannel)
        ch._exchange_auto_delete = not xp._xs._xs_auto_delete

        ch._declare_exchange(xp.exchange)

        # cool, now cleanup (we don't expose this via Channel)
        at = AMQPTransport.get_instance()
        at.delete_exchange_impl(ch._amq_chan, xp.exchange)

    def test_delete_xn(self):
        raise unittest.SkipTest("broken 2 mar, skipping for now")
        # same as the other deletes except with queues instead

        xn = self.container.ex_manager.create_xn_service('test_service')

        # prove queue is declared already (can't declare the same named one with diff params)
        ch = self.container.node.channel(RecvChannel)
        ch._queue_auto_delete = not xn._xn_auto_delete

        # must set recv_name
        ch._recv_name = xn
        self.assertRaises(TransportError, ch._declare_queue, xn.queue)

        # now let's delete via ex manager
        self.container.ex_manager.delete_xn(xn)

        # grab another channel and declare (should work fine this time)
        ch = self.container.node.channel(RecvChannel)
        ch._exchange_auto_delete = not xn._xs._xs_auto_delete

        # must set recv_name
        ch._recv_name = xn
        ch._declare_queue(xn.queue)

        # cool, now cleanup (we don't expose this via Channel)
        at = AMQPTransport.get_instance()
        at.delete_queue_impl(ch._amq_chan, xn.queue)
