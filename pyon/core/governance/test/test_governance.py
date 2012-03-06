#!/usr/bin/env python

__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'


from pyon.util.unit_test import PyonTestCase
from mock import Mock
from nose.plugins.attrib import attr
from pyon.core.governance.governance_controller import GovernanceController

@attr('UNIT')
class GovernanceTest(PyonTestCase):

    governance_controller = None
    
    def setUp(self):
        self.governance_controller = GovernanceController()
  
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

