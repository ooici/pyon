#!/usr/bin/env python


__author__ = 'Stephen P. Henrie'
__license__ = 'Apache 2.0'

import datetime

from pyon.core.bootstrap import IonObject
from pyon.core.exception import  Inconsistent, NotFound, BadRequest
from pyon.ion.resource import RT, PRED
from pyon.util.log import log

now = datetime.datetime.now()


REQUEST_APPROVED = 'Approved'
REQUEST_DENIED = 'Denied'
REQUEST_ACCEPTED = 'Accepted'
REQUEST_REJECTED = 'Rejected'
REQUEST_GRANTED = 'Granted'

class NegotiateRequestFactory(object):

    @classmethod
    def create_enrollment_request(self,org_id, user_id):

        request_object = IonObject(RT.EnrollmentRequest, name='Enroll Request', org_id=org_id, user_id=user_id,
            status="Initialized", description='%s Org Enrollment Request at %s' % (user_id, str(now)))

        return request_object

    @classmethod
    def create_role_request(self,org_id, user_id):

        request_object = IonObject(RT.RoleRequest, name='Role Request', org_id=org_id, user_id=user_id,
            status="Initialized", description='%s Role Request at %s' % (user_id, str(now)))

        return request_object


    @classmethod
    def create_acquire_resource(self,org_id, user_id, resource_id):

        request_object = IonObject(RT.ResourceRequest, name='Acquire Resource Request', org_id=org_id, user_id=user_id, resource_id=resource_id,
            status="Initialized", description='%s Acquire Resource Request at %s' % (user_id, str(now)))

        return request_object


class NegotiateRequest(object):

    def __init__(self,serv_prov):
        self.service_provider = serv_prov

    def open_request(self, request_object):

        org_id = request_object.org_id
        user_id = request_object.user_id

        neg_obj = self._get_negotiation_definition(request_object)

        #First make sure the preconditions for the object are met
        if neg_obj is not None:
            for pc in neg_obj.pre_condition:
                pre_condition_met = eval("self."+pc)

        #if no exceptions were thrown evaluating pre-conditions then return request object
        request_object.status = "Open"
        request_object = self._create_request(org_id, user_id, request_object)

        #Publish request opened event
        self._publish_status_event(request_object)


        return request_object._id


    def approve_request(self, request_object):
        request_object.status = REQUEST_APPROVED
        request_object.status_description = "The request was approved"
        self.service_provider.clients.resource_registry.update(request_object)

        #Publish request approved notification
        self._publish_status_event(request_object)

        return request_object

    def deny_request(self, request_object, reason):
        request_object.status = REQUEST_DENIED
        if not reason:
            request_object.status_description = "The request was denied"
        else:
            request_object.status_description = reason

        self.service_provider.clients.resource_registry.update(request_object)

        #Publish request denied notification
        self._publish_status_event(request_object)

        return request_object

    def accept_request(self, request_object):
        request_object.status = REQUEST_ACCEPTED
        request_object.status_description = "The request was accepted"
        self.service_provider.clients.resource_registry.update(request_object)

        #Publish request accepted notification
        self._publish_status_event(request_object)

        return request_object

    def reject_request(self, request_object, reason):
        request_object.status = REQUEST_REJECTED
        if not reason:
            request_object.status_description = "The request was denied"
        else:
            request_object.status_description = reason

        self.service_provider.clients.resource_registry.update(request_object)

        #Publish request rejected notification
        self._publish_status_event(request_object)

        return request_object


    def _publish_status_event(self, request_object):
        #Sent request opened event

        event_type = self._get_request_type(request_object)+ 'StatusEvent'

        #This will be used for the orgin
        org_id = request_object.org_id

        event_data = dict()
        event_data['origin_type'] = 'Org'
        event_data['description'] = request_object.description
        event_data['sub_type'] = request_object.status
        event_data['request_id'] = request_object._id
        event_data['user_id'] = request_object.user_id

        if request_object._schema.has_key('resource_id'):
            event_data['resource_id'] = request_object.resource_id

        if request_object._schema.has_key('role_name'):
            event_data['role_name'] = request_object.role_name

        self.service_provider.event_pub.publish_event(event_type=event_type,
            origin=org_id, **event_data)

    def _get_request_type(self,request_object):
        return request_object.__class__.__name__

    def _get_negotiation_definition(self, request_object):

        #Get the name of the associated negotiation type
        negotiation_type = self._get_request_type(request_object)

        neg_def, _ = self.service_provider.clients.resource_registry.find_resources(restype=RT.NegotiationDefinition, name=negotiation_type)
        if len(neg_def) > 0:
            return neg_def[0]

        return None

    def _create_request(self, org_id, user_id, request_object):
        req_id, _ = self.service_provider.clients.resource_registry.create(request_object)
        req_obj = self.service_provider.clients.resource_registry.read(req_id)
        self.service_provider.clients.resource_registry.create_association(org_id, PRED.hasRequest, req_obj)
        self.service_provider.clients.resource_registry.create_association(user_id, PRED.hasRequest, req_obj)
        return req_obj

    def _delete_request(self, org_id, user_id, request_object):

        aid = self.service_provider.clients.resource_registry.find_associations(user_id, PRED.hasRequest, request_object)
        self.service_provider.clients.resource_registry.delete_association(aid[0])
        aid = self.service_provider.clients.resource_registry.find_associations(org_id, PRED.hasRequest, request_object)
        self.service_provider.clients.resource_registry.delete_association(aid[0])
        try:
            self.service_provider.clients.resource_registry.delete(request_object._id)
        except Exception, e:
            log.debug("Error: " + e.message)


    def execute_accept_action(self, request_object):

        org_id = request_object.org_id
        user_id = request_object.user_id

        if request_object._schema.has_key('resource_id'):
            resource_id = request_object.resource_id

        if request_object._schema.has_key('role_name'):
            role_name = request_object.role_name


        neg_obj = self._get_negotiation_definition(request_object)
        action_result = ''

        #First make sure the preconditions for the object are met
        if neg_obj is not None and neg_obj._schema.has_key('accept_action'):
            action = neg_obj.accept_action
            action_result = eval("self."+action)

        #Update Request Object
        request_object.status = REQUEST_GRANTED
        request_object.status_description = "The request was granted"
        self.service_provider.clients.resource_registry.update(request_object)

        #Publish request granted notification
        self._publish_status_event(request_object)

        return action_result

    #Negotiation helper functions are below

    def is_registered(self,user_id):
        try:
            user = self.service_provider.clients.resource_registry.read(user_id)
            return True
        except:
            raise BadRequest("The user id %s is not registered with the ION system" % (user_id))


    def is_enrolled(self,org_id,user_id):
        try:
            ret = self.service_provider.is_enrolled(org_id, user_id)
            return ret
        except:
            raise BadRequest("The user id %s is already enrolled in the specified Org %s" % (user_id, org_id))


    def enroll_req_exists(self,org_id,user_id):

        request_list,_ = self.service_provider.clients.resource_registry.find_objects(user_id, PRED.hasRequest, org_id)

        if len(request_list) > 0 :
            raise BadRequest("The user id %s already has an outstanding request to enroll with Org %s" % (user_id, org_id))

        return False

    def enroll_member(self, org_id,user_id):
        ret = self.service_provider.enroll_member(org_id, user_id)
        return ret

    def grant_role(self, org_id,user_id, role_name):
        ret = self.service_provider.grant_role(org_id, user_id, role_name)
        return ret

    def acquire_resource(self, org_id,user_id, resource_id):
        ret = self.service_provider.acquire_resource(org_id, user_id, resource_id)
        return ret