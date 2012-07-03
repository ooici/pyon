#!/usr/bin/env python

"""Integration test base class and utils"""

from pyon.container.cc import Container
from pyon.core.bootstrap import bootstrap_pyon, get_service_registry, CFG
from pyon.util.containers import DotDict
from pyon.util.log import log
from mock import patch
import unittest
import os
from gevent import greenlet, spawn

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
        self._patch_out_fail_fast_kill()

        # delete/create any known DBs with names matching our prefix - should be rare
        self._force_clean(True)

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

        if CFG.get_safe('system.elasticsearch'):
            self.addCleanup(self._clean_es)

    def _stop_container(self):
        if self.container:
            self.container.stop()
            self.container = None
        if os.environ.get('CEI_LAUNCH_TEST', None) is None:
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
            clcls = get_service_registry().services[svc].simple_client
            self.clients[svc] = clcls(name=svc, node=self.container.node)

        log.debug("Service dependencies started")

    def _start_service(self, servicename, servicecls=None, config=None):
        if servicename and not servicecls:
            global scanned_services
            if not scanned_services:
                get_service_registry().discover_service_classes()
                scanned_services = True
            assert servicename in get_service_registry().services, "Service %s unknown" % servicename
            servicecls = get_service_registry().services[servicename].impl[0]

        assert servicecls, "Cannot start service %s" % servicename

        if type(servicecls) is str:
            mod, cls = servicecls.rsplit('.', 1)
        else:
            mod = servicecls.__module__
            cls = servicecls.__name__
        self.container.spawn_process(servicename, mod, cls, config)

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

    def _clean_es(self):
        from pyon.core.bootstrap import get_sys_name
        import elasticpy as ep
        indexes = [ 
            '%s_sites_index' % get_sys_name().lower()           ,
            '%s_agents_index' % get_sys_name().lower()          ,
            '%s_agents_instance_index' % get_sys_name().lower() ,
            '%s_devices_index' % get_sys_name().lower()         ,
            '%s_models_index' % get_sys_name().lower()          ,
            '%s_data_products_index' % get_sys_name().lower()   ,
            '%s_searches_and_catalogs' % get_sys_name().lower() ,
            '%s_users_index' % get_sys_name().lower()           ,
            '%s_resources_index' % get_sys_name().lower() ,
            '%s_events_index'    % get_sys_name().lower()
        ]

        es_host = CFG.get_safe('server.elasticsearch.host', 'localhost')
        es_port = CFG.get_safe('server.elasticsearch.port', '9200')
        es = ep.ElasticSearch(
            host=es_host,
            port=es_port,
            timeout=10
        )
        for index in indexes:
            self._es_call(es.river_couchdb_delete,index)
            self._es_call(es.index_delete,index)


    @staticmethod
    def _es_call(es, *args, **kwargs):
        from gevent.event import AsyncResult
        from gevent import Timeout
        from gevent import spawn as gspawn
        import pyon.core.exception as exceptions
        res = AsyncResult()
        def async_call(es, *args, **kwargs):
            res.set(es(*args,**kwargs))
        gspawn(async_call,es,*args,**kwargs)
        try:
            retval = res.get(timeout=10)
        except Timeout:
            raise exceptions.Timeout("Call to ElasticSearch timed out.")
        return retval

