#!/usr/bin/env python

__author__ = 'Prashant Kediyal'

from nose.plugins.attrib import attr
from mock import Mock
from pyon.core.governance.policy.policy_interceptor import PolicyInterceptor
from ndg.xacml.core.context.result import Decision
from pyon.util.int_test import IonIntegrationTestCase
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher



@attr('INT')
class PolicyInterceptorIntTest(IonIntegrationTestCase):

    def setUp(self):
        self._start_container()
        # create the object to be tested
        self.policy_interceptor = PolicyInterceptor()

        #set up the invocation parameter which is passed to the outgoing and incoming methods
        self.invocation = Mock()
        self.invocation.get_arg_value.return_value = 'invocation.get_arg_value(''process'', invocation)'

    def test_outgoing(self):
        policy_interceptor = self.policy_interceptor
        invocation = self.invocation

        rval = policy_interceptor.outgoing(invocation)

        # makes no changes
        self.assertEquals(rval, invocation)
        # check that invocation is called to get arg value
        invocation.get_arg_value.assert_called_with('process', invocation)

    def test_incoming(self):

        ##########
        #           TEST 1
        #           check a request is denied
        ##########
        policy_interceptor = self.policy_interceptor

        # mock up invocation header values
        mock_header = Mock()
        self.invocation.headers = {'op':'not_start_from_rel', 'process':'process','request':'request','ion-actor-id':'ion-actor-id','receiver':'resource-registry'}

        def get_header_value(key, default):
            return self.invocation.headers.get(key, default)

        mock_header.side_effect = get_header_value
        self.invocation.get_header_value = mock_header

        #run test case when messages are not to resource_registry and it is so set up that request is denied
        self.invocation.get_message_receiver.return_value = 'not_resource_registry'
        message_annotations = {}
        self.invocation.message_annotations = message_annotations

        # patch its governance_controller
        governance_controller = Mock()
        self.container.instance.governance_controller = governance_controller
        policy_interceptor.Container = self.container

        # set it up so that the request is denied
        governance_controller.policy_decision_point_manager.check_resource_request_policies.return_value = Decision.DENY_STR
        governance_controller.get_container_org_boundary_id.return_value = 'ion'

        rval = policy_interceptor.incoming(self.invocation)
        # check that the request is denied
        self.assertEquals(rval.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION], GovernanceDispatcher.STATUS_REJECT)

        ##########
        #           TEST 2
        #           check that request (one that doesn't have a policy token) fails when sent to resource_registry
        ##########

        # simulate that the higher service is calling the resource registry with token set previously
        self.invocation.get_message_receiver.return_value = 'resource_registry'
        # simulate creating a policy token to be part of invocation
        #policy_token = create_policy_token('ion','ion-actor-id','requesting_message', 'ALLOW_RESOURCE_REGISTRY_SUB_CALLS')


        # Since this is a sub RPC request to the RR (resource registry) from a higher level service that has already been validated and set a token
        # then skip checking policy yet again - should help with performance and to simplify policy
        # thus the invocation is simply returned back
        rval = policy_interceptor.incoming(self.invocation)
        self.assertEquals(rval.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION], GovernanceDispatcher.STATUS_REJECT)



        ##########
        #           TEST 3
        #           check a request from an agent is accepted
        ##########

        # make this an invocation from an agent
        self.invocation.get_invocation_process_type.return_value = 'agent'

        # set it up so that the request is accepted
        governance_controller.policy_decision_point_manager.check_resource_request_policies.return_value = Decision.PERMIT
        governance_controller.policy_decision_point_manager.check_agent_request_policies.return_value = Decision.PERMIT

        rval = policy_interceptor.incoming(self.invocation)
        # check that the request is accepted
        self.assertEquals(rval.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION], GovernanceDispatcher.STATUS_COMPLETE)


        ##########
        #           TEST 4
        #           check that the validated request (one that has a policy token) from TEST3 passes through when sent to resource_registry
        ##########

        # simulate that the higher service is calling the resource registry with token set previously
        self.invocation.get_message_receiver.return_value = 'resource_registry'

        # Since this is a sub RPC request to the RR (resource registry) from a higher level service that has already been validated and set a token
        # then skip checking policy yet again - should help with performance and to simplify policy
        # thus the invocation is simply returned back
        rval = policy_interceptor.incoming(self.invocation)
        self.assertEquals(rval.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION], GovernanceDispatcher.STATUS_COMPLETE)

        ##########
        #           TEST 5
        #           check a request from a service is accepted
        ##########

        # make this an invocation from a service
        self.invocation.get_invocation_process_type.return_value = 'service'

        # set it up so that the request is accepted
        governance_controller.policy_decision_point_manager.check_service_request_policies.return_value = Decision.PERMIT

        rval = policy_interceptor.incoming(self.invocation)
        # check that the request is accepted
        self.assertEquals(rval.message_annotations[GovernanceDispatcher.POLICY__STATUS_ANNOTATION], GovernanceDispatcher.STATUS_COMPLETE)

