#!/usr/bin/env python
import unittest

__author__ = 'Dave Foster <dfoster@asascience.com>'

from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr
from examples.service.hello_service import HelloService
from interface.services.examples.hello.ihello_service import HelloServiceClient
from pyon.net.endpoint import RPCServer
from pyon.util.async import spawn

@attr('INT', group='exchange')
class TestExchangeObjects(IonIntegrationTestCase):
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