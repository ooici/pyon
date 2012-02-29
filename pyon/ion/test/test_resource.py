#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from unittest import SkipTest


from pyon.ion.resource import lcs_workflows, CommonResourceLifeCycleSM, LCS, LCE
from pyon.util.unit_test import IonUnitTestCase
from nose.plugins.attrib import attr

@attr('UNIT', group='resource')
class TestResources(IonUnitTestCase):

    def test_resource_lcworkflow(self):
        default_workflow = lcs_workflows['InstrumentDevice']

        self.assertEquals(len(CommonResourceLifeCycleSM.BASE_STATES), 16)
        self.assertEquals(len(default_workflow.BASE_STATES), 16)
        self.assertEquals(len(LCS), len(CommonResourceLifeCycleSM.BASE_STATES) + len(CommonResourceLifeCycleSM.STATE_ALIASES))

        self.assert_(LCS.DRAFT_PRIVATE in CommonResourceLifeCycleSM.BASE_STATES)

        self.assert_(CommonResourceLifeCycleSM.is_in_state(LCS.DRAFT_PRIVATE, LCS.DRAFT_PRIVATE))
        self.assert_(CommonResourceLifeCycleSM.is_in_state(LCS.DEVELOPED_PRIVATE, 'REGISTERED'))

        events = set(ev for (s0,ev) in CommonResourceLifeCycleSM.BASE_TRANSITIONS)
        self.assertFalse(set(CommonResourceLifeCycleSM.BASE_STATES) & events)

        self.assertEquals(len(default_workflow.transitions), 84)

        self.assertEquals(default_workflow.get_successor(LCS.DRAFT_PRIVATE, LCE.PLAN), LCS.PLANNED_PRIVATE)

        self.assertEquals(default_workflow.get_successor(LCS.DRAFT_PRIVATE, LCE.ANNOUNCE), LCS.DRAFT_DISCOVERABLE)
        self.assertEquals(default_workflow.get_successor(LCS.DRAFT_DISCOVERABLE, LCE.UNANNOUNCE), LCS.DRAFT_PRIVATE)
        self.assertEquals(default_workflow.get_successor(LCS.DRAFT_PRIVATE, LCE.ENABLE), LCS.DRAFT_AVAILABLE)
        self.assertEquals(default_workflow.get_successor(LCS.DRAFT_AVAILABLE, LCE.DISABLE), LCS.DRAFT_DISCOVERABLE)
        self.assertEquals(default_workflow.get_successor(LCS.DRAFT_AVAILABLE, LCE.UNANNOUNCE), LCS.DRAFT_PRIVATE)

        self.assertEquals(default_workflow.get_successor(LCS.PLANNED_PRIVATE, LCE.PLAN), None)

        self.assertEquals(default_workflow.get_successor(LCS.PLANNED_PRIVATE, LCE.DEVELOP), LCS.DEVELOPED_PRIVATE)
        self.assertEquals(default_workflow.get_successor(LCS.DEVELOPED_PRIVATE, LCE.RETIRE), LCS.RETIRED)

        self.assertEquals(default_workflow.get_successors(LCS.PLANNED_PRIVATE), {LCE.DEVELOP: LCS.DEVELOPED_PRIVATE,
                                                                                 LCE.INTEGRATE: LCS.INTEGRATED_PRIVATE,
                                                                                 LCE.DEPLOY: LCS.DEPLOYED_PRIVATE,
                                                                                 LCE.ANNOUNCE: LCS.PLANNED_DISCOVERABLE,
                                                                                 LCE.ENABLE: LCS.PLANNED_AVAILABLE,
                                                                                 LCE.RETIRE: LCS.RETIRED})

#        self.assertEquals(default_workflow.get_predecessors(LCS.DEVELOPED_PRIVATE), {LCS.PLANNED: LCE.DEVELOP})
