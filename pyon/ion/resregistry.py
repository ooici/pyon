#!/usr/bin/env python

"""Resource Registry implementation"""

__author__ = 'Michael Meisinger'

from pyon.core import bootstrap
from pyon.core.bootstrap import IonObject, CFG
from pyon.core.exception import BadRequest, NotFound, Inconsistent
from pyon.core.object import IonObjectBase
from pyon.core.registry import getextends
from pyon.datastore.datastore import DataStore
from pyon.datastore.datastore_query import DatastoreQueryBuilder, DQ
from pyon.ion.event import EventPublisher
from pyon.ion.identifier import create_unique_resource_id, create_unique_association_id
from pyon.ion.resource import LCS, LCE, PRED, RT, AS, OT, get_restype_lcsm, is_resource, ExtendedResourceContainer, \
    lcstate, lcsplit, Predicates, create_access_args
from pyon.ion.process import get_ion_actor_id
from pyon.util.containers import get_ion_ts
from pyon.util.log import log

from interface.objects import Attachment, AttachmentType, ResourceModificationType


class ResourceRegistry(object):
    """
    Class that uses a datastore to provide a resource registry.
    The resource registry adds knowledge of resource objects and associations.
    Resources have lifecycle state.
    Add special treatment of Attachment resources
    """
    DEFAULT_ATTACHMENT_NAME = 'resource.attachment'

    def __init__(self, datastore_manager=None, container=None):
        self.container = container or bootstrap.container_instance

        # Get an instance of datastore configured as resource registry.
        datastore_manager = datastore_manager or self.container.datastore_manager
        self.rr_store = datastore_manager.get_datastore(DataStore.DS_RESOURCES, DataStore.DS_PROFILE.RESOURCES)
        self.name = 'container_resource_registry'
        self.id = 'container_resource_registry'

        self.event_pub = EventPublisher()

        self.superuser_actors = None

    def start(self):
        pass

    def stop(self):
        self.close()

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.rr_store.close()

    # -------------------------------------------------------------------------
    # Resource object manipulation

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
        if "_id" in object:
            raise BadRequest("Object must not contain _id")
        if "_rev" in object:
            raise BadRequest("Object must not contain _rev")


        lcsm = get_restype_lcsm(object.type_)
        object.lcstate = lcsm.initial_state if lcsm else LCS.DEPLOYED
        object.availability = lcsm.initial_availability if lcsm else AS.AVAILABLE
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
            log.debug("Associate resource_id=%s with owner=%s", res_id, actor_id)
            self.create_association(res_id, PRED.hasOwner, actor_id)

        if self.container.has_capability(self.container.CCAP.EVENT_PUBLISHER):
            self.event_pub.publish_event(event_type="ResourceModifiedEvent",
                                     origin=res_id, origin_type=object.type_,
                                     sub_type="CREATE",
                                     mod_type=ResourceModificationType.CREATE)

        return res

    def create_mult(self, res_list, actor_id=None):
        """Creates a list of resources from objects. Objects may have _id in it to predetermine their ID.
        Returns a list of 2-tuples (resource_id, rev)"""
        cur_time = get_ion_ts()
        id_list = []
        for resobj in res_list:
            lcsm = get_restype_lcsm(resobj.type_)
            resobj.lcstate = lcsm.initial_state if lcsm else LCS.DEPLOYED
            resobj.availability = lcsm.initial_availability if lcsm else AS.AVAILABLE
            resobj.ts_created = cur_time
            resobj.ts_updated = cur_time
            id_list.append(resobj._id if "_id" in resobj else create_unique_resource_id())

        res = self.rr_store.create_mult(res_list, id_list, allow_ids=True)
        rid_list = [(rid, rrv) for success, rid, rrv in res]

        # Associations with owners
        if actor_id and actor_id != 'anonymous':
            assoc_list = []
            for resobj, (rid, rrv) in zip(res_list, rid_list):
                resobj._id = rid
                assoc_list.append((resobj, PRED.hasOwner, actor_id))
            self.create_association_mult(assoc_list)

        # Publish events
        for resobj, (rid, rrv) in zip(res_list, rid_list):
            self.event_pub.publish_event(event_type="ResourceModifiedEvent",
                origin=rid, origin_type=resobj.type_,
                mod_type=ResourceModificationType.CREATE)

        return rid_list

    def read(self, object_id='', rev_id=''):
        if not object_id:
            raise BadRequest("The object_id parameter is an empty string")

        return self.rr_store.read(object_id, rev_id)

    def read_mult(self, object_ids=None, strict=True):
        """
        @param object_ids  a list of resource ids (can be empty)
        @param strict  a bool - if True (default), raise a NotFound in case one of the resources was not found
        Returns resource objects for given list of resource ids in the same order. If a resource object was not
        found, contains None (unless strict==True) in which case NotFound will be raised.
        """
        if object_ids is None:
            raise BadRequest("The object_ids parameter is empty")
        return self.rr_store.read_mult(object_ids, strict=strict)

    def update(self, object):
        if object is None:
            raise BadRequest("Object not present")
        if not hasattr(object, "_id") or not hasattr(object, "_rev"):
            raise BadRequest("Object does not have required '_id' or '_rev' attribute")
            # Do an check whether LCS has been modified
        res_obj = self.read(object._id)

        object.ts_updated = get_ion_ts()
        if res_obj.lcstate != object.lcstate or res_obj.availability != object.availability:
            log.warn("Cannot modify %s life cycle state or availability in update current=%s/%s given=%s/%s. " +
                     "DO NOT REUSE THE SAME OBJECT IN CREATE THEN UPDATE",
                      type(res_obj).__name__, res_obj.lcstate, res_obj.availability, object.lcstate, object.availability)
            object.lcstate = res_obj.lcstate
            object.availability = res_obj.availability

        self.event_pub.publish_event(event_type="ResourceModifiedEvent",
                                     origin=object._id, origin_type=object.type_,
                                     sub_type="UPDATE",
                                     mod_type=ResourceModificationType.UPDATE)

        return self.rr_store.update(object)

    def delete(self, object_id='', del_associations=False):
        res_obj = self.read(object_id)
        if not res_obj:
            raise NotFound("Resource %s does not exist" % object_id)

        if not del_associations:
            self._delete_owners(object_id)

        if del_associations:
            assoc_ids = self.find_associations(anyside=object_id, id_only=True)
            self.rr_store.delete_doc_mult(assoc_ids, object_type="Association")
            #log.debug("Deleted %s associations for resource %s", len(assoc_ids), object_id)

        elif self._is_in_association(object_id):
            log.warn("Deleting object %s that still has associations" % object_id)

        res = self.rr_store.delete(object_id)

        if self.container.has_capability(self.container.CCAP.EVENT_PUBLISHER):
            self.event_pub.publish_event(event_type="ResourceModifiedEvent",
                                     origin=res_obj._id, origin_type=res_obj.type_,
                                     sub_type="DELETE",
                                     mod_type=ResourceModificationType.DELETE)

        return res

    def _delete_owners(self, resource_id):
        # Delete all owner users.
        owners, assocs = self.rr_store.find_objects(resource_id, PRED.hasOwner, RT.ActorIdentity, id_only=True)
        for aid in assocs:
            self.delete_association(aid)

    def retire(self, resource_id):
        return self.execute_lifecycle_transition(resource_id, LCE.RETIRE)

    def lcs_delete(self, resource_id):
        """
        This is the official "delete" for resource objects: they are set to DELETED lcstate.
        All associations are set to deleted as well.
        """
        res_obj = self.read(resource_id)
        old_state = res_obj.lcstate
        if old_state == LCS.DELETED:
            raise BadRequest("Resource id=%s already DELETED" % (resource_id))

        res_obj.lcstate = LCS.DELETED
        res_obj.ts_updated = get_ion_ts()

        updres = self.rr_store.update(res_obj)
        log.debug("retire(res_id=%s). Change %s_%s to %s_%s", resource_id,
                  old_state, res_obj.availability, res_obj.lcstate, res_obj.availability)

        assocs = self.find_associations(anyside=resource_id, id_only=False)
        for assoc in assocs:
            assoc.retired = True  # retired means soft deleted
        if assocs:
            self.rr_store.update_mult(assocs)
            log.debug("lcs_delete(res_id=%s). Retired %s associations", resource_id, len(assocs))

        if self.container.has_capability(self.container.CCAP.EVENT_PUBLISHER):
            self.event_pub.publish_event(event_type="ResourceLifecycleEvent",
                                     origin=res_obj._id, origin_type=res_obj.type_,
                                     sub_type="%s.%s" % (res_obj.lcstate, res_obj.availability),
                                     lcstate=res_obj.lcstate, availability=res_obj.availability,
                                     lcstate_before=old_state, availability_before=res_obj.availability)


    def execute_lifecycle_transition(self, resource_id='', transition_event=''):
        if transition_event == LCE.DELETE:
            return self.lcs_delete(resource_id)

        res_obj = self.read(resource_id)
        old_lcstate = res_obj.lcstate
        old_availability = res_obj.availability

        if transition_event == LCE.RETIRE:
            if res_obj.lcstate == LCS.RETIRED or res_obj.lcstate == LCS.DELETED:
                raise BadRequest("Resource id=%s, type=%s, lcstate=%s, availability=%s has no transition for event %s" % (
                    resource_id, res_obj.type_, old_lcstate, old_availability, transition_event))
            res_obj.lcstate = LCS.RETIRED
        else:
            restype = res_obj.type_
            restype_workflow = get_restype_lcsm(restype)
            if not restype_workflow:
                raise BadRequest("Resource id=%s type=%s has no lifecycle" % (resource_id, restype))

            new_lcstate = restype_workflow.get_lcstate_successor(old_lcstate, transition_event)
            new_availability = restype_workflow.get_availability_successor(old_availability, transition_event)
            if not new_lcstate and not new_availability:
                raise BadRequest("Resource id=%s, type=%s, lcstate=%s, availability=%s has no transition for event %s" % (
                    resource_id, restype, old_lcstate, old_availability, transition_event))

            if new_lcstate:
                res_obj.lcstate = new_lcstate
            if new_availability:
                res_obj.availability = new_availability

        res_obj.ts_updated = get_ion_ts()
        self.rr_store.update(res_obj)
        log.debug("execute_lifecycle_transition(res_id=%s, event=%s). Change %s_%s to %s_%s", resource_id, transition_event,
                  old_lcstate, old_availability, res_obj.lcstate, res_obj.availability)

        if self.container.has_capability(self.container.CCAP.EVENT_PUBLISHER):
            self.event_pub.publish_event(event_type="ResourceLifecycleEvent",
                                     origin=res_obj._id, origin_type=res_obj.type_,
                                     sub_type="%s.%s" % (res_obj.lcstate, res_obj.availability),
                                     lcstate=res_obj.lcstate, availability=res_obj.availability,
                                     lcstate_before=old_lcstate, availability_before=old_availability,
                                     transition_event=transition_event)

        return "%s_%s" % (res_obj.lcstate, res_obj.availability)

    def set_lifecycle_state(self, resource_id='', target_lcstate=''):
        """Sets the lifecycle state (if possible) to the target state. Supports compound states"""
        if not target_lcstate:
            raise BadRequest("Bad life-cycle state %s" % target_lcstate)
        if target_lcstate.startswith(LCS.DELETED):
            self.lcs_delete(resource_id)
        if target_lcstate.startswith(LCS.RETIRED):
            self.execute_lifecycle_transition(resource_id, LCE.RETIRE)

        res_obj = self.read(resource_id)
        old_lcstate = res_obj.lcstate
        old_availability = res_obj.availability

        restype = res_obj.type_
        restype_workflow = get_restype_lcsm(restype)
        if not restype_workflow:
            raise BadRequest("Resource id=%s type=%s has no lifecycle" % (resource_id, restype))

        if '_' in target_lcstate:    # Support compound
            target_lcs, target_av = lcsplit(target_lcstate)
            if target_lcs not in LCS:
                raise BadRequest("Unknown life-cycle state %s" % target_lcs)
            if target_av and target_av not in AS:
                raise BadRequest("Unknown life-cycle availability %s" % target_av)
        elif target_lcstate in LCS:
            target_lcs, target_av = target_lcstate, res_obj.availability
        elif target_lcstate in AS:
            target_lcs, target_av = res_obj.lcstate, target_lcstate
        else:
            raise BadRequest("Unknown life-cycle state %s" % target_lcstate)

        # Check that target state is allowed
        lcs_successors = restype_workflow.get_lcstate_successors(old_lcstate)
        av_successors = restype_workflow.get_availability_successors(old_availability)
        found_lcs, found_av = target_lcs in lcs_successors.values(), target_av in av_successors.values()
        if not found_lcs and not found_av:
            raise BadRequest("Target state %s not reachable for resource in state %s_%s" % (
                target_lcstate, old_lcstate, old_availability))

        res_obj.lcstate = target_lcs
        res_obj.availability = target_av
        res_obj.ts_updated = get_ion_ts()

        updres = self.rr_store.update(res_obj)
        log.debug("set_lifecycle_state(res_id=%s, target=%s). Change %s_%s to %s_%s", resource_id, target_lcstate,
                  old_lcstate, old_availability, res_obj.lcstate, res_obj.availability)

        if self.container.has_capability(self.container.CCAP.EVENT_PUBLISHER):
            self.event_pub.publish_event(event_type="ResourceLifecycleEvent",
                                     origin=res_obj._id, origin_type=res_obj.type_,
                                     sub_type="%s.%s" % (res_obj.lcstate, res_obj.availability),
                                     lcstate=res_obj.lcstate, availability=res_obj.availability,
                                     lcstate_before=old_lcstate, availability_before=old_availability)


    # -------------------------------------------------------------------------
    # Attachment operations

    def create_attachment(self, resource_id='', attachment=None, actor_id=None):
        """
        Creates an Attachment resource from given argument and associates it with the given resource.
        @retval the resource ID for the attachment resource.
        """
        if attachment is None:
            raise BadRequest("Object not present")
        if not isinstance(attachment, Attachment):
            raise BadRequest("Object is not an Attachment")

        attachment.object_id = resource_id if resource_id else ""
        attachment.attachment_size = -1

        attachment_content = None

        if attachment.attachment_type == AttachmentType.BLOB:
            if type(attachment.content) is not str:
                raise BadRequest("Attachment content must be str")
            attachment.attachment_size = len(attachment.content)
            attachment_content = attachment.content
        elif attachment.attachment_type == AttachmentType.ASCII:
            if type(attachment.content) is not str:
                raise BadRequest("Attachment content must be str")
            attachment.attachment_size = len(attachment.content)
            attachment_content = attachment.content
        elif attachment.attachment_type == AttachmentType.OBJECT:
            raise BadRequest("AttachmentType.OBJECT is not supported currently")
        elif attachment.attachment_type == AttachmentType.REFERENCE:
            if not isinstance(attachment.content, basestring):
                raise BadRequest("Attachment content must be binary string")
            attachment.attachment_size = len(attachment.content)
            attachment_content = attachment.content
        else:
            raise BadRequest("Unknown attachment-type: %s" % attachment.attachment_type)

        attachment.content = ''
        content = dict(data=attachment_content, content_type=attachment.content_type)

        att_id, _ = self.create(attachment, attachments={self.DEFAULT_ATTACHMENT_NAME: content}, actor_id=actor_id)

        if resource_id:
            self.create_association(resource_id, PRED.hasAttachment, att_id)

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
                                                               attachment_name=self.DEFAULT_ATTACHMENT_NAME)
            if attachment.attachment_type == AttachmentType.BLOB:
                if type(attachment.content) is not str:
                    raise BadRequest("Attachment content must be str")

        return attachment

    def delete_attachment(self, attachment_id=''):
        try:
            self.rr_store.delete_attachment(attachment_id, attachment_name=self.DEFAULT_ATTACHMENT_NAME)
        finally:
            return self.delete(attachment_id, del_associations=True)

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
                    att.content = self.rr_store.read_attachment(doc=att._id, attachment_name=self.DEFAULT_ATTACHMENT_NAME)
            return atts


    # -------------------------------------------------------------------------
    # Association operations

    def create_association(self, subject=None, predicate=None, object=None, assoc_type=None):
        """
        Create an association between two IonObjects with a given predicate
        @param assoc_type  DEPRECATED
        """
        if not (subject and predicate and object):
            raise BadRequest("Association must have all elements set")

        if type(subject) is str:
            subject_id = subject
            subject = self.read(subject_id)
            subject_type = subject.type_
        else:
            if "_id" not in subject:
                raise BadRequest("Subject id not available")
            subject_id = subject._id
            subject_type = subject.type_

        if type(object) is str:
            object_id = object
            object = self.read(object_id)
            object_type = object.type_
        else:
            if "_id" not in object:
                raise BadRequest("Object id not available")
            object_id = object._id
            object_type = object.type_

        # Check that subject and object type are permitted by association definition
        try:
            pt = Predicates.get(predicate)
        except AttributeError:
            raise BadRequest("Predicate unknown %s" % predicate)
        if not subject_type in pt['domain']:
            found_st = False
            for domt in pt['domain']:
                if subject_type in getextends(domt):
                    found_st = True
                    break
            if not found_st:
                raise BadRequest("Illegal subject type %s for predicate %s" % (subject_type, predicate))
        if not object_type in pt['range']:
            found_ot = False
            for rant in pt['range']:
                if object_type in getextends(rant):
                    found_ot = True
                    break
            if not found_ot:
                raise BadRequest("Illegal object type %s for predicate %s" % (object_type, predicate))

        # Finally, ensure this isn't a duplicate
        assoc_list = self.find_associations(subject_id, predicate, object_id, id_only=False)
        if len(assoc_list) != 0:
            assoc = assoc_list[0]
            #print "**** Found associations:"
            #import pprint
            #pprint.pprint(assoc_list)
            raise BadRequest("Association between %s and %s with predicate %s already exists" % (subject_id, object_id, predicate))

        assoc = IonObject("Association",
                          s=subject_id, st=subject_type,
                          p=predicate,
                          o=object_id, ot=object_type,
                          ts=get_ion_ts())
        return self.rr_store.create(assoc, create_unique_association_id())

    def create_association_mult(self, assoc_list=None):
        """
        Create multiple associations between two IonObjects with a given predicate.
        @param assoc_list  A list of 3-tuples of (subject, predicate, object). Subject/object can be str or object
        """
        if not assoc_list:
            return []

        lookup_rid = set()
        for s, p, o in assoc_list:
            if type(s) is str:
                lookup_rid.add(s)
            if type(o) is str:
                lookup_rid.add(o)
        lookup_rid = list(lookup_rid)
        lookup_obj = self.read_mult(lookup_rid) if lookup_rid else []
        res_by_id = dict(zip(lookup_rid, lookup_obj))

        create_ts = get_ion_ts()
        new_assoc_list = []
        for s, p, o in assoc_list:
            new_s = s
            new_o = o
            if type(s) is str:
                new_s = res_by_id[s]
                if not new_s:
                    raise NotFound("Subject %s not found" % s)
            else:
                if "_id" not in s:
                    raise BadRequest("Subject id not available")
            if type(o) is str:
                new_o = res_by_id[o]
                if not new_o:
                    raise NotFound("Object %s not found" % o)
            else:
                if "_id" not in object:
                    raise BadRequest("Object id not available")

            # Check that subject and object type are permitted by association definition
            if p not in Predicates:
                raise BadRequest("Predicate unknown %s" % p)
            pt = Predicates.get(p)
            if not new_s.type_ in pt['domain']:
                found_st = False
                for domt in pt['domain']:
                    if new_s.type_ in getextends(domt):
                        found_st = True
                        break
                if not found_st:
                    raise BadRequest("Illegal subject type %s for predicate %s" % (new_s.type_, p))
            if not new_o.type_ in pt['range']:
                found_ot = False
                for rant in pt['range']:
                    if new_o.type_ in getextends(rant):
                        found_ot = True
                        break
                if not found_ot:
                    raise BadRequest("Illegal object type %s for predicate %s" % (new_o.type_, p))

            # Skip duplicate check

            assoc = IonObject("Association",
                              s=new_s._id, st=new_s.type_,
                              p=p,
                              o=new_o._id, ot=new_o.type_,
                              ts=create_ts)
            new_assoc_list.append(assoc)

        new_assoc_ids = [create_unique_association_id() for i in xrange(len(new_assoc_list))]
        return self.rr_store.create_mult(new_assoc_list, new_assoc_ids)

    def delete_association(self, association=''):
        """
        Delete an association between two IonObjects
        @param association  Association object, association id or 3-list of [subject, predicate, object]
        """
        if type(association) in (list, tuple) and len(association) == 3:
            subject, predicate, obj = association
            assoc_id_list = self.find_associations(subject=subject, predicate=predicate, object=obj, id_only=True)
            success = True
            for aid in assoc_id_list:
                success = success and self.rr_store.delete(aid, object_type="Association")
            return success
        else:
            return self.rr_store.delete(association, object_type="Association")

    def _is_in_association(self, obj_id):
        if not obj_id:
            raise BadRequest("Must provide object id")

        assoc_ids = self.find_associations(anyside=obj_id, id_only=True, limit=1)
        if assoc_ids:
            log.debug("_is_in_association(%s): Object has associations: %s", obj_id, assoc_ids)
            return True

        return False

    def read_association(self, association_id=None):
        if not association_id:
            raise BadRequest("Missing association_id parameter")

        return self.rr_store.read(association_id, object_type="Association")


    # -------------------------------------------------------------------------
    # Resource find operations

    def read_object(self, subject="", predicate="", object_type="", assoc="", id_only=False):
        if assoc:
            if type(assoc) is str:
                assoc = self.read_association(assoc)
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
                assoc = self.read_association(assoc)
            return assoc.s if id_only else self.read(assoc.s)
        else:
            sub_list, assoc_list = self.find_subjects(subject_type=subject_type, predicate=predicate, object=object, id_only=True)
            if not sub_list:
                raise NotFound("No subject found for subject_type=%s, predicate=%s, object=%s" % (subject_type, predicate, object))
            elif len(sub_list) > 1:
                raise Inconsistent("More than one subject found for subject_type=%s, predicate=%s, object=%s: count=%s" % (
                    subject_type, predicate, object, len(sub_list)))
            return sub_list[0] if id_only else self.read(sub_list[0])

    def find_objects(self, subject="", predicate="", object_type="", id_only=False,
                     limit=None, skip=None, descending=None, access_args=None):
        return self.rr_store.find_objects(subject, predicate, object_type, id_only=id_only,
                                          limit=limit, skip=skip, descending=descending, access_args=access_args)

    def find_subjects(self, subject_type="", predicate="", object="", id_only=False,
                      limit=None, skip=None, descending=None, access_args=None):
        return self.rr_store.find_subjects(subject_type, predicate, object, id_only=id_only,
                                           limit=limit, skip=skip, descending=descending, access_args=access_args)

    def find_associations(self, subject="", predicate="", object="", assoc_type=None, id_only=False, anyside=None, query=None,
                          limit=None, skip=None, descending=None, access_args=None):
        return self.rr_store.find_associations(subject, predicate, object, assoc_type, id_only=id_only, anyside=anyside,
                                               query=query, limit=limit, skip=skip, descending=descending, access_args=access_args)

    def find_objects_mult(self, subjects=[], id_only=False, predicate="", access_args=None):
        return self.rr_store.find_objects_mult(subjects=subjects, id_only=id_only, predicate=predicate, access_args=access_args)

    def find_subjects_mult(self, objects=[], id_only=False, predicate="", access_args=None):
        return self.rr_store.find_subjects_mult(objects=objects, id_only=id_only, predicate=predicate, access_args=access_args)

    def get_association(self, subject="", predicate="", object="", assoc_type=None, id_only=False):
        assoc = self.rr_store.find_associations(subject, predicate, object, id_only=id_only)
        if not assoc:
            raise NotFound("Association for subject/predicate/object/type %s/%s/%s not found" % (
                subject, predicate, object))
        elif len(assoc) > 1:
            raise Inconsistent("Duplicate associations found for subject/predicate/object/type %s/%s/%s" % (
                subject, predicate, object))
        return assoc[0]

    def find_resources(self, restype="", lcstate="", name="", id_only=False, access_args=None):
        return self.rr_store.find_resources(restype, lcstate, name, id_only=id_only, access_args=access_args)

    def find_resources_ext(self, restype="", lcstate="", name="",
                           keyword=None, nested_type=None,
                           attr_name=None, attr_value=None, alt_id="", alt_id_ns="",
                           limit=None, skip=None, descending=None, id_only=False,
                           query=None,
                           access_args=None):
        return self.rr_store.find_resources_ext(restype=restype, lcstate=lcstate, name=name,
            keyword=keyword, nested_type=nested_type,
            attr_name=attr_name, attr_value=attr_value, alt_id=alt_id, alt_id_ns=alt_id_ns,
            limit=limit, skip=skip, descending=descending,
            id_only=id_only, query=query, access_args=access_args)


    def get_superuser_actors(self, reset=False):
        """Returns a memoized list of system superusers, including the system actor and all actors with
        ION_MANAGER role assignment"""
        if reset or self.superuser_actors is None:
            found_actors = []
            system_actor_name = CFG.get_safe("system.system_actor", "ionsystem")
            sysactors,_ = self.find_resources(restype=RT.ActorIdentity, name=system_actor_name, id_only=True)
            found_actors.extend(sysactors)
            ion_mgrs,_ = self.find_resources_ext(restype=RT.UserRole, attr_name="governance_name", attr_value="ION_MANAGER", id_only=False)
            # roles,_ = self.find_resources(restype=RT.UserRole, id_only=False)
            # ion_mgrs = [role for role in roles if role.governance_name == "ION_MANAGER"]
            actors, assocs = self.find_subjects_mult(ion_mgrs, id_only=False)
            super_actors = list({actor._id for actor, assoc in zip(actors, assocs) if assoc.p == PRED.hasRole and assoc.st == RT.ActorIdentity})
            found_actors.extend(super_actors)
            self.superuser_actors = found_actors
            log.info("get_superuser_actors(): system actor=%s, superuser actors=%s" % (sysactors, super_actors))
        return self.superuser_actors


    # -------------------------------------------------------------------------
    # Extended resource framework operations

    def get_resource_extension(self, resource_id='', resource_extension='', computed_resource_type=None, ext_associations=None, ext_exclude=None, **kwargs ):
        """Returns any ExtendedResource object containing additional related information derived from associations

        @param resource_id    str
        @param resource_extension    str
        @param ext_associations    dict
        @param ext_exclude    list
        @retval extended_resource    ExtendedResource
        @throws BadRequest    A parameter is missing
        @throws NotFound    An object with the specified resource_id does not exist
        """
        if not resource_id:
            raise BadRequest("The resource_id parameter is empty")

        if not resource_extension:
            raise BadRequest("The resource_extension parameter is not set")

        extended_resource_handler = ExtendedResourceContainer(self, self)

        #Handle differently if the resource_id parameter is a list of ids
        if resource_id.find('[') > -1:
            res_input = eval(resource_id)
            extended_resource_list = extended_resource_handler.create_extended_resource_container_list(extended_resource_type=resource_extension,
                resource_id_list=res_input, computed_resource_type=computed_resource_type, ext_associations=ext_associations, ext_exclude=ext_exclude, **kwargs)
            return extended_resource_list

        extended_resource = extended_resource_handler.create_extended_resource_container(extended_resource_type=resource_extension,
            resource_id=resource_id, computed_resource_type=computed_resource_type, ext_associations=ext_associations, ext_exclude=ext_exclude, **kwargs)

        return extended_resource

    def prepare_resource_support(self, resource_type='', resource_id=''):
        """Returns a structured dict with information to help create/update a resource

        @param resource_type    str
        @param resource_id    str
        @retval resource_data    GenericPrepareSupport
        @throws BadRequest    A parameter is missing
        @throws NotFound    An object with the specified resource_id does not exist
        """

        if not resource_type:
            raise BadRequest("The resource_type parameter is required")

        extended_resource_handler = ExtendedResourceContainer(self, self)

        resource_data = extended_resource_handler.create_prepare_resource_support(resource_id=resource_id, prepare_resource_type=OT.GenericPrepareSupport, origin_resource_type=resource_type)

        #Fill out service request information for creating a instrument device
        extended_resource_handler.set_service_requests(resource_data.create_request, 'resource_registry',
            'create', { "object":  "$(object)" })

        #Fill out service request information for creating a instrument device
        extended_resource_handler.set_service_requests(resource_data.update_request, 'resource_registry',
            'update', { "object":  "$(object)" })

        return resource_data


    # This is a method used for testing - do not remove
    def get_user_id_test(self, resource_id, user_id=None):
        return user_id


