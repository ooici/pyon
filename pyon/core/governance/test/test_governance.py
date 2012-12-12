#!/usr/bin/env python

__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'


from pyon.util.unit_test import PyonTestCase
from mock import Mock
from nose.plugins.attrib import attr
from pyon.core.governance.governance_controller import GovernanceController
from pyon.core.exception import NotFound, Unauthorized
from pyon.service.service import BaseService
from pyon.util.int_test import IonIntegrationTestCase
from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound, Inconsistent
from pyon.ion.resource import PRED, RT
from pyon.core.governance.governance_controller import ORG_MANAGER_ROLE, ORG_MEMBER_ROLE, ION_MANAGER

class FakeContainer(object):
    def __init__(self):
        self.id = "containerid"
        self.node = None


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
        config = {'interceptor_order':intlist,
                  'governance_interceptors':
                    {'conversation': {'class': 'pyon.core.governance.conversation.conversation_monitor_interceptor.ConversationMonitorInterceptor' },
                    'information': {'class': 'pyon.core.governance.information.information_model_interceptor.InformationModelInterceptor' },
                    'policy': {'class': 'pyon.core.governance.policy.policy_interceptor.PolicyInterceptor' } }}

        self.governance_controller.initialize_from_config(config)

        self.assertEquals(self.governance_controller.interceptor_order,intlist)
        self.assertEquals(len(self.governance_controller.interceptor_by_name_dict),len(config['governance_interceptors']))

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
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 1)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', 'func1')
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 1)


        self.governance_controller.register_process_operation_precondition(bs, 'test_op', self.pre_func1)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 2)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', self.pre_func1)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 1)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op',  bs.func2)
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)), 0)


    def test_check_process_operation_preconditions(self):

        bs = UnitTestService()

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.func1)
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'func2')
        with self.assertRaises(Unauthorized) as cm:
            self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})
        self.assertIn('No reason',cm.exception.message)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', bs.func2)
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.func3)
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.func2)
        with self.assertRaises(Unauthorized) as cm:
            self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})
        self.assertIn('No reason',cm.exception.message)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', 'func2')
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})


        self.governance_controller.register_process_operation_precondition(bs, 'test_op', self.pre_func1)
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', self.pre_func2)
        with self.assertRaises(Unauthorized) as cm:
            self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})
        self.assertIn('Cannot call the test_op operation',cm.exception.message)

        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', self.pre_func2)
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})

        #Its possible to register invalid functions - but it should get ignored when checked
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'func4')
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})
        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', 'func4')

        #Its possible to register invalid functions - but it should get ignored when checked
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.bad_signature)
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})
        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', bs.bad_signature)

        #Its possible to register invalid functions - but it should get ignored when checked
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', bs.bad_return)
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})
        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', bs.bad_return)

        #Its possible to register invalid functions - but they it get ignored when checked
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', self.bad_pre_func1)
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})
        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', self.bad_pre_func1)

        #Its possible to register invalid functions - but it should get ignored when checked
        self.governance_controller.register_process_operation_precondition(bs, 'test_op', self.bad_pre_func2)
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})
        self.governance_controller.unregister_process_operation_precondition(bs, 'test_op', self.bad_pre_func2)



@attr('INT')
class GovernanceIntTest(IonIntegrationTestCase):

    def setUp(self):
        self._start_container()

        self.rr = self.container.resource_registry


    def add_user_role(self, org='', user_role=None):
        """Adds a UserRole to an Org. Will call Policy Management Service to actually
        create the role object that is passed in, if the role by the specified
        name does not exist. Throws exception if either id does not exist.
        """
        user_role.org_name = org.name
        user_role_id,_ = self.rr.create(user_role)

        aid = self.rr.create_association(org._id, PRED.hasRole, user_role_id)

        return user_role_id

    def test_get_actor_header(self):


        #Setup data
        actor = IonObject(RT.ActorIdentity, name='actor1')

        actor_id,_ = self.rr.create(actor)

        ion_org = IonObject(RT.Org, name='ION')

        ion_org_id,_ = self.rr.create(ion_org)
        ion_org._id = ion_org_id

        manager_role = IonObject(RT.UserRole, name=ORG_MANAGER_ROLE,label='Org Manager', description='Org Manager')
        manager_role_id = self.add_user_role(ion_org, manager_role)

        member_role = IonObject(RT.UserRole, name=ORG_MEMBER_ROLE,label='Org Member', description='Org Member')
        member_role_id = self.add_user_role(ion_org, member_role)

        actor_roles = self.container.governance_controller.find_roles_by_actor(actor_id)
        self.assertDictEqual(actor_roles, {'ION': [ORG_MEMBER_ROLE]})

        actor_header = self.container.governance_controller.get_actor_header(actor_id)
        self.assertDictEqual(actor_header, {'ion-actor-id': actor_id, 'ion-actor-roles': {'ION': [ORG_MEMBER_ROLE]}})


        #Add Org Manager Role
        aid = self.rr.create_association(actor_id, PRED.hasRole, manager_role_id)

        actor_roles = self.container.governance_controller.find_roles_by_actor(actor_id)
        self.assertDictEqual(actor_roles, {'ION': [ORG_MANAGER_ROLE, ORG_MEMBER_ROLE]})

        org2 = IonObject(RT.Org, name='Org2')

        org2_id,_ = self.rr.create(org2)
        org2._id = org2_id

        manager2_role = IonObject(RT.UserRole, name=ORG_MANAGER_ROLE,label='Org Manager', description='Org Manager')
        manager2_role_id = self.add_user_role(org2, manager_role)

        member2_role = IonObject(RT.UserRole, name=ORG_MEMBER_ROLE,label='Org Member', description='Org Member')
        member2_role_id = self.add_user_role(org2, member2_role)

        operator2_role = IonObject(RT.UserRole, name='INSTRUMENT_OPERATOR',label='Instrument Operator', description='Instrument Operator')
        operator2_role_id = self.add_user_role(org2, operator2_role)

        aid = self.rr.create_association(actor_id, PRED.hasRole, member2_role_id)

        aid = self.rr.create_association(actor_id, PRED.hasRole, operator2_role_id)

        actor_roles = self.container.governance_controller.find_roles_by_actor(actor_id)
        self.assertEqual(len(actor_roles), 2)
        self.assertIn('Org2', actor_roles)
        self.assertEqual(len(actor_roles['Org2']), 2)
        self.assertIn('INSTRUMENT_OPERATOR', actor_roles['Org2'])
        self.assertIn(ORG_MEMBER_ROLE, actor_roles['Org2'])
        self.assertIn('ION', actor_roles)
        self.assertIn(ORG_MANAGER_ROLE, actor_roles['ION'])
        self.assertIn(ORG_MEMBER_ROLE, actor_roles['ION'])

        actor_header = self.container.governance_controller.get_actor_header(actor_id)

        self.assertEqual(actor_header['ion-actor-id'], actor_id)
        self.assertEqual(actor_header['ion-actor-roles'], actor_roles)
