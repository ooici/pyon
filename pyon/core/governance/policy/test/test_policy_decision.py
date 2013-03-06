#!/usr/bin/env python

__author__ = 'Prashant Kediyal'

from nose.plugins.attrib import attr
from mock import Mock
import unittest
from pyon.core.governance.policy.policy_decision import PolicyDecisionPointManager
from pyon.core.exception import NotFound
from pyon.util.unit_test import PyonTestCase

@attr('UNIT')
class PolicyDecisionUnitTest(PyonTestCase):

    permit_ION_MANAGER_rule = '''
        <Rule RuleId="%s:" Effect="Permit">
            <Description>
                %s
            </Description>


        <Target>
            <Subjects>
                <Subject>
                    <SubjectMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                        <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">ION_MANAGER</AttributeValue>
                        <SubjectAttributeDesignator
                             AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-role-id"
                             DataType="http://www.w3.org/2001/XMLSchema#string"/>
                    </SubjectMatch>
                </Subject>
            </Subjects>
        </Target>


        </Rule>
        '''

    deny_ION_MANAGER_rule = '''
        <Rule RuleId="%s:" Effect="Deny">
            <Description>
                %s
            </Description>


        <Target>
            <Subjects>
                <Subject>
                    <SubjectMatch MatchId="urn:oasis:names:tc:xacml:1.0:function:string-equal">
                        <AttributeValue DataType="http://www.w3.org/2001/XMLSchema#string">ION_MANAGER</AttributeValue>
                        <SubjectAttributeDesignator
                             AttributeId="urn:oasis:names:tc:xacml:1.0:subject:subject-role-id"
                             DataType="http://www.w3.org/2001/XMLSchema#string"/>
                    </SubjectMatch>
                </Subject>
            </Subjects>
        </Target>


        </Rule>
        '''

    def test_resource_policies(self):
        gc = Mock()
        resource_id = 'resource_key'
        pdpm = PolicyDecisionPointManager(gc)
        # see that the PDP for resource is empty
        self.assertEqual(pdpm.get_resource_pdp(resource_id), pdpm.empty_pdp)

        pdpm.load_resource_policy_rules(resource_id, self.permit_ION_MANAGER_rule)

        # see that the PDP for resource is not empty anymore
        self.assertNotEqual(pdpm.get_resource_pdp(resource_id), pdpm.empty_pdp)

        # check request without a resource_id raises NotFound error
        self.invocation = Mock()
        with self.assertRaises(NotFound) as chk_res:
            pdpm.check_resource_request_policies(self.invocation, None)
        self.assertIn(chk_res.exception.message, 'The resource_id is not set')

        # check that, because actor does not have ION_MANAGER role, policy evaluates to a denial
        # (really Not Applicable, because of the inelegant hack of a policy we are setting up our pdp with)
        mock_header = Mock()
        self.invocation.headers = {'op': 'op', 'process': 'process', 'request': 'request', 'ion-actor-id': 'ion-actor-id', 'receiver': 'resource-registry',
                                   'sender-type': 'sender-type', 'sender-service': 'sender-service', 'ion-actor-roles': {'org_name': ['ion-actor-roles']}}

        def get_header_value(key, default):
            return self.invocation.headers.get(key, default)
        mock_header.side_effect = get_header_value
        self.invocation.get_header_value = mock_header
        mock_args = Mock()
        process = Mock()
        process.org_name = 'org_name'
        self.invocation.args = {'process': process}

        def get_arg_value(key, default):
            return self.invocation.args.get(key, default)
        mock_args.side_effect = get_arg_value
        self.invocation.get_arg_value = mock_args

        gc.system_root_org_name = 'sys_org_name'

        response = pdpm.check_resource_request_policies(self.invocation, resource_id)
        self.assertEqual(response.value, "NotApplicable")

        # check that policy evaluates to Permit because actor has ION_MANAGER role
        self.invocation.headers = {'op': 'op', 'process': 'process', 'request': 'request', 'ion-actor-id': 'ion-actor-id', 'receiver': 'resource-registry',
                                   'sender-type': 'sender-type', 'sender-service': 'sender-service', 'ion-actor-roles': {'sys_org_name': ['ION_MANAGER']}}
        response = pdpm.check_resource_request_policies(self.invocation, resource_id)
        self.assertEqual(response.value, "Permit")

    def test_service_policies(self):
        gc = Mock()
        service_key = 'service_key'
        pdpm = PolicyDecisionPointManager(gc)
        # see that the PDP for service is the default
        self.assertEqual(pdpm.get_service_pdp(service_key), pdpm.load_common_service_pdp)

        pdpm.load_service_policy_rules(service_key, self.permit_ION_MANAGER_rule)

        # see that the PDP for service is not the default anymore
        self.assertNotEqual(pdpm.get_service_pdp(service_key), pdpm.load_common_service_pdp)

        # check request without a service_key raises NotFound error
        self.invocation = Mock()
        self.invocation.get_message_receiver.return_value = None
        with self.assertRaises(NotFound) as chk_res:
            pdpm.check_service_request_policies(self.invocation)
        self.assertIn(chk_res.exception.message, 'No receiver for this message')

        # check that, because actor does not have ION_MANAGER role, policy evaluates to a denial
        # (really Not Applicable, because of the inelegant hack of a policy we are setting up our pdp with)
        mock_header = Mock()
        self.invocation.headers = {'op': 'op', 'process': 'process', 'request': 'request', 'ion-actor-id': 'ion-actor-id', 'receiver': 'resource-registry',
                                   'sender-type': 'sender-type', 'sender-service': 'Unknown', 'ion-actor-roles': {'org_name': ['ion-actor-roles']}}
        self.invocation.get_message_receiver.return_value = 'service_key'
        self.invocation.get_service_name.return_value = 'Unknown'

        def get_header_value(key, default):
            return self.invocation.headers.get(key, default)
        mock_header.side_effect = get_header_value
        self.invocation.get_header_value = mock_header
        mock_args = Mock()
        process = Mock()
        process.org_name = 'org_name'
        self.invocation.args = {'process': process}

        def get_arg_value(key, default):
            return self.invocation.args.get(key, default)
        mock_args.side_effect = get_arg_value
        self.invocation.get_arg_value = mock_args

        gc.system_root_org_name = 'sys_org_name'

        response = pdpm.check_service_request_policies(self.invocation)
        self.assertEqual(response.value, "NotApplicable")

        # check that policy evaluates to Permit because actor has ION_MANAGER role
        self.invocation.headers = {'op': 'op', 'process': 'process', 'request': 'request', 'ion-actor-id': 'ion-actor-id', 'receiver': 'resource-registry',
                                   'sender-type': 'sender-type', 'sender-service': 'sender-service', 'ion-actor-roles': {'sys_org_name': ['ION_MANAGER']}}
        response = pdpm.check_service_request_policies(self.invocation)
        self.assertEqual(response.value, "Permit")

    def test_agent_policies(self):

        # set up data
        gc = Mock()
        service_key = 'service_key'
        resource_id = 'resource_id'
        pdpm = PolicyDecisionPointManager(gc)
        self.invocation = Mock()
        mock_header = Mock()
        self.invocation.headers = {'op': 'op', 'process': 'process', 'request': 'request', 'ion-actor-id': 'ion-actor-id', 'receiver': 'resource-registry',
                                   'sender-type': 'sender-type', 'sender-service': 'Unknown', 'ion-actor-roles': {'org_name':  ['ION_MANAGER']}}
        self.invocation.get_message_receiver.return_value = 'service_key'
        self.invocation.get_service_name.return_value = 'Unknown'

        def get_header_value(key, default):
            return self.invocation.headers.get(key, default)
        mock_header.side_effect = get_header_value
        self.invocation.get_header_value = mock_header
        mock_args = Mock()
        process = Mock()
        process.org_name = 'org_name'
        process.resource_id = 'resource_id'
        self.invocation.args = {'process': process}

        def get_arg_value(key, default='Unknown'):
            return self.invocation.args.get(key, default)
        mock_args.side_effect = get_arg_value
        self.invocation.get_arg_value = mock_args
        gc.system_root_org_name = 'sys_org_name'

        # check that service policies result in denying the request
        pdpm.load_service_policy_rules(service_key, self.deny_ION_MANAGER_rule)
        pdpm.load_resource_policy_rules(resource_id, self.permit_ION_MANAGER_rule)
        response = pdpm.check_agent_request_policies(self.invocation)
        self.assertEqual(response.value, "Deny")

        # check that resource policies result in denying the request
        pdpm.load_service_policy_rules(service_key, self.permit_ION_MANAGER_rule)
        pdpm.load_resource_policy_rules(resource_id, self.deny_ION_MANAGER_rule)
        response = pdpm.check_agent_request_policies(self.invocation)
        self.assertEqual(response.value, "Deny")

        # check that both service and resource policies need to allow a request
        pdpm.load_service_policy_rules(service_key, self.permit_ION_MANAGER_rule)
        pdpm.load_resource_policy_rules(resource_id, self.permit_ION_MANAGER_rule)
        response = pdpm.check_agent_request_policies(self.invocation)
        self.assertEqual(response.value, "Permit")
