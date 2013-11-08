#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from unittest import SkipTest
from mock import Mock, patch, ANY, sentinel, call
from nose.plugins.attrib import attr
from couchdb.http import ResourceNotFound
from gevent.event import AsyncResult, Event
import gevent

from pyon.agent.simple_agent import SimpleResourceAgent
from pyon.container.procs import ProcManager
from pyon.core.exception import BadRequest, NotFound
from pyon.ion.endpoint import ProcessRPCServer
from pyon.ion.process import IonProcessError
from pyon.ion.conversation import ConversationRPCServer
from pyon.net.transport import NameTrio, TransportError
from pyon.public import PRED, CCAP, IonObject
from pyon.ion.service import BaseService
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import PyonTestCase

from interface.objects import ProcessStateEnum

class FakeContainer(object):
    def __init__(self):
        self.id = "containerid"
        self.node = None
        self.name = "containername"
        self.CCAP = CCAP
    def has_capability(self, cap):
        return True

class SampleProcess(BaseService):
    name = 'sample'
    dependencies = []

    def call_process(self, *args, **kwargs):
        pass

class BadProcess(BaseService):
    name = 'bad'
    dependencies = []

    def on_quit(self):
        bad = 3 / 0     # boom
        return bad

    def sleep_target(self, *args, **kwargs):
        self.sleep_event = Event()
        gevent.sleep(0.2)
        self.sleep_event.set()

    def fail_target(self, *args, **kwargs):
        raise Exception("Blow up to test failure chain")

class SampleAgent(SimpleResourceAgent):
    dependencies = []

class TestRPCServer(ProcessRPCServer):
    pass


@attr('UNIT')
class TestProcManager(PyonTestCase):
    def setUp(self):
        self.container = Mock()
        self.pm = ProcManager(self.container)

        self.container.resource_registry.create.return_value = (sentinel.rid, sentinel.rev)
        self.container.resource_registry.find_resources.return_value = ([sentinel.oid], [sentinel.orev])

    def test_start(self):
        self.pm.start()

        self.assertEquals(self.pm.cc_id, sentinel.rid)

    def test_start_with_org(self):
        self.patch_cfg('pyon.container.procs.CFG', {'container':{'org_name':'NOT_DEFAULT'}})
        self.pm.start()

        self.container.resource_registry.create_association.assert_called_once_with(sentinel.oid, PRED.hasResource, sentinel.rid)

#    @patch('pyon.datastore.couchdb.couchdb_datastore.CouchDB_DataStore._stats')
#    def test_stop(self, statsmock):
#        self.pm.start()
#
#        self.pm.stop()
#
#        self.assertEquals(statsmock.get_stats.call_count, 2)

    def test__cleanup_method(self):
        ep = Mock()
        ep._chan._queue_auto_delete = False

        self.pm._cleanup_method(sentinel.queue, ep)

        ch = self.container.node.channel.return_value
        ch._destroy_queue.assert_called_once_with()
        self.assertIsInstance(ch._recv_name, NameTrio)
        self.assertIn(str(sentinel.queue), str(ch._recv_name))

    @patch('pyon.container.procs.log')
    def test__cleanup_method_raises_error(self, mocklog):
        ep = Mock()
        ep._chan._queue_auto_delete = False
        ch = self.container.node.channel.return_value
        ch._destroy_queue.side_effect = TransportError

        self.pm._cleanup_method(sentinel.queue, ep)

        self.assertEquals(mocklog.warn.call_count, 1)

