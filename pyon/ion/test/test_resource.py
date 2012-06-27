#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from unittest import SkipTest

from mock import Mock
from pyon.ion.resource import lcs_workflows, CommonResourceLifeCycleSM, LCS, LCE, ExtendedResourceContainer, OT, RT,PRED
from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest
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


    def test_create_extended_resource_container(self):

        mock_clients = self._create_service_mock('resource_registry')

        self.clients = mock_clients

        extended_resource_handler = ExtendedResourceContainer(self, mock_clients.resource_registry)

        instrument_device = Mock()
        instrument_device._id = '123'
        instrument_device.name = "MyInstrument"
        instrument_device.type_ = RT.InstrumentDevice


        actor_identity = Mock()
        actor_identity._id = '111'
        actor_identity.name = "Foo"
        actor_identity.type_ = RT.ActorIdentity



        user_info = Mock()
        user_info.name = "John Doe"
        user_info.email = "John.Doe@devnull.com"
        user_info.phone = "555-555-5555"
        user_info.variables = [{"name": "subscribeToMailingList", "value": "False"}]

        # ActorIdentity to UserInfo association
        actor_identity_to_info_association = Mock()
        actor_identity_to_info_association._id = '555'
        actor_identity_to_info_association.s = "111"
        actor_identity_to_info_association.st = RT.ActorIdentity
        actor_identity_to_info_association.p = PRED.hasInfo
        actor_identity_to_info_association.o = "444"
        actor_identity_to_info_association.ot = RT.UserInfo

        # ActorIdentity to UserInfo association
        Instrument_device_to_actor_identity_association = Mock()
        Instrument_device_to_actor_identity_association._id = '666'
        Instrument_device_to_actor_identity_association.s = "123"
        Instrument_device_to_actor_identity_association.st = RT.InstumentDevice
        Instrument_device_to_actor_identity_association.p = PRED.hasOwner
        Instrument_device_to_actor_identity_association.o = "111"
        Instrument_device_to_actor_identity_association.ot = RT.ActorIdentity

        with self.assertRaises(BadRequest) as cm:
            extended_user = extended_resource_handler.create_extended_resource_container(RT.ActorIdentity, '111')
        self.assertIn( 'Requested resource ActorIdentity is not extended from ResourceContainer',cm.exception.message)



        obj = IonObject(OT.TestExtendedResource)
        list_objs = ['123', '456', '789']
        extended_resource_handler.set_field_associations(obj, 'policies', list_objs)
        extended_resource_handler.set_field_associations(obj, 'policy_count', list_objs)
        extended_resource_handler.set_field_associations(obj, 'resource_object', list_objs)

        self.assertEquals(obj.policies, list_objs)
        self.assertEquals(obj.policy_count, 3)
        self.assertEquals(obj.resource_object, '123')

        mock_clients.resource_registry.read.return_value = instrument_device
        mock_clients.resource_registry.find_objects.return_value = ([actor_identity], [Instrument_device_to_actor_identity_association])

        extended_res = extended_resource_handler.create_extended_resource_container(OT.TestExtendedResource, '123')
        self.assertEquals(extended_res.resource, instrument_device)
        self.assertEquals(len(extended_res.owners),1)



