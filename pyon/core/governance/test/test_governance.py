#!/usr/bin/env python

__author__ = 'Stephen P. Henrie'



from pyon.util.unit_test import PyonTestCase
from mock import Mock
from nose.plugins.attrib import attr
from pyon.core.governance.governance_controller import GovernanceController
from pyon.core.exception import Unauthorized, BadRequest, Inconsistent
from pyon.ion.service import BaseService
from pyon.util.int_test import IonIntegrationTestCase
from pyon.core.bootstrap import IonObject
from pyon.ion.resource import PRED, RT
from pyon.core.governance import ORG_MANAGER_ROLE, ORG_MEMBER_ROLE, ION_MANAGER, GovernanceHeaderValues
from pyon.core.governance import find_roles_by_actor, get_actor_header, get_system_actor_header, get_role_message_headers, get_valid_resource_commitments
from interface.services.examples.hello.ihello_service  import HelloServiceProcessClient
from pyon.util.context import LocalContextMixin

class UnitTestService(BaseService):
    name = 'UnitTestService'

    def test_op(self):
        pass

    def func1(self, msg,  header):
        return True, ''

    def func2(self, msg,  header):
        return False, 'No reason'

    def func3(self, msg,  header):
        return True, ''

    #This invalid test function does not have the proper signature
    def bad_signature(self, msg):
        return True, ''

    #This invalid test function does not have the proper return tuple
    def bad_return(self, msg, header):
        return True


