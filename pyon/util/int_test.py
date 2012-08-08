#!/usr/bin/env python

"""Integration test base class and utils"""

from mock import patch
import unittest
import os
from gevent import greenlet, spawn

from pyon.container.cc import Container
from pyon.core import bootstrap
from pyon.core.bootstrap import bootstrap_pyon, CFG
from pyon.core.interfaces.interfaces import InterfaceAdmin
from pyon.util.log import log


def pre_initialize_ion():
    # Do necessary system initialization
    # Make sure this happens only once
    iadm = InterfaceAdmin(bootstrap.get_sys_name(), config=CFG)
    iadm.create_core_datastores()
    #iadm.store_config(CFG)
    iadm.store_interfaces(idempotent=True)
    iadm.close()

# This is the only place where code is executed once before any integration test
# is run.
def initialize_ion_int_tests():
    # Bootstrap pyon CFG, logging and object/resource interfaces
    bootstrap_pyon()
    if bootstrap.is_testing():
        IonIntegrationTestCase._force_clean(False)
        pre_initialize_ion()



class IonIntegrationTestCase(unittest.TestCase):
    """
    Base test class to allow operations such as starting the container
    TODO: Integrate with IonUnitTestCase
    """

    def run(self, result=None):
        unittest.TestCase.run(self, result)

    def _start_container(self):
        # hack to force queue auto delete on for int tests
        self._turn_on_queue_auto_delete()
        self._patch_out_diediedie()
        self._patch_out_fail_fast_kill()

        bootstrap.testing_fast = True

        if os.environ.get('CEI_LAUNCH_TEST', None):
            # Let's force clean again.  The static initializer is causing
            # issues
            self._force_clean()
            self._patch_out_start_rel()
            from pyon.datastore.datastore_admin import DatastoreAdmin
            da = DatastoreAdmin(config=CFG)
            da.load_datastore('res/dd')
        else:
            # We cannot live without pre-initialized datastores and resource objects
            pre_initialize_ion()

        # hack to force_clean on filesystem
        try:
            CFG['container']['filesystem']['force_clean'] = True
        except KeyError:
            CFG['container']['filesystem'] = {}
            CFG['container']['filesystem']['force_clean'] = True

        self.container = None
        self.addCleanup(self._stop_container)
        self.container = Container()
        self.container.start()

        bootstrap.testing_fast = False


    def _stop_container(self):
        bootstrap.testing_fast = True
        if self.container:
            self.container.stop()
            self.container = None
        # Let's not do force clean at the end for CEI so we can debug
        if not os.environ.get('CEI_LAUNCH_TEST', None):
            self._force_clean()         # deletes only
        bootstrap.testing_fast = False

    def _turn_on_queue_auto_delete(self):
        patcher = patch('pyon.net.channel.RecvChannel._queue_auto_delete', True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _patch_out_diediedie(self):
        """
        If things are running slowly, diediedie will send a kill -9 to the owning process,
        which could be the test runner! Let the test runner decide if it's time to die.
        """
        patcher = patch('pyon.core.thread.shutdown_or_die')
        patcher.start()
        self.addCleanup(patcher.stop)

    def _patch_out_start_rel(self):
        def start_rel_from_url(*args, **kwargs):
            return True

        patcher = patch('pyon.container.apps.AppManager.start_rel_from_url', start_rel_from_url)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _patch_out_fail_fast_kill(self):
        # Not only is this an enormous hack, it doens't work :/
        # reinvestigate later
#        def kill(*args, **kwargs):
#            def call_in_main_context(main_gl):
#                main_gl.throw(AssertionError("Container.fail_fast trying to terminate OS process, preventing"))
#            spawn(call_in_main_context, greenlet.getcurrent())

        patcher = patch('pyon.container.cc.os.kill')        # , kill)
        patcher.start()
        self.addCleanup(patcher.stop)

    @classmethod
    def _force_clean(cls, recreate=False):
        from pyon.core.bootstrap import get_sys_name, CFG
        from pyon.datastore.couchdb.couchdb_standalone import CouchDataStore
        datastore = CouchDataStore(config=CFG)
        dbs = datastore.list_datastores()
        things_to_clean = filter(lambda x: x.startswith('%s_' % get_sys_name().lower()), dbs)
        try:
            for thing in things_to_clean:
                datastore.delete_datastore(datastore_name=thing)
                if recreate:
                    datastore.create_datastore(datastore_name=thing)

        finally:
            datastore.close()

initialize_ion_int_tests()
