#!/usr/bin/env python

"""Integration test base class and utils"""

from mock import patch
import unittest
import os
from gevent import greenlet, spawn
import sys

from pyon.container.cc import Container
from pyon.core import bootstrap
from pyon.core.bootstrap import bootstrap_pyon, CFG
from pyon.util.containers import DotDict
from pyon.util.log import log

# This is the only place where code is executed once before any integration test
# is run.
def initialize_ion_int_tests():
    # Bootstrap pyon CFG, logging and object/resource interfaces
    bootstrap_pyon()
    # Do necessary system initialization
    # Make sure this happens only once
    iadm = InterfaceAdmin(bootstrap.get_sys_name(), config=CFG)
    iadm.create_core_datastores()
    #iadm.store_config(CFG)
    iadm.store_interfaces(idempotent=True)
    iadm.initialize_ion_system_core()

initialize_ion_int_tests()


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

        if os.environ.get('CEI_LAUNCH_TEST', None):
            self._patch_out_start_rel()
            from pyon.datastore.datastore_admin import DatastoreAdmin
            da = DatastoreAdmin(config=CFG)
            da.load_datastore('res/dd')

        # hack to force_clean on filesystem
        try:
            CFG['container']['filesystem']['force_clean'] = True
        except KeyError:
            CFG['container']['filesystem'] = {}
            CFG['container']['filesystem']['force_clean'] = True

        # hack to clean up the previous pid if it's still there.
        pidfile = "cc-pid-%d" % os.getpid()
        log.debug("Cleanup pidfile: %s", pidfile)
        try:
            os.remove(pidfile)
        except Exception, e:
            log.warn("Pidfile could not be deleted: %s" % str(e))

        self.container = None
        self.addCleanup(self._stop_container)
        self.container = Container()
        self.container.start()

        # For integration tests, if class variable "service_dependencies" exists
        self._start_dependencies()


    def _stop_container(self):
        if self.container:
            # destroy any created XO in the process of a test
            try:
                self.container.ex_manager.cleanup_xos()
            except Exception as ex:
                # to stderr so it stands out!
                print >>sys.stderr, "\nCleanup XOs caused an exception:", ex

            self.container.stop()
            self.container = None
        self._force_clean()         # deletes only


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

    def _start_dependencies(self):
        """
        Starts the services declared in the class or instance variable "service_dependencies"
        """
        self.clients = DotDict()

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

    def _force_clean(self, recreate=False):
        from pyon.core.bootstrap import get_sys_name, CFG
        from pyon.datastore.couchdb.couchdb_standalone import CouchDataStore
        datastore = CouchDataStore(config=CFG)
        dbs = datastore.list_datastores()
        things_to_clean = filter(lambda x: x.startswith('%s_' % get_sys_name()), dbs)
        try:
            for thing in things_to_clean:
                datastore.delete_datastore(datastore_name=thing)
                if recreate:
                    datastore.create_datastore(datastore_name=thing)

        finally:
            datastore.close()