@attr('UNIT')
class GovernanceUnitTest(PyonTestCase):

    governance_controller = None

    def setUp(self):
        FakeContainer = Mock()
        FakeContainer.id = "containerid"
        FakeContainer.node = Mock()
        self.governance_controller = GovernanceController(FakeContainer())

        self.pre_func1 =\
        """def precondition_func(process, msg, headers):
            if headers['op'] != 'test_op':
                return False, 'Cannot call the test_op operation'
            else:
                return True, ''

        """

        self.pre_func2 =\
        """def precondition_func(process, msg, headers):
            if headers['op'] == 'test_op':
                return False, 'Cannot call the test_op operation'
            else:
                return True, ''

        """

        #This invalid test function does not have the proper signature
        self.bad_pre_func1 =\
        """def precondition_func(msg, headers):
            if headers['op'] == 'test_op':
                return False, 'Cannot call the test_op operation'
            else:
                return True, ''

        """

        #This invalid test function does not return the proper tuple
        self.bad_pre_func2 =\
        """def precondition_func(process, msg, headers):
            if headers['op'] == 'test_op':
                return False
            else:
                return True

        """

    def test_initialize_from_config(self):

        intlist = {'conversation', 'information', 'policy'}
        config = {'interceptor_order': intlist,
                  'governance_interceptors':
                  {'conversation': {'class': 'pyon.core.governance.conversation.conversation_monitor_interceptor.ConversationMonitorInterceptor'},
                   'information': {'class': 'pyon.core.governance.information.information_model_interceptor.InformationModelInterceptor'},
                   'policy': {'class': 'pyon.core.governance.policy.policy_interceptor.PolicyInterceptor'}}}

        self.governance_controller.initialize_from_config(config)

        self.assertEquals(self.governance_controller.interceptor_order, intlist)
        self.assertEquals(len(self.governance_controller.interceptor_by_name_dict),
                          len(config['governance_interceptors']))

    # TODO - Need to fill this method out
    def test_process_message(self):
        pass

    def test_register_process_operation_precondition(self):

        bs = UnitTestService()

        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)), 0)
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.func1)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)), 1)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 1)

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'func2')
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 2)

        #Its possible to register invalid functions
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'func4')
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 3)

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'self.pre_func1')
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 4)

        #Its possible to register invalid functions
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.bad_signature)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 5)

    def test_unregister_process_operation_precondition(self):

        bs = UnitTestService()

        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)), 0)
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.func1)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)), 1)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 1)

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'func2')
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 2)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', 'func1')
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 2)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', bs.func1)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 1)

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', self.pre_func1)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 2)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', self.pre_func1)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 1)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op',  'func2')
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)), 0)

    def test_check_process_operation_preconditions(self):

        bs = UnitTestService()

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.func1)
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'func2')
        with self.assertRaises(Unauthorized) as cm:
            self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})
        self.assertIn('No reason', cm.exception.message)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', 'func2')
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.func3)
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.func2)
        with self.assertRaises(Unauthorized) as cm:
            self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})
        self.assertIn('No reason', cm.exception.message)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', bs.func2)
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', self.pre_func1)
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', self.pre_func2)
        with self.assertRaises(Unauthorized) as cm:
            self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})
        self.assertIn('Cannot call the test_op operation', cm.exception.message)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', self.pre_func2)
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})

        #Its possible to register invalid functions - but it should get ignored when checked
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'func4')
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})
        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', 'func4')

        #Its possible to register invalid functions - but it should get ignored when checked
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.bad_signature)
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})
        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', bs.bad_signature)

        #Its possible to register invalid functions - but it should get ignored when checked
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.bad_return)
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})
        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', bs.bad_return)

        #Its possible to register invalid functions - but they it get ignored when checked
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', self.bad_pre_func1)
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})
        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', self.bad_pre_func1)

        #Its possible to register invalid functions - but it should get ignored when checked
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', self.bad_pre_func2)
        self.governance_controller.check_process_operation_preconditions(bs, {}, {'op': 'test_op'})
        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', self.bad_pre_func2)

    def test_resource_policy_event_callback(self):

        event_data = Mock()
        event_data.resource_id = 'resource._id'
        event_data.resource_type = 'resource.type_'
        event_data.resource_name = 'resource.name'
        event_data.origin = 'policy._id'

        policy_rules = 'policy_rules'
        pc = Mock()
        pc.get_active_resource_access_policy_rules.return_value = policy_rules
        self.governance_controller.policy_client = pc
        self.governance_controller.system_actor_user_header = {}
        # call resource_policy_event_callback without a PDP
        self.governance_controller.resource_policy_event_callback(event_data)
        # expect that nothing happened since there was no PDP to update
        self.assertEqual(pc.get_active_resource_access_policy_rules.called, False)

        #add a pdp
        pdp = Mock()
        self.governance_controller.policy_decision_point_manager = pdp

        self.governance_controller.resource_policy_event_callback(event_data)

        # expect that policy rules are retrieved for resource
        pc.get_active_resource_access_policy_rules.assert_called_with(event_data.resource_id, headers={})

        # expect that pdp is called with new rules
        pdp.load_resource_policy_rules.assert_called_with(event_data.resource_id, policy_rules)

    def test_service_policy_event_callback(self):

        # mock service policy event
        service_policy_event = Mock()
        service_policy_event.origin = 'policy_id'
        service_policy_event.service_name = 'UnitTestService'
        service_policy_event.op = 'test_op'

        # mock a container
        container = Mock()
        self.governance_controller.container = container
        # set it up so that service_name resolves neither to a service nor an agent
        container.proc_manager.is_local_service_process.return_value = False
        container.proc_manager.is_local_agent_process.return_value = False

        # add a pdp
        pdp = Mock()
        self.governance_controller.policy_decision_point_manager = pdp

        # check that the pdp is not called because service_name is neither a service nor an agent
        self.governance_controller.service_policy_event_callback(service_policy_event)
        self.assertEqual(pdp.called, False)

        #########
        #########
        # make the service_name a local service process
        container.proc_manager.is_local_service_process.return_value = True

        # set up mock policy client with rules
        policy_rules = 'policy_rules'
        pc = Mock()
        self.governance_controller.policy_client = pc
        self.governance_controller.system_actor_user_header = {}
        pc.get_active_service_access_policy_rules.return_value = policy_rules

        # set local process
        local_process = Mock()
        local_process.name = 'local_process'
        container.proc_manager.get_a_local_process.return_value = local_process
        # register process operation precondition
        self.governance_controller.register_process_operation_precondition(local_process, 'test_op', 'func1')

        # set up the active precondition
        op = Mock()
        op.op = 'test_op_2'
        op.preconditions = ['func2']
        pc.get_active_process_operation_preconditions.return_value = [op]

        self.governance_controller.service_policy_event_callback(service_policy_event)

        # check that the service_policy_event_callback did not delete all registered preconditions (func1) on operation test_op
        self.assertEquals('test_op' in self.governance_controller.get_process_operation_dict(local_process.name), True)
        # and updated with the active one (func2) on test_op2
        self.assertEquals('test_op_2' in self.governance_controller.get_process_operation_dict(local_process.name), True)

        # expect that policy rules are retrieved for resource
        pc.get_active_service_access_policy_rules.assert_called_with(service_name=service_policy_event.service_name, org_name=self.governance_controller.container_org_name, headers={})
        pdp.load_service_policy_rules.assert_called_with(service_policy_event.service_name, policy_rules)


    def test_governance_header_values(self):

        process = Mock()
        process.name = 'test_process'

        headers = {'op': 'test_op', 'process': process, 'request': 'request', 'ion-actor-id': 'ionsystem', 'receiver': 'resource-registry',
                                   'sender-type': 'sender-type', 'resource-id': '123xyz' ,'sender-service': 'sender-service',
                                   'ion-actor-roles': {'ION': [ION_MANAGER, ORG_MANAGER_ROLE, ORG_MEMBER_ROLE]}}

        gov_values = GovernanceHeaderValues(headers)
        self.assertEqual(gov_values.op, 'test_op')
        self.assertEqual(gov_values.process_name, 'test_process')
        self.assertEqual(gov_values.actor_id, 'ionsystem')
        self.assertEqual(gov_values.actor_roles, {'ION': [ION_MANAGER, ORG_MANAGER_ROLE, ORG_MEMBER_ROLE]})
        self.assertEqual(gov_values.resource_id,'123xyz')

        self.assertRaises(BadRequest, GovernanceHeaderValues, {})

        headers = {'op': 'test_op', 'request': 'request', 'ion-actor-id': 'ionsystem', 'receiver': 'resource-registry',
                   'sender-type': 'sender-type', 'resource-id': '123xyz' ,'sender-service': 'sender-service',
                   'ion-actor-roles': {'ION': [ION_MANAGER, ORG_MANAGER_ROLE, ORG_MEMBER_ROLE]}}

        gov_values = GovernanceHeaderValues(headers)
        self.assertEqual(gov_values.op, 'test_op')
        self.assertEqual(gov_values.process_name, 'Unknown-Process')
        self.assertEqual(gov_values.actor_id, 'ionsystem')
        self.assertEqual(gov_values.actor_roles, {'ION': [ION_MANAGER, ORG_MANAGER_ROLE, ORG_MEMBER_ROLE]})
        self.assertEqual(gov_values.resource_id,'123xyz')

        headers = {'op': 'test_op', 'request': 'request', 'receiver': 'resource-registry',
                   'sender-type': 'sender-type', 'resource-id': '123xyz' ,'sender-service': 'sender-service',
                   'ion-actor-roles': {'ION': [ION_MANAGER, ORG_MANAGER_ROLE, ORG_MEMBER_ROLE]}}

        self.assertRaises(Inconsistent, GovernanceHeaderValues, headers)

        headers = {'op': 'test_op', 'request': 'request', 'ion-actor-id': 'ionsystem', 'receiver': 'resource-registry',
                   'sender-type': 'sender-type', 'resource-id': '123xyz' ,'sender-service': 'sender-service',
                   'ion-actor-123-roles': {'ION': [ION_MANAGER, ORG_MANAGER_ROLE, ORG_MEMBER_ROLE]}}

        self.assertRaises(Inconsistent, GovernanceHeaderValues, headers)

        headers = {'op': 'test_op', 'request': 'request', 'ion-actor-id': 'ionsystem', 'receiver': 'resource-registry',
                   'sender-type': 'sender-type','sender-service': 'sender-service',
                   'ion-actor-roles': {'ION': [ION_MANAGER, ORG_MANAGER_ROLE, ORG_MEMBER_ROLE]}}

        self.assertRaises(Inconsistent, GovernanceHeaderValues, headers)

        gov_values = GovernanceHeaderValues(headers, resource_id_required=False)
        self.assertEqual(gov_values.op, 'test_op')
        self.assertEqual(gov_values.process_name, 'Unknown-Process')
        self.assertEqual(gov_values.actor_id, 'ionsystem')
        self.assertEqual(gov_values.actor_roles, {'ION': [ION_MANAGER, ORG_MANAGER_ROLE, ORG_MEMBER_ROLE]})
        self.assertEqual(gov_values.resource_id,'')