class ResourceRegistryServiceWrapper(object):
    """
    The purpose of this class is to map the service interface of the resource_registry service (YML)
    to the container's resource registry instance.
    In particular it extracts the actor from the current message context for use as owner.
    """
    def __init__(self, rr, process):
        self._rr = rr
        self._process = process

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return getattr(self, attr)
        return getattr(self._rr, attr)

    def create(self, object=None):
        return self._rr.create(object=object, actor_id=get_ion_actor_id(self._process))

    def create_attachment(self, resource_id='', attachment=None):
        return self._rr.create_attachment(resource_id=resource_id, attachment=attachment, actor_id=get_ion_actor_id(self._process))

    def find_objects(self, subject="", predicate="", object_type="", id_only=False, limit=0, skip=0, descending=False):
        access_args = create_access_args(current_actor_id=get_ion_actor_id(self._process),
                                         superuser_actor_ids=self._rr.get_superuser_actors())
        return self._rr.find_objects(subject=subject, predicate=predicate,
            object_type=object_type, id_only=id_only,
            limit=limit, skip=skip, descending=descending, access_args=access_args)

    def find_subjects(self, subject_type="", predicate="", object="", id_only=False, limit=0, skip=0, descending=False):
        access_args = create_access_args(current_actor_id=get_ion_actor_id(self._process),
                                         superuser_actor_ids=self._rr.get_superuser_actors())
        return self._rr.find_subjects(subject_type=subject_type, predicate=predicate,
            object=object, id_only=id_only,
            limit=limit, skip=skip, descending=descending, access_args=access_args)

    def find_objects_mult(self, subjects=None, id_only=False, predicate=""):
        access_args = create_access_args(current_actor_id=get_ion_actor_id(self._process),
                                         superuser_actor_ids=self._rr.get_superuser_actors())
        return self._rr.find_objects_mult(subjects=subjects, id_only=id_only,
                                                        predicate=predicate, access_args=access_args)

    def find_subjects_mult(self, objects=None, id_only=False, predicate=""):
        access_args = create_access_args(current_actor_id=get_ion_actor_id(self._process),
                                         superuser_actor_ids=self._rr.get_superuser_actors())
        return self._rr.find_subjects_mult(objects=objects, id_only=id_only,
                                                         predicate=predicate, access_args=access_args)

    def find_resources(self, restype="", lcstate="", name="", id_only=False):
        access_args = create_access_args(current_actor_id=get_ion_actor_id(self._process),
                                         superuser_actor_ids=self._rr.get_superuser_actors())
        return self._rr.find_resources(restype=restype, lcstate=lcstate, name=name, id_only=id_only,
                                                     access_args=access_args)

    def find_resources_ext(self, restype='', lcstate='', name='', keyword='', nested_type='', attr_name='', attr_value='',
                           alt_id='', alt_id_ns='', limit=0, skip=0, descending=False, id_only=False, query=''):
        access_args = create_access_args(current_actor_id=get_ion_actor_id(self._process),
                                         superuser_actor_ids=self._rr.get_superuser_actors())
        return self._rr.find_resources_ext(restype=restype, lcstate=lcstate, name=name,
            keyword=keyword, nested_type=nested_type, attr_name=attr_name, attr_value=attr_value,
            alt_id=alt_id, alt_id_ns=alt_id_ns,
            limit=limit, skip=skip, descending=descending,
            id_only=id_only, query=query, access_args=access_args)


