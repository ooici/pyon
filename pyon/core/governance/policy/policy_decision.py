    #!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

from os import path

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
XACML_ION_POLICY_FILENAME='sample_policies.xml'

SERVICE_PROVIDER_ATTRIBUTE_ID=XACML_1_0_PREFIX + 'resource:service-provider'
ROLE_ATTRIBUTE_ID=XACML_1_0_PREFIX + 'subject:subject-role'
SENDER_ID=XACML_1_0_PREFIX + 'subject:subject-id-sender'

#"""XACML DATATYPES"""
attributeValueFactory = AttributeValueClassFactory()
AnyUriAttributeValue = attributeValueFactory(AttributeValue.ANY_TYPE_URI)
StringAttributeValue = attributeValueFactory(AttributeValue.STRING_TYPE_URI)

class PolicyDecisionPoint(object):

    def __init__(self, *args, **kwargs):
        self.policy_decision_point = None

    def createPDP(self):
        """Create PDP from ion agents policy file"""

        log.debug("Creating a new PDP")
        #Adding an not function to XACML
        from pyon.core.governance.policy.xacml.not_function import Not
        from pyon.core.governance.policy.xacml.not_equal import NotEqualBase
        functionMap['urn:oasis:names:tc:xacml:ooi:function:not'] = Not
        #functionMap['urn:oasis:names:tc:xacml:ooi:function:string-not-equal'] = NotEqualBase

        self.policy_decision_point = PDP.fromPolicySource(path.join(THIS_DIR, XACML_ION_POLICY_FILENAME), ReaderFactory)

        return self.policy_decision_point


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



        log.info("XACML Request: sender: %s, receiver:%s, op:%s,  ion_actor_id:%s, ion_actor_roles:%s" % (sender, receiver, op, ion_actor_id, str(actor_roles)))


        request = Request()
        subject = Subject()
        subject.attributes.append(self.create_string_attribute(SENDER_ID,sender))
        subject.attributes.append(self.create_string_attribute(Identifiers.Subject.SUBJECT_ID,ion_actor_id))
       # subject.attributes.append(self.create_string_attribute(Identifiers.Subject.SUBJECT_ID_QUALIFIER, ion_org_id))

        #Iterate over the roles associated with the user and create attributes for each - #TODO - figure out how to specify proper Org from multiple Orgs.
        for org in actor_roles:
            for role in actor_roles[org]:
                subject.attributes.append(self.create_string_attribute(ROLE_ATTRIBUTE_ID+'-'+role, "True"))

        request.subjects.append(subject)

        resource = Resource()
        resource.attributes.append(self.create_string_attribute(Identifiers.Resource.RESOURCE_ID, receiver))
        request.resources.append(resource)

        request.action = Action()
        request.action.attributes.append(self.create_string_attribute(Identifiers.Action.ACTION_ID, op))
        return request


    def check_policies(self, invocation):


        requestCtx = self.create_request_from_message(invocation)

        if self.policy_decision_point is None:
            self.createPDP()

        if self.policy_decision_point is None:
            log.debug("pdp could not be created")
            raise ContainerError("Could not create the PDP instance")

        response = self.policy_decision_point.evaluate(requestCtx)

        if response is None:
            log.debug('response from PDP contains nothing, so not authorized')
            return Decision.DENY_STR
        else:
            for result in response.results:
                if str(result.decision) == Decision.DENY_STR:
                    break

        return result.decision
    