#    @patch('pyon.datastore.couchdb.couchdb_datastore.CouchDB_DataStore._stats', Mock())
    @patch('pyon.container.procs.log')
    def test_stop_with_error(self, mocklog):
        self.pm.start()
        self.pm.terminate_process = Mock(side_effect=BadRequest)

        procmock = Mock()
        procmock._proc_start_time = 0
        procmock.id = sentinel.pid
        self.pm.procs[sentinel.pid] = procmock
        self.pm.procs_by_name['dummy'] = procmock

        self.pm.stop()

        self.pm.terminate_process.assert_called_once_with(sentinel.pid)
        mocklog.warn.assert_has_calls([call("Failed to terminate process (%s): %s", sentinel.pid, ANY),
                                       call("ProcManager procs not empty: %s", self.pm.procs),
                                       call("ProcManager procs_by_name not empty: %s", self.pm.procs_by_name)])

    def test_list_local_processes(self):
        pmock = Mock()
        pmock.process_type = sentinel.ptype
        pmock2 = Mock()
        pmock2.process_type = sentinel.ptype2

        self.pm.procs = {'one':pmock,
                         'two':pmock2,
                         'three':pmock}

        self.assertEquals(self.pm.list_local_processes(),
                          [pmock, pmock2, pmock])

    def test_list_local_processes_proc_type_filter(self):
        pmock = Mock()
        pmock.process_type = sentinel.ptype
        pmock2 = Mock()
        pmock2.process_type = sentinel.ptype2

        self.pm.procs = {'one':pmock,
                         'two':pmock2,
                         'three':pmock}

        self.assertEquals(self.pm.list_local_processes(sentinel.ptype2),
                          [pmock2])

    def test_get_a_local_process(self):
        pmock = Mock()
        pmock.name = sentinel.name
        pmock2 = Mock()
        pmock2.name = sentinel.name2

        self.pm.procs = {'one':pmock,
                         'two':pmock2}

        self.assertEquals(self.pm.get_a_local_process(sentinel.name2),
                          pmock2)

    def test_get_a_local_process_for_agent_res_id(self):
        pmock = Mock()
        pmock.process_type = 'agent'
        pmock.resource_type = sentinel.rtype
        pmock2 = Mock()
        pmock2.process_type = 'agent'
        pmock2.resource_type = sentinel.rtype2

        self.pm.procs = {'one':pmock,
                         'two':pmock2}

        self.assertEquals(self.pm.get_a_local_process(sentinel.rtype2),
                          pmock2)

    def test_get_a_local_process_no_match(self):
        self.assertIsNone(self.pm.get_a_local_process())

    def test_is_local_service_process(self):
        pmock = Mock()
        pmock.name          = sentinel.name
        pmock.process_type = 'simple'
        pmock2 = Mock()
        pmock2.name         = sentinel.name2
        pmock2.process_type = 'service'
        pmock3 = Mock()
        pmock3.name         = sentinel.name3
        pmock3.process_type = 'service'

        self.pm.procs = {'one':pmock,
                         'two':pmock2,
                         'three':pmock3}

        self.assertTrue(self.pm.is_local_service_process(sentinel.name3))

    def test_is_local_service_process_name_matches_but_type_doesnt(self):
        pmock = Mock()
        pmock.name          = sentinel.name
        pmock.process_type = 'simple'
        pmock2 = Mock()
        pmock2.name         = sentinel.name2
        pmock2.process_type = 'notservice'
        pmock3 = Mock()
        pmock3.name         = sentinel.name3
        pmock3.process_type = 'notservice'

        self.pm.procs = {'one':pmock,
                         'two':pmock2,
                         'three':pmock3}

        self.assertFalse(self.pm.is_local_service_process(sentinel.name3))

    def test_is_local_agent_process(self):
        # agent is similar to above, but checks resource_type instead
        pmock = Mock()
        pmock.name          = sentinel.name
        pmock.process_type = 'simple'
        pmock2 = Mock()
        pmock2.resource_type = sentinel.name2
        pmock2.process_type = 'agent'
        pmock3 = Mock()
        pmock3.name         = sentinel.name3
        pmock3.process_type = 'notservice'

        self.pm.procs = {'one':pmock,
                         'two':pmock2,
                         'three':pmock3}

        self.assertTrue(self.pm.is_local_agent_process(sentinel.name2))

    def test_is_local_agent_process_not_found(self):
        self.assertFalse(self.pm.is_local_agent_process(sentinel.one))

    def test__unregister_process_errors(self):
        pmock = Mock()
        pmock._proc_name = '1'
        pmock._proc_type = 'service'
        pmock._proc_res_id = sentinel.presid
        pmock._proc_svc_id = sentinel.psvcid

        self.container.resource_registry.delete.side_effect = NotFound
        self.container.resource_registry.find_objects.side_effect = ResourceNotFound

        self.pm.procs[sentinel.pid] = pmock
        self.pm.procs_by_name['1'] = pmock

        self.pm._unregister_process(sentinel.pid, pmock)

        # show we tried to interact with the RR
        self.container.resource_registry.delete.assert_call(sentinel.presid, del_associations=True)
        self.container.resource_registry.find_objects.assert_called_once_with(sentinel.psvcid, "hasProcess", "Process", id_only=True)
        self.assertEquals(self.pm.procs, {})
        self.assertEquals(self.pm.procs_by_name, {})

        # NEXT: find_objects works fine and gives us an error deletion
        self.container.resource_registry.delete.reset_mock()
        self.container.resource_registry.find_objects.reset_mock()
        self.container.resource_registry.find_objects.side_effect = None
        self.container.resource_registry.find_objects.return_value = ([sentinel.svcid],[None])

        self.pm.procs[sentinel.pid] = pmock
        self.pm.procs_by_name['1'] = pmock

        self.pm._unregister_process(sentinel.pid, pmock)

        self.container.resource_registry.delete.assert_calls([call(sentinel.presid, del_associations=True),
                                                              call(sentinel.psvcid, del_associations=True)])

        # NEXT: agent
        pmock = Mock()
        pmock.id = sentinel.pid
        pmock._proc_name = '1'
        pmock._proc_type = 'agent'

        self.pm.procs[sentinel.pid] = pmock
        self.pm.procs_by_name['1'] = pmock

        self.pm._unregister_process(sentinel.pid, pmock)

        self.container.directory.unregister_safe.assert_called_once_with("/Agents", sentinel.pid)

    def test__create_listening_endpoint_with_cfg(self):
        self.patch_cfg('pyon.container.procs.CFG', container=dict(messaging=dict(endpoint=dict(proc_listening_type='pyon.container.test.test_procs.TestRPCServer'))))

        ep = self.pm._create_listening_endpoint(process=sentinel.process)

        self.assertIsInstance(ep, TestRPCServer)

    def test__create_listening_endpoint_without_cfg_and_no_conv(self):
        self.patch_cfg('pyon.container.procs.CFG', container=dict(messaging=dict(endpoint=dict(proc_listening_type=None, rpc_conversation_enabled=False))))

        ep = self.pm._create_listening_endpoint(process=sentinel.process)

        self.assertIsInstance(ep, ProcessRPCServer)

    def test__create_listening_endpoint_without_cfg_and_conv(self):
        self.patch_cfg('pyon.container.procs.CFG', container=dict(messaging=dict(endpoint=dict(proc_listening_type=None, rpc_conversation_enabled=True))))

        ep = self.pm._create_listening_endpoint(process=sentinel.process)

        self.assertIsInstance(ep, ConversationRPCServer)

    def test_failed_process(self):
        self.pm.start()
        self.container.fail_fast = Mock()

        self.pm.procs['pid1'] = Mock()

        proc2 = BadProcess()
        self.pm.proc_sup.spawn(name="bad", service=proc2, target=proc2.fail_target)
        gevent.sleep(0)  # Allow the new thread to fail and trigger the chain

        self.assertFalse(self.container.fail_fast.called)

        del self.pm.procs['pid1']

        proc3 = BadProcess()
        self.pm.proc_sup.spawn(name="bad", service=proc3, target=proc3.fail_target)
        gevent.sleep(0)  # Allow the new thread to fail and trigger the chain

        self.assertTrue(self.container.fail_fast.called)

