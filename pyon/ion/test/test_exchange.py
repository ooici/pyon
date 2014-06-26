#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'

import unittest
from nose.plugins.attrib import attr
from mock import Mock, sentinel, patch, call, MagicMock
import requests
from gevent.queue import Queue
import os
import time
from gevent.timeout import Timeout
from uuid import uuid4
import simplejson as json
from copy import deepcopy

from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from pyon.core.bootstrap import get_sys_name
from pyon.core import exception
from pyon.core.bootstrap import CFG
from pyon.util.async import spawn
from pyon.ion.exchange import ExchangeManager, ION_ROOT_XS, ExchangeNameProcess, ExchangeNameService, ExchangeName, ExchangeNameQueue, ExchangeManagerError
from pyon.net.endpoint import RPCServer, Subscriber, Publisher
from pyon.net.transport import BaseTransport, NameTrio, TransportError
from pyon.net.messaging import NodeB
from pyon.net.channel import SendChannel
from pyon.util.containers import DotDict

from examples.service.hello_service import HelloService

from interface.services.examples.hello.ihello_service import HelloServiceClient

def _make_exchange_cfg(**kwargs):
    return DotDict(CFG.exchange, exchange_brokers=kwargs)

def _make_broker_cfg(**kwargs):
    default = {'server':'amqp',
               'description':'',
               'join_xs':[ION_ROOT_XS],
               'join_xp':[]}

    default.update(**kwargs)

    ddkwargs = DotDict(default)
    return ddkwargs

dict_amqp                = DotDict(type='amqp')
dict_amqp_again          = DotDict(type='amqp')
dict_amqp_fail           = DotDict(type='amqp')
dict_amqp_not_default    = DotDict(type='amqp')

