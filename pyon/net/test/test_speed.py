#!/usr/bin/env python
from pyon.net.endpoint import Publisher

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.util.int_test import IonIntegrationTestCase
from interface.services.examples.hello.ihello_service import HelloServiceClient
from nose.plugins.attrib import attr
import time
import sys
from pyon.util.async import spawn

@attr('PFM')
class TestMessagingSpeed(IonIntegrationTestCase):

    def setUp(self):
        self._start_container()
        self.container.start_rel_from_url('res/deploy/examples/hello.yml')

    def tearDown(self):
        self._stop_container()

    def test_rpc_speed(self):
        hsc = HelloServiceClient()

        print >>sys.stderr, ""

        self.counter = 0
        self.alive = True
        def sendem():
            while self.alive:
                hsc.noop('data')
                self.counter += 1

        start_time = time.time()

        sendgl = spawn(sendem)
        time.sleep(5)
        end_time = time.time()

        self.alive = False
        sendgl.join(timeout=2)
        sendgl.kill()

        diff = end_time - start_time
        mps = float(self.counter) / diff

        print >>sys.stderr, "Requests per second (RPC):", mps, "(", self.counter, "messages in", diff, "seconds)"

    def test_pub_speed(self):
        pub = Publisher(node=self.container.node, name="i_no_exist")

        print >>sys.stderr, ""

        self.counter = 0
        self.alive = True
        def sendem():
            while self.alive:
                self.counter += 1
                pub.publish('meh')

        start_time = time.time()

        sendgl = spawn(sendem)
        time.sleep(5)
        end_time = time.time()

        self.alive = False
        sendgl.join(timeout=2)
        sendgl.kill()



        diff = end_time - start_time
        mps = float(self.counter) / diff

        print >>sys.stderr, "Published messages per second:", mps, "(", self.counter, "messages in", diff, "seconds)"