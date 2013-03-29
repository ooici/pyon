
from pyon.util.unit_test import PyonTestCase
import pyon.container.management
import interface.objects
import logging
from ooi.logging import config, log, TRACE
from pyon.core.bootstrap import IonObject
from pyon.ion.resource import OT

#config.set_debug(True)

class AdminMessageTest(PyonTestCase):
#    def setUp(self):
#        pyon.core.bootstrap._ob
    def test_selector_peer(self):
        ion = IonObject(OT.AllContainers)
        obj = pyon.container.management.ContainerSelector.from_object(ion)
        ion2 = obj.get_peer()
        self.assertEqual(ion.type_,ion2.type_)

    def test_logging_handler(self):
        """ initial log level for ion.processes.event is INFO -- test we can change it to TRACE """
        config.replace_configuration('pyon/container/test/logging.yml')
        log.debug('this should probably not be logged')

        self.assertFalse(log.isEnabledFor(TRACE))
        #
        handler = pyon.container.management.LogLevelHandler()
        action = IonObject(OT.ChangeLogLevel, logger='pyon.container', level='TRACE')
        handler.handle_request(action)
        #
        self.assertTrue(log.isEnabledFor(TRACE))

    def test_logging_clear(self):
        """ initial log level for ion.processes.event is INFO -- test that we can clear it
            (root level WARN should apply)
        """
        config.replace_configuration('pyon/container/test/logging.yml')
        log.debug('this should probably not be logged')

        self.assertTrue(log.isEnabledFor(logging.INFO), msg=repr(log.__dict__))
        #
        handler = pyon.container.management.LogLevelHandler()
        action = IonObject(OT.ChangeLogLevel, logger='pyon.container', level='NOTSET')
        handler.handle_request(action)
        #
        self.assertFalse(log.isEnabledFor(logging.INFO))


    def test_logging_root(self):
        """ initial root log level is WARN -- test that we can change it to ERROR """
        config.replace_configuration('pyon/container/test/logging.yml')
        otherlog = logging.getLogger('pyon')

        self.assertTrue(otherlog.isEnabledFor(logging.WARN))
        #
        handler = pyon.container.management.LogLevelHandler()
        action = IonObject(OT.ChangeLogLevel, logger='', level='ERROR')
        handler.handle_request(action)
        #
        self.assertFalse(otherlog.isEnabledFor(logging.WARN))

    def test_policy_cache_handler(self):
        """ initial log level for ion.processes.event is INFO -- test we can change it to TRACE """

        #
        handler = pyon.container.management.PolicyCacheHandler()
        action = IonObject(OT.ResetPolicyCache)
        handler.handle_request(action)
        #

    def test_garbage_collection_handler(self):
        """ initial log level for ion.processes.event is INFO -- test we can change it to TRACE """

        #
        handler = pyon.container.management.GarbageCollectionHandler()
        action = IonObject(OT.TriggerGarbageCollection)
        handler.handle_request(action)
        #
