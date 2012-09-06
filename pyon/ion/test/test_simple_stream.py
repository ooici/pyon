#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@date Mon Jul 16 14:07:06 EDT 2012
@file pyon/ion/test/test_simple_stream.py
'''

from pyon.util.int_test import IonIntegrationTestCase
from pyon.ion.stream import StreamSubscriber, StreamPublisher
from interface.objects import StreamRoute
from gevent.event import Event

from nose.plugins.attrib import attr
@attr('INT')
class StreamPubsubTest(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()

        self.queue_cleanup = []
        self.exchange_cleanup = []

    def tearDown(self):
        for queue in self.queue_cleanup:
            xn = self.container.ex_manager.create_xn_queue(queue)
            xn.delete()
        for exchange in self.exchange_cleanup:
            xp = self.container.ex_manager.create_xp(exchange)
            xp.delete()

    def test_stream_pub_sub(self):
        self.verified = Event()
        def verify(message, route, stream):
            self.assertEquals(message,'test')
            self.verified.set()

        sub1 = StreamSubscriber('sub1', verify)
        sub1.start()
        self.queue_cleanup.append('sub1')

        route = StreamRoute(exchange_point='xp_test', routing_key='route')

        pub1 = StreamPublisher(stream_route=route)
        sub1.xn.bind(route.routing_key,pub1.xp) 

        pub1.publish('test')

        self.assertTrue(self.verified.wait(2))