class ResourceQuery(DatastoreQueryBuilder):
    """
    Helper class to build datastore queries for the resource registry.
    Based on the DatastoreQueryBuilder
    """

    def __init__(self):
        super(ResourceQuery, self).__init__(datastore=DataStore.DS_RESOURCES, profile=DataStore.DS_PROFILE.RESOURCES)

    def filter_type(self, type_expr):
        return self.eq_in(DQ.ATT_TYPE, type_expr)

    def filter_lcstate(self, expr):
        return self.eq_in(DQ.RA_LCSTATE, expr)

    def filter_availability(self, expr):
        return self.eq_in(DQ.RA_AVAILABILITY, expr)

    def filter_name(self, name_expr, cmpop=None):
        return self.txt_cmp(DQ.RA_NAME, name_expr, cmpop)

    def filter_attribute(self, attr_name, expr, cmpop=None):
        return self.txt_cmp(attr_name, expr, cmpop)

    def filter_owner(self, owner_actor):
        return self.filter_associated_with_subject(object=owner_actor, object_type=RT.ActorIdentity, predicate=PRED.hasOwner)

    def filter_by_association(self, target=None, target_type=None, predicate=None, direction=None, target_filter=None):
        """Establishes a filter by association to target(s) based on various criteria (predicate, target id, target type,
        association direction) over one or multiple levels.
        @param predicate  A predicate or list of predicate (one level) or list of (predicate/list of predicate) for multi level
        @param target  An id (str) or list of ids of associated resources as determined by
        @param target_type  A type (str) or list of types of associated resources
        @param direction  Indicates the directionality of associations in one character: S=to subject (== find objects),
                O=to object (==find subjects), A=any side (== find associated). If this expression is more than one
                character long, it indicates to search multiple levels, e.g. "SO" -- TODO: >-<
        @param target_filter  Filter expressions applicable to association target
        """
        return self.associated_with(target=target, target_type=target_type, predicate=predicate,
                                    direction=direction, target_filter=target_filter)

    def filter_associated_with_subject(self, object=None, object_type=None, predicate=None, target_filter=None):
        """Shorthand for a filter by association with a subject"""
        return self.filter_by_association(predicate=predicate, target=object, target_type=object_type,
                                          direction="S", target_filter=target_filter)

    def filter_associated_with_object(self, subject=None, subject_type=None, predicate=None, target_filter=None):
        """Shorthand for a filter by association with an object"""
        return self.filter_by_association(predicate=predicate, target=subject, target_type=subject_type,
                                          direction="O", target_filter=target_filter)

    def filter_associated_with(self, target=None, target_type=None, predicate=None, target_filter=None):
        """Shorthand for a filter by association with another resource (any direction)"""
        return self.filter_by_association(predicate=predicate, target=target, target_type=target_type,
                                          direction="A", target_filter=target_filter)

    def filter_object_descendants(self, parent=None, object_type=None, predicate=None, max_depth=0):
        """Filter to all descendant (child) resources in the association object direction"""
        return self.op_expr(self.ASSOP_DESCEND_O, parent, object_type, predicate, max_depth)

    def filter_subject_descendants(self, parent=None, subject_type=None, predicate=None, max_depth=0):
        """Filter to all descendant (child) resources in the association subject direction"""
        return self.op_expr(self.ASSOP_DESCEND_S, parent, subject_type, predicate, max_depth)


class AssociationQuery(DatastoreQueryBuilder):
    def __init__(self):
        super(AssociationQuery, self).__init__(datastore=DataStore.DS_RESOURCES,
                                               profile=DataStore.DS_PROFILE.RESOURCES, ds_sub="assoc")

    def filter_subject(self, expr):
        return self.eq_in(DQ.AA_SUBJECT, expr)

    def filter_subject_type(self, expr):
        return self.eq_in(DQ.AA_SUBJECT_TYPE, expr)

    def filter_object(self, expr):
        return self.eq_in(DQ.AA_OBJECT, expr)

    def filter_object_type(self, expr):
        return self.eq_in(DQ.AA_OBJECT_TYPE, expr)

    def filter_predicate(self, expr):
        return self.eq_in(DQ.AA_PREDICATE, expr)

    def filter_object_descendants(self, parent=None, object_type=None, predicate=None, max_depth=0):
        return self.op_expr(self.ASSOP_DESCEND_O, parent, object_type, predicate, max_depth)

    def filter_subject_descendants(self, parent=None, subject_type=None, predicate=None, max_depth=0):
        return self.op_expr(self.ASSOP_DESCEND_S, parent, subject_type, predicate, max_depth)
