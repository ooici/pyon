#!/usr/bin/env python

"""ION common code for couch style datastores"""

__author__ = 'Michael Meisinger'

import simplejson as json
from pyon.core.bootstrap import get_obj_registry
from pyon.core.exception import BadRequest, Conflict, NotFound
from pyon.core.object import IonObjectBase, IonObjectSerializer, IonObjectDeserializer
from pyon.datastore.couchdb.couch_common import AbstractCouchDataStore
from pyon.ion.resource import AvailabilityStates
from pyon.util.arg_check import validate_is_instance
from pyon.util.log import log

try:
    from couchdb.client import ViewResults, Row
    from couchdb.http import ResourceNotFound
except Exception:
    class Row(object):
        pass
    class ViewResults(object):
        pass
    class ResourceNotFound(Exception):
        pass


class PyonCouchDataStoreMixin(AbstractCouchDataStore):
    """
    Mixin class for common couch style datastore code
    """

    # -------------------------------------------------------------------------
    # Couch document operations

    def create(self, obj, object_id=None, attachments=None, datastore_name=""):
        """
        Converts ion objects to python dictionary before persisting them using the optional
        suggested identifier and creates attachments to the object.
        Returns an identifier and revision number of the object
        """
        if not isinstance(obj, IonObjectBase):
            raise BadRequest("Obj param is not instance of IonObjectBase")

        return self.create_doc(self._ion_object_to_persistence_dict(obj),
                                  object_id=object_id, datastore_name=datastore_name,
                                  attachments=attachments)

    def create_mult(self, objects, object_ids=None, allow_ids=None):
        if any([not isinstance(obj, IonObjectBase) for obj in objects]):
            raise BadRequest("Obj param is not instance of IonObjectBase")

        return self.create_doc_mult([self._ion_object_to_persistence_dict(obj) for obj in objects], object_ids)


    def update(self, obj, datastore_name=""):
        if not isinstance(obj, IonObjectBase):
            raise BadRequest("Obj param is not instance of IonObjectBase")

        return self.update_doc(self._ion_object_to_persistence_dict(obj))

    def update_mult(self, objects):
        if any([not isinstance(obj, IonObjectBase) for obj in objects]):
            raise BadRequest("Obj param is not instance of IonObjectBase")

        return self.update_doc_mult([self._ion_object_to_persistence_dict(obj) for obj in objects])


    def read(self, object_id, rev_id="", datastore_name="", object_type=None):
        if not isinstance(object_id, str):
            raise BadRequest("Object id param is not string")

        doc = self.read_doc(object_id, rev_id, datastore_name=datastore_name, object_type=object_type)
        obj = self._persistence_dict_to_ion_object(doc)

        return obj

    def read_mult(self, object_ids, strict=True, datastore_name=""):
        if any([not isinstance(object_id, str) for object_id in object_ids]):
            raise BadRequest("Object ids are not string: %s" % str(object_ids))

        docs = self.read_doc_mult(object_ids, datastore_name, strict=strict)
        obj_list = [self._persistence_dict_to_ion_object(doc) if doc is not None else None for doc in docs]

        return obj_list


    def delete(self, obj, datastore_name="", object_type=None):
        if not isinstance(obj, IonObjectBase) and not isinstance(obj, str):
            raise BadRequest("Obj param is not instance of IonObjectBase or string id")
        if type(obj) is str:
            self.delete_doc(obj, datastore_name=datastore_name)
        else:
            if '_id' not in obj:
                raise BadRequest("Doc must have '_id'")
            if '_rev' not in obj:
                raise BadRequest("Doc must have '_rev'")
            self.delete_doc(self._ion_object_to_persistence_dict(obj),
                               datastore_name=datastore_name, object_type=object_type)

    def delete_mult(self, object_ids, datastore_name=None):
        return self.delete_doc_mult(object_ids, datastore_name)

    # -------------------------------------------------------------------------
    # View operations

    def find_objects_mult(self, subjects, id_only=False):
        """
        Returns a list of associations for a given list of subjects
        """
        ds, datastore_name = self._get_datastore()
        validate_is_instance(subjects, list, 'subjects is not a list of resource_ids')
        view_args = dict(keys=subjects, include_docs=True)
        results = self.query_view(self._get_view_name("association", "by_bulk"), view_args)
        ids = [i['value'] for i in results]
        assocs = [i['doc'] for i in results]
        self._count(find_assocs_mult_call=1, find_assocs_mult_obj=len(ids))
        if id_only:
            return ids, assocs
        else:
            return self.read_mult(ids), assocs

    def find_subjects_mult(self, objects, id_only=False):
        """
        Returns a list of associations for a given list of objects
        """
        ds, datastore_name = self._get_datastore()
        validate_is_instance(objects, list, 'objects is not a list of resource_ids')
        view_args = dict(keys=objects, include_docs=True)
        results = self.query_view(self._get_view_name("association", "by_subject_bulk"), view_args)
        ids = [i['value'] for i in results]
        assocs = [i['doc'] for i in results]
        self._count(find_assocs_mult_call=1, find_assocs_mult_obj=len(ids))
        if id_only:
            return ids, assocs
        else:
            return self.read_mult(ids), assocs

    def find_objects(self, subject, predicate=None, object_type=None, id_only=False, **kwargs):
        log.debug("find_objects(subject=%s, predicate=%s, object_type=%s, id_only=%s", subject, predicate, object_type, id_only)

        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not subject:
            raise BadRequest("Must provide subject")
        if object_type and not predicate:
            raise BadRequest("Cannot provide object type without a predicate")

        ds, datastore_name = self._get_datastore()

        if type(subject) is str:
            subject_id = subject
        else:
            if "_id" not in subject:
                raise BadRequest("Object id not available in subject")
            else:
                subject_id = subject._id

        view_args = self._get_view_args(kwargs)
        key = [subject_id]
        if predicate:
            key.append(predicate)
            if object_type:
                key.append(object_type)
        endkey = self._get_endkey(key)
        rows = ds.view(self._get_view_name("association", "by_sub"), start_key=key, end_key=endkey, **view_args)

        obj_assocs = [self._persistence_dict_to_ion_object((row['value'])) for row in rows]
        obj_ids = [str(assoc.o) for assoc in obj_assocs]
        self._count(find_objects_call=1, find_objects_obj=len(obj_assocs))

        log.debug("find_objects() found %s objects", len(obj_ids))
        if id_only:
            return (obj_ids, obj_assocs)

        obj_list = self.read_mult(obj_ids)
        return obj_list, obj_assocs

    def find_subjects(self, subject_type=None, predicate=None, obj=None, id_only=False, **kwargs):
        log.debug("find_subjects(subject_type=%s, predicate=%s, object=%s, id_only=%s", subject_type, predicate, obj, id_only)

        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not obj:
            raise BadRequest("Must provide object")
        if subject_type and not predicate:
            raise BadRequest("Cannot provide subject type without a predicate")

        ds, datastore_name = self._get_datastore()

        if type(obj) is str:
            object_id = obj
        else:
            if "_id" not in obj:
                raise BadRequest("Object id not available in object")
            else:
                object_id = obj._id

        view_args = self._get_view_args(kwargs)
        key = [object_id]
        if predicate:
            key.append(predicate)
            if subject_type:
                key.append(subject_type)
        endkey = self._get_endkey(key)
        rows = ds.view(self._get_view_name("association", "by_obj"), start_key=key, end_key=endkey, **view_args)

        sub_assocs = [self._persistence_dict_to_ion_object(row['value']) for row in rows]
        sub_ids = [str(assoc.s) for assoc in sub_assocs]
        self._count(find_subjects_call=1, find_subjects_obj=len(sub_assocs))

        log.debug("find_subjects() found %s subjects", len(sub_ids))
        if id_only:
            return (sub_ids, sub_assocs)

        sub_list = self.read_mult(sub_ids)
        return sub_list, sub_assocs

    def find_associations(self, subject=None, predicate=None, obj=None, assoc_type=None, id_only=True, anyside=None, **kwargs):
        log.debug("find_associations(subject=%s, predicate=%s, object=%s, anyside=%s)", subject, predicate, obj, anyside)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not (subject or obj or predicate or anyside):
            raise BadRequest("Illegal parameters: No S/P/O or anyside")
            #if assoc_type:
        #    raise BadRequest("Illegal parameters: assoc_type deprecated")
        if anyside and (subject or obj):
            raise BadRequest("Illegal parameters: anyside cannot be combined with S/O")
        if anyside and predicate and type(anyside) in (list, tuple):
            raise BadRequest("Illegal parameters: anyside list cannot be combined with P")

        if subject:
            if type(subject) is str:
                subject_id = subject
            else:
                if "_id" not in subject:
                    raise BadRequest("Object id not available in subject")
                else:
                    subject_id = subject._id
        if obj:
            if type(obj) is str:
                object_id = obj
            else:
                if "_id" not in obj:
                    raise BadRequest("Object id not available in object")
                else:
                    object_id = obj._id
        if anyside:
            if type(anyside) is str:
                anyside_ids = [anyside]
            elif type(anyside) in (list, tuple):
                if not all([type(o) in (str, list, tuple) for o in anyside]):
                    raise BadRequest("List of object ids or (object id, predicate) expected")
                anyside_ids = anyside
            else:
                if "_id" not in anyside:
                    raise BadRequest("Object id not available in anyside")
                else:
                    anyside_ids = [anyside._id]

        ds, datastore_name = self._get_datastore()
        view_args = self._get_view_args(kwargs)

        if subject and obj:
            key = [subject_id, object_id]
            if predicate:
                key.append(predicate)
            endkey = self._get_endkey(key)
            rows = ds.view(self._get_view_name("association", "by_match"), start_key=key, end_key=endkey, **view_args)
        elif subject:
            key = [subject_id]
            if predicate:
                key.append(predicate)
            endkey = self._get_endkey(key)
            rows = ds.view(self._get_view_name("association", "by_sub"), start_key=key, end_key=endkey, **view_args)
        elif obj:
            key = [object_id]
            if predicate:
                key.append(predicate)
            endkey = self._get_endkey(key)
            rows = ds.view(self._get_view_name("association", "by_obj"), start_key=key, end_key=endkey, **view_args)
        elif anyside:
            if predicate:
                key = [anyside, predicate]
                endkey = self._get_endkey(key)
                rows = ds.view(self._get_view_name("association", "by_idpred"), start_key=key, end_key=endkey, **view_args)
            elif type(anyside_ids[0]) is str:
                #anyside_ids = json.dumps(anyside_ids)
                rows = ds.view(self._get_view_name("association", "by_id"), keys=anyside_ids, **view_args)
            else:
                rows = ds.view(self._get_view_name("association", "by_idpred"), keys=anyside_ids, **view_args)
        elif predicate:
            if predicate == "*":
                key = []
            else:
                key = [predicate]
            endkey = self._get_endkey(key)
            rows = ds.view(self._get_view_name("association", "by_pred"), start_key=key, end_key=endkey, **view_args)
        else:
            raise BadRequest("Illegal arguments")

        if id_only:
            assocs = [row['id'] for row in rows]
        else:
            assocs = [self._persistence_dict_to_ion_object(row['value']) for row in rows]
        log.debug("find_associations() found %s associations", len(assocs))
        self._count(find_assocs_call=1, find_assocs_obj=len(assocs))
        return assocs

    def _prepare_find_return(self, rows, res_assocs=None, id_only=True, **kwargs):
        if id_only:
            res_ids = [row['id'] for row in rows]
            return res_ids, res_assocs
        else:
            res_docs = [self._persistence_dict_to_ion_object(self._get_row_doc(row)) for row in rows]
            if [True for doc in res_docs if doc is None]:
                res_ids = [row.id for row in rows]
                log.error("Datastore returned None docs despite include_docs==True.\nids=%s\ndocs=%s\nassocs=%s", res_ids, res_docs, res_assocs)
            return res_docs, res_assocs

    def find_resources(self, restype="", lcstate="", name="", id_only=True):
        return self.find_resources_ext(restype=restype, lcstate=lcstate, name=name, id_only=id_only)

    def find_resources_ext(self, restype="", lcstate="", name="",
                           keyword=None, nested_type=None,
                           attr_name=None, attr_value=None, alt_id=None, alt_id_ns=None,
                           limit=None, skip=None, descending=None, id_only=True):
        filter_kwargs = self._get_view_args(dict(limit=limit, skip=skip, descending=descending))
        if name:
            if lcstate:
                raise BadRequest("find by name does not support lcstate")
            return self.find_res_by_name(name, restype, id_only, filter=filter_kwargs)
        elif keyword:
            return self.find_res_by_keyword(keyword, restype, id_only, filter=filter_kwargs)
        elif alt_id or alt_id_ns:
            return self.find_res_by_alternative_id(alt_id, alt_id_ns, id_only, filter=filter_kwargs)
        elif nested_type:
            return self.find_res_by_nested_type(nested_type, restype, id_only, filter=filter_kwargs)
        elif restype and attr_name:
            return self.find_res_by_attribute(restype, attr_name, attr_value, id_only=id_only, filter=filter_kwargs)
        elif restype and lcstate:
            return self.find_res_by_lcstate(lcstate, restype, id_only, filter=filter_kwargs)
        elif restype:
            return self.find_res_by_type(restype, lcstate, id_only, filter=filter_kwargs)
        elif lcstate:
            return self.find_res_by_lcstate(lcstate, restype, id_only, filter=filter_kwargs)
        elif not restype and not lcstate and not name:
            return self.find_res_by_type(None, None, id_only, filter=filter_kwargs)

    def find_res_by_type(self, restype, lcstate=None, id_only=False, filter=None):
        log.debug("find_res_by_type(restype=%s, lcstate=%s)", restype, lcstate)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if lcstate:
            raise BadRequest('lcstate not supported anymore in find_res_by_type')

        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        if restype:
            key = [restype]
            endkey = self._get_endkey(key)
            rows = ds.view(self._get_view_name("resource", "by_type"), include_docs=(not id_only), start_key=key, end_key=endkey, **filter)
        else:
            # Returns ALL documents, only limited by filter
            rows = ds.view(self._get_view_name("resource", "by_type"), include_docs=(not id_only), **filter)

        res_assocs = [dict(type=row['key'][0], name=row['key'][1], id=row['id']) for row in rows]
        log.debug("find_res_by_type() found %s objects", len(res_assocs))
        self._count(find_res_by_type_call=1, find_res_by_type_obj=len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_lcstate(self, lcstate, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_lcstate(lcstate=%s, restype=%s)", lcstate, restype)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if '_' in lcstate:
            log.warn("Search for compound lcstate restricted to maturity: %s", lcstate)
            lcstate,_ = lcstate.split("_", 1)
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        key = [1, lcstate] if lcstate in AvailabilityStates else [0, lcstate]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        rows = ds.view(self._get_view_name("resource", "by_lcstate"), include_docs=(not id_only),  start_key=key, end_key=endkey, **filter)

        res_assocs = [dict(lcstate=row['key'][1], type=row['key'][2], name=row['key'][3], id=row['id']) for row in rows]

        log.debug("find_res_by_lcstate() found %s objects", len(res_assocs))
        self._count(find_res_by_lcstate_call=1, find_res_by_lcstate_obj=len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_name(self, name, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_name(name=%s, restype=%s)", name, restype)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        key = [name]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        rows = ds.view(self._get_view_name("resource", "by_name"), include_docs=(not id_only), start_key=key, end_key=endkey, **filter)

        res_assocs = [dict(name=row['key'][0], type=row['key'][1], id=row['id']) for row in rows]
        log.debug("find_res_by_name() found %s objects", len(res_assocs))
        self._count(find_res_by_name_call=1, find_res_by_name_obj=len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_keyword(self, keyword, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_keyword(keyword=%s, restype=%s)", keyword, restype)
        if not keyword or type(keyword) is not str:
            raise BadRequest('Argument keyword illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        key = [keyword]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        rows = ds.view(self._get_view_name("resource", "by_keyword"), include_docs=(not id_only), start_key=key, end_key=endkey, **filter)

        res_assocs = [dict(keyword=row['key'][0], type=row['key'][1], id=row['id']) for row in rows]
        log.debug("find_res_by_keyword() found %s objects", len(res_assocs))
        self._count(find_res_by_kw_call=1, find_res_by_kw_obj=len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_nested_type(self, nested_type, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_nested_type(nested_type=%s, restype=%s)", nested_type, restype)
        if not nested_type or type(nested_type) is not str:
            raise BadRequest('Argument nested_type illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        key = [nested_type]
        if restype:
            key.append(restype)
        endkey = self._get_endkey(key)
        rows = ds.view(self._get_view_name("resource", "by_nestedtype"), include_docs=(not id_only), start_key=key, end_key=endkey, **filter)

        res_assocs = [dict(nested_type=row['key'][0], type=row['key'][1], id=row['id']) for row in rows]
        log.debug("find_res_by_nested_type() found %s objects", len(res_assocs))
        self._count(find_res_by_nested_call=1, find_res_by_nested_obj=len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_attribute(self, restype, attr_name, attr_value=None, id_only=False, filter=None):
        log.debug("find_res_by_attribute(restype=%s, attr_name=%s, attr_value=%s)", restype, attr_name, attr_value)
        if not attr_name or type(attr_name) is not str:
            raise BadRequest('Argument attr_name illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        key = [restype, attr_name]
        if attr_value:
            key.append(attr_value)
        endkey = self._get_endkey(key)
        rows = ds.view(self._get_view_name("resource", "by_attribute"), include_docs=(not id_only), start_key=key, end_key=endkey, **filter)

        res_assocs = [dict(type=row['key'][0], attr_name=row['key'][1], attr_value=row['key'][2], id=row['id']) for row in rows]
        log.debug("find_res_by_attribute() found %s objects", len(res_assocs))
        self._count(find_res_by_attribute_call=1, find_res_by_attribute_obj=len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_alternative_id(self, alt_id=None, alt_id_ns=None, id_only=False, filter=None):
        log.debug("find_res_by_alternative_id(restype=%s, alt_id_ns=%s)", alt_id, alt_id_ns)
        if alt_id and type(alt_id) is not str:
            raise BadRequest('Argument alt_id illegal')
        if alt_id_ns and type(alt_id_ns) is not str:
            raise BadRequest('Argument alt_id_ns illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        ds, datastore_name = self._get_datastore()
        key = []
        if alt_id:
            key.append(alt_id)
            if alt_id_ns is not None:
                key.append(alt_id_ns)

        endkey = self._get_endkey(key)
        rows = ds.view(self._get_view_name("resource", "by_altid"), include_docs=(not id_only), start_key=key, end_key=endkey, **filter)

        if alt_id_ns and not alt_id:
            res_assocs = [dict(alt_id=row['key'][0], alt_id_ns=row['key'][1], id=row['id']) for row in rows if row['key'][1] == alt_id_ns]
        else:
            res_assocs = [dict(alt_id=row['key'][0], alt_id_ns=row['key'][1], id=row['id']) for row in rows]
        log.debug("find_res_by_alternative_id() found %s objects", len(res_assocs))
        self._count(find_res_by_altid_call=1, find_res_by_altid_obj=len(res_assocs))
        if id_only:
            res_ids = [row['id'] for row in res_assocs]
            return (res_ids, res_assocs)
        else:
            if alt_id_ns and not alt_id:
                res_docs = [self._persistence_dict_to_ion_object(self._get_row_doc(row)) for row in rows if row['key'][1] == alt_id_ns]
            else:
                res_docs = [self._persistence_dict_to_ion_object(self._get_row_doc(row)) for row in rows]
            return (res_docs, res_assocs)

    def find_by_view(self, design_name, view_name, key=None, keys=None, start_key=None, end_key=None,
                     id_only=True, convert_doc=True, **kwargs):
        """
        Generic find function using a defined index
        @param design_name  design document
        @param view_name  view name
        @param key  specific key to find
        @param keys  list of keys to find
        @param start_key  find range start value
        @param end_key  find range end value
        @param id_only  if True, the 4th element of each triple is the document
        @param convert_doc  if True, make IonObject out of doc
        @retval Returns a list of 3-tuples: (document id, index key, index value or document)
        """
        res_rows = self.find_docs_by_view(design_name=design_name, view_name=view_name, key=key, keys=keys,
                                          start_key=start_key, end_key=end_key, id_only=id_only, **kwargs)

        res_rows = [(rid, key,
                     self._persistence_dict_to_ion_object(doc) if convert_doc and isinstance(doc, dict) else doc)
                    for rid, key, doc in res_rows]

        log.debug("find_by_view() found %s objects" % (len(res_rows)))
        return res_rows
        # -------------------------------------------------------------------------
    # View operations

    def _parse_results(self, doc):
        ''' Parses a complex object and organizes it into basic types
        '''
        ret = {}

        #-------------------------------
        # Handle ViewResults type (CouchDB type)
        #-------------------------------
        # \_ Ignore the meta data and parse the rows only
        if isinstance(doc, ViewResults):
            try:
                ret = self._parse_results(doc.rows)
            except ResourceNotFound as e:
                raise BadRequest('The desired resource does not exist.')

            return ret

        #-------------------------------
        # Handle A Row (CouchDB type)
        #-------------------------------
        # \_ Split it into a dict with a key and a value
        #    Recursively parse down through the structure.
        if isinstance(doc, Row):
            if 'id' in doc:
                ret['id'] = doc['id']
            ret['key'] = self._parse_results(doc['key'])
            ret['value'] = self._parse_results(doc['value'])
            if 'doc' in doc:
                ret['doc'] = self._parse_results(doc['doc'])
            return ret

        #-------------------------------
        # Handling a list
        #-------------------------------
        # \_ Break it apart and parse each element in the list

        if isinstance(doc, list):
            ret = []
            for element in doc:
                ret.append(self._parse_results(element))
            return ret
            #-------------------------------
        # Handle a dic
        #-------------------------------
        # \_ Check to make sure it's not an IonObject
        # \_ Parse the key value structure for other objects
        if isinstance(doc, dict):
            if '_id' in doc:
                # IonObject
                return self._persistence_dict_to_ion_object(doc)

            for key, value in doc.iteritems():
                ret[key] = self._parse_results(value)
            return ret

        #-------------------------------
        # Primitive type
        #-------------------------------
        return doc


    def _ion_object_to_persistence_dict(self, ion_object):
        if ion_object is None:
            return None

        obj_dict = self._io_serializer.serialize(ion_object)
        return obj_dict

    def _persistence_dict_to_ion_object(self, obj_dict):
        if obj_dict is None:
            return None

        ion_object = self._io_deserializer.deserialize(obj_dict)
        return ion_object
