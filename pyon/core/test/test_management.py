
from unittest import TestCase
from pyon.core.management import *
import logging
from ooi.logging import config, log, TRACE

class AdminMessageTest(TestCase):
    def test_selector_persistence(self):
        msg1 = AllContainers()
        val = str(msg1)
        msg2 = ContainerSelector.from_string(val)
        self.assertEqual(msg1, msg2)

    def test_string_persistence(self):
        msg1 = LogAdmin(AllContainers(), 'ion.agents', logging.INFO, False)
        val = str(msg1)
        msg2 = AdminRequest.from_string(val)
        self.assertEqual(msg1, msg2)

    def test_logging_change(self):
        """ initial log level for ion.processes.event is INFO -- test we can change it to TRACE """
        config.replace_configuration('pyon/core/test/logging.yml')
        log.debug('this should probably not be logged')

        self.assertFalse(log.isEnabledFor(TRACE))
        #
        msg = LogAdmin(AllContainers(), 'pyon.core', 'TRACE')
        msg.perform_action('not really a container')
        #
        self.assertTrue(log.isEnabledFor(TRACE))

    def test_logging_clear(self):
        """ initial log level for ion.processes.event is INFO -- test that we can clear it
            (root level WARN should apply)
        """
        config.replace_configuration('pyon/core/test/logging.yml')
        log.debug('this should probably not be logged')

        self.assertTrue(log.isEnabledFor(logging.INFO))
        #
        msg = LogAdmin(AllContainers(), 'pyon.core', 'NOTSET')
        msg.perform_action('not really a container')
        #
        self.assertFalse(log.isEnabledFor(logging.INFO))


    def test_logging_root(self):
        """ initial root log level is WARN -- test that we can change it to ERROR """
        config.replace_configuration('pyon/core/test/logging.yml')
        otherlog = logging.getLogger('pyon')

        self.assertTrue(otherlog.isEnabledFor(logging.WARN))
        #
        msg = LogAdmin(AllContainers(), '', 'ERROR')
        msg.perform_action('not really a container')
        #
        self.assertFalse(log.isEnabledFor(logging.WARN))
