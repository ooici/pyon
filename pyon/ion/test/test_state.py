#!/usr/bin/env python

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from unittest import SkipTest
from nose.plugins.attrib import attr
import uuid

from pyon.datastore.datastore import DatastoreManager
from pyon.ion.state import StateRepository, StatefulProcessMixin
from pyon.ion.process import StandaloneProcess
from pyon.public import Inconsistent
from pyon.util.containers import get_ion_ts
from pyon.util.log import log
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import IonUnitTestCase

from interface.services.isample_service import SampleServiceClient

@attr('UNIT', group='datastore')
class TestState(IonUnitTestCase):

    def test_state(self):
        dsm = DatastoreManager()
        state_repo = StateRepository(dsm)
        state_repo.start()
        state_repo1 = StateRepository(dsm)

        state1 = {'key':'value1'}
        state_repo.put_state("id1", state1)

        state2 = state_repo.get_state("id1")
        self.assertEquals(state1, state2)

        state3 = {'key':'value2', 'key2': {}}
        state_repo.put_state("id1", state3)

        state4 = state_repo.get_state("id1")
        self.assertEquals(state3, state4)

@attr('INT', group='state')
class TestStatefulProcess(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()

    def test_process_state(self):
        pid = "testproc_%s" % uuid.uuid4().hex
        # Create a process
        newpid = self.container.spawn_process("testproc", "pyon.ion.test.test_state", "StatefulTestProcess", process_id=pid)
        self.assertEquals(pid, newpid)

        # Send it a message to do stuff and change state
        proc_client = SampleServiceClient(to_name=pid)
        result = proc_client.sample_other_op("state1")
        self.assertEquals(result, "")

        # Try the force state store and load
        proc_client.sample_ping()

        # Check state
        # Kill process (not terminate)
        self.container.terminate_process(pid)
        # Restart process with prior id
        # Send it a message
        # Check that state reflects

class StatefulTestProcess(StandaloneProcess, StatefulProcessMixin):
    name = "sample_service"

    def on_start(self):
        log.info("StatefulTestProcess START")

    def sample_other_op(self, foo='bar', num=84, name=''):
        log.info("StatefulTestProcess OP, state=%s", foo)
        newstate = foo
        oldstate = self._get_state("statevalue") or ""
        self._set_state("statevalue", newstate)
        self._set_state("statets", get_ion_ts())
        return oldstate

    def sample_ping(self, name='name', time='2011-07-27T02:59:43.1Z', an_int=0, a_float=0.0, a_str='',
                    none=None, a_dict=None, a_list=None):
        log.info("StatefulTestProcess trying to force store and load the state")
        state_vector = self._get_state_vector()

        self._set_state("othervalue", "TOKEN")

        if not "othervalue" in state_vector:
            raise Inconsistent("state value not found in state vector")

        self._flush_state()
        state_vector['othervalue'] = "FUZZ"
        self._load_state()

        state_vector1 = self._get_state_vector()
        if not state_vector == state_vector1:
            raise Inconsistent("State vectors are different after load")

        if not state_vector['othervalue'] == "TOKEN":
            raise Inconsistent("state vector not restored. content: %s" % state_vector)





