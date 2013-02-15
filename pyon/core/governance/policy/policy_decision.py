    #!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'


from os import path
from StringIO import StringIO

from ndg.xacml.parsers.etree.factory import ReaderFactory


from ndg.xacml.core import Identifiers, XACML_1_0_PREFIX
from ndg.xacml.core.attribute import Attribute
from ndg.xacml.core.attributevalue import (AttributeValue,
                                           AttributeValueClassFactory)
from ndg.xacml.core.context.request import Request
from ndg.xacml.core.context.subject import Subject
from ndg.xacml.core.context.resource import Resource
from ndg.xacml.core.context.action import Action
from ndg.xacml.core.context.pdp import PDP
from ndg.xacml.core.context.result import Decision

from pyon.core.exception import NotFound
from pyon.util.log import log

COMMON_SERVICE_POLICY_RULES = 'common_service_policy_rules'


THIS_DIR = path.dirname(__file__)
XACML_EMPTY_POLICY_FILENAME = 'empty_policy_set.xml'

ROLE_ATTRIBUTE_ID = XACML_1_0_PREFIX + 'subject:subject-role-id'
SENDER_ID = XACML_1_0_PREFIX + 'subject:subject-sender-id'
RECEIVER_TYPE = XACML_1_0_PREFIX + 'resource:receiver-type'

#"""XACML DATATYPES"""
attributeValueFactory = AttributeValueClassFactory()
AnyUriAttributeValue = attributeValueFactory(AttributeValue.ANY_TYPE_URI)
StringAttributeValue = attributeValueFactory(AttributeValue.STRING_TYPE_URI)


