    #!/usr/bin/env python


__author__ = 'Stephen P. Henrie'



from os import path
from StringIO import StringIO

from ndg.xacml.parsers.etree.factory import ReaderFactory


from ndg.xacml.core import Identifiers, XACML_1_0_PREFIX
from ndg.xacml.core.attribute import Attribute
from ndg.xacml.core.attributevalue import (AttributeValue,
                                           AttributeValueClassFactory)
from ndg.xacml.core.functions import functionMap
from ndg.xacml.core.context.request import Request
from ndg.xacml.core.context.subject import Subject
from ndg.xacml.core.context.resource import Resource
from ndg.xacml.core.context.action import Action
from ndg.xacml.core.context.environment import Environment
from ndg.xacml.core.context.pdp import PDP
from ndg.xacml.core.context.result import Decision
from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound
from pyon.core.governance import ION_MANAGER
from pyon.core.registry import is_ion_object, message_classes, get_class_decorator_value
from pyon.core.governance.governance_dispatcher import GovernanceDispatcher

from pyon.util.log import log

COMMON_SERVICE_POLICY_RULES = 'common_service_policy_rules'


THIS_DIR = path.dirname(__file__)
XACML_EMPTY_POLICY_FILENAME = 'empty_policy_set.xml'

ROLE_ATTRIBUTE_ID = XACML_1_0_PREFIX + 'subject:subject-role-id'
SENDER_ID = XACML_1_0_PREFIX + 'subject:subject-sender-id'
RECEIVER_TYPE = XACML_1_0_PREFIX + 'resource:receiver-type'
ACTION_VERB = XACML_1_0_PREFIX + 'action:action-verb'
ACTION_PARAMETERS = XACML_1_0_PREFIX + 'action:param-dict'

DICT_TYPE_URI = AttributeValue.IDENTIFIER_PREFIX + 'dict'
OBJECT_TYPE_URI = AttributeValue.IDENTIFIER_PREFIX + 'object'

#"""XACML DATATYPES"""
attributeValueFactory = AttributeValueClassFactory()
StringAttributeValue = attributeValueFactory(AttributeValue.STRING_TYPE_URI)
IntAttributeValue = attributeValueFactory(AttributeValue.INTEGER_TYPE_URI)
DoubleAttributeValue = attributeValueFactory(AttributeValue.DOUBLE_TYPE_URI)
BooleanAttributeValue = attributeValueFactory(AttributeValue.BOOLEAN_TYPE_URI)