@attr('UNIT', group='COI')
@patch('pyon.ion.exchange.messaging')
class TestExchangeManager(PyonTestCase):

    def setUp(self):
        self.container = Mock()
        self.ex_manager = ExchangeManager(self.container)
        self.ex_manager.get_transport = Mock()

    def test_verify_service(self, mockmessaging):
        PyonTestCase.test_verify_service(self)

    @patch.dict('pyon.ion.exchange.CFG',
                exchange=_make_exchange_cfg())
    def test_start_with_no_connections(self, mockmessaging):
        self.assertRaises(ExchangeManagerError, self.ex_manager.start)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':dict_amqp, 'postgresql':CFG.server.postgresql},
                exchange=_make_exchange_cfg(system_broker=_make_broker_cfg(server='amqp')))
    def test_start_with_one_connection(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop
        self.ex_manager.start()

        mockmessaging.make_node.assert_called_once_with(dict_amqp, 'system_broker', 0)
        self.assertIn('system_broker', self.ex_manager._nodes)
        self.assertIn('system_broker', self.ex_manager._ioloops)
        self.assertEquals(self.ex_manager._nodes['system_broker'], mockmessaging.make_node.return_value[0])
        self.assertEquals(self.ex_manager._ioloops['system_broker'], mockmessaging.make_node.return_value[1])

    @patch.dict('pyon.ion.exchange.CFG', server={'amqp':dict_amqp, 'amqp_again':dict_amqp_again, 'postgresql':CFG.server.postgresql},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp'),
                                            secondary=_make_broker_cfg(server='amqp_again')))
    def test_start_with_multi_connections(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop
        self.ex_manager.start()

        mockmessaging.make_node.assert_calls(call(dict_amqp, 'primary', 0), call(dict_amqp_again, 'secondary', 0))

        self.assertIn('primary', self.ex_manager._nodes)
        self.assertIn('primary', self.ex_manager._ioloops)
        self.assertEquals(self.ex_manager._nodes['primary'], mockmessaging.make_node.return_value[0])
        self.assertEquals(self.ex_manager._ioloops['primary'], mockmessaging.make_node.return_value[1])

        self.assertIn('secondary', self.ex_manager._nodes)
        self.assertIn('secondary', self.ex_manager._ioloops)
        self.assertEquals(self.ex_manager._nodes['secondary'], mockmessaging.make_node.return_value[0])
        self.assertEquals(self.ex_manager._ioloops['secondary'], mockmessaging.make_node.return_value[1])

    @patch.dict('pyon.ion.exchange.CFG',
                server={},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='idontexist')))
    def test_start_with_non_existing_connection_in_server(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop

        self.assertRaises(ExchangeManagerError, self.ex_manager.start)
        self.assertFalse(mockmessaging.make_node.called)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':dict_amqp, 'amqp_fail':dict_amqp_fail, 'postgresql':CFG.server.postgresql},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp'),
                                            secondary=_make_broker_cfg(server='amqp_fail')))
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

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp_fail':dict_amqp_fail, 'postgresql':CFG.server.postgresql},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp_fail')))
    def test_start_with_only_failing_connections(self, mockmessaging):
        nodemock = Mock()
        nodemock.running = False
        iomock = Mock()

        mockmessaging.make_node.return_value = (nodemock, iomock)

        self.assertRaises(ExchangeManagerError, self.ex_manager.start)
        iomock.kill.assert_called_once_with()

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':dict_amqp, 'postgresql':CFG.server.postgresql},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp')))
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

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp_not_default':dict_amqp_not_default, 'postgresql':CFG.server.postgresql},
                exchange=_make_exchange_cfg(secondary=_make_broker_cfg(server='amqp_not_default')))
    def test_default_node_no_default_name(self, mockmessaging):
        nodemock = Mock()
        mockmessaging.make_node.return_value = (nodemock, Mock())     # node, ioloop

        self.ex_manager.start()

        self.assertEquals(self.ex_manager.default_node, nodemock)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':dict_amqp, 'amqp_again':dict_amqp_again, 'postgresql':CFG.server.postgresql},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp'),
                                            secondary=_make_broker_cfg(server='amqp_again')))
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

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':dict_amqp, 'amqp_again':dict_amqp_again},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp')))
    def test_priv_transports_point_to_default_node(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop
        self.ex_manager.get_transport = Mock()
        self.ex_manager.start()

        self.assertEquals(len(self.ex_manager._priv_transports), 1)
        self.assertIn('primary', self.ex_manager._priv_transports)
        self.ex_manager.get_transport.assert_called_once_with(mockmessaging.make_node.return_value[0])

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':dict_amqp, 'amqp_again':dict_amqp_again},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp', server_priv='amqp_again')))
    def test_start_with_privileged_connection(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop
        self.ex_manager.start()

        mockmessaging.make_node.assert_calls(call(dict_amqp, 'primary', 0), call(dict_amqp_again, 'primary', 0))

        self.assertIn('primary', self.ex_manager._nodes)
        self.assertIn('primary', self.ex_manager._ioloops)
        self.assertEquals(self.ex_manager._nodes['primary'], mockmessaging.make_node.return_value[0])
        self.assertEquals(self.ex_manager._ioloops['primary'], mockmessaging.make_node.return_value[1])

        self.assertIn('primary', self.ex_manager._priv_nodes)
        self.assertIn('primary', self.ex_manager._priv_ioloops)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':dict_amqp, 'amqp_again':dict_amqp_again},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp', server_priv='amqp_again')))
    def test_start_with_privileged_connection_transports_point_to_priv_node(self, mockmessaging):
        non_priv_node = Mock()
        priv_node = Mock()

        mockmessaging.make_node.side_effect = [(non_priv_node, Mock()), (priv_node, Mock())]
        self.ex_manager.get_transport = Mock()
        self.ex_manager.start()

        self.ex_manager.get_transport.assert_called_once_with(priv_node)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':dict_amqp, 'amqp_again':dict_amqp_again},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp', server_priv='amqp_again'),
                                            secondary=_make_broker_cfg(server='amqp_again')))
    def test_start_with_some_privileged_connections(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop
        self.ex_manager.start()

        mockmessaging.make_node.assert_calls(call(dict_amqp, 'primary', 0),
                                             call(dict_amqp_again, 'primary', 0),
                                             call(dict_amqp_again, 'secondary', 0))

        self.assertEquals(len(self.ex_manager._nodes), 2)
        self.assertEquals(len(self.ex_manager._priv_nodes), 1)
        self.assertNotIn('secondary', self.ex_manager._priv_nodes)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':dict_amqp, 'amqp_again':dict_amqp_again},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp', server_priv='amqp_again'),
                                            secondary=_make_broker_cfg(server='amqp_again',
                                                                       join_xs=['blake','keen','dopefish'])))
    def test__get_node_for_xs(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop
        self.ex_manager.start()

        one, _ = self.ex_manager._get_node_for_xs('ioncore')
        self.assertEquals(one, 'primary')

        two, _ = self.ex_manager._get_node_for_xs('keen')
        self.assertEquals(two, 'secondary')

        three, _ = self.ex_manager._get_node_for_xs('dopefish')
        self.assertEquals(three, 'secondary')

        four, _ = self.ex_manager._get_node_for_xs('duke')  # not explicitly known
        self.assertEquals(four, 'primary')

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':dict_amqp, 'amqp_again':dict_amqp_again},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp', server_priv='amqp_again',
                                                                     join_xp=['events', 'data']),
                                            secondary=_make_broker_cfg(server='amqp_again',
                                                                       join_xs=['blake','keen','dopefish'],
                                                                       join_xp=['try'])))
    def test__get_node_for_xp(self, mockmessaging):
        mockmessaging.make_node.return_value = (Mock(), Mock())     # node, ioloop
        self.ex_manager.start()

        one, _ = self.ex_manager._get_node_for_xp('data', 'ioncore')
        self.assertEquals(one, 'primary')

        two, _ = self.ex_manager._get_node_for_xp('data', 'keen')    # maybe not intuitive?
        self.assertEquals(two, 'primary')

        three, _ = self.ex_manager._get_node_for_xp('try', '')
        self.assertEquals(three, 'secondary')

        four, _ = self.ex_manager._get_node_for_xp('unknown', 'dopefish')  # falls back to xs
        self.assertEquals(four, 'secondary')

        five, _ = self.ex_manager._get_node_for_xp('unknown', 'unknown')  # falls back to defaults
        self.assertEquals(five, 'primary')

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

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':CFG.server.amqp, 'postgresql':CFG.server.postgresql},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp')))
    def test_start_stop(self):
        self._start_container()

        self.assertEquals(self.container.node, self.container.ex_manager.default_node)
        self.assertEquals(len(self.container.ex_manager._nodes), 1)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':CFG.server.amqp, 'postgresql':CFG.server.postgresql, 'amqp_fail':fail_bad_user_cfg},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp'),
                                            secondary=_make_broker_cfg(server='amqp_fail')))
    def test_start_stop_with_one_success_and_one_failure(self):
        self._start_container()

        self.assertEquals(len(self.container.ex_manager._nodes), 1)
        self.assertIn('primary', self.container.ex_manager._nodes)
        self.assertNotIn('secondary', self.container.ex_manager._nodes)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':CFG.server.amqp, 'postgresql':CFG.server.postgresql, 'amqp_fail':fail_bad_user_cfg, 'amqp_fail2':fail_bad_port_cfg},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp'),
                                            secondary=_make_broker_cfg(server='amqp_fail'),
                                            thirdly=_make_broker_cfg(server='amqp_fail2')))
    def test_start_stop_with_one_success_and_multiple_failures(self):
        self._start_container()

        self.assertEquals(len(self.container.ex_manager._nodes), 1)
        self.assertIn('primary', self.container.ex_manager._nodes)
        self.assertNotIn('secondary', self.container.ex_manager._nodes)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'postgresql':CFG.server.postgresql, 'amqp':fail_bad_user_cfg},
                exchange=_make_exchange_cfg())
    def test_start_stop_with_no_connections(self):
        self.assertRaises(ExchangeManagerError, self._start_container)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'postgresql':CFG.server.postgresql, 'amqp_bad':fail_bad_port_cfg},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp_bad')))
    def test_start_stop_with_bad_port_failure(self):
        self.assertRaises(ExchangeManagerError, self._start_container)

    @patch.dict('pyon.ion.exchange.CFG',
                server={'postgresql':CFG.server.postgresql, 'amqp_bad':fail_bad_host_cfg},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp_bad')))
    def test_start_stop_with_bad_host_failure(self):
        self.assertRaises(ExchangeManagerError, self._start_container)

    def test_privileged_transport_dying_means_fail_fast(self):
        self._start_container()

        self.container.fail_fast = Mock()

        name = str(uuid4())[0:6]
        bind = str(uuid4())[0:6]

        xn = self.container.ex_manager.create_xn_queue(name)
        self.assertRaises(TransportError, xn.unbind, bind)

        self.assertEquals(self.container.fail_fast.call_count, 1)
        self.assertIn("ExManager privileged transport", self.container.fail_fast.call_args[0][0])

    @patch.dict('pyon.ion.exchange.CFG',
                server={'amqp':CFG.server.amqp, 'postgresql':CFG.server.postgresql},
                exchange=_make_exchange_cfg(primary=_make_broker_cfg(server='amqp', server_priv='amqp')))
    def test_privileged_connection(self):
        self._start_container()

        self.assertEquals(self.container.node, self.container.ex_manager.default_node)
        self.assertEquals(len(self.container.ex_manager._nodes), 1)
        self.assertEquals(len(self.container.ex_manager._priv_nodes), 1)

@attr('UNIT', group='exchange')
class TestExchangeObjects(PyonTestCase):
    def setUp(self):
        self.ex_manager = ExchangeManager(Mock())
        self.pt = Mock(spec=BaseTransport)
        self.ex_manager.get_transport = Mock(return_value=self.pt)

        # set up some nodes
        self.ex_manager._nodes = {'primary': Mock()}

        # skirt some RR/Mock issues
        self.ex_manager._get_xs_obj = Mock(return_value=None)

        # patch for setUp and test
        self.patch_cfg('pyon.ion.exchange.CFG',
                       {'container':{'exchange':{'auto_register':False}},
                        'exchange':_make_exchange_cfg()})

        # start ex manager
        self.ex_manager.start()

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
        self.pt.declare_exchange_impl.assert_called_with(exstr, auto_delete=True, durable=False, exchange_type='topic')

    def test_create_xs_with_params(self):
        xs      = self.ex_manager.create_xs(sentinel.xs, exchange_type=sentinel.ex_type, durable=True)
        exstr   = '%s.ion.xs.%s' % (get_sys_name(), str(sentinel.xs))     # what we expect the exchange property to return

        self.assertEquals(xs._xs_durable, True)
        self.assertEquals(xs._xs_exchange_type, sentinel.ex_type)

        # declaration?
        self.pt.declare_exchange_impl.assert_called_with(exstr, auto_delete=True, durable=True, exchange_type=sentinel.ex_type)

    def test_delete_xs(self):
        # need an XS first
        xs      = self.ex_manager.create_xs(sentinel.delete_me)
        exstr   = '%s.ion.xs.%s' % (get_sys_name(), str(sentinel.delete_me))     # what we expect the exchange property to return

        self.assertIn(sentinel.delete_me, self.ex_manager.xs_by_name)

        self.ex_manager.delete_xs(xs)

        self.assertNotIn(sentinel.delete_me, self.ex_manager.xs_by_name)

        # call to broker
        self.pt.delete_exchange_impl.assert_called_once_with(exstr)

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
        self.pt.declare_exchange_impl.assert_called_with(exstr)

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
        self.pt.delete_exchange_impl.assert_called_once_with(exstr)

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
        self.pt.declare_queue_impl.assert_called_once(qstr, durable=ExchangeNameService._xn_durable, auto_delete=ExchangeNameService._xn_auto_delete)

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
        self.pt.delete_queue_impl.assert_called_once_with(qstr)

    def test_xn_setup_listener(self):
        xn      = self.ex_manager.create_xn_service('servicename')
        qstr    = '%s.%s' % (xn.exchange, 'servicename')        # what we expect the queue name to look like

        xn.setup_listener(sentinel.binding, None)

        self.pt.bind_impl.assert_called_once_with(xn.exchange, qstr, sentinel.binding)

    def test_xn_bind(self):
        xn      = self.ex_manager.create_xn_service('servicename')

        xn.bind(sentinel.bind)

        self.pt.bind_impl.assert_called_once_with(xn.exchange, xn.queue, sentinel.bind)

    def test_xn_unbind(self):
        xn      = self.ex_manager.create_xn_service('servicename')

        xn.unbind(sentinel.bind)

        self.pt.unbind_impl.assert_called_once_with(xn.exchange, xn.queue, sentinel.bind)


@attr('INT', group='exchange')
@unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False),'Test reaches into container, doesn\'t work with CEI')
class TestExchangeObjectsInt(IonIntegrationTestCase):
    def setUp(self):
        self.patch_cfg('pyon.ion.exchange.CFG', {'container':{'profile':"res/profile/development.yml",
                                                              'datastore':CFG['container']['datastore'],
                                                              'exchange':{'auto_register': False}},
                                                 'exchange': _make_exchange_cfg(system_broker=_make_broker_cfg(server='amqp'),
                                                                                other=_make_broker_cfg(server='amqp', join_xs=['other'])),
                                                 'server':CFG['server']})
        self._start_container()

    def test_rpc_with_xn(self):
        # get an xn to use for send/recv
        xn = self.container.ex_manager.create_xn_service('hello')
        self.addCleanup(xn.delete)

        # create an RPCServer for a hello service
        hs = HelloService()
        rpcs = RPCServer(from_name=xn, service=hs)

        # spawn the listener, kill on test exit (success/fail/error should cover?)
        gl_listen = spawn(rpcs.listen)
        def cleanup():
            rpcs.close()
            gl_listen.join(timeout=2)
            gl_listen.kill()
        self.addCleanup(cleanup)

        # wait for listen to be ready
        rpcs.get_ready_event().wait(timeout=5)

        # ok, now create a client using same xn
        hsc = HelloServiceClient(to_name=xn)

        # try to message it!
        ret = hsc.hello('hi there')

        # did we get back what we expected?
        self.assertEquals(ret, 'BACK:hi there')

    def test_create_xn_on_diff_broker(self):
        xs = self.container.create_xs('other')
        self.assertEquals(xs.node, self.container.ex_manager._nodes['other'])

        xn = self.container.create_xn_service('hello', xs=xs)
        self.assertEquals(xn.node, self.container.ex_manager._nodes['other'])

        xn = self.container.create_xn_service('other_hello')
        self.assertEquals(xn.node, self.container.ex_manager._nodes['system_broker'])

        # @TODO: name collisions in xn_by_name/RR with same name/different XS?
        # should likely raise error

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

        def cb(m, h):
            raise StandardError("Subscriber callback never gets called back!")

        sub = Subscriber(from_name=xq, callback=cb)
        sub.initialize()

        # publish 10 messages - we're not bound yet, so they'll just dissapear
        for x in xrange(10):
            pub3.publish("3,%s" % str(x))

        # allow time for routing
        time.sleep(2)

        # no messages yet
        self.assertRaises(Timeout, sub.get_one_msg, timeout=0)

        # now, we'll bind the xq
        xq.bind('routed.3')

        # even tho we are consuming, there are no messages - the previously published ones all dissapeared
        self.assertRaises(Timeout, sub.get_one_msg, timeout=0)

        # publish those messages again
        for x in xrange(10):
            pub3.publish("3,%s" % str(x))

        # allow time for routing
        time.sleep(2)

        # NOW we have messages!
        for x in xrange(10):
            mo = sub.get_one_msg(timeout=10)
            self.assertEquals(mo.body, "3,%s" % str(x))
            mo.ack()

        # we've cleared it all
        self.assertRaises(Timeout, sub.get_one_msg, timeout=0)

        # bind a wildcard and publish on both
        xq.bind('routed.*')

        for x in xrange(10):
            time.sleep(0.3)
            pub3.publish("3,%s" % str(x))
            time.sleep(0.3)
            pub5.publish("5,%s" % str(x))

        # allow time for routing
        time.sleep(2)

        # should get all 20, interleaved
        for x in xrange(10):
            mo = sub.get_one_msg(timeout=1)
            self.assertEquals(mo.body, "3,%s" % str(x))
            mo.ack()

            mo = sub.get_one_msg(timeout=1)
            self.assertEquals(mo.body, "5,%s" % str(x))
            mo.ack()

        # add 5 binding, remove all other bindings
        xq.bind('routed.5')
        xq.unbind('routed.3')
        xq.unbind('routed.*')

        # try publishing to 3, shouldn't arrive anymore
        pub3.publish("3")

        self.assertRaises(Timeout, sub.get_one_msg, timeout=0)

        # let's turn off the consumer and let things build up a bit
        sub._chan.stop_consume()

        for x in xrange(10):
            pub5.publish("5,%s" % str(x))

        # allow time for routing
        time.sleep(2)

        # 10 messages in the queue, no consumers
        self.assertTupleEqual((10, 0), sub._chan.get_stats())

        # drain queue
        sub._chan.start_consume()

        for x in xrange(10):
            mo = sub.get_one_msg(timeout=1)
            mo.ack()

        sub.close()

