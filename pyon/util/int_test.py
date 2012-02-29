#!/usr/bin/env python

"""Integration test base class and utils"""

from pyon.container.cc import Container
from pyon.core.bootstrap import bootstrap_pyon, service_registry
from pyon.datastore.datastore import DatastoreManager
from pyon.event.event import EventRepository
from pyon.ion.directory import Directory
from pyon.ion.state import StateRepository
from pyon.util.containers import DotDict, dict_merge, DictModifier
from pyon.util.log import log
from mock import patch
from pyon.public import CFG
from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from pyon.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from contextlib import contextmanager
import unittest
import os

# Make this call more deterministic in time.
bootstrap_pyon()

scanned_services = False

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
        db_type = os.environ.get('DB_TYPE', None)
        if not db_type:
            pass
        elif db_type == 'MOCK':
            self._turn_on_mockdb()
        elif db_type == 'COUCH':
            self._turn_on_couchdb()
        if os.environ.get('CEI_LAUNCH_TEST', None):
            self._patch_out_start_rel()
            self._turn_on_couchdb()
            self._turn_off_force_clean()
            from ion.processes.bootstrap.datastore_loader import DatastoreLoader
            DatastoreLoader.load_datastore('res/dd')
        # hack to force_clean on filesystem
        try:
            CFG['container']['filesystem']['force_clean']=True
        except KeyError:
            CFG['container']['filesystem'] = {}
            CFG['container']['filesystem']['force_clean'] = True
        self.container = None
        self.addCleanup(self._stop_container)
        self.container = Container()
        self.container.start()

        # For integration tests, if class variable "service_dependencies" exists
        self._start_dependencies()

    def _stop_container(self):
        if self.container:
            self.container.stop()
            self.container = None
        self._force_clean()


    def _turn_on_queue_auto_delete(self):
        patcher = patch('pyon.net.channel.RecvChannel._queue_auto_delete', True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _patch_out_diediedie(self):
        """
        If things are running slowly, diediedie will send a kill -9 to the owning process,
        which could be the test runner! Let the test runner decide if it's time to die.
        """
        patcher = patch('pyon.core.process.shutdown_or_die')
        patcher.start()
        self.addCleanup(patcher.stop)

    def _start_dependencies(self):
        """
        Starts the services declared in the class or instance variable "service_dependencies"
        """
        self.clients = DotDict()
        svc_deps = getattr(self, "service_dependencies", {})
        log.debug("Starting service dependencies. Number=%s" % len(svc_deps))
        if not svc_deps:
            return
        for svc in svc_deps:
            config = None
            if type(svc) in (tuple, list):
                config = svc[1]
                svc = svc[0]

            # Start the service
            self._start_service(svc, config=config)

            # Create a client
            clcls = service_registry.services[svc].simple_client
            self.clients[svc] = clcls(name=svc, node=self.container.node)

        log.debug("Service dependencies started")

    def _start_service(self, servicename, servicecls=None, config=None):
        if servicename and not servicecls:
            global scanned_services
            if not scanned_services:
                service_registry.discover_service_classes()
                scanned_services = True
            assert servicename in service_registry.services, "Service %s unknown" % servicename
            servicecls = service_registry.services[servicename].impl[0]

        assert servicecls, "Cannot start service %s" % servicename

        if type(servicecls) is str:
            mod, cls = servicecls.rsplit('.', 1)
        else:
            mod = servicecls.__module__
            cls = servicecls.__name__
        self.container.spawn_process(servicename, mod, cls, config)

    def _turn_on_couchdb(self):
        # Called via pyon.datastore.datastore.DataStoreManager.get_datastore()
        patcher =patch('pyon.datastore.datastore.DatastoreManager.persistent', True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _turn_on_mockdb(self):
        # Called via pyon.datastore.datastore.DataStoreManager.get_datastore()
        patcher =patch('pyon.datastore.datastore.DatastoreManager.persistent', False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _turn_off_force_clean(self):
        # Called via pyon.datastore.datastore.DataStoreManager.get_datastore()
        patcher =patch('pyon.datastore.datastore.DatastoreManager.force_clean', False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _patch_out_start_rel(self):
        def start_rel_from_url(*args, **kwargs):
            return True

        patcher = patch('pyon.container.apps.AppManager.start_rel_from_url', start_rel_from_url)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _force_clean(self):
        from pyon.core.bootstrap import get_sys_name
        from pyon.datastore.datastore import DatastoreManager
        if DatastoreManager.persistent is None:
            DatastoreManager.persistent = not CFG.system.mockdb
        if not DatastoreManager.persistent:
            datastore = MockDB_DataStore()
        else:
            datastore = CouchDB_DataStore()
        dbs = datastore.list_datastores()
        things_to_clean = filter(lambda x: x.startswith('%s_' % get_sys_name()), dbs)
        try:
            for thing in things_to_clean:
                datastore.delete_datastore(datastore_name=thing)
                datastore.create_datastore(datastore_name=thing)
        finally:
            datastore.close()