class PolicyDecisionPointManager(object):

    def __init__(self, governance_controller):
        self.resource_policy_decision_point = dict()
        self.service_policy_decision_point = dict()

        self.empty_pdp = PDP.fromPolicySource(path.join(THIS_DIR, XACML_EMPTY_POLICY_FILENAME), ReaderFactory)
        self.load_common_service_policy_rules('')

        self.governance_controller = governance_controller


        #Create and register an Attribute Value derived class to handle a dict type used for the messages
        _className = 'Dict' + AttributeValue.CLASS_NAME_SUFFIX
        _classVars = {'TYPE': dict, 'IDENTIFIER': DICT_TYPE_URI}
        _attributeValueClass = type(_className, (AttributeValue, ), _classVars)
        AttributeValue.register(_attributeValueClass)
        attributeValueFactory.addClass(DICT_TYPE_URI, _attributeValueClass)

        self.DictAttributeValue = attributeValueFactory(DICT_TYPE_URI)


        #Create and register an Attribute Value derived class to handle any object
        _className = 'Object' + AttributeValue.CLASS_NAME_SUFFIX
        _classVars = {'TYPE': object, 'IDENTIFIER': OBJECT_TYPE_URI}
        _attributeValueClass = type(_className, (AttributeValue, ), _classVars)
        AttributeValue.register(_attributeValueClass)
        attributeValueFactory.addClass(OBJECT_TYPE_URI, _attributeValueClass)

        self.ObjectAttributeValue = attributeValueFactory(OBJECT_TYPE_URI)

        #Create and add new function for evaluating functions that take the message as a dict
        from pyon.core.governance.policy.evaluate import EvaluateCode, EvaluateFunction
        functionMap['urn:oasis:names:tc:xacml:1.0:function:evaluate-code'] = EvaluateCode
        functionMap['urn:oasis:names:tc:xacml:1.0:function:evaluate-function'] = EvaluateFunction


    def _get_default_policy_template(self):

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

    def _get_resource_policy_template(self):

        #TODO - Put in resource registry as object and load in preload

        policy_template = '''<?xml version="1.0" encoding="UTF-8"?>
        <Policy xmlns="urn:oasis:names:tc:xacml:2.0:policy:schema:os"
            xmlns:xacml-context="urn:oasis:names:tc:xacml:2.0:context:schema:os"
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="urn:oasis:names:tc:xacml:2.0:policy:schema:os http://docs.oasis-open.org/xacml/access_control-xacml-2.0-policy-schema-os.xsd"
            xmlns:xf="http://www.w3.org/TR/2002/WD-xquery-operators-20020816/#"
            xmlns:md="http:www.med.example.com/schemas/record.xsd"
            PolicyId="%s"
            RuleCombiningAlgId="urn:oasis:names:tc:xacml:1.0:rule-combining-algorithm:first-applicable">
            <PolicyDefaults>
                <XPathVersion>http://www.w3.org/TR/1999/Rec-xpath-19991116</XPathVersion>
            </PolicyDefaults>

            %s
        </Policy>'''

        return policy_template





    def create_policy_from_rules(self, policy_identifier, rules):
        policy = self._get_default_policy_template()
        policy_rules = policy % (policy_identifier, rules)
        return policy_rules

    def create_resource_policy_from_rules(self, policy_identifier, rules):
        policy = self._get_resource_policy_template()
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

    def list_resource_policies(self):
        return self.resource_policy_decision_point.keys()

    def list_service_policies(self):
        return self.service_policy_decision_point.keys()

    def load_common_service_policy_rules(self, rules_text):

        self.common_service_rules = rules_text
        input_source = StringIO(self.create_policy_from_rules(COMMON_SERVICE_POLICY_RULES, rules_text))
        self.load_common_service_pdp = PDP.fromPolicySource(input_source, ReaderFactory)

    def load_service_policy_rules(self, service_name, rules_text):

        if not rules_text and not self.service_policy_decision_point.has_key(service_name):
            return

        log.debug("Loading policies for service: %s" % service_name)

        self.clear_service_policy(service_name)
        service_rule_set = self.common_service_rules + rules_text

        #Simply create a new PDP object for the service
        input_source = StringIO(self.create_policy_from_rules(service_name, service_rule_set))
        self.service_policy_decision_point[service_name] = PDP.fromPolicySource(input_source, ReaderFactory)

    def load_resource_policy_rules(self, resource_key, rules_text):

        if not rules_text and not self.resource_policy_decision_point.has_key(resource_key):
            return

        log.debug("Loading policies for resource: %s" % resource_key)
        #print rules_text

        self.clear_resource_policy(resource_key)

        #Simply create a new PDP object for the service
        input_source = StringIO(self.create_resource_policy_from_rules(resource_key, rules_text))
        self.resource_policy_decision_point[resource_key] = PDP.fromPolicySource(input_source, ReaderFactory)

    #Remove any policy indexed by the resource_key
    def clear_resource_policy(self, resource_key):
        if self.resource_policy_decision_point.has_key(resource_key):
            del self.resource_policy_decision_point[resource_key]

    #Remove any policy indexed by the service_name
    def clear_service_policy(self, service_name):
        if self.service_policy_decision_point.has_key(service_name):
            del self.service_policy_decision_point[service_name]

    #Remove all policies
    def clear_policy_cache(self):
        self.resource_policy_decision_point.clear()
        self.service_policy_decision_point.clear()
        self.load_common_service_policy_rules('')


    def create_attribute(self, attrib_class, attrib_id, val):
        attribute = Attribute()
        attribute.attributeId = attrib_id
        attribute.dataType = attrib_class.IDENTIFIER
        attribute.attributeValues.append(attrib_class())
        attribute.attributeValues[-1].value = val
        return attribute


    def create_string_attribute(self, attrib_id, val):
        return self.create_attribute(StringAttributeValue, attrib_id, val)

    def create_int_attribute(self, attrib_id, val):
        return self.create_attribute(IntAttributeValue, attrib_id, val)

    def create_double_attribute(self, attrib_id, val):
        return self.create_attribute(DoubleAttributeValue, attrib_id, val)

    def create_boolean_attribute(self, attrib_id, val):
        return self.create_attribute(BooleanAttributeValue, attrib_id, val)

    def create_dict_attribute(self, attrib_id, val):
        return self.create_attribute(self.DictAttributeValue, attrib_id, val)

    def create_object_attribute(self, attrib_id, val):
        return self.create_attribute(self.ObjectAttributeValue, attrib_id, val)


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

        sender, sender_type = invocation.get_message_sender()
        op = invocation.get_header_value('op', 'Unknown')
        ion_actor_id = invocation.get_header_value('ion-actor-id', 'anonymous')
        actor_roles = invocation.get_header_value('ion-actor-roles', {})
        message_format = invocation.get_header_value('format', '')

        #log.debug("Checking XACML Request: receiver_type: %s, sender: %s, receiver:%s, op:%s,  ion_actor_id:%s, ion_actor_roles:%s", receiver_type, sender, receiver, op, ion_actor_id, actor_roles)

        request = Request()
        subject = Subject()
        subject.attributes.append(self.create_string_attribute(SENDER_ID, sender))
        subject.attributes.append(self.create_string_attribute(Identifiers.Subject.SUBJECT_ID, ion_actor_id))

        #Get the Org name associated with the endpoint process
        endpoint_process = invocation.get_arg_value('process', None)
        if endpoint_process is not None and hasattr(endpoint_process,'org_governance_name'):
            org_governance_name = endpoint_process.org_governance_name
        else:
            org_governance_name = self.governance_controller.system_root_org_name

        #If this process is not associated wiht the root Org, then iterate over the roles associated with the user only for
        #the Org that this process is associated with otherwise include all roles and create attributes for each
        if org_governance_name == self.governance_controller.system_root_org_name:
            #log.debug("Including roles for all Orgs")
            #If the process Org name is the same for the System Root Org, then include all of them to be safe
            for org in actor_roles:
                self.create_org_role_attribute(actor_roles[org],subject)
        else:
            if actor_roles.has_key(org_governance_name):
                log.debug("Org Roles (%s): %s" , org_governance_name, ' '.join(actor_roles[org_governance_name]))
                self.create_org_role_attribute(actor_roles[org_governance_name],subject)

            #Handle the special case for the ION system actor
            if actor_roles.has_key(self.governance_controller.system_root_org_name):
                if ION_MANAGER in actor_roles[self.governance_controller.system_root_org_name]:
                    log.debug("Including ION_MANAGER role")
                    self.create_org_role_attribute([ION_MANAGER],subject)


        request.subjects.append(subject)

        resource = Resource()
        resource.attributes.append(self.create_string_attribute(Identifiers.Resource.RESOURCE_ID, receiver))
        resource.attributes.append(self.create_string_attribute(RECEIVER_TYPE, receiver_type))

        request.resources.append(resource)

        request.action = Action()
        request.action.attributes.append(self.create_string_attribute(Identifiers.Action.ACTION_ID, op))

        #Check to see if there is a OperationVerb decorator specifying a Verb used with policy
        if is_ion_object(message_format):
            try:
                msg_class = message_classes[message_format]
                operation_verb = get_class_decorator_value(msg_class,'OperationVerb')
                if operation_verb is not None:
                    request.action.attributes.append(self.create_string_attribute(ACTION_VERB, operation_verb))

            except NotFound:

                pass

        #Create generic attributes for each of the primitive message parameter types to be available in XACML rules

        parameter_dict = {'message': invocation.message, 'headers': invocation.headers, 'annotations': invocation.message_annotations }
        if endpoint_process is not None:
            parameter_dict['process'] = endpoint_process

        request.action.attributes.append(self.create_dict_attribute(ACTION_PARAMETERS, parameter_dict))

        return request

    def check_agent_request_policies(self, invocation):

        process = invocation.get_arg_value('process')

        if not process:
            raise NotFound('Cannot find process in message')

        decision = self.check_resource_request_policies(invocation, process.resource_id)

        log.debug("Resource policy Decision: %s", decision)

        # todo: check if its OK to treat everything but Deny as Permit (Ex: NotApplicable)
        # Return if agent service policies deny the operation
        if decision == Decision.DENY:
            return decision

        # Else check any policies that might be associated with the resource.
        decision = self._check_service_request_policies(invocation, 'agent')

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
            return Decision.NOT_APPLICABLE

        return self._evaluate_pdp(invocation, pdp, requestCtx)

    def check_resource_request_policies(self, invocation, resource_id):

        if not resource_id:
            raise NotFound('The resource_id is not set')

        requestCtx = self._create_request_from_message(invocation, resource_id, 'resource')

        pdp = self.get_resource_pdp(resource_id)

        if pdp is None:
            return Decision.NOT_APPLICABLE

        return self._evaluate_pdp(invocation, pdp, requestCtx)

    def _evaluate_pdp(self, invocation, pdp, requestCtx):

        try:
            response = pdp.evaluate(requestCtx)
        except Exception, e:
            log.error("Error evaluating policies: %s" % e.message)
            return Decision.NOT_APPLICABLE

        if response is None:
            log.debug('response from PDP contains nothing, so not authorized')
            return Decision.DENY

        if invocation.message_annotations.has_key(GovernanceDispatcher.POLICY__STATUS_REASON_ANNOTATION):
            return Decision.DENY

        for result in response.results:
            if result.decision == Decision.DENY:
                break

        return result.decision