@attr('INT', group='exchange')
@unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False),'Test reaches into container, doesn\'t work with CEI')
class TestExchangeObjectsIntWithLocal(TestExchangeObjectsInt):
    def setUp(self):
        self.patch_cfg('pyon.ion.exchange.CFG', {'container':{'profile':"res/profile/development.yml",
                                                              'datastore':CFG['container']['datastore'],
                                                              'exchange':{'auto_register': False}},
                                                 'exchange': _make_exchange_cfg(system_broker=_make_broker_cfg(server='amqp')),
                                                 'server':CFG['server']})
        self._start_container()


@attr('INT', group='exchange')
@patch.dict('pyon.ion.exchange.CFG', {'container':{'capability':{'profile':"res/profile/development.yml"},'exchange':{'auto_register': False}}})
class TestExchangeObjectsCreateDelete(IonIntegrationTestCase):
    """
    Tests creation and deletion of things on the broker.
    """
    def setUp(self):
        self._start_container()

        # skip if we're not an amqp node
        if not isinstance(self.container.ex_manager.default_node, NodeB):
            raise unittest.SkipTest("Management API only works with AMQP nodes for now")

        # test to see if we have access to management URL!
        url = self.container.ex_manager._get_management_url('overview')
        try:
            self.container.ex_manager._make_management_call(url, use_ems=False)
        except exception.IonException as ex:
            raise unittest.SkipTest("Cannot find management API: %s" % str(ex))

    def test_create_xs(self):
        xs = self.container.ex_manager.create_xs('test_xs')
        self.addCleanup(xs.delete)

        self.assertIn(xs.exchange, self.container.ex_manager.list_exchanges())

    def test_create_xp(self):
        xp = self.container.ex_manager.create_xp('test_xp')
        self.addCleanup(xp.delete)

        self.assertIn(xp.exchange, self.container.ex_manager.list_exchanges())

    def test_create_xn(self):
        xn = self.container.ex_manager.create_xn_service('test_service')
        self.addCleanup(xn.delete)

        self.assertIn(xn.queue, self.container.ex_manager.list_queues())

    def test_delete_xs(self):
        xs = self.container.ex_manager.create_xs('test_xs')

        self.assertIn(xs.exchange, self.container.ex_manager.list_exchanges())

        # now let's delete via ex manager
        self.container.ex_manager.delete_xs(xs)

        self.assertNotIn(xs.exchange, self.container.ex_manager.list_exchanges())

    def test_delete_xp(self):
        # same as test_delete_xs
        xp = self.container.ex_manager.create_xp('test_xp')

        self.assertIn(xp.exchange, self.container.ex_manager.list_exchanges())

        # now let's delete via ex manager
        self.container.ex_manager.delete_xp(xp)

        self.assertNotIn(xp.exchange, self.container.ex_manager.list_exchanges())

    def test_delete_xn(self):
        # same as the other deletes except with queues instead

        xn = self.container.ex_manager.create_xn_service('test_service')

        self.assertIn(xn.queue, self.container.ex_manager.list_queues())

        # now let's delete via ex manager
        self.container.ex_manager.delete_xn(xn)

        self.assertNotIn(xn.queue, self.container.ex_manager.list_queues())

