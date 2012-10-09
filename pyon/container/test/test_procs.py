#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from unittest import SkipTest
from mock import Mock, patch, ANY

from pyon.agent.agent import ResourceAgent
from pyon.container.procs import ProcManager
from pyon.service.service import BaseService
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr
from interface.objects import ProcessStateEnum

class FakeContainer(object):
    def __init__(self):
        self.id = "containerid"
        self.node = None
        self.name = "containername"

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

class SampleAgent(ResourceAgent):
    dependencies = []

@attr('INT')
class TestProcManager(IonIntegrationTestCase):

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

        self._spawnproc(pm, 'service')

        self._spawnproc(pm, 'stream_process')

        #self._spawnproc(pm, 'agent', 'SampleAgent')

        self._spawnproc(pm, 'standalone')

        self._spawnproc(pm, 'simple')

        self._spawnproc(pm, 'immediate')

        with self.assertRaises(Exception) as ex:
            config = {'process':{'type':'unknown_type'}}
            pid = pm.spawn_process('sample1', 'pyon.container.test.test_procs', 'SampleProcess', config)
            self.assertEqual(ex.exception, 'Unknown process type: BAMM')

        self.assertEquals(len(pm.procs), 4)     # service, stream_proc, (no agent), standalone, simple.  NO IMMEDIATE

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

        config = {'process':{'type':'standalone'}, 'org_name': 'Org2'}
        pid2 = pm.spawn_process('sample2', 'pyon.container.test.test_procs', 'SampleProcess', config)
        self.assertTrue(pid2)

        proc = pm.procs_by_name['sample1']
        self.assertEqual(proc.org_name,'ION')

        proc = pm.procs_by_name['sample2']
        self.assertEqual(proc.org_name,'Org2')


    def test_procmanager_shutdown(self):
        self.test_procmanager()
        pm = self.container.proc_manager

        pm.stop()

        self.assertEquals(len(pm.procs), 0)

    def test_procmanager_badquit_shutdown(self):
        self._start_container()

        pm = self.container.proc_manager
        pid = pm.spawn_process('badprocess', 'pyon.container.test.test_procs', 'BadProcess', {'process':{'type':'service'}})

        with patch('pyon.service.service.log') as m:
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

