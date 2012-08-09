#!/usr/bin/env python

__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'


from pyon.util.unit_test import PyonTestCase
from mock import Mock
from nose.plugins.attrib import attr
from pyon.core.governance.governance_controller import GovernanceController
from pyon.core.exception import NotFound, Unauthorized
from pyon.service.service import BaseService

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



@attr('UNIT')
class GovernanceTest(PyonTestCase):

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


        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'func4')
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 3)


        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'self.pre_func1')
        self.assertEqual(len(self.governance_controller.get_process_operation_dict(bs.name)['test_op']), 4)

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

        self.governance_controller.register_process_operation_precondition(bs, 'test_op', 'func4')
        self.governance_controller.check_process_operation_preconditions(bs,{}, {'op': 'test_op'})

class FakeContainer(object):
    def __init__(self):
        self.id = "containerid"
        self.node = None