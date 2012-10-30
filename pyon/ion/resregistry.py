#!/usr/bin/env python

"""Resource Registry implementation"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'


import base64

from pyon.core import bootstrap
from pyon.core.exception import BadRequest, NotFound, Inconsistent
from pyon.core.object import IonObjectBase
from pyon.datastore.datastore import DataStore
from pyon.event.event import EventPublisher
from pyon.ion.identifier import create_unique_resource_id
from pyon.ion.resource import LCS, PRED, AT, RT, get_restype_lcsm, is_resource
from pyon.util.containers import get_ion_ts
from pyon.util.log import log

from interface.objects import Attachment, AttachmentType, ResourceModificationType


class ResourceRegistry(object):
    """
    Class that uses a data store to provide a resource registry.
    """
    DEFAULT_ATTACHMENT_NAME = 'resource.attachment'

    def __init__(self, datastore_manager=None):

        # Get an instance of datastore configured as resource registry.
        # May be persistent or mock, forced clean, with indexes
        datastore_manager = datastore_manager or bootstrap.container_instance.datastore_manager
        self.rr_store = datastore_manager.get_datastore("resources", DataStore.DS_PROFILE.RESOURCES)

        self.event_pub = EventPublisher()

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.rr_store.close()

    def create(self, object=None, actor_id=None, object_id=None, attachments=None):
        """
        Accepts object that is to be stored in the data store and tags them with additional data
        (timestamp and such) If actor_id is provided, creates hasOwner association with objects.
        If attachments are provided
        (in dict(att1=dict(data=xyz), att2=dict(data=aaa, content_type='text/plain') form)
        they get attached to the object.
        Returns a tuple containing object and revision identifiers.
        """
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
        if object_id is None:
            new_res_id = create_unique_resource_id()
        else:
            new_res_id = object_id
        res = self.rr_store.create(object, new_res_id, attachments=attachments)
        res_id, rev = res

        if actor_id and actor_id != 'anonymous':
            log.debug("Associate resource_id=%s with owner=%s" % (res_id, actor_id))
            self.rr_store.create_association(res_id, PRED.hasOwner, actor_id)

        self.event_pub.publish_event(event_type="ResourceModifiedEvent",
                                     origin=res_id, origin_type=object._get_type(),
                                     sub_type="CREATE",
                                     mod_type=ResourceModificationType.CREATE)

        return res

    def _create_mult(self, res_list):
        cur_time = get_ion_ts()
        for resobj in res_list:
            lcsm = get_restype_lcsm(resobj._get_type())
            resobj.lcstate = lcsm.initial_state if lcsm else "DEPLOYED_AVAILABLE"
            resobj.ts_created = cur_time
            resobj.ts_updated = cur_time

        id_list = [create_unique_resource_id() for i in xrange(len(res_list))]
        res = self.rr_store.create_mult(res_list, id_list)
        res_list = [(rid, rrv) for success, rid, rrv in res]

        # TODO: Publish events (skipped, because this is inefficent one by one for a large list
#        for rid,rrv in res_list:
#            self.event_pub.publish_event(event_type="ResourceModifiedEvent",
#                origin=res_id, origin_type=object._get_type(),
#                mod_type=ResourceModificationType.CREATE)

        return res_list

    def read(self, object_id='', rev_id=''):
        if not object_id:
            raise BadRequest("The object_id parameter is an empty string")

        return self.rr_store.read(object_id, rev_id)

    def read_mult(self, object_ids=None):
        if not object_ids:
            raise BadRequest("The object_ids parameter is empty")
        return self.rr_store.read_mult(object_ids)

    def update(self, object):
        if object is None:
            raise BadRequest("Object not present")
        if not hasattr(object, "_id") or not hasattr(object, "_rev"):
            raise BadRequest("Object does not have required '_id' or '_rev' attribute")
            # Do an check whether LCS has been modified
        res_obj = self.read(object._id)

        object.ts_updated = get_ion_ts()
        if res_obj.lcstate != object.lcstate:
            log.warn("Cannot modify %s life cycle state in update current=%s given=%s. " +
                     "DO NOT REUSE THE SAME OBJECT IN CREATE THEN UPDATE",
                      type(res_obj).__name__, res_obj.lcstate, object.lcstate)
            object.lcstate = res_obj.lcstate

        self.event_pub.publish_event(event_type="ResourceModifiedEvent",
                                     origin=object._id, origin_type=object._get_type(),
                                     sub_type="UPDATE",
                                     mod_type=ResourceModificationType.UPDATE)

        return self.rr_store.update(object)

    def retire(self, resource_id):
        """
        This is the official "delete" for resource objects: they are set to RETIRED lcstate
        """
        self.set_lifecycle_state(resource_id, LCS.RETIRED)

    def delete(self, object_id='', del_associations=False):
        res_obj = self.read(object_id)
        if not res_obj:
            raise NotFound("Resource %s does not exist" % object_id)

        if not del_associations:
            self._delete_owners(object_id)

        res_obj.lcstate = LCS.RETIRED
        self.rr_store.update(res_obj)
        res = self.rr_store.delete(object_id, del_associations=del_associations)

        self.event_pub.publish_event(event_type="ResourceModifiedEvent",
                                     origin=res_obj._id, origin_type=res_obj._get_type(),
                                     sub_type="DELETE",
                                     mod_type=ResourceModificationType.DELETE)

        return res

    def _delete_owners(self, resource_id):
        # Delete all owner users.
        owners, assocs = self.rr_store.find_objects(resource_id, PRED.hasOwner, RT.ActorIdentity, id_only=True)
        for aid in assocs:
            self.rr_store.delete_association(aid)

    def execute_lifecycle_transition(self, resource_id='', transition_event=''):
        res_obj = self.read(resource_id)

        restype = res_obj._get_type()
        restype_workflow = get_restype_lcsm(restype)
        if not restype_workflow:
            raise BadRequest("Resource id=%s type=%s has no lifecycle" % (resource_id, restype))

        old_state = res_obj.lcstate
        new_state = restype_workflow.get_successor(old_state, transition_event)
        if not new_state:
            raise BadRequest("Resource id=%s, type=%s, lcstate=%s has no transition for event %s" % (
                resource_id, restype, res_obj.lcstate, transition_event))

        res_obj.lcstate = new_state
        res_obj.ts_updated = get_ion_ts()
        self.rr_store.update(res_obj)

        self.event_pub.publish_event(event_type="ResourceLifecycleEvent",
                                     origin=res_obj._id, origin_type=res_obj._get_type(),
                                     sub_type=new_state,
                                     old_state=old_state, new_state=new_state, transition_event=transition_event)

        return new_state

    def set_lifecycle_state(self, resource_id='', target_lcstate=''):
        if not target_lcstate or target_lcstate not in LCS:
            raise BadRequest("Unknown life-cycle state %s" % target_lcstate)

        res_obj = self.read(resource_id)
        old_state = res_obj.lcstate
        if target_lcstate != LCS.RETIRED:
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

        self.event_pub.publish_event(event_type="ResourceLifecycleEvent",
                                     origin=res_obj._id, origin_type=res_obj._get_type(),
                                     sub_type=target_lcstate,
                                     old_state=old_state, new_state=target_lcstate)

    def create_attachment(self, resource_id='', attachment=None):
        """
        Persists the given attachment and associates it with the given resource.
        Returns an identifier for the attachment from the data store.
        """

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
            attachment.content = base64.encodestring(attachment.content)
        elif attachment.attachment_type == AttachmentType.OBJECT:
            pass
        else:
            raise BadRequest("Unknown attachment-type: %s" % attachment.attachment_type)

        content = dict(data=attachment.content, content_type=attachment.content_type)
        attachment.content = self.DEFAULT_ATTACHMENT_NAME

        att_id, _ = self.create(attachment, attachments={self.DEFAULT_ATTACHMENT_NAME: content})
        # for multiple attachments use the below sample
        # attachments = dict(att1=dict(data=xyz), att2=dict(data=aaa, content_type='text/plain')

        if resource_id:
            self.rr_store.create_association(resource_id, PRED.hasAttachment, att_id)

        return att_id

    def read_attachment(self, attachment_id='', include_content=False):
        """
        Returns the metadata of an attachment. Unless indicated otherwise the content returned
        is only a name to the actual attachment content.
        """
        attachment = self.read(attachment_id)
        if not isinstance(attachment, Attachment):
            raise Inconsistent("Object in datastore must be Attachment, not %s" % type(attachment))

        if include_content:
            attachment.content = self.rr_store.read_attachment(attachment_id,
                                                               attachment_name=attachment.content)
            if attachment.attachment_type == AttachmentType.BLOB:
                if type(attachment.content) is not str:
                    raise BadRequest("Attachment content must be str")

        return attachment

    def delete_attachment(self, attachment_id=''):
        return self.rr_store.delete(attachment_id, del_associations=True)

    def find_attachments(self, resource_id='', keyword=None,
                         limit=0, descending=False, include_content=False, id_only=True):
        key = [resource_id]
        att_res = self.rr_store.find_by_view("attachment", "by_resource", start_key=key,
                                             end_key=list(key), descending=descending, limit=limit,
                                             id_only=True)

        att_ids = [att[0] for att in att_res if not keyword or keyword in att[1][2]]
        if id_only:
            return att_ids
        else:
            atts = self.rr_store.read_mult(att_ids)
            if include_content:
                for att in atts:
                    att.content = self.rr_store.read_attachment(doc=att._id,
                                                                attachment_name=att.content)
            return atts

    def create_association(self, subject=None, predicate=None, object=None, assoc_type=None):
        return self.rr_store.create_association(subject, predicate, object, assoc_type)

    def delete_association(self, association=''):
        return self.rr_store.delete_association(association)

    def find(self, **kwargs):
        raise NotImplementedError("Do not use find. Use a specific find operation instead.")

    def read_object(self, subject="", predicate="", object_type="", assoc="", id_only=False):
        if assoc:
            if type(assoc) is str:
                assoc = self.read(assoc)
            return assoc.o if id_only else self.read(assoc.o)
        else:
            obj_list, assoc_list = self.find_objects(subject=subject, predicate=predicate, object_type=object_type, id_only=True)
            if not obj_list:
                raise NotFound("No object found for subject=%s, predicate=%s, object_type=%s" % (subject, predicate, object_type))
            elif len(obj_list) > 1:
                raise Inconsistent("More than one object found for subject=%s, predicate=%s, object_type=%s: count=%s" % (
                    subject, predicate, object_type, len(obj_list)))
            return obj_list[0] if id_only else self.read(obj_list[0])

    def read_subject(self, subject_type="", predicate="", object="", assoc="", id_only=False):
        if assoc:
            if type(assoc) is str:
                assoc = self.read(assoc)
            return assoc.s if id_only else self.read(assoc.s)
        else:
            sub_list, assoc_list = self.find_subjects(subject_type=subject_type, predicate=predicate, object=object, id_only=True)
            if not sub_list:
                raise NotFound("No subject found for subject_type=%s, predicate=%s, object=%s" % (subject_type, predicate, object))
            elif len(sub_list) > 1:
                raise Inconsistent("More than one subject found for subject_type=%s, predicate=%s, object=%s: count=%s" % (
                    subject_type, predicate, object, len(sub_list)))
            return sub_list[0] if id_only else self.read(sub_list[0])

    def find_objects(self, subject="", predicate="", object_type="", id_only=False):
        return self.rr_store.find_objects(subject, predicate, object_type, id_only=id_only)

    def find_subjects(self, subject_type="", predicate="", object="", id_only=False):
        return self.rr_store.find_subjects(subject_type, predicate, object, id_only=id_only)

    def find_associations(self, subject="", predicate="", object="", assoc_type=None, id_only=False):
        return self.rr_store.find_associations(subject, predicate, object, assoc_type, id_only=id_only)

    def find_associations_mult(self, subjects=[], id_only=False):
        return self.rr_store.find_associations_mult(subjects=subjects, id_only=id_only)

    def get_association(self, subject="", predicate="", object="", assoc_type=None, id_only=False):
        if predicate:
            assoc_type = assoc_type or AT.H2H
        assoc = self.rr_store.find_associations(subject, predicate, object, assoc_type, id_only=id_only)
        if not assoc:
            raise NotFound("Association for subject/predicate/object/type %s/%s/%s/%s not found" % (
                str(subject), str(predicate), str(object), str(assoc_type)))
        elif len(assoc) > 1:
            raise Inconsistent("Duplicate associations found for subject/predicate/object/type %s/%s/%s/%s" % (
                str(subject), str(predicate), str(object), str(assoc_type)))
        return assoc[0]

    def find_resources(self, restype="", lcstate="", name="", id_only=False):
        return self.rr_store.find_resources(restype, lcstate, name, id_only=id_only)

    def find_resources_ext(self, restype="", lcstate="", name="",
                           keyword=None, nested_type=None,
                           attr_name=None, attr_value=None, alt_id="", alt_id_ns="",
                           limit=None, skip=None, descending=None, id_only=True):
        return self.rr_store.find_resources_ext(restype=restype, lcstate=lcstate, name=name,
            keyword=keyword, nested_type=nested_type,
            attr_name=attr_name, attr_value=attr_value, alt_id=alt_id, alt_id_ns=alt_id_ns,
            limit=limit, skip=skip, descending=descending,
            id_only=id_only)
