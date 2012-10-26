#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@date Thu Oct 25 15:41:44 EDT 2012
@file pyon/util/test/test_poller.py
@brief Test for poller
'''

from pyon.util.unit_test import PyonTestCase
from pyon.util.poller import poll
from nose.plugins.attrib import attr
import gevent


@attr('UNIT')
class TestPoller(PyonTestCase):
    counter = 0
    def test_polling(self):
        with self.assertRaises(gevent.timeout.Timeout):
            def callback_bad():
                return False

            poll(callback_bad, timeout=0.5)

        def callback_good():
            self.counter+=1
            return (self.counter == 2)

        self.assertTrue(poll(callback_good, timeout=0.5))



