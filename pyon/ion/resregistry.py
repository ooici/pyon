#!/usr/bin/env python

"""Resource Registry implementation"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'


import base64

from pyon.core import bootstrap
from pyon.core.exception import BadRequest, NotFound, Inconsistent
from pyon.core.object import IonObjectBase
from pyon.datastore.datastore import DataStore
from pyon.ion.resource import LCS, PRED, AT, RT, get_restype_lcsm, is_resource
from pyon.util.config import CFG
from pyon.util.containers import get_ion_ts
from pyon.util.log import log

from interface.objects import Attachment, AttachmentType, ServiceDefinition


class ResourceRegistry(object):
    """
    Class that uses a data store to provide a resource registry.
    """

    def __init__(self, datastore_manager=None):

        # Get an instance of datastore configured as resource registry.
        # May be persistent or mock, forced clean, with indexes
        datastore_manager = datastore_manager or bootstrap.container_instance.datastore_manager
        self.rr_store = datastore_manager.get_datastore("resources", DataStore.DS_PROFILE.RESOURCES)

        self._init()

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.rr_store.close()

    def _init(self):
        res_list,_ = self.find_resources(RT.ServiceDefinition, id_only=True)
        auto_bootstrap = CFG.get_safe("system.auto_bootstrap", False)
        if not res_list and auto_bootstrap:
            self._register_service_definitions()

    def _register_service_definitions(self):
        from pyon.core.bootstrap import service_registry
        svc_list = []
        for svcname, svc in service_registry.services.iteritems():
            svc_def = ServiceDefinition(name=svcname, definition="")
            svc_list.append(svc_def)
        self._create_mult(svc_list)
        log.info("Created %d ServiceDefinition resources" % len(svc_list))

    def create(self, object=None, actor_id=None):
        if object is None:
            raise BadRequest("Object not present")
        if not isinstance(object, IonObjectBase):
            raise BadRequest("Object is not an IonObject")
        if not is_resource(object):
            raise BadRequest("Object is not a Resource")

        lcsm = get_restype_lcsm(object._get_type())
        object.lcstate = lcsm.initial_state if lcsm else "DEPLOYED_AVAILABLE"
        cur_time = get_ion_ts()
        object.ts_created = cur_time
        object.ts_updated = cur_time
        res = self.rr_store.create(object)
        res_id, rev = res

        if actor_id and actor_id != 'anonymous':
            log.debug("Associate resource_id=%s with owner=%s" % (res_id, actor_id))
            self.rr_store.create_association(res_id, PRED.hasOwner, actor_id)

        return res

    def _create_mult(self, res_list):
        cur_time = get_ion_ts()
        for resobj in res_list:
            lcsm = get_restype_lcsm(resobj._get_type())
            resobj.lcstate = lcsm.initial_state if lcsm else "DEPLOYED_AVAILABLE"
            resobj.ts_created = cur_time
            resobj.ts_updated = cur_time

        res = self.rr_store.create_mult(res_list)
        return [(rid,rrv) for success,rid,rrv in res]

    def read(self, object_id='', rev_id=''):
        if not object_id:
            raise BadRequest("The object_id parameter is an empty string")

        return self.rr_store.read(object_id, rev_id)

    def update(self, object=None):
        if object is None:
            raise BadRequest("Object not present")
        if not hasattr(object, "_id") or not hasattr(object, "_rev"):
            raise BadRequest("Object does not have required '_id' or '_rev' attribute")
            # Do an check whether LCS has been modified
        res_obj = self.read(object._id)

        object.ts_updated = get_ion_ts()
        if res_obj.lcstate != object.lcstate:
            log.warn("Cannot modify life cycle state in update current=%s given=%s. DO NOT REUSE THE SAME OBJECT IN CREATE THEN UPDATE" % (
                res_obj.lcstate, object.lcstate))
            object.lcstate = res_obj.lcstate

        return self.rr_store.update(object)

    def delete(self, object_id=''):
        res_obj = self.read(object_id)
        if not res_obj:
            raise NotFound("Resource %s does not exist" % object_id)

        # Delete all owner users.
        owners,_ = self.rr_store.find_objects(object_id, PRED.hasOwner, RT.UserIdentity, id_only=True)
        for oid in owners:
            self.rr_store.delete_association(object_id, PRED.hasOwner, oid)

        res = self.rr_store.delete(res_obj)
        return res

    def execute_lifecycle_transition(self, resource_id='', transition_event=''):
        res_obj = self.read(resource_id)

        restype = res_obj._get_type()
        restype_workflow = get_restype_lcsm(restype)
        if not restype_workflow:
            raise BadRequest("Resource id=%s type=%s has no lifecycle" % (resource_id, restype))

        new_state = restype_workflow.get_successor(res_obj.lcstate, transition_event)
        if not new_state:
            raise BadRequest("Resource id=%s, type=%s, lcstate=%s has no transition for event %s" % (
                resource_id, restype, res_obj.lcstate, transition_event))

        res_obj.lcstate = new_state
        res_obj.ts_updated = get_ion_ts()
        updres = self.rr_store.update(res_obj)
        return new_state

    def set_lifecycle_state(self, resource_id='', target_lcstate=''):
        if not target_lcstate or target_lcstate not in LCS:
            raise BadRequest("Unknown life-cycle state %s" % target_lcstate)

        res_obj = self.read(resource_id)
        restype = res_obj._get_type()
        restype_workflow = get_restype_lcsm(restype)
        if not restype_workflow:
            raise BadRequest("Resource id=%s type=%s has no lifecycle" % (resource_id, restype))

        # Check that target state is allowed
        if not target_lcstate in restype_workflow.get_successors(res_obj.lcstate).values():
            raise BadRequest("Target state %s not reachable for resource in state %s" % (target_lcstate, res_obj.lcstate))

        res_obj.lcstate = target_lcstate
        res_obj.ts_updated = get_ion_ts()
        updres = self.rr_store.update(res_obj)

    def create_attachment(self, resource_id='', attachment=None):
        if attachment is None:
            raise BadRequest("Object not present")
        if not isinstance(attachment, Attachment):
            raise BadRequest("Object is not an Attachment")

        attachment.object_id = resource_id if resource_id else ""

        if attachment.attachment_type == AttachmentType.BLOB:
            if type(attachment.content) is not str:
                raise BadRequest("Attachment content must be str")
            attachment.content = base64.encodestring(attachment.content)
        elif attachment.attachment_type == AttachmentType.ASCII:
            if type(attachment.content) is not str:
                raise BadRequest("Attachment content must be str")
        elif attachment.attachment_type == AttachmentType.OBJECT:
            pass
        else:
            raise BadRequest("Unknown attachment-type: %s" % attachment.attachment_type)

        att_id,_ = self.create(attachment)

        if resource_id:
            self.rr_store.create_association(resource_id, PRED.hasAttachment, att_id)

        return att_id

    def read_attachment(self, attachment_id=''):
        attachment = self.read(attachment_id)
        if not isinstance(attachment, Attachment):
            raise Inconsistent("Object in datastore must be Attachment, not %s" % type(attachment))

        if attachment.attachment_type == AttachmentType.BLOB:
            if type(attachment.content) is not str:
                raise BadRequest("Attachment content must be str")
            attachment.content = base64.decodestring(attachment.content)

        return attachment

    def delete_attachment(self, attachment_id=''):
        return self.rr_store.delete(attachment_id, del_associations=True)

    def find_attachments(self, resource_id='', limit=0, descending=False, include_content=False, id_only=True):
        key = [resource_id]
        att_res = self.rr_store.find_by_view("attachment", "by_resource", start_key=key, end_key=list(key),
            descending=descending, limit=limit, id_only=id_only)

        if id_only:
            att_ids = [att[0] for att in att_res]
            return att_ids
        else:
            atts = [att[2] for att in att_res]
            if include_content:
                for att in atts:
                    att.content = None
            return atts

    def create_association(self, subject=None, predicate=None, object=None, assoc_type=None):
        return self.rr_store.create_association(subject, predicate, object, assoc_type)

    def delete_association(self, association=''):
        return self.rr_store.delete_association(association)

    def find(self, **kwargs):
        raise NotImplementedError("Do not use find. Use a specific find operation instead.")

    def find_objects(self, subject="", predicate="", object_type="", id_only=False):
        return self.rr_store.find_objects(subject, predicate, object_type, id_only=id_only)

    def find_subjects(self, subject_type="", predicate="", object="", id_only=False):
        return self.rr_store.find_subjects(subject_type, predicate, object, id_only=id_only)

    def find_associations(self, subject="", predicate="", object="", assoc_type=None, id_only=False):
        return self.rr_store.find_associations(subject, predicate, object, assoc_type, id_only=id_only)

    def get_association(self, subject="", predicate="", object="", assoc_type=None, id_only=False):
        if predicate:
            assoc_type = assoc_type or AT.H2H
        assoc = self.rr_store.find_associations(subject, predicate, object, assoc_type, id_only=id_only)
        if not assoc:
            raise NotFound("Association for subject/predicate/object/type %s/%s/%s/%s not found" % (
                str(subject),str(predicate),str(object),str(assoc_type)))
        elif len(assoc) > 1:
            raise Inconsistent("Duplicate associations found for subject/predicate/object/type %s/%s/%s/%s" % (
                str(subject),str(predicate),str(object),str(assoc_type)))
        return assoc[0]

    def find_resources(self, restype="", lcstate="", name="", id_only=False):
        return self.rr_store.find_resources(restype, lcstate, name, id_only=id_only)
