#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from unittest import SkipTest
from nose.plugins.attrib import attr

from pyon.agent.simple_agent import SimpleResourceAgent
from pyon.agent.agent import ResourceAgentClient
from pyon.public import IonObject
from pyon.util.int_test import IonIntegrationTestCase


class SampleAgent(SimpleResourceAgent):
    dependencies = []

@attr('INT')
class TestResourceAgentClient(IonIntegrationTestCase):

    def test_agent_registration(self):
        self._start_container()

        idev = IonObject("InstrumentDevice", name="any_resource")
        idev_id, _ = self.container.resource_registry.create(idev)

        config = dict(agent=dict(resource_id=idev_id))
        pid1 = self.container.spawn_process('agent1', 'pyon.agent.test.test_agent', 'SampleAgent', config)

        rac = ResourceAgentClient(idev_id)
        rac_pid = rac.get_agent_process_id()
        rac_de = rac.get_agent_directory_entry()
        self.assertEquals(rac_pid, pid1)

        # Now fake a second agent directory entry that wasn't cleaned up
        self.container.directory.register("/Agents", "fake_pid",
            **dict(name="agent1",
                container=self.container.id,
                resource_id=idev_id,
                agent_id="fake"))

        entries = self.container.directory.find_by_value('/Agents', 'resource_id', idev_id)
        self.assertEquals(len(entries), 2)

        rac = ResourceAgentClient(idev_id)
        rac_pid1 = rac.get_agent_process_id()
        self.assertEquals(rac_pid1, "fake_pid")

        # Check cleanup side effect of agent client
        entries = self.container.directory.find_by_value('/Agents', 'resource_id', idev_id)
        self.assertEquals(len(entries), 1)

        # Now restore the original process id
        self.container.directory.register("/Agents", pid1,
            **dict(name="agent1",
                container=self.container.id,
                resource_id=idev_id,
                agent_id=rac_de.attributes["agent_id"]))

        rac = ResourceAgentClient(idev_id)
        rac_pid1 = rac.get_agent_process_id()
        self.assertEquals(rac_pid1, pid1)

        # Check cleanup side effect of agent client
        entries = self.container.directory.find_by_value('/Agents', 'resource_id', idev_id)
        self.assertEquals(len(entries), 1)

        self.container.terminate_process(pid1)
