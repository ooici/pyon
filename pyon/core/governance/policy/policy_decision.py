    #!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

from os import path

from ndg.xacml.parsers.etree.factory import ReaderFactory

from ndg.xacml.core import Identifiers
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

SERVICE_PROVIDER_ATTRIBUTE_ID="urn:oasis:names:tc:xacml:1.0:ooici:resource:service-provider"
ROLE_ATTRIBUTE_ID='urn:oasis:names:tc:xacml:1.0:ooici:subject-id-role'
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
        # TODO - May need to implement a not function here.
        #from pyon.core.governance.ndg_xacml.ooi_and import And
        #functionMap['urn:oasis:names:tc:xacml:ooi:function:and'] = And

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


        ion_actor_id = invocation.headers['ion-actor-id'] if invocation.headers.has_key('ion-actor-id') and invocation.headers['ion-actor-id'] != '' else 'anonymous'
        ion_org_id = invocation.headers['ion-org-id'] if invocation.headers.has_key('ion-org-id') and  invocation.headers['ion-org-id'] != '' else 'no-ooi'
        receiver = invocation.headers['receiver'] if invocation.headers.has_key('receiver') and  invocation.headers['receiver']  != '' else 'Unknown'
        op = invocation.headers['op'] if invocation.headers.has_key('op') and  invocation.headers['op'] != '' else 'Unknown'

        log.debug("XACML Request: ion_actor_id:%s ion-org-id:%s receiver:%s op:%s " % (ion_actor_id,ion_org_id, receiver, op))
        request = Request()
        subject = Subject()
        subject.attributes.append(self.create_string_attribute(Identifiers.Subject.SUBJECT_ID,ion_actor_id))
        subject.attributes.append(self.create_string_attribute(Identifiers.Subject.SUBJECT_ID_QUALIFIER, ion_org_id))

        #subject.attributes.append(createStringAttribute(ROLE_ATTRIBUTE_ID, 'researcher'))
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
    