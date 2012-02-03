#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'

from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
from pyon.container.cc import Container
import signal
from gevent.event import Event
from mock import Mock, patch

@attr('UNIT')
class TestCC(PyonTestCase):
    def setUp(self):
        self.cc = Container()

    @patch('pyon.container.cc.log')
    @patch('pyon.container.cc.os')
    def test_fail_fast(self, osmock, logmock):
        self.cc.stop = Mock()

        self.cc.fail_fast('dippin dots')

        # make sure it called the things we expect
        self.assertIn('dippin dots', str(logmock.error.call_args_list[0]))
        self.cc.stop.assert_called_once_with()
        osmock.kill.assert_called_once_with(osmock.getpid(), signal.SIGTERM)

@attr('INT')
class TestCCInt(IonIntegrationTestCase):

    def setUp(self):
        # we don't want to connect to AMQP or do a pidfile or any of that jazz - just the proc manager please
        self.cc = Container()
        self.cc.proc_manager.start()
        self.cc.stop = Mock()
        self.cc.stop.side_effect = self.cc.proc_manager.stop()

    def tearDown(self):
        pass

    def test_fail_fast(self):

        # need to install signal protection so we don't kill nosetests!
        ev = Event()
        def no_abort(*args):
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
            ev.set()

        signal.signal(signal.SIGTERM, no_abort)

        # spawn the proc, wait for it to die and kill the container
        def failtarget(*args, **kwargs):
            raise StandardError("I am supposed to fail!")

        self.cc.proc_manager.proc_sup.spawn(('green', failtarget))

        # wait for the kill signal to happen
        ev.wait(timeout=5)

        # verify things got called
        self.cc.stop.assert_called_once_with()

