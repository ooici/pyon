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
from pyon.core.exception import ContainerError

from ndg.xacml.core.context.request import Request
from ndg.xacml.core.context.subject import Subject
from ndg.xacml.core.context.resource import Resource
from ndg.xacml.core.context.action import Action
from ndg.xacml.core.context.pdp import PDP
from ndg.xacml.core.context.result import Decision
from ndg.xacml.core.functions import functionMap, FunctionMap

from pyon.util.log import log


THIS_DIR = path.dirname(__file__)
XACML_SAMPLE_POLICY_FILENAME='sample_policies.xml'
XACML_EMPTY_POLICY_FILENAME='empty_policy_set.xml'


SERVICE_PROVIDER_ATTRIBUTE=XACML_1_0_PREFIX + 'resource:service-provider'
ROLE_ATTRIBUTE_ID=XACML_1_0_PREFIX + 'subject:subject-role-id'
SENDER_ID=XACML_1_0_PREFIX + 'subject:subject-sender-id'

#"""XACML DATATYPES"""
attributeValueFactory = AttributeValueClassFactory()
AnyUriAttributeValue = attributeValueFactory(AttributeValue.ANY_TYPE_URI)
StringAttributeValue = attributeValueFactory(AttributeValue.STRING_TYPE_URI)

class PolicyDecisionPointManager(object):

    def __init__(self, *args, **kwargs):
        self.policy_decision_point = dict()
        self.default_pdp = None

        #Adding an not function to XACML
        from pyon.core.governance.policy.xacml.not_function import Not
        from pyon.core.governance.policy.xacml.and_function import And
        functionMap['urn:oasis:names:tc:xacml:ooi:function:not'] = Not
        functionMap['urn:oasis:names:tc:xacml:ooi:function:and'] = And


    def get_pdp(self, resource_policy):


        if self.policy_decision_point.has_key(resource_policy):
            return self.policy_decision_point[resource_policy]

        #If a PDP does not exist for this resource - then return default.
        if self.default_pdp is None:
            #Loads a blank policy set as the default or an unknown resource_policy
            self.default_pdp = PDP.fromPolicySource(path.join(THIS_DIR, XACML_EMPTY_POLICY_FILENAME), ReaderFactory)

        return self.default_pdp


    def load_policy_rules(self, resource_policy, rules_text):
        log.debug("Loading rules for service: %s" % resource_policy)

        #Simply create a new PDP object for the service
        #TODO - make sure this is thread safe with the evaluation that uses it.
        input_source = StringIO(rules_text)
        self.policy_decision_point[resource_policy] = PDP.fromPolicySource(input_source, ReaderFactory)



    def create_string_attribute(self, attrib_id, id):
        attribute = Attribute()
        attribute.attributeId = attrib_id
        attribute.dataType = StringAttributeValue.IDENTIFIER
        attribute.attributeValues.append(StringAttributeValue())
        attribute.attributeValues[-1].value = id
        return attribute

    def create_request_from_message(self, invocation):


        sender_type = invocation.get_header_value('sender-type', 'Unknown')
        if sender_type == 'service':
            sender_header = invocation.get_header_value('sender-service', 'Unknown')
            sender = invocation.get_service_name(sender_header)
        else:
            sender = invocation.get_header_value('sender', 'Unknown')

        receiver_header = invocation.get_header_value('receiver', 'Unknown')
        receiver = invocation.get_service_name(receiver_header)

        op = invocation.get_header_value('op', 'Unknown')
        ion_actor_id = invocation.get_header_value('ion-actor-id', 'anonymous')
        actor_roles = invocation.get_header_value('ion-actor-roles', {})



        log.debug("XACML Request: sender: %s, receiver:%s, op:%s,  ion_actor_id:%s, ion_actor_roles:%s" % (sender, receiver, op, ion_actor_id, str(actor_roles)))


        request = Request()
        subject = Subject()
        subject.attributes.append(self.create_string_attribute(SENDER_ID,sender))
        subject.attributes.append(self.create_string_attribute(Identifiers.Subject.SUBJECT_ID,ion_actor_id))

        #Iterate over the roles associated with the user and create attributes for each
        for org in actor_roles:
            attribute = None
            for role in actor_roles[org]:
                if attribute is None:
                    attribute = self.create_string_attribute(ROLE_ATTRIBUTE_ID,  role)  #TODO - Figure out how to handle multiple Org Roles
                else:
                    attribute.attributeValues.append(StringAttributeValue())
                    attribute.attributeValues[-1].value = org + "_" + role

            subject.attributes.append(attribute)

        request.subjects.append(subject)

        resource = Resource()
        resource.attributes.append(self.create_string_attribute(Identifiers.Resource.RESOURCE_ID, receiver))
        request.resources.append(resource)

        request.action = Action()
        request.action.attributes.append(self.create_string_attribute(Identifiers.Action.ACTION_ID, op))
        return request


    def check_policies(self, invocation):


        receiver_header = invocation.get_header_value('receiver', 'Unknown')
        receiver = invocation.get_service_name(receiver_header)

        #TODO - Only handing services at the moment - enhance for generic resources
        resource_pdp = self.get_pdp(receiver)

        if resource_pdp is None:
            log.debug("pdp could not be created for resource: %s" % receiver )

        requestCtx = self.create_request_from_message(invocation)

        try:
            response = resource_pdp.evaluate(requestCtx)
        except Exception, e:
            log.error("Error evaluating policies: %s" % e.message)
            return Decision.NOT_APPLICABLE_STR

        if response is None:
            log.debug('response from PDP contains nothing, so not authorized')
            return Decision.DENY_STR
        else:
            for result in response.results:
                if str(result.decision) == Decision.DENY_STR:
                    break

        return result.decision
    