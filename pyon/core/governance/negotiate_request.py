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



class NegotiateRequest(object):

    def __init__(self,svc):
        self.requesting_service = svc

    def open_request(self, request_object):

        org_id = request_object.org_id
        user_id = request_object.user_id


        #First make sure the preconditions for the object are met
        for pc in request_object.pre_condition:
            pre_condition_met = eval("self."+pc)

        #if no exceptions were thrown evaluating pre-conditions then return request object
        request_object.status = "Open"
        req_id = self._create_request(org_id, user_id, request_object)

        #TODO - Send request_accepted notification

        return req_id

    def approve_request(self, request_object):
        request_object.status = REQUEST_APPROVED
        request_object.status_description = "The request was approved"
        self.requesting_service.clients.resource_registry.update(request_object)
        #TODO - Send request_accepted notification

        return request_object

    def deny_request(self, request_object, reason):
        request_object.status = REQUEST_DENIED
        if not reason:
            request_object.status_description = "The request was denied"
        else:
            request_object.status_description = reason

        self.requesting_service.clients.resource_registry.update(request_object)
        #TODO - Send request_accepted notification

        return request_object

    def accept_request(self, request_object):
        request_object.status = REQUEST_ACCEPTED
        request_object.status_description = "The request was accepted"
        self.requesting_service.clients.resource_registry.update(request_object)
        #TODO - Send request_accepted notification

        return request_object

    def reject_request(self, request_object, reason):
        request_object.status = REQUEST_REJECTED
        if not reason:
            request_object.status_description = "The request was denied"
        else:
            request_object.status_description = reason

        self.requesting_service.clients.resource_registry.update(request_object)
        #TODO - Send request_accepted notification

        return request_object


    def _create_request(self, org_id, user_id, request_object):
        req_id, _ = self.requesting_service.clients.resource_registry.create(request_object)
        req_obj = self.requesting_service.clients.resource_registry.read(req_id)
        self.requesting_service.clients.resource_registry.create_association(org_id, PRED.hasRequest, req_obj)
        self.requesting_service.clients.resource_registry.create_association(user_id, PRED.hasRequest, req_obj)
        return req_id

    def _delete_request(self, org_id, user_id, request_object):

        aid = self.requesting_service.clients.resource_registry.find_associations(user_id, PRED.hasRequest, request_object)
        self.requesting_service.clients.resource_registry.delete_association(aid[0])
        aid = self.requesting_service.clients.resource_registry.find_associations(org_id, PRED.hasRequest, request_object)
        self.requesting_service.clients.resource_registry.delete_association(aid[0])
        try:
            self.requesting_service.clients.resource_registry.delete(request_object._id)
        except Exception, e:
            log.debug("Error: " + e.message)


    def execute_accept_action(self, request_object):

        org_id = request_object.org_id
        user_id = request_object.user_id

        if request_object._schema.has_key('resource_id'):
            resource_id = request_object.resource_id

        if request_object._schema.has_key('role_name'):
            role_name = request_object.role_name

        if request_object._schema.has_key('accept_action'):
            action = request_object.accept_action


        action_result = eval("self."+action)

        #TODO - Send request_accepted notification

        return action_result

    #Negotiation helper functions are below

    def is_registered(self,user_id):
        try:
            user = self.requesting_service.clients.resource_registry.read(user_id)
            return True
        except:
            raise BadRequest("The user id %s is not registered with the ION system" % (user_id))


    def is_enrolled(self,org_id,user_id):
        try:
            ret = self.requesting_service.is_enrolled(org_id, user_id)
            return ret
        except:
            raise BadRequest("The user id %s is already enrolled in the specified Org %s" % (user_id, org_id))


    def enroll_req_exists(self,org_id,user_id):

        request_list,_ = self.requesting_service.clients.resource_registry.find_objects(user_id, PRED.hasRequest, org_id)

        if len(request_list) > 0 :
            raise BadRequest("The user id %s already has an outstanding request to enroll with Org %s" % (user_id, org_id))

        return False

    def enroll_member(self, org_id,user_id):
        ret = self.requesting_service.enroll_member(org_id, user_id)
        return ret

    def grant_role(self, org_id,user_id, role_name):
        ret = self.requesting_service.grant_role(org_id, user_id, role_name)
        return ret