class GovernanceTestProcess(LocalContextMixin):
    name = 'gov_test'
    id='gov_client'
    process_type = 'simple'


@attr('INT')
class GovernanceIntTest(IonIntegrationTestCase):


    def setUp(self):

        self._start_container()

        #Instantiate a process to represent the test
        self.gov_client = GovernanceTestProcess()

        self.rr = self.container.resource_registry

    def add_user_role(self, org='', user_role=None):
        """Adds a UserRole to an Org. Will call Policy Management Service to actually
        create the role object that is passed in, if the role by the specified
        name does not exist. Throws exception if either id does not exist.
        """
        user_role.org_governance_name = org.org_governance_name
        user_role_id, _ = self.rr.create(user_role)

        aid = self.rr.create_association(org._id, PRED.hasRole, user_role_id)

        return user_role_id

    def test_get_actor_header(self):

        #Setup data
        actor = IonObject(RT.ActorIdentity, name='actor1')
        actor_id, _ = self.rr.create(actor)

        ion_org = IonObject(RT.Org, name='ION', org_governance_name='ION')
        ion_org_id, _ = self.rr.create(ion_org)
        ion_org._id = ion_org_id

        manager_role = IonObject(RT.UserRole, name='Org Manager', governance_name=ORG_MANAGER_ROLE, description='Org Manager')
        manager_role_id = self.add_user_role(ion_org, manager_role)

        member_role = IonObject(RT.UserRole, name='Org Member', governance_name=ORG_MEMBER_ROLE, description='Org Member')


        # all actors have a defaul org_member_role
        actor_roles = find_roles_by_actor(actor_id)
        self.assertDictEqual(actor_roles, {'ION': [ORG_MEMBER_ROLE]})

        actor_header = get_actor_header(actor_id)
        self.assertDictEqual(actor_header, {'ion-actor-id': actor_id, 'ion-actor-roles': {'ION': [ORG_MEMBER_ROLE]}})

        #Add Org Manager Role
        self.rr.create_association(actor_id, PRED.hasRole, manager_role_id)

        actor_roles = find_roles_by_actor(actor_id)
        role_header = get_role_message_headers({'ION': [manager_role, member_role]})
        self.assertDictEqual(actor_roles, role_header)

        org2 = IonObject(RT.Org, name='Org 2', org_governance_name='Second_Org')

        org2_id, _ = self.rr.create(org2)
        org2._id = org2_id


        member2_role = IonObject(RT.UserRole, governance_name=ORG_MEMBER_ROLE, name='Org Member', description='Org Member')
        member2_role_id = self.add_user_role(org2, member2_role)

        operator2_role = IonObject(RT.UserRole, governance_name='INSTRUMENT_OPERATOR', name='Instrument Operator',
                                   description='Instrument Operator')
        operator2_role_id = self.add_user_role(org2, operator2_role)

        self.rr.create_association(actor_id, PRED.hasRole, member2_role_id)

        self.rr.create_association(actor_id, PRED.hasRole, operator2_role_id)

        actor_roles = find_roles_by_actor(actor_id)

        role_header = get_role_message_headers({'ION': [manager_role, member_role], 'Second_Org': [operator2_role, member2_role]})

        self.assertEqual(len(actor_roles), 2)
        self.assertEqual(len(role_header), 2)
        self.assertIn('Second_Org', actor_roles)
        self.assertIn('Second_Org', role_header)
        self.assertEqual(len(actor_roles['Second_Org']), 2)
        self.assertEqual(len(role_header['Second_Org']), 2)
        self.assertIn('INSTRUMENT_OPERATOR', actor_roles['Second_Org'])
        self.assertIn('INSTRUMENT_OPERATOR', role_header['Second_Org'])
        self.assertIn(ORG_MEMBER_ROLE, actor_roles['Second_Org'])
        self.assertIn(ORG_MEMBER_ROLE, role_header['Second_Org'])
        self.assertIn('ION', actor_roles)
        self.assertIn('ION', role_header)
        self.assertIn(ORG_MANAGER_ROLE, actor_roles['ION'])
        self.assertIn(ORG_MEMBER_ROLE, actor_roles['ION'])
        self.assertIn(ORG_MANAGER_ROLE, role_header['ION'])
        self.assertIn(ORG_MEMBER_ROLE, role_header['ION'])

        actor_header = get_actor_header(actor_id)

        self.assertEqual(actor_header['ion-actor-id'], actor_id)
        self.assertEqual(actor_header['ion-actor-roles'], actor_roles)

        #Now make sure we can change the name of the Org and not affect the headers
        org2 = self.rr.read(org2_id)
        org2.name = 'Updated Org 2'
        org2_id, _ = self.rr.update(org2)

        actor_roles = find_roles_by_actor(actor_id)

        self.assertEqual(len(actor_roles), 2)
        self.assertEqual(len(role_header), 2)
        self.assertIn('Second_Org', actor_roles)
        self.assertIn('Second_Org', role_header)
        self.assertEqual(len(actor_roles['Second_Org']), 2)
        self.assertEqual(len(role_header['Second_Org']), 2)
        self.assertIn('INSTRUMENT_OPERATOR', actor_roles['Second_Org'])
        self.assertIn('INSTRUMENT_OPERATOR', role_header['Second_Org'])
        self.assertIn(ORG_MEMBER_ROLE, actor_roles['Second_Org'])
        self.assertIn(ORG_MEMBER_ROLE, role_header['Second_Org'])
        self.assertIn('ION', actor_roles)
        self.assertIn('ION', role_header)
        self.assertIn(ORG_MANAGER_ROLE, actor_roles['ION'])
        self.assertIn(ORG_MEMBER_ROLE, actor_roles['ION'])
        self.assertIn(ORG_MANAGER_ROLE, role_header['ION'])
        self.assertIn(ORG_MEMBER_ROLE, role_header['ION'])

        actor_header = get_actor_header(actor_id)

        self.assertEqual(actor_header['ion-actor-id'], actor_id)
        self.assertEqual(actor_header['ion-actor-roles'], actor_roles)


    def test_get_sytsem_actor_header(self):
        actor = IonObject(RT.ActorIdentity, name='ionsystem')

        actor_id, _ = self.rr.create(actor)

        system_actor_header = get_system_actor_header()
        self.assertDictEqual(system_actor_header['ion-actor-roles'],{'ION': [ORG_MEMBER_ROLE]})

    def test_get_valid_resource_commitment(self):
        from pyon.util.containers import get_ion_ts_millis

        # create ION org and an actor
        ion_org = IonObject(RT.Org, name='ION')
        ion_org_id, _ = self.rr.create(ion_org)
        ion_org._id = ion_org_id
        actor = IonObject(RT.ActorIdentity, name='actor1')
        actor_id, _ = self.rr.create(actor)

        # create an expired commitment in the org
        ts = get_ion_ts_millis() - 50000
        com_obj = IonObject(RT.Commitment, provider=ion_org_id, consumer=actor_id, commitment=True, expiration=ts)
        com_id, _ = self.rr.create(com_obj)
        id = self.rr.create_association(ion_org_id, PRED.hasCommitment, com_id)
        c = get_valid_resource_commitments(ion_org_id, actor_id)
        #verify that the commitment is not returned
        self.assertIsNone(c)

        # create a commitment that has not expired yet
        ts = get_ion_ts_millis() + 50000
        com_obj = IonObject(RT.Commitment, provider=ion_org_id, consumer=actor_id, commitment=True, expiration=ts)
        com_id, _ = self.rr.create(com_obj)
        id = self.rr.create_association(ion_org_id, PRED.hasCommitment, com_id)
        c = get_valid_resource_commitments(ion_org_id, actor_id)

        #verify that the commitment is returned
        self.assertIsNotNone(c)


    ### THIS TEST USES THE HELLO SERVICE EXAMPLE

    @attr('PRECONDITION1')
    def test_multiple_process_pre_conditions(self):
        hello1 = self.container.spawn_process('hello_service1','examples.service.hello_service','HelloService' )
        self.addCleanup(self.container.terminate_process, hello1)

        hello2 = self.container.spawn_process('hello_service2','examples.service.hello_service','HelloService' )
        self.addCleanup(self.container.terminate_process, hello2)

        hello3 = self.container.spawn_process('hello_service3','examples.service.hello_service','HelloService' )
        #self.addCleanup(self.container.terminate_process, hello3)

        client = HelloServiceProcessClient(node=self.container.node, process=self.gov_client)

        actor_id='anonymous'
        text='mytext 123'

        actor_headers = get_actor_header(actor_id)
        ret = client.hello(text, headers=actor_headers)
        self.assertIn(text, ret)

        with self.assertRaises(Unauthorized) as cm:
            ret = client.noop(text=text)
        self.assertIn('The noop operation has been denied', cm.exception.message)

        self.container.terminate_process(hello3)

        with self.assertRaises(Unauthorized) as cm:
            ret = client.noop(text=text)
        self.assertIn('The noop operation has been denied', cm.exception.message)
