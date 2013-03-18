#!/usr/bin/env python

"""Resource Registry implementation"""

__author__ = 'Michael Meisinger'

from pyon.core import bootstrap
from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest, NotFound, Inconsistent
from pyon.core.object import IonObjectBase
from pyon.core.registry import getextends
from pyon.datastore.datastore import DataStore
from pyon.ion.event import EventPublisher
from pyon.ion.identifier import create_unique_resource_id, create_unique_association_id
from pyon.ion.resource import LCS, LCE, PRED, RT, AS, get_restype_lcsm, is_resource, ExtendedResourceContainer, lcstate, lcsplit, Predicates
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
#        self.rr_store_backend = datastore_manager.get_datastore(DataStore.DS_RESOURCES, DataStore.DS_PROFILE.RESOURCES)
#        self.rr_store = IonCouchDataStore(self.rr_store_backend, self.container)

        self.rr_store = datastore_manager.get_datastore(DataStore.DS_RESOURCES, DataStore.DS_PROFILE.RESOURCES)

        self.event_pub = EventPublisher()

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


        lcsm = get_restype_lcsm(object._get_type())
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
            log.debug("Associate resource_id=%s with owner=%s" % (res_id, actor_id))
            self.create_association(res_id, PRED.hasOwner, actor_id)

        if self.container.has_capability(self.container.CCAP.EVENT_PUBLISHER):
            self.event_pub.publish_event(event_type="ResourceModifiedEvent",
                                     origin=res_id, origin_type=object._get_type(),
                                     sub_type="CREATE",
                                     mod_type=ResourceModificationType.CREATE)

        return res

    def create_mult(self, res_list):
        cur_time = get_ion_ts()
        for resobj in res_list:
            lcsm = get_restype_lcsm(resobj._get_type())
            resobj.lcstate = lcsm.initial_state if lcsm else LCS.DEPLOYED
            resobj.availability = lcsm.initial_availability if lcsm else AS.AVAILABLE
            resobj.ts_created = cur_time
            resobj.ts_updated = cur_time

        id_list = [create_unique_resource_id() for i in xrange(len(res_list))]
        res = self.rr_store.create_mult(res_list, id_list)
        res_list = [(rid, rrv) for success, rid, rrv in res]

        # TODO: Publish events (skipped, because this is inefficient one by one for a large list
