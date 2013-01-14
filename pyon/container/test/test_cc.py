#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'

from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
from pyon.container.cc import Container
import signal
from gevent.event import Event
from mock import Mock, patch, ANY
from interface.services.icontainer_agent import ContainerAgentClient
from interface.objects import ProcessStateEnum

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

    @patch('pyon.container.cc.os')
    def test_fail_fast_no_stop(self, osmock):
        self.cc.stop = Mock()

        self.cc.fail_fast("icecream (of the future)", True)
        self.assertEquals(self.cc.stop.call_count, 0)

    def test_node_when_not_started(self):
        self.assertEquals(self.cc.node, None)

    def test_node_when_started(self):
        self.cc._capabilities.append("EXCHANGE_MANAGER")
        self.cc.ex_manager = Mock()

        self.assertEquals(self.cc.node, self.cc.ex_manager.default_node)

@attr('INT')
class TestCCInt(IonIntegrationTestCase):

    def test_start_hello(self):
        # start a service over messaging
        self._start_container()
        cc_client = ContainerAgentClient(node=self.container.node, name=self.container.name)

        p = cc_client.spawn_process('hello', 'examples.service.hello_service', 'HelloService')

@attr('INT')
class TestCCIntProcs(IonIntegrationTestCase):

    class ExpectedFailure(StandardError):
        pass

    def setUp(self):
        # we don't want to connect to AMQP or do a pidfile or any of that jazz - just the proc manager please
        self.cc = Container()
        self.cc.resource_registry = Mock()
        self.cc.resource_registry.create.return_value=["ID","rev"]
        self.cc.event_pub = Mock()

        self.cc.proc_manager.start()

        self.cc.stop = Mock()
        self.cc.stop.side_effect = self.cc.proc_manager.stop

    def tearDown(self):
        pass

