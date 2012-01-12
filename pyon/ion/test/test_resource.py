#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from unittest import SkipTest


from pyon.ion.resource import lcs_workflows, ResourceLifeCycleSM, LCS
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr

@attr('UNIT', group='resource')
class TestResources(PyonTestCase):

    def test_resource_lcworkflow(self):
        default_workflow = lcs_workflows['Resource']

        self.assertEquals(len(ResourceLifeCycleSM.BASE_STATES), 8)
        self.assertEquals(len(default_workflow.BASE_STATES), 8)
        self.assertEquals(len(LCS), len(ResourceLifeCycleSM.BASE_STATES) + len(ResourceLifeCycleSM.STATE_ALIASES))

        self.assert_(LCS.DRAFT in ResourceLifeCycleSM.BASE_STATES)

        self.assert_(ResourceLifeCycleSM.is_in_state(LCS.DRAFT, LCS.DRAFT))
        self.assert_(ResourceLifeCycleSM.is_in_state(LCS.DEVELOPED, ResourceLifeCycleSM.UNDEPLOYED))
        self.assertFalse(ResourceLifeCycleSM.is_in_state(LCS.DEVELOPED, ResourceLifeCycleSM.DEPLOYED))
        self.assert_(ResourceLifeCycleSM.is_in_state(LCS.DEVELOPED, ResourceLifeCycleSM.REGISTERED))

        events = set(ev for (s0,ev) in ResourceLifeCycleSM.BASE_TRANSITIONS)
        self.assertFalse(set(ResourceLifeCycleSM.BASE_STATES) & events)

        self.assertEquals(len(default_workflow.transitions), 20)

        self.assertEquals(default_workflow.get_successor(LCS.DRAFT, ResourceLifeCycleSM.REGISTER), LCS.PLANNED)

        self.assertEquals(default_workflow.get_successor(LCS.PLANNED, ResourceLifeCycleSM.REGISTER), None)

        self.assertEquals(default_workflow.get_successor(LCS.PLANNED, ResourceLifeCycleSM.DEVELOP), LCS.DEVELOPED)
        self.assertEquals(default_workflow.get_successor(LCS.DEVELOPED, ResourceLifeCycleSM.RETIRE), LCS.RETIRED)

        self.assertEquals(default_workflow.get_successors(LCS.PLANNED), {ResourceLifeCycleSM.DEPLOY: LCS.PRIVATE,
                                                                         ResourceLifeCycleSM.DEVELOP: LCS.DEVELOPED,
                                                                         ResourceLifeCycleSM.RETIRE: LCS.RETIRED})
        self.assertEquals(default_workflow.get_predecessors(LCS.DEVELOPED), {LCS.PLANNED: ResourceLifeCycleSM.DEVELOP})
