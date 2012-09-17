#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@date Mon Jul 16 14:07:06 EDT 2012
@file pyon/ion/test/test_stream_pubsub.py
'''

from pyon.util.int_test import IonIntegrationTestCase
from pyon.ion.stream import StreamSubscriber, StreamPublisher
from pyon.ion.process import SimpleProcess
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
        self.route = StreamRoute(exchange_point='xp_test', routing_key='route')
        def verify(message, route, stream):
            self.assertEquals(message,'test')
            self.assertEquals(route, self.route)
            self.assertEquals(stream, '')
            self.verified.set()

        sub_proc = SimpleProcess()
        sub_proc.container = self.container

        sub1 = StreamSubscriber(process=sub_proc, exchange_name='sub1', callback=verify)
        sub1.start()
        self.queue_cleanup.append('sub1')


        pub_proc = SimpleProcess()
        pub_proc.container = self.container
        pub1 = StreamPublisher(process=pub_proc,stream_route=self.route)
        sub1.xn.bind(self.route.routing_key,pub1.xp) 

        pub1.publish('test')

        self.assertTrue(self.verified.wait(2))


