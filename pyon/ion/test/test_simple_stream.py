#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@date Mon Jul 16 14:07:06 EDT 2012
@file pyon/ion/test/test_simple_stream.py
'''

from pyon.util.int_test import IonIntegrationTestCase
from pyon.ion.stream import SimpleStreamPublisher, SimpleStreamSubscriber
from gevent.event import Event

from nose.plugins.attrib import attr
@attr('INT')
class SimpleStreamIntTest(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()

    def test_stream_pub_sub(self):
        exchange_name = 'queue'
        exchange_point = 'test_exchagne'
        self.event = Event()
        def verify(m,h):
            self.event.set()

        sub = SimpleStreamSubscriber.new_subscriber(self.container,exchange_name, verify)
        sub.start()

        xn = self.container.ex_manager.create_xn_queue(exchange_name)
        xp = self.container.ex_manager.create_xp(exchange_point)
        xn.bind('stream_id.data', xp)

        pub = SimpleStreamPublisher.new_publisher(self.container, exchange_point,'stream_id')

        pub.publish('test')
        self.assertTrue(self.event.wait(10))
        sub.stop()


