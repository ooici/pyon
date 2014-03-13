#!/usr/bin/env python

__author__ = 'Michael Meisinger, Stephen Henrie'

from unittest import SkipTest

from mock import Mock
from unittest import SkipTest
from nose.plugins.attrib import attr

from pyon.ion.resource import lcs_workflows, LCS, LCE, ExtendedResourceContainer, OT, RT, PRED, AS, lcstate, get_object_schema
from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest, Inconsistent
from pyon.util.unit_test import IonUnitTestCase


@attr('UNIT', group='resource')
class TestResources(IonUnitTestCase):

    def test_resource_lcworkflow(self):
        default_workflow = lcs_workflows['InstrumentDevice']

        self.assertEquals(len(default_workflow.lcstate_states), 7)
        self.assertEquals(len(default_workflow.lcstate_transitions), 24)

        self.assertEquals(len(default_workflow.availability_states), 3)
        self.assertEquals(len(default_workflow.availability_transitions), 6)

        self.assertIn(LCS.DRAFT, default_workflow.lcstate_states)
        self.assertIn(AS.PRIVATE, default_workflow.availability_states)

        self.assertTrue(default_workflow.is_in_state(LCS.DRAFT, LCS.DRAFT))
        self.assertTrue(default_workflow.is_in_state(AS.PRIVATE, AS.PRIVATE))

        self.assertEquals(default_workflow.get_lcstate_successor(LCS.DRAFT, LCE.PLAN), LCS.PLANNED)
        self.assertEquals(default_workflow.get_lcstate_successor(LCS.PLANNED, LCE.PLAN), None)
        self.assertEquals(default_workflow.get_lcstate_successor(LCS.PLANNED, LCE.DEVELOP), LCS.DEVELOPED)
        self.assertEquals(default_workflow.get_lcstate_successor(LCS.DEVELOPED, LCE.RETIRE), LCS.RETIRED)
        self.assertEquals(default_workflow.get_lcstate_successor(LCS.DEVELOPED, LCE.DELETE), LCS.DELETED)
        self.assertEquals(default_workflow.get_lcstate_successor(LCS.RETIRED, LCE.DELETE), LCS.DELETED)

        self.assertEquals(default_workflow.get_availability_successor(AS.PRIVATE, LCE.ANNOUNCE), AS.DISCOVERABLE)
        self.assertEquals(default_workflow.get_availability_successor(AS.DISCOVERABLE, LCE.UNANNOUNCE), AS.PRIVATE)
        self.assertEquals(default_workflow.get_availability_successor(AS.PRIVATE, LCE.ENABLE), AS.AVAILABLE)
        self.assertEquals(default_workflow.get_availability_successor(AS.AVAILABLE, LCE.DISABLE), AS.DISCOVERABLE)
        self.assertEquals(default_workflow.get_availability_successor(AS.AVAILABLE, LCE.UNANNOUNCE), AS.PRIVATE)

        self.assertEquals(default_workflow.get_lcstate_successors(LCS.PLANNED),
                          {LCE.DEVELOP: LCS.DEVELOPED,
                           LCE.INTEGRATE: LCS.INTEGRATED,
                           LCE.DEPLOY: LCS.DEPLOYED,
                           LCE.RETIRE: LCS.RETIRED,
                           LCE.DELETE: LCS.DELETED})

        self.assertEquals(default_workflow.get_lcstate_successors(LCS.RETIRED),
                          {LCE.DELETE: LCS.DELETED})

        self.assertEquals(default_workflow.get_availability_successors(AS.PRIVATE),
                          {LCE.ANNOUNCE: AS.DISCOVERABLE,
                           LCE.ENABLE: AS.AVAILABLE})

        # Simplified workflows
        infres_workflow = lcs_workflows['DataProduct']

        self.assertEquals(len(infres_workflow.lcstate_states), 4)
        self.assertEquals(len(infres_workflow.availability_states), 3)

        simple_workflow = lcs_workflows['Deployment']

        self.assertEquals(len(simple_workflow.lcstate_states), 5)
        self.assertEquals(len(simple_workflow.availability_states), 3)

        # Cloning a LCSM
        restrictions = dict(
            initial_lcstate=LCS.DRAFT,
            initial_availability=AS.PRIVATE,
            remove_states=[LCS.DEVELOPED, LCS.INTEGRATED],
            remove_transitions=[],
            )

        restricted_wf = default_workflow._clone_with_restrictions(restrictions)

        for (a_state, a_transition), a_newstate in restricted_wf.lcstate_transitions.iteritems():
            if LCS.DEVELOPED in a_state or LCS.DEVELOPED in a_newstate:
                self.fail("Workflow contains illegal state")



    def test_create_extended_resource_container(self):

        mock_clients = self._create_service_mock('resource_registry')

        self.clients = mock_clients
        self.container = Mock()

        extended_resource_handler = ExtendedResourceContainer(self, mock_clients.resource_registry)

        instrument_device = Mock()
        instrument_device._id = '123'
        instrument_device.name = "MyInstrument"
        instrument_device.type_ = RT.InstrumentDevice
        instrument_device.lcstate = LCS.DRAFT
        instrument_device.availability = AS.PRIVATE

        instrument_device2 = Mock()
        instrument_device2._id = '456'
        instrument_device2.name = "MyInstrument2"
        instrument_device2.type_ = RT.InstrumentDevice


        actor_identity = Mock()
        actor_identity._id = '111'
        actor_identity.name = "Foo"
        actor_identity.type_ = RT.ActorIdentity


        actor_identity = Mock()
        actor_identity._id = '1112'
        actor_identity.name = "Foo2"
        actor_identity.type_ = RT.ActorIdentity

        user_info = Mock()
        user_info._id = '444'
        user_info.name = "John Doe"
        user_info.email = "John.Doe@devnull.com"
        user_info.phone = "555-555-5555"
        user_info.variables = [{"name": "subscribeToMailingList", "value": "False"}]

        user_info2 = Mock()
        user_info2._id = '445'
        user_info2.name = "aka Evil Twin"
        user_info2.email = "Evil.Twin@devnull.com"
        user_info2.phone = "555-555-5555"
        user_info2.variables = [{"name": "subscribeToMailingList", "value": "False"}]


        # ActorIdentity to UserInfo association
        actor_identity_to_info_association = Mock()
        actor_identity_to_info_association._id = '555'
        actor_identity_to_info_association.s = "111"
        actor_identity_to_info_association.st = RT.ActorIdentity
        actor_identity_to_info_association.p = PRED.hasInfo
        actor_identity_to_info_association.o = "444"
        actor_identity_to_info_association.ot = RT.UserInfo

        # ActorIdentity to UserInfo association
        actor_identity_to_info_association2 = Mock()
        actor_identity_to_info_association2._id = '556'
        actor_identity_to_info_association2.s = "1112"
        actor_identity_to_info_association2.st = RT.ActorIdentity
        actor_identity_to_info_association2.p = PRED.hasInfo
        actor_identity_to_info_association2.o = "445"
        actor_identity_to_info_association2.ot = RT.UserInfo

        # ActorIdentity to Instrument Device association
        Instrument_device_to_actor_identity_association = Mock()
        Instrument_device_to_actor_identity_association._id = '666'
        Instrument_device_to_actor_identity_association.s = "123"
        Instrument_device_to_actor_identity_association.st = RT.InstrumentDevice
        Instrument_device_to_actor_identity_association.p = PRED.hasOwner
        Instrument_device_to_actor_identity_association.o = "111"
        Instrument_device_to_actor_identity_association.ot = RT.ActorIdentity


        # ActorIdentity to Instrument Device association
        Instrument_device_to_actor_identity_association2 = Mock()
        Instrument_device_to_actor_identity_association2._id = '667'
        Instrument_device_to_actor_identity_association2.s = "456"
        Instrument_device_to_actor_identity_association2.st = RT.InstrumentDevice
        Instrument_device_to_actor_identity_association2.p = PRED.hasOwner
        Instrument_device_to_actor_identity_association2.o = "111"
        Instrument_device_to_actor_identity_association2.ot = RT.ActorIdentity

        with self.assertRaises(BadRequest) as cm:
            extended_user = extended_resource_handler.create_extended_resource_container(RT.ActorIdentity, '111')
        self.assertIn( 'The requested resource ActorIdentity is not extended from ResourceContainer',cm.exception.message)


        mock_clients.resource_registry.read.return_value = instrument_device
        mock_clients.resource_registry.find_objects.return_value = ([actor_identity], [Instrument_device_to_actor_identity_association])
        mock_clients.resource_registry.find_subjects.return_value = (None,None)
        mock_clients.resource_registry.find_associations.return_value = [actor_identity_to_info_association, Instrument_device_to_actor_identity_association]
        mock_clients.resource_registry.read_mult.return_value = [user_info]

        extended_res = extended_resource_handler.create_extended_resource_container(OT.TestExtendedResource, '123')
        self.assertEquals(extended_res.resource, instrument_device)
        self.assertEquals(len(extended_res.owners),2)
        self.assertEquals(extended_res.resource_object.type_, RT.SystemResource)
        self.assertEquals(extended_res.remote_resource_object.type_, RT.InstrumentDevice)
        self.assertEquals(extended_res.resource_object.name, 'TestSystem_Resource')
        self.assertEquals(extended_res.owner_count, 2)
        self.assertEquals(extended_res.single_owner.name, user_info.name)
        self.assertEquals(len(extended_res.lcstate_transitions), 6)
        self.assertEquals(set(extended_res.lcstate_transitions.keys()), set(['develop', 'deploy', 'retire', 'plan', 'integrate', 'delete']))
        self.assertEquals(len(extended_res.availability_transitions), 2)
        self.assertEquals(set(extended_res.availability_transitions.keys()), set(['enable', 'announce']))

        extended_res = extended_resource_handler.create_extended_resource_container(OT.TestExtendedResourceDevice, '123')
        self.assertEquals(extended_res.resource, instrument_device)
        self.assertEquals(len(extended_res.owners),2)


        with self.assertRaises(Inconsistent) as cm:
            extended_res = extended_resource_handler.create_extended_resource_container(OT.TestExtendedResourceBad, '123')

        #Test adding extra paramaters to methods
        extended_res = extended_resource_handler.create_extended_resource_container(OT.TestExtendedResource, '123', resource_name='AltSystem_Resource')
        self.assertEquals(extended_res.resource, instrument_device)
        self.assertEquals(len(extended_res.owners),2)
        self.assertEquals(extended_res.resource_object.type_, RT.SystemResource)
        self.assertEquals(extended_res.remote_resource_object.type_, RT.InstrumentDevice)
        self.assertEquals(extended_res.resource_object.name, 'AltSystem_Resource')


        #Test field exclusion
        extended_res = extended_resource_handler.create_extended_resource_container(OT.TestExtendedResource, '123',ext_exclude=['owners'])
        self.assertEquals(extended_res.resource, instrument_device)
        self.assertEquals(len(extended_res.owners),0)
        self.assertEquals(extended_res.resource_object.type_, RT.SystemResource)
        self.assertEquals(extended_res.remote_resource_object.type_, RT.InstrumentDevice)

        #Test the list of ids interface
        extended_res_list = extended_resource_handler.create_extended_resource_container_list(OT.TestExtendedResource, ['123','456'])
        self.assertEqual(len(extended_res_list), 2)
        self.assertEquals(extended_res_list[0].resource, instrument_device)
        self.assertEquals(len(extended_res_list[0].owners),2)
        self.assertEquals(extended_res_list[0].resource_object.type_, RT.SystemResource)
        self.assertEquals(extended_res.remote_resource_object.type_, RT.InstrumentDevice)

        #Test create_prepare_update_resource
        prepare_create = extended_resource_handler.create_prepare_resource_support(prepare_resource_type=OT.TestPrepareUpdateResource)
        self.assertEqual(prepare_create.type_, OT.TestPrepareUpdateResource)
        self.assertEqual(prepare_create._id, '')

        prepare_update = extended_resource_handler.create_prepare_resource_support(resource_id='123',prepare_resource_type=OT.TestPrepareUpdateResource)
        self.assertEqual(prepare_update.type_, OT.TestPrepareUpdateResource)
        self.assertEqual(prepare_update._id, '123')

    def get_resource_object(self, my_resource_id, resource_name='TestSystem_Resource'):
        '''
        Method used for testing
        '''
        return IonObject(RT.SystemResource, name=resource_name)

    def test_get_object_schema(self):

        schema = get_object_schema('InstrumentSite')
        self.assertEqual(len(schema['schemas']), 6)
        self.assertItemsEqual([k for k,v in schema['schemas'].iteritems()], ['InstrumentSite', 'PlatformPort', 'GeospatialCoordinateReferenceSystem', 'GeospatialIndex', 'SiteEnvironmentType', 'ResourceVisibilityEnum'])

        #Loop through all of the schemas and get them too.
        for k, v in schema['schemas'].iteritems():
            sub_schema = get_object_schema(k)