@attr('INT')
class TestProcManagerInt(IonIntegrationTestCase):

    class ExpectedFailure(Exception):
        pass

    def test_proc_fails(self):
        self._start_container()
        pm = self.container.proc_manager

        ar = AsyncResult()
        def failedhandler(proc, state, container):
            if state == ProcessStateEnum.FAILED:
                ar.set()
        pm.add_proc_state_changed_callback(failedhandler)

        pid = self._spawnproc(pm, 'service')

        # cause a failure
        pm.procs[pid]._process._ctrl_thread.proc.kill(exception=self.ExpectedFailure, block=False)

        # wait for proc state changed notification
        ar.get(timeout=5)

        # make sure removed
        self.assertNotIn(pid, pm.procs)

    def test_procmanager_iso(self):
        fakecc = FakeContainer()
        fakecc.resource_registry = Mock()
        fakecc.resource_registry.create.return_value=["ID","rev"]

        pm = ProcManager(fakecc)
        self.assertTrue(hasattr(fakecc, "spawn_process"))
        pm.start()
        pm.stop()

    def test_procmanager(self):
        self._start_container()

        pm = self.container.proc_manager

        pid1 = self._spawnproc(pm, 'service')

        pid2 = self._spawnproc(pm, 'stream_process')

        pid3 = self._spawnproc(pm, 'agent', 'SampleAgent')

        pid4 = self._spawnproc(pm, 'standalone')

        pid5 = self._spawnproc(pm, 'simple')

        pid6 = self._spawnproc(pm, 'immediate')

        with self.assertRaises(Exception) as ex:
            config = {'process':{'type':'unknown_type'}}
            pid = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', config)
            self.assertEqual(ex.exception, 'Unknown process type: BAMM')

        self.assertEquals(len(pm.procs), 5)     # service, stream_proc, (no agent), standalone, simple.  NO IMMEDIATE

        pm.terminate_process(pid1)
        pm.terminate_process(pid2)
        pm.terminate_process(pid3)
        pm.terminate_process(pid4)
        pm.terminate_process(pid5)

        self.assertEquals(len(pm.procs), 0)

    def _spawnproc(self, pm, ptype, pcls=None):
        pcls = pcls or 'SampleProcess'
        config = {'process':{'type':ptype}}
        pid = pm.spawn_process('sample1', 'pyon.container.test.test_procs', pcls, config)
        self.assertTrue(pid)

        return pid

    def test_proc_org(self):
        self._start_container()

        pm = self.container.proc_manager

        config = {'process':{'type':'standalone'}}
        pid1 = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', config)
        self.assertTrue(pid1)

        config = {'process':{'type':'standalone'}, 'org_governance_name': 'Org2'}
        pid2 = pm.spawn_process('sample2', 'pyon.container.test.test_procs', 'SampleProcess', config)
        self.assertTrue(pid2)

        proc = pm.procs_by_name['sample1']
        self.assertEqual(proc.org_governance_name,'ION')

        proc = pm.procs_by_name['sample2']
        self.assertEqual(proc.org_governance_name,'Org2')


    def test_procmanager_shutdown(self):
        self.test_procmanager()
        pm = self.container.proc_manager

        pm.stop()

        self.assertEquals(len(pm.procs), 0)

    def test_procmanager_badquit_shutdown(self):
        self._start_container()

        pm = self.container.proc_manager
        pid = pm.spawn_process('badprocess', 'pyon.container.test.test_procs', 'BadProcess', {'process':{'type':'service'}})

        with patch('pyon.ion.service.log') as m:
            pm.stop()
            self.assertEquals(len(pm.procs), 0)
            self.assertEquals(m.exception.call_count, 1)

    def test_immediate_terminate(self):
        self._start_container()

        self._spawnproc(self.container.proc_manager, 'immediate')
        self.assertEquals(len(self.container.proc_manager.procs), 0)

    def test_terminate_process(self):
        self._start_container()

        pid = self._spawnproc(self.container.proc_manager, 'service')

        self.container.terminate_process(pid)

        self.assertEquals(len(self.container.proc_manager.procs), 0)

        # now try to terminate it again, it shouldn't exist
        self.assertRaises(BadRequest, self.container.terminate_process, pid)

    def test_proc_state_change_callback(self):
        self._start_container()

        m = Mock()
        pm = self.container.proc_manager
        pm.add_proc_state_changed_callback(m)

        pid = self._spawnproc(pm, 'service')

        m.assert_called_with(ANY, ProcessStateEnum.RUNNING, self.container)
        self.assertIsInstance(m.call_args[0][0], SampleProcess)

        self.container.terminate_process(pid)

        m.assert_called_with(ANY, ProcessStateEnum.TERMINATED, self.container)
        self.assertIsInstance(m.call_args[0][0], SampleProcess)

        pm.remove_proc_state_changed_callback(m)

        cur_call_count = m.call_count
        pid = self._spawnproc(pm, 'service')

        self.assertEquals(m.call_count, cur_call_count) # should not have been touched

        self.container.terminate_process(pid)

        self.assertEquals(m.call_count, cur_call_count) # should not have been touched

    def test_create_listening_endpoint(self):
        self.patch_cfg('pyon.container.procs.CFG', {'container':{'messaging':{'endpoint':{'proc_listening_type':'pyon.container.test.test_procs.TestRPCServer'}}}})

        fakecc = FakeContainer()
        fakecc.resource_registry = Mock()
        fakecc.resource_registry.create.return_value=["ID","rev"]

        pm = ProcManager(fakecc)

        ep = pm._create_listening_endpoint(node=sentinel.node,
                                           service=sentinel.service,
                                           process=sentinel.process)

        self.assertIsInstance(ep, TestRPCServer)

    def test_error_on_start_listeners_of_proc(self):
        self._start_container()

        m = Mock()

        pm = self.container.proc_manager
        pm.add_proc_state_changed_callback(m)

        with patch('pyon.ion.process.IonProcessThread.start_listeners', Mock(side_effect=IonProcessError)):
            pid = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', {'process':{'type':'service'}})
            self.assertIsNone(pid)

            pid = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', {'process':{'type':'stream_process'}})
            self.assertIsNone(pid)

            pid = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', {'process':{'type':'standalone'}})
            self.assertIsNone(pid)

            m.assert_calls([call(ANY, ProcessStateEnum.FAILED),
                            call(ANY, ProcessStateEnum.FAILED),
                            call(ANY, ProcessStateEnum.FAILED)])


    def test_process_config_reg(self):
        self._start_container()

        pm = self.container.proc_manager

        # Test OK case

        res_config = {'special':{'more':'exists'}}
        res_obj = IonObject("AgentInstance", agent_spawn_config=res_config)
        res_id, _ = self.container.resource_registry.create(res_obj)
        config_ref = "resources:%s/agent_spawn_config" % res_id
        config = {'process':{'config_ref':config_ref}}

        pid1 = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', config)
        self.assertTrue(pid1)

        proc = pm.procs_by_name['sample1']
        self.assertTrue(proc)
        self.assertIn('special', proc.CFG)
        self.assertTrue(proc.CFG.get_safe("special.more"), 'exists')

        pm.terminate_process(pid1)

        # Test failure cases

        config_ref = "XXXXX:%s/agent_spawn_config" % res_id
        config = {'process':{'config_ref':config_ref}}
        with self.assertRaises(BadRequest) as ex:
            pid2 = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', config)

        config_ref = "resources:badbadbad/agent_spawn_config"
        config = {'process':{'config_ref':config_ref}}
        with self.assertRaises(NotFound) as ex:
            pid3 = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', config)

        config_ref = "resources:%s/not_existing" % res_id
        config = {'process':{'config_ref':config_ref}}
        with self.assertRaises(BadRequest) as ex:
            pid4 = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', config)

        config_ref = "resources:%s/name" % res_id
        config = {'process':{'config_ref':config_ref}}
        with self.assertRaises(BadRequest) as ex:
            pid4 = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', config)


        # Test for objects method

        obj_id = "test_" + res_id
        self.container.object_store.create_doc(res_config, object_id=obj_id)
        obj2 = self.container.object_store.read_doc(obj_id)
        self.assertEquals(obj2, res_config)

        config_ref = "objects:%s/" % obj_id
        config = {'process':{'config_ref':config_ref}}

        pid1 = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', config)
        self.assertTrue(pid1)

        proc = pm.procs_by_name['sample1']
        self.assertTrue(proc)
        self.assertIn('special', proc.CFG)
        self.assertTrue(proc.CFG.get_safe("special.more"), 'exists')

        pm.terminate_process(pid1)


        config_ref = "objects:%s/special" % obj_id
        config = {'process':{'config_ref':config_ref}}

        pid1 = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', config)
        self.assertTrue(pid1)

        proc = pm.procs_by_name['sample1']
        self.assertTrue(proc)
        self.assertIn('more', proc.CFG)
        self.assertTrue(proc.CFG.more, 'exists')

        pm.terminate_process(pid1)
