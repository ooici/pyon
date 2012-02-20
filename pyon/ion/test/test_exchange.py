#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'

from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import IonUnitTestCase
from nose.plugins.attrib import attr
from examples.service.hello_service import HelloService
from interface.services.examples.hello.ihello_service import HelloServiceClient
from pyon.net.endpoint import RPCServer
from pyon.util.async import spawn
import unittest
from pyon.ion.exchange import ExchangeManager, ION_ROOT_XS
from mock import Mock, sentinel
from pyon.net.transport import BaseTransport

@attr('UNIT', group='exchange')
class TestExchangeObjects(IonUnitTestCase):
    def setUp(self):
        self.ex_manager = ExchangeManager(Mock())
        self.ex_manager._transport  = Mock(BaseTransport)
        self.ex_manager._client     = Mock()

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
        xn1 = self.ex_manager.create_xn(self.ex_manager.default_xs, 'xn1')
        self.assertIn('xn1', self.ex_manager.xn_by_name)
        self.assertIn(xn1, self.ex_manager.xn_by_name.values())
        self.assertEquals(xn1, self.ex_manager.xn_by_name['xn1'])

        self.assertEquals({ION_ROOT_XS:[xn1]}, self.ex_manager.xn_by_xs)

        xn2 = self.ex_manager.create_xn(self.ex_manager.default_xs, 'xn2')
        self.assertIn('xn2', self.ex_manager.xn_by_name)
        self.assertIn(xn2, self.ex_manager.xn_by_xs[ION_ROOT_XS])

        # create one under our second xn3
        xn3 = self.ex_manager.create_xn(xs, 'xn3')
        self.assertIn('xn3', self.ex_manager.xn_by_name)
        self.assertIn(xn3, self.ex_manager.xn_by_xs['exchange'])
        self.assertNotIn(xn3, self.ex_manager.xn_by_xs[ION_ROOT_XS])

@attr('INT', group='exchange')
class TestExchangeObjectsInt(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()

    def test_rpc_with_xn(self):
        # get an xn to use for send/recv
        xn = self.container.ex_manager.create_xn(self.container.ex_manager.default_xs, 'hello', auto_delete=False)

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

    def test_pubsub_with_xp(self):
        raise unittest.SkipTest("not done yet")

    def test_exchange_by_name(self):
        raise unittest.SkipTest("not done yet")

    def test_create_xs(self):
        raise unittest.SkipTest("not done yet")

    def test_create_xp(self):
        raise unittest.SkipTest("not done yet")

    def test_create_xn(self):
        raise unittest.SkipTest("not done yet")

    def test_delete_xs(self):
        raise unittest.SkipTest("not done yet")

    def test_delete_xp(self):
        raise unittest.SkipTest("not done yet")

    def test_delete_xn(self):
        raise unittest.SkipTest("not done yet")