#        for rid,rrv in res_list:
#            self.event_pub.publish_event(event_type="ResourceModifiedEvent",
#                origin=res_id, origin_type=object._get_type(),
#                mod_type=ResourceModificationType.CREATE)

        return res_list

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
                                     origin=object._id, origin_type=object._get_type(),
                                     sub_type="UPDATE",
                                     mod_type=ResourceModificationType.UPDATE)

        return self.rr_store.update(object)

    def read(self, object_id='', rev_id=''):
        if not object_id:
            raise BadRequest("The object_id parameter is an empty string")

        return self.rr_store.read(object_id, rev_id)

    def read_mult(self, object_ids=None):
        if object_ids is None:
            raise BadRequest("The object_ids parameter is empty")
        return self.rr_store.read_mult(object_ids)

    def delete(self, object_id='', del_associations=False):
        res_obj = self.read(object_id)
        if not res_obj:
            raise NotFound("Resource %s does not exist" % object_id)

        if not del_associations:
            self._delete_owners(object_id)

        # Update first to RETIRED to give ElasticSearch a hint
        res_obj.lcstate = LCS.RETIRED
        res_obj.availability = AS.PRIVATE
        self.rr_store.update(res_obj)

        if del_associations:
            assoc_ids = self.find_associations(anyside=object_id, id_only=True)
            self.rr_store.delete_doc_mult(assoc_ids)
            log.debug("Deleted %s associations for resource %s", len(assoc_ids), object_id)

        elif self._is_in_association(object_id):
            log.warn("Deleting object %s that still has associations" % object_id)

        res = self.rr_store.delete(object_id)

        if self.container.has_capability(self.container.CCAP.EVENT_PUBLISHER):
            self.event_pub.publish_event(event_type="ResourceModifiedEvent",
                                     origin=res_obj._id, origin_type=res_obj._get_type(),
                                     sub_type="DELETE",
                                     mod_type=ResourceModificationType.DELETE)

        return res

    def _delete_owners(self, resource_id):
        # Delete all owner users.
        owners, assocs = self.rr_store.find_objects(resource_id, PRED.hasOwner, RT.ActorIdentity, id_only=True)
        for aid in assocs:
            self.delete_association(aid)

    def retire(self, resource_id):
        """
        This is the official "delete" for resource objects: they are set to RETIRED lcstate.
        All associations are set to retired as well.
        """
        res_obj = self.read(resource_id)
        old_state = res_obj.lcstate
        old_availability = res_obj.availability
        if old_state == LCS.RETIRED:
            raise BadRequest("Resource id=%s already RETIRED" % (resource_id))

        res_obj.lcstate = LCS.RETIRED
        res_obj.availability = AS.PRIVATE
        res_obj.ts_updated = get_ion_ts()

        updres = self.rr_store.update(res_obj)
        log.debug("retire(res_id=%s). Change %s_%s to %s_%s", resource_id,
                  old_state, old_availability, res_obj.lcstate, res_obj.availability)

        assocs = self.find_associations(anyside=resource_id, id_only=False)
        for assoc in assocs:
            assoc.retired = True
        if assocs:
            self.rr_store.update_mult(assocs)
            log.debug("retire(res_id=%s). Retired %s associations", resource_id, len(assocs))

        if self.container.has_capability(self.container.CCAP.EVENT_PUBLISHER):
            self.event_pub.publish_event(event_type="ResourceLifecycleEvent",
                                     origin=res_obj._id, origin_type=res_obj.type_,
                                     sub_type="%s.%s" % (res_obj.lcstate, res_obj.availability),
                                     lcstate=res_obj.lcstate, availability=res_obj.availability,
                                     lcstate_before=old_state, availability_before=old_availability)


    def execute_lifecycle_transition(self, resource_id='', transition_event=''):
        if transition_event == LCE.RETIRE:
            return self.retire(resource_id)

        res_obj = self.read(resource_id)

        old_state = res_obj.lcstate
        old_availability = res_obj.availability
        old_lcs = lcstate(old_state, old_availability)

        restype = res_obj._get_type()
        restype_workflow = get_restype_lcsm(restype)
        if not restype_workflow:
            raise BadRequest("Resource id=%s type=%s has no lifecycle" % (resource_id, restype))

        new_state = restype_workflow.get_successor(old_lcs, transition_event)
        if not new_state:
            raise BadRequest("Resource id=%s, type=%s, lcstate=%s has no transition for event %s" % (
                resource_id, restype, old_lcs, transition_event))

        lcmat, lcav = lcsplit(new_state)
        res_obj.lcstate = lcmat
        res_obj.availability = lcav

        res_obj.ts_updated = get_ion_ts()
        self.rr_store.update(res_obj)
        log.debug("execute_lifecycle_transition(res_id=%s, event=%s). Change %s_%s to %s_%s", resource_id, transition_event,
                  old_state, old_availability, res_obj.lcstate, res_obj.availability)

        if self.container.has_capability(self.container.CCAP.EVENT_PUBLISHER):
            self.event_pub.publish_event(event_type="ResourceLifecycleEvent",
                                     origin=res_obj._id, origin_type=res_obj.type_,
                                     sub_type="%s.%s" % (res_obj.lcstate, res_obj.availability),
                                     lcstate=res_obj.lcstate, availability=res_obj.availability,
                                     lcstate_before=old_state, availability_before=old_availability,
                                     transition_event=transition_event)

        return lcstate(res_obj.lcstate, res_obj.availability)

    def set_lifecycle_state(self, resource_id='', target_lcstate=''):
        """Sets the lifecycle state (if possible) to the target state. Supports compound states"""
        if not target_lcstate:
            raise BadRequest("Bad life-cycle state %s" % target_lcstate)
        if target_lcstate.startswith('RETIRED'):
            return self.retire(resource_id)

        res_obj = self.read(resource_id)
        old_target = target_lcstate
        old_state = res_obj.lcstate
        old_availability = res_obj.availability
        old_lcs = lcstate(old_state, old_availability)
        restype = res_obj._get_type()
        restype_workflow = get_restype_lcsm(restype)
        if not restype_workflow:
            raise BadRequest("Resource id=%s type=%s has no lifecycle" % (resource_id, restype))

        if '_' in target_lcstate:    # Support compound
            target_lcmat, target_lcav = lcsplit(target_lcstate)
            if target_lcmat not in LCS:
                raise BadRequest("Unknown life-cycle state %s" % target_lcmat)
            if target_lcav and target_lcav not in AS:
                raise BadRequest("Unknown life-cycle availability %s" % target_lcav)
        elif target_lcstate in LCS:
            target_lcmat, target_lcav = target_lcstate, res_obj.availability
            target_lcstate = lcstate(target_lcmat, target_lcav)
        elif target_lcstate in AS:
            target_lcmat, target_lcav = res_obj.lcstate, target_lcstate
            target_lcstate = lcstate(target_lcmat, target_lcav)
        else:
            raise BadRequest("Unknown life-cycle state %s" % target_lcstate)

        # Check that target state is allowed
        if not target_lcstate in restype_workflow.get_successors(old_lcs).values():
            raise BadRequest("Target state %s not reachable for resource in state %s" % (target_lcstate, old_lcs))

        res_obj.lcstate = target_lcmat
        res_obj.availability = target_lcav

        res_obj.ts_updated = get_ion_ts()

        updres = self.rr_store.update(res_obj)
        log.debug("set_lifecycle_state(res_id=%s, target=%s). Change %s_%s to %s_%s", resource_id, old_target,
                  old_state, old_availability, res_obj.lcstate, res_obj.availability)

        if self.container.has_capability(self.container.CCAP.EVENT_PUBLISHER):
            self.event_pub.publish_event(event_type="ResourceLifecycleEvent",
                                     origin=res_obj._id, origin_type=res_obj.type_,
                                     sub_type="%s.%s" % (res_obj.lcstate, res_obj.availability),
                                     lcstate=res_obj.lcstate, availability=res_obj.availability,
                                     lcstate_before=old_state, availability_before=old_availability)


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
        assoc_list = self.find_associations(subject, predicate, object, id_only=False)
        if len(assoc_list) != 0:
            assoc = assoc_list[0]
            raise BadRequest("Association between %s and %s with predicate %s already exists" % (subject, object, predicate))

        assoc = IonObject("Association",
                          s=subject_id, st=subject_type,
                          p=predicate,
                          o=object_id, ot=object_type,
                          ts=get_ion_ts())
        return self.rr_store.create(assoc, create_unique_association_id())

    def delete_association(self, association=''):
        """
        Delete an association between two IonObjects
        @param association  Association object, association id or 3-list of [subject, predicate, object]
        """
        if type(association) in (list, tuple) and len(association) == 3:
            subject, predicate, obj = association
            assoc_id_list = self.find_associations(subject=subject, predicate=predicate, obj=obj, id_only=True)
            success = True
            for aid in assoc_id_list:
                success = success and self.delete(aid)
            return success
        else:
            return self.rr_store.delete(association)

    def _is_in_association(self, obj_id):
        if not obj_id:
            raise BadRequest("Must provide object id")

        assoc_ids = self.find_associations(anyside=obj_id, id_only=True, limit=1)
        if assoc_ids:
            log.debug("_is_in_association(%s): Object has associations: %s", obj_id, assoc_ids)
            return True

        return False


    # -------------------------------------------------------------------------
    # Resource find operations

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

    def find_objects(self, subject="", predicate="", object_type="", id_only=False, limit=None, skip=None, descending=None):
        return self.rr_store.find_objects(subject, predicate, object_type, id_only=id_only, limit=limit, skip=skip, descending=descending)

    def find_subjects(self, subject_type="", predicate="", object="", id_only=False, limit=None, skip=None, descending=None):
        return self.rr_store.find_subjects(subject_type, predicate, object, id_only=id_only, limit=limit, skip=skip, descending=descending)

    def find_associations(self, subject="", predicate="", object="", assoc_type=None, id_only=False, anyside=None, limit=None, skip=None, descending=None):
        return self.rr_store.find_associations(subject, predicate, object, assoc_type, id_only=id_only, anyside=anyside, limit=limit, skip=skip, descending=descending)

    def find_objects_mult(self, subjects=[], id_only=False):
        return self.rr_store.find_objects_mult(subjects=subjects, id_only=id_only)

    def find_subjects_mult(self, objects=[], id_only=False):
        return self.rr_store.find_subjects_mult(objects=objects, id_only=id_only)
    
    def get_association(self, subject="", predicate="", object="", assoc_type=None, id_only=False):
        assoc = self.rr_store.find_associations(subject, predicate, object, id_only=id_only)
        if not assoc:
            raise NotFound("Association for subject/predicate/object/type %s/%s/%s not found" % (
                subject, predicate, object))
        elif len(assoc) > 1:
            raise Inconsistent("Duplicate associations found for subject/predicate/object/type %s/%s/%s" % (
                subject, predicate, object))
        return assoc[0]

    def find_resources(self, restype="", lcstate="", name="", id_only=False):
        return self.rr_store.find_resources(restype, lcstate, name, id_only=id_only)

    def find_resources_ext(self, restype="", lcstate="", name="",
                           keyword=None, nested_type=None,
                           attr_name=None, attr_value=None, alt_id="", alt_id_ns="",
                           limit=None, skip=None, descending=None, id_only=False):
        return self.rr_store.find_resources_ext(restype=restype, lcstate=lcstate, name=name,
            keyword=keyword, nested_type=nested_type,
            attr_name=attr_name, attr_value=attr_value, alt_id=alt_id, alt_id_ns=alt_id_ns,
            limit=limit, skip=skip, descending=descending,
            id_only=id_only)


    # -------------------------------------------------------------------------
    # Extended resource framework operations

    def get_resource_extension(self, resource_id='', resource_extension='', ext_associations=None, ext_exclude=None):
        """Returns any ExtendedResource object containing additional related information derived from associations

        @param resource_id    str
        @param resource_extension    str
        @param ext_associations    dict
        @param ext_exclude    list
        @retval actor_identity    ExtendedResource
        @throws BadRequest    A parameter is missing
        @throws NotFound    An object with the specified resource_id does not exist
        """
        if not resource_id:
            raise BadRequest("The resource_id parameter is empty")

        if not resource_extension:
            raise BadRequest("The extended_resource parameter not set")

        extended_resource_handler = ExtendedResourceContainer(self, self)

        #Handle differently if the resource_id parameter is a list of ids
        if resource_id.find('[') > -1:
            res_input = eval(resource_id)
            extended_resource_list = extended_resource_handler.create_extended_resource_container_list(resource_extension,
                res_input, computed_resource_type=None, ext_associations=ext_associations, ext_exclude=ext_exclude)
            return extended_resource_list

        extended_resource = extended_resource_handler.create_extended_resource_container(resource_extension,
            resource_id, computed_resource_type=None, ext_associations=ext_associations, ext_exclude=ext_exclude)

        return extended_resource

class ResourceRegistryServiceWrapper(object):
    """
    The purpose of this class is to provide the exact service interface of the resource_registry (YML)
    interface definition. In particular for create that extracts the actor header for use as owner.
    """
    def __init__(self, rr, process):
        self._rr = rr
        self._process = process

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return getattr(self, attr)
        return getattr(self._rr, attr)

    def create(self, object=None):
        ion_actor_id = None
        if self._process:
            ctx = self._process.get_context()
            ion_actor_id = ctx.get('ion-actor-id', None) if ctx else None
        return self._rr.create(object=object, actor_id=ion_actor_id)

    def create_attachment(self, resource_id='', attachment=None):
        ion_actor_id = None
        if self._process:
            ctx = self._process.get_context()
            ion_actor_id = ctx.get('ion-actor-id', None) if ctx else None
        return self._rr.create_attachment(resource_id=resource_id, attachment=attachment, actor_id=ion_actor_id)