class PolicyDecisionPointManager(object):

    def __init__(self, governance_controller):
        self.resource_policy_decision_point = dict()
        self.service_policy_decision_point = dict()

        self.empty_pdp = PDP.fromPolicySource(path.join(THIS_DIR, XACML_EMPTY_POLICY_FILENAME), ReaderFactory)
        self.load_common_service_policy_rules('')

        self.governance_controller = governance_controller

        #No longer need this cause these were added to the XACML engine library, but left here for historical purposes.
        #from pyon.core.governance.policy.xacml.not_function import Not
        #from pyon.core.governance.policy.xacml.and_function import And
        #functionMap['urn:oasis:names:tc:xacml:ooi:function:not'] = Not
        #functionMap['urn:oasis:names:tc:xacml:ooi:function:and'] = And

    def _get_policy_template(self):

        #TODO - Put in resource registry as object and load in preload

        policy_template = '''<?xml version="1.0" encoding="UTF-8"?>
        <Policy xmlns="urn:oasis:names:tc:xacml:2.0:policy:schema:os"
            xmlns:xacml-context="urn:oasis:names:tc:xacml:2.0:context:schema:os"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="urn:oasis:names:tc:xacml:2.0:policy:schema:os http://docs.oasis-open.org/xacml/access_control-xacml-2.0-policy-schema-os.xsd"
            xmlns:xf="http://www.w3.org/TR/2002/WD-xquery-operators-20020816/#"
            xmlns:md="http:www.med.example.com/schemas/record.xsd"
            PolicyId="%s"
            RuleCombiningAlgId="urn:oasis:names:tc:xacml:1.0:rule-combining-algorithm:permit-overrides">
            <PolicyDefaults>
                <XPathVersion>http://www.w3.org/TR/1999/Rec-xpath-19991116</XPathVersion>
            </PolicyDefaults>

            %s
        </Policy>'''

        return policy_template

    def create_policy_from_rules(self, policy_identifier, rules):
        policy = self._get_policy_template()
        policy_rules = policy % (policy_identifier, rules)
        return policy_rules

    #Return a compiled policy indexed by the specified resource_id
    def get_resource_pdp(self, resource_key):

        #First look for requested resource key
        if self.resource_policy_decision_point.has_key(resource_key):
            return self.resource_policy_decision_point[resource_key]

        #If a PDP does not exist for this resource key - then return default
        return self.empty_pdp

    #Return a compiled policy indexed by the specified resource_id
    def get_service_pdp(self, service_name):

        #First look for requested resource key
        if self.service_policy_decision_point.has_key(service_name):
            return self.service_policy_decision_point[service_name]

        #If a PDP does not exist for this resource key - then return common set of service policies
        return self.load_common_service_pdp

    def get_list_service_policies(self):
        return self.service_policy_decision_point.keys()

    def load_common_service_policy_rules(self, rules_text):

        self.common_service_rules = rules_text
        input_source = StringIO(self.create_policy_from_rules(COMMON_SERVICE_POLICY_RULES, rules_text))
        self.load_common_service_pdp = PDP.fromPolicySource(input_source, ReaderFactory)

    def load_service_policy_rules(self, service_name, rules_text):

        if not rules_text and not self.service_policy_decision_point.has_key(service_name):
            return

        log.info("Loading policies for service: %s" % service_name)

        self.clear_service_policy(service_name)
        service_rule_set = self.common_service_rules + rules_text

        #Simply create a new PDP object for the service
        input_source = StringIO(self.create_policy_from_rules(service_name, service_rule_set))
        self.service_policy_decision_point[service_name] = PDP.fromPolicySource(input_source, ReaderFactory)

    def load_resource_policy_rules(self, resource_key, rules_text):

        if not rules_text and not self.resource_policy_decision_point.has_key(resource_key):
            return

        log.info("Loading policies for resource: %s" % resource_key)

        self.clear_resource_policy(resource_key)

        #Simply create a new PDP object for the service
        input_source = StringIO(self.create_policy_from_rules(resource_key, rules_text))
        self.resource_policy_decision_point[resource_key] = PDP.fromPolicySource(input_source, ReaderFactory)

    #Remove any policy indexed by the resource_key
    def clear_resource_policy(self, resource_key):
        if self.resource_policy_decision_point.has_key(resource_key):
            del self.resource_policy_decision_point[resource_key]

    #Remove any policy indexed by the service_name
    def clear_service_policy(self, service_name):
        if self.service_policy_decision_point.has_key(service_name):
            del self.service_policy_decision_point[service_name]

    def create_string_attribute(self, attrib_id, id):
        attribute = Attribute()
        attribute.attributeId = attrib_id
        attribute.dataType = StringAttributeValue.IDENTIFIER
        attribute.attributeValues.append(StringAttributeValue())
        attribute.attributeValues[-1].value = id
        return attribute

    def create_org_role_attribute(self, actor_roles, subject):
        attribute = None
        for role in actor_roles:
            if attribute is None:
                attribute = self.create_string_attribute(ROLE_ATTRIBUTE_ID,  role)
            else:
                attribute.attributeValues.append(StringAttributeValue())
                attribute.attributeValues[-1].value = role

        if attribute is not None:
            subject.attributes.append(attribute)

    def _create_request_from_message(self, invocation, receiver, receiver_type='service'):

        sender_type = invocation.get_header_value('sender-type', 'Unknown')
        if sender_type == 'service':
            sender_header = invocation.get_header_value('sender-service', 'Unknown')
            sender = invocation.get_service_name(sender_header)
        else:
            sender = invocation.get_header_value('sender', 'Unknown')

        op = invocation.get_header_value('op', 'Unknown')
        ion_actor_id = invocation.get_header_value('ion-actor-id', 'anonymous')
        actor_roles = invocation.get_header_value('ion-actor-roles', {})

        log.debug("Using XACML Request: sender: %s, receiver:%s, op:%s,  ion_actor_id:%s, ion_actor_roles:%s" % (sender, receiver, op, ion_actor_id, str(actor_roles)))

        request = Request()
        subject = Subject()
        subject.attributes.append(self.create_string_attribute(SENDER_ID, sender))
        subject.attributes.append(self.create_string_attribute(Identifiers.Subject.SUBJECT_ID, ion_actor_id))

        #Get the Org name associated with the endpoint process
        endpoint_process = invocation.get_arg_value('process', invocation)
        if hasattr(endpoint_process,'org_name'):
            org_name = endpoint_process.org_name
        else:
            org_name = self.governance_controller._system_root_org_name

        #If this process is not associated wiht the root Org, then iterate over the roles associated with the user only for
        #the Org that this process is associated with otherwise include all roles and create attributes for each
        if org_name == self.governance_controller._system_root_org_name:
            log.debug("Including roles for all Orgs")
            #If the process Org name is the same for the System Root Org, then include all of them to be safe
            for org in actor_roles:
                self.create_org_role_attribute(actor_roles[org],subject)
        else:
            if actor_roles.has_key(org_name):
                log.debug("Org Roles (%s): %s" , org_name, ' '.join(actor_roles[org_name]))
                self.create_org_role_attribute(actor_roles[org_name],subject)

            #Handle the special case for the ION system actor
            if actor_roles.has_key(self.governance_controller._system_root_org_name):
                if 'ION_MANAGER' in actor_roles[self.governance_controller._system_root_org_name]:
                    log.debug("Including ION_MANAGER role")
                    self.create_org_role_attribute(['ION_MANAGER'],subject)


        request.subjects.append(subject)

        resource = Resource()
        resource.attributes.append(self.create_string_attribute(Identifiers.Resource.RESOURCE_ID, receiver))
        resource.attributes.append(self.create_string_attribute(RECEIVER_TYPE, receiver_type))
        request.resources.append(resource)

        request.action = Action()
        request.action.attributes.append(self.create_string_attribute(Identifiers.Action.ACTION_ID, op))


        return request

    def check_agent_request_policies(self, invocation):

        process = invocation.get_arg_value('process')

        if not process:
            raise NotFound('Cannot find process in message')

        decision = self._check_service_request_policies(invocation, 'agent')

        # todo: check if its OK to treat everything but Deny as Permit (Ex: NotApplicable)
        # Return if agent service policies deny the operation
        if decision == Decision.DENY_STR:
            return decision

        # Else check any policies that might be associated with the resource.
        decision = self.check_resource_request_policies(invocation, process.resource_id)

        return decision

    def check_service_request_policies(self, invocation):
        decision = self._check_service_request_policies(invocation, 'service')
        return decision

    def _check_service_request_policies(self, invocation, receiver_type):

        receiver = invocation.get_message_receiver()

        if not receiver:
            raise NotFound('No receiver for this message')

        requestCtx = self._create_request_from_message(invocation, receiver, receiver_type)

        pdp = self.get_service_pdp(receiver)

        if pdp is None:
            return Decision.NOT_APPLICABLE_STR

        return self._evaluate_pdp(pdp, requestCtx)

    def check_resource_request_policies(self, invocation, resource_id):

        if not resource_id:
            raise NotFound('The resource_id is not set')

        requestCtx = self._create_request_from_message(invocation, resource_id, 'resource')

        pdp = self.get_resource_pdp(resource_id)

        if pdp is None:
            return Decision.NOT_APPLICABLE_STR

        return self._evaluate_pdp(pdp, requestCtx)

    def _evaluate_pdp(self, pdp, requestCtx):

        try:
            response = pdp.evaluate(requestCtx)
        except Exception, e:
            log.error("Error evaluating policies: %s" % e.message)
            return Decision.NOT_APPLICABLE_STR

        if response is None:
            log.debug('response from PDP contains nothing, so not authorized')
            return Decision.DENY_STR

        for result in response.results:
            if result.decision == Decision.DENY_STR:
                break

        return result.decision