@attr('INT', group='exchange')
@patch.dict('pyon.ion.exchange.CFG', {'container':{'exchange':{'auto_register': False,
                                                               'names':{'durable':True}}}})
class TestExchangeObjectsDurableFlag(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()
        def cleanup_broker():
            # @Dave: This is maybe too brute force and there is maybe a better pattern...
            connect_str = "-q -H %s -P %s -u %s -p %s -V %s" % (CFG.get_safe('server.amqp_priv.host', CFG.get_safe('server.amqp.host', 'localhost')),
                                                                   CFG.get_safe('container.exchange.management.port', '55672'),
                                                                   CFG.get_safe('container.exchange.management.username', 'guest'),
                                                                   CFG.get_safe('container.exchange.management.password', 'guest'),
                                                                   '/')

            from putil.rabbithelper import clean_by_sysname
            clean_by_sysname(connect_str, get_sys_name())
        self.addCleanup(cleanup_broker)

    @patch.dict('pyon.ion.exchange.CFG', {'container':{'exchange':{'names':{'durable':False}}}})
    def test_durable_off_on_create(self):
        xq = self.container.ex_manager.create_xn_queue('belb')
        self.addCleanup(xq.delete)

        # declared, find it via internal management API call
        all_queues = self.container.ex_manager._list_queues()
        filtered = [q['durable'] for q in all_queues if q['name'] == xq.queue]

        self.assertNotEquals([], filtered)
        self.assertEquals(len(filtered), 1)
        self.assertFalse(filtered[0])       # not durable

    def test_durable_on_on_create(self):
        xq = self.container.ex_manager.create_xn_queue('belb')
        self.addCleanup(xq.delete)

        # declared, find it via internal management API call
        all_queues = self.container.ex_manager._list_queues()
        filtered = [q['durable'] for q in all_queues if q['name'] == xq.queue]

        self.assertNotEquals([], filtered)
        self.assertEquals(len(filtered), 1)
        self.assertTrue(filtered[0])       # IS durable

    def test_xp_durable_send(self):
        xp = self.container.ex_manager.create_xp('an_xp')
        #self.addCleanup(xp.delete)

        xq = self.container.ex_manager.create_xn_queue('no_matter', xp)
        self.addCleanup(xq.delete)
        xq.bind('one')

        pub = Publisher(to_name=xp.create_route('one'))
        pub.publish('test')
        pub.close()


        try:
            url = self.container.ex_manager._get_management_url("queues", "%2f", xq.queue, "get")
            res = self.container.ex_manager._make_management_call(url,
                                                                  use_ems=False,
                                                                  method='post',
                                                                  data=json.dumps({'count':1, 'requeue':True,'encoding':'auto'}))

            self.assertEquals(len(res), 1)
            self.assertIn('properties', res[0])
            self.assertIn('delivery_mode', res[0]['properties'])
            self.assertEquals(2, res[0]['properties']['delivery_mode'])

        except Exception, e:
            # Rabbit 3.x does not support this command anymore apparently.
            self.assertIn('Method Not Allowed', e.message)

    def test_xn_service_is_not_durable_with_cfg_on(self):
        xns = self.container.ex_manager.create_xn_service('fake_service')
        self.addCleanup(xns.delete)

        # declared, find it via internal management API call
        all_queues = self.container.ex_manager._list_queues()
        filtered = [q['durable'] for q in all_queues if q['name'] == xns.queue]

        self.assertNotEquals([], filtered)
        self.assertEquals(len(filtered), 1)
        self.assertFalse(filtered[0])       # not durable, even tho config says base ones are

@attr('UNIT', group='exchange')
@patch.dict('pyon.ion.exchange.CFG', {'container':{'exchange':{'auto_register': False, 'management':{'username':'user', 'password':'pass', 'port':'port'}}}})
class TestManagementAPI(PyonTestCase):
    def setUp(self):
        self.ex_manager = ExchangeManager(Mock())
        self.ex_manager._priv_nodes = MagicMock()
        self.ex_manager._priv_nodes.get.return_value.client.parameters.host = "testhost" # stringifies so don't use sentinel

        self.ex_manager._ems_client = Mock()

    def test__get_management_url(self):
        url = self.ex_manager._get_management_url()

        self.assertEquals(url, "http://testhost:port/api/")

    def test__get_management_url_with_parts(self):
        url = self.ex_manager._get_management_url("test", "this")

        self.assertEquals(url, "http://testhost:port/api/test/this")

    @patch('pyon.ion.exchange.json')
    @patch('pyon.ion.exchange.requests')
    def test__call_management(self, reqmock, jsonmock):
        content = self.ex_manager._call_management(sentinel.url)

        self.assertEquals(content, jsonmock.loads.return_value)
        reqmock.get.assert_called_once_with(sentinel.url, auth=('user', 'pass'), data=None)

    @patch('pyon.ion.exchange.json')
    @patch('pyon.ion.exchange.requests')
    def test__call_management_delete(self, reqmock, jsonmock):
        content = self.ex_manager._call_management_delete(sentinel.url)

        self.assertEquals(content, jsonmock.loads.return_value)
        reqmock.delete.assert_called_once_with(sentinel.url, auth=('user', 'pass'), data=None)

    @patch('pyon.ion.exchange.json')
    @patch('pyon.ion.exchange.requests')
    def test__make_management_call(self, reqmock, jsonmock):
        content = self.ex_manager._make_management_call(sentinel.url, method="scoop")

        reqmock.scoop.assert_called_once_with(sentinel.url, auth=('user', 'pass'), data=None)

    def test__make_management_call_delegates_to_ems(self):
        self.ex_manager._ems_available = Mock(return_value=True)

        content = self.ex_manager._make_management_call(sentinel.url, method=sentinel.anymeth)

        self.ex_manager._ems_client.call_management.assert_called_once_with(sentinel.url, sentinel.anymeth, headers=None)

    def test__make_management_call_raises_exceptions(self):
        rmock = Mock()
        rmock.return_value.raise_for_status.side_effect = requests.exceptions.Timeout

        with patch('pyon.ion.exchange.requests.get', rmock):
            self.assertRaises(exception.Timeout, self.ex_manager._make_management_call, sentinel.url, use_ems=False)

    def test_list_queues_does_filtering(self):
        self.ex_manager._list_queues = Mock(return_value=[{'name':'a_1'}, {'name':'a_2'}, {'name':'b_1'}, {'name':'b_2'}])

        self.assertEquals(len(self.ex_manager.list_queues("a_")), 2)
        self.assertEquals(len(self.ex_manager.list_queues("b_")), 2)
        self.assertEquals(len(self.ex_manager.list_queues("_")), 4)
        self.assertEquals(len(self.ex_manager.list_queues("_1")), 2)
        self.assertEquals(len(self.ex_manager.list_queues("_2")), 2)

    def test_list_bindings_does_filtering(self):
        self.ex_manager._list_bindings = Mock(return_value=[{'source':'ex_1', 'destination':'qq', 'routing_key':'', 'properties_key':'', 'destination_type':'queue'},
                                                            {'source':'ex_2', 'destination':'qa', 'routing_key':'', 'properties_key':'', 'destination_type':'queue'},
                                                            {'source':'ex_1', 'destination':'aq', 'routing_key':'', 'properties_key':'', 'destination_type':'queue'},
                                                            {'source':'ex_2', 'destination':'za', 'routing_key':'', 'properties_key':'', 'destination_type':'queue'},])

        self.assertEquals(len(self.ex_manager.list_bindings(exchange="ex_1")), 2)
        self.assertEquals(len(self.ex_manager.list_bindings(exchange="ex_2")), 2)
        self.assertEquals(len(self.ex_manager.list_bindings(exchange="ex_")), 4)
        self.assertEquals(len(self.ex_manager.list_bindings(queue="qq")), 1)
        self.assertEquals(len(self.ex_manager.list_bindings(queue="a")), 3)
        self.assertEquals(len(self.ex_manager.list_bindings(queue="q")), 3)


@attr('INT', group='exchange')
@patch.dict('pyon.ion.exchange.CFG', {'container':{'exchange':{'auto_register': False}}})
@unittest.skipIf(os.getenv('CEI_LAUNCH_TEST', False),'Test reaches into container, doesn\'t work with CEI')
class TestManagementAPIInt(IonIntegrationTestCase):

    def setUp(self):
        self._start_container()

        # skip if we're not an amqp node
        if not isinstance(self.container.ex_manager.default_node, NodeB):
            raise unittest.SkipTest("Management API only works with AMQP nodes for now")

        self.transport = self.container.ex_manager.get_transport(self.container.ex_manager.default_node)

        # test to see if we have access to management URL!
        url = self.container.ex_manager._get_management_url('overview')
        try:
            self.container.ex_manager._make_management_call(url, use_ems=False)
        except exception.IonException as ex:
            raise unittest.SkipTest("Cannot find management API: %s" % str(ex))

        self.ex_name = ".".join([get_sys_name(), "ex", str(uuid4())[0:6]])
        self.queue_name = ".".join([get_sys_name(), "q", str(uuid4())[0:6]])
        self.bind_name = str(uuid4())[0:6]

    def test_list_exchanges(self):

        exchanges = self.container.ex_manager.list_exchanges()

        self.assertNotIn(self.ex_name, exchanges)

        # do declaration via ex manager's transport
        self.transport.declare_exchange_impl(self.ex_name)
        self.addCleanup(self.transport.delete_exchange_impl, self.ex_name)

        new_exchanges = self.container.ex_manager.list_exchanges()

        self.assertNotEquals(exchanges, new_exchanges)
        self.assertIn(self.ex_name, new_exchanges)

    def test_list_queues(self):

        queues = self.container.ex_manager.list_queues()

        self.assertNotIn(self.queue_name, queues)

        # do declaration via ex manager's transport
        self.transport.declare_queue_impl(self.queue_name)
        self.addCleanup(self.transport.delete_queue_impl, self.queue_name)

        new_queues = self.container.ex_manager.list_queues()

        self.assertNotEquals(queues, new_queues)
        self.assertIn(self.queue_name, new_queues)

    def test_list_bindings(self):

        # declare both ex and queue
        self.transport.declare_exchange_impl(self.ex_name)
        self.transport.declare_queue_impl(self.queue_name)

        self.addCleanup(self.transport.delete_queue_impl, self.queue_name)
        #self.addCleanup(self.container.ex_manager.delete_exchange, self.ex_name)   #@TODO exchange AD takes care of this when delete of queue

        bindings = self.container.ex_manager.list_bindings()

        # test only - extract the 4-tuples into just 2-tuples here to make sure we have no binds
        bindings = [(x[0], x[1]) for x in bindings]
        self.assertNotIn((self.ex_name, self.queue_name), bindings)

        # declare a bind
        self.transport.bind_impl(self.ex_name, self.queue_name, self.bind_name)
        self.addCleanup(self.transport.unbind_impl, self.ex_name, self.queue_name, self.bind_name)

        bindings = self.container.ex_manager.list_bindings()

        self.assertIn((self.ex_name, self.queue_name, self.bind_name, self.bind_name), bindings)

    def test_list_bindings_for_queue(self):

        # declare both ex and queue
        self.transport.declare_exchange_impl(self.ex_name)
        self.transport.declare_queue_impl(self.queue_name)

        self.addCleanup(self.transport.delete_queue_impl, self.queue_name)
        #self.addCleanup(self.container.ex_manager.delete_exchange, self.ex_name)   #@TODO exchange AD takes care of this when delete of queue

        bindings = self.container.ex_manager.list_bindings_for_queue(self.queue_name)
        self.assertEquals(bindings, [])

        # declare a bind
        self.transport.bind_impl(self.ex_name, self.queue_name, self.bind_name)
        self.addCleanup(self.transport.unbind_impl, self.ex_name, self.queue_name, self.bind_name)

        bindings = self.container.ex_manager.list_bindings_for_queue(self.queue_name)

        self.assertEquals(bindings, [(self.ex_name, self.queue_name, self.bind_name, self.bind_name)])

    def test_list_bindings_for_exchange(self):

        # declare both ex and queue
        self.transport.declare_exchange_impl(self.ex_name)
        self.transport.declare_queue_impl(self.queue_name)

        self.addCleanup(self.transport.delete_queue_impl, self.queue_name)
        #self.addCleanup(self.container.ex_manager.delete_exchange, self.ex_name)   #@TODO exchange AD takes care of this when delete of queue

        bindings = self.container.ex_manager.list_bindings_for_exchange(self.ex_name)
        self.assertEquals(bindings, [])

        # declare a bind
        self.transport.bind_impl(self.ex_name, self.queue_name, self.bind_name)
        self.addCleanup(self.transport.unbind_impl, self.ex_name, self.queue_name, self.bind_name)

        bindings = self.container.ex_manager.list_bindings_for_exchange(self.ex_name)

        self.assertEquals(bindings, [(self.ex_name, self.queue_name, self.bind_name, self.bind_name)])

    def test_delete_binding(self):

        # declare both ex and queue
        self.transport.declare_exchange_impl(self.ex_name)
        self.transport.declare_queue_impl(self.queue_name)

        self.addCleanup(self.transport.delete_queue_impl, self.queue_name)
        #self.addCleanup(self.container.ex_manager.delete_exchange, self.ex_name)   #@TODO exchange AD takes care of this when delete of queue

        bindings = self.container.ex_manager.list_bindings_for_exchange(self.ex_name)
        self.assertEquals(bindings, [])

        # declare a bind
        self.transport.bind_impl(self.ex_name, self.queue_name, self.bind_name)

        bindings = self.container.ex_manager.list_bindings_for_exchange(self.ex_name)

        self.assertEquals(bindings, [(self.ex_name, self.queue_name, self.bind_name, self.bind_name)])

        # delete the bind
        self.transport.unbind_impl(self.ex_name, self.queue_name, self.bind_name)

        bindings = self.container.ex_manager.list_bindings_for_exchange(self.ex_name)
        self.assertEquals(bindings, [])

    def test_purge(self):
        # declare both ex and queue
        self.transport.declare_exchange_impl(self.ex_name)
        self.transport.declare_queue_impl(self.queue_name)

        self.addCleanup(self.transport.delete_queue_impl, self.queue_name)
        #self.addCleanup(self.container.ex_manager.delete_exchange, self.ex_name)   #@TODO exchange AD takes care of this when delete of queue

        # declare a bind
        self.transport.bind_impl(self.ex_name, self.queue_name, self.bind_name)

        # deliver some messages
        ch = self.container.node.channel(SendChannel)
        ch._send_name = NameTrio(self.ex_name, self.bind_name)

        ch.send('one')
        ch.send('two')

        ch.close()

        # should have two messages after routing happens (non-deterministic)
        time.sleep(2)

        queue_info = self.container.ex_manager.get_queue_info(self.queue_name)
        self.assertEquals(queue_info['messages'], 2)

        # now purge it
        self.transport.purge_impl(self.queue_name)

        time.sleep(2)

        queue_info = self.container.ex_manager.get_queue_info(self.queue_name)
        self.assertEquals(queue_info['messages'], 0)

    def test_get_queue_info_not_declared(self):
        # try and make sure raises due to not exist
        self.assertRaises(exception.ServerError, self.container.ex_manager.get_queue_info, self.queue_name)

    def test_get_queue_info(self):
        # declare both ex and queue
        self.transport.declare_exchange_impl(self.ex_name)
        self.transport.declare_queue_impl(self.queue_name)

        self.addCleanup(self.transport.delete_queue_impl, self.queue_name)
        #self.addCleanup(self.container.ex_manager.delete_exchange, self.ex_name)   #@TODO exchange AD takes care of this when delete of queue

        queue_info = self.container.ex_manager.get_queue_info(self.queue_name)
        self.assertEquals(queue_info['name'], self.queue_name)

    def test_delete_queue(self):
        self.transport.declare_queue_impl(self.queue_name)
        queues = self.container.ex_manager.list_queues()

        self.assertIn(self.queue_name, queues)

        self.container.ex_manager.delete_queue(self.queue_name)

        new_queues = self.container.ex_manager.list_queues()

        self.assertNotEquals(queues, new_queues)
        self.assertNotIn(self.queue_name, new_queues)

