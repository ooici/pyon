#!/usr/bin/env python

"""Datastore for PostgreSQL with ION extensions"""

__author__ = 'Michael Meisinger'

from pyon.core.bootstrap import get_obj_registry, CFG
from pyon.core.exception import BadRequest, Conflict, NotFound, Inconsistent
from pyon.core.object import IonObjectBase, IonObjectSerializer, IonObjectDeserializer
from pyon.datastore.postgresql.base_store import PostgresDataStore
from pyon.datastore.postgresql.pg_query import PostgresQueryBuilder
from pyon.datastore.datastore import DataStore
from pyon.util.log import log
from pyon.ion.resource import AvailabilityStates, OT, RT


class PostgresPyonDataStore(PostgresDataStore):
    """
    Base class common to both CouchDB and Couchbase datastores.
    """

    def __init__(self, datastore_name=None, config=None, scope=None, profile=None):
        """
        @param datastore_name  Name of datastore within server. May be scoped to sysname
        @param config  A server config dict with connection params
        @param scope  Prefix for the datastore name (e.g. sysname) to separate multiple systems
        """

        PostgresDataStore.__init__(self, datastore_name=datastore_name,
                                     config=config or CFG.get_safe("server.postgresql"),
                                     profile=profile or DataStore.DS_PROFILE.BASIC,
                                     scope=scope)

        # IonObject Serializers
        self._io_serializer = IonObjectSerializer()
        self._io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())

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

    def read_mult(self, object_ids, datastore_name="", strict=True):
        if any([not isinstance(object_id, str) for object_id in object_ids]):
            raise BadRequest("Object ids are not string: %s" % str(object_ids))

        docs = self.read_doc_mult(object_ids, datastore_name, strict=strict)
        obj_list = [self._persistence_dict_to_ion_object(doc) if doc is not None else None for doc in docs]

        return obj_list

    def delete(self, obj, datastore_name="", object_type=None):
        if not isinstance(obj, IonObjectBase) and not isinstance(obj, str):
            raise BadRequest("Obj param is not instance of IonObjectBase or string id")
        if type(obj) is str:
            self.delete_doc(obj, datastore_name=datastore_name, object_type=object_type)
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

    def find_objects_mult(self, subjects, id_only=False, predicate=None, access_args=None):
        """
        Returns a list of associations for a given list of subjects
        """
        # TODO: Port this implementation to Postgres single query
        res_list = [[], []]
        if not subjects:
            return res_list
        for sub in subjects:
            res_ids, res_assocs = self.find_objects(subject=sub, id_only=id_only, predicate=predicate, access_args=access_args)
            res_list[0].extend(res_ids)
            res_list[1].extend(res_assocs)
        return res_list

    def find_subjects_mult(self, objects, id_only=False, predicate=None, access_args=None):
        """
        Returns a list of associations for a given list of objects
        """
        # TODO: Port this implementation to Postgres single query
        res_list = [[], []]
        if not objects:
            return res_list
        for obj in objects:
            res_ids, res_assocs = self.find_subjects(obj=obj, id_only=id_only, predicate=predicate, access_args=access_args)
            res_list[0].extend(res_ids)
            res_list[1].extend(res_assocs)
        return res_list

    def find_objects(self, subject, predicate=None, object_type=None, id_only=False, access_args=None, **kwargs):
        #log.debug("find_objects(subject=%s, predicate=%s, object_type=%s, id_only=%s", subject, predicate, object_type, id_only)

        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not subject:
            raise BadRequest("Must provide subject")
        if object_type and not predicate:
            raise BadRequest("Cannot provide object type without a predicate")

        if type(subject) is str:
            subject_id = subject
        else:
            if "_id" not in subject:
                raise BadRequest("Object id not available in subject")
            else:
                subject_id = subject._id

        qual_ds_name = self._get_datastore_name()
        assoc_table_name = qual_ds_name+"_assoc"
        table_names = dict(ds=qual_ds_name, dsa=assoc_table_name)
        view_args = self._get_view_args(kwargs, access_args)

        if id_only:
            #query = "SELECT o, doc FROM %(dsa)s WHERE retired<>true " % table_names
            query = "SELECT %(dsa)s.o, %(dsa)s.doc FROM %(dsa)s, %(ds)s WHERE retired<>true AND %(dsa)s.o=%(ds)s.id " % table_names
        else:
            query = "SELECT %(ds)s.doc, %(dsa)s.doc FROM %(dsa)s, %(ds)s WHERE retired<>true AND %(dsa)s.o=%(ds)s.id " % table_names
        query_args = dict(s=subject_id, ot=object_type, p=predicate)

        query_clause = "AND s=%(s)s"
        if predicate:
            query_clause += " AND p=%(p)s"
            if object_type:
                query_clause += " AND ot=%(ot)s"

        query_clause = self._add_access_filter(access_args, qual_ds_name, query_clause, query_args)
        extra_clause = view_args.get("extra_clause", "")
        with self.pool.cursor(**self.cursor_args) as cur:
            cur.execute(query + query_clause + extra_clause, query_args)
            rows = cur.fetchall()

        obj_assocs = [self._persistence_dict_to_ion_object(row[-1]) for row in rows]
        #log.debug("find_objects() found %s objects", len(obj_assocs))
        if id_only:
            res_ids = [self._prep_id(row[0]) for row in rows]
            return res_ids, obj_assocs
        else:
            res_objs = [self._persistence_dict_to_ion_object(row[0]) for row in rows]
            return res_objs, obj_assocs

    def find_subjects(self, subject_type=None, predicate=None, obj=None, id_only=False, access_args=None, **kwargs):
        #log.debug("find_subjects(subject_type=%s, predicate=%s, object=%s, id_only=%s", subject_type, predicate, obj, id_only)

        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not obj:
            raise BadRequest("Must provide object")
        if subject_type and not predicate:
            raise BadRequest("Cannot provide subject type without a predicate")

        if type(obj) is str:
            object_id = obj
        else:
            if "_id" not in obj:
                raise BadRequest("Object id not available in object")
            else:
                object_id = obj._id

        qual_ds_name = self._get_datastore_name()
        assoc_table_name = qual_ds_name+"_assoc"
        table_names = dict(ds=qual_ds_name, dsa=assoc_table_name)
        view_args = self._get_view_args(kwargs, access_args)

        if id_only:
            #query = "SELECT s, doc FROM %(dsa)s WHERE retired<>true " % table_names
            query = "SELECT %(dsa)s.s, %(dsa)s.doc FROM %(dsa)s, %(ds)s WHERE retired<>true AND %(dsa)s.s=%(ds)s.id " % table_names
        else:
            query = "SELECT %(ds)s.doc, %(dsa)s.doc FROM %(dsa)s, %(ds)s WHERE retired<>true AND %(dsa)s.s=%(ds)s.id " % table_names
        query_args = dict(o=object_id, st=subject_type, p=predicate)

        query_clause = "AND o=%(o)s"
        if predicate:
            query_clause += " AND p=%(p)s"
            if subject_type:
                query_clause += " AND st=%(st)s"

        query_clause = self._add_access_filter(access_args, qual_ds_name, query_clause, query_args)
        extra_clause = view_args.get("extra_clause", "")
        with self.pool.cursor(**self.cursor_args) as cur:
            cur.execute(query + query_clause + extra_clause, query_args)
            rows = cur.fetchall()

        obj_assocs = [self._persistence_dict_to_ion_object(row[-1]) for row in rows]
        #log.debug("find_subjects() found %s subjects", len(obj_assocs))
        if id_only:
            res_ids = [self._prep_id(row[0]) for row in rows]
            return res_ids, obj_assocs
        else:
            res_objs = [self._persistence_dict_to_ion_object(row[0]) for row in rows]
            return res_objs, obj_assocs

    def find_associations(self, subject=None, predicate=None, obj=None, assoc_type=None, id_only=True,
                          anyside=None, query=None, **kwargs):
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if not (subject or obj or predicate or anyside or query):
            raise BadRequest("Illegal parameters: No S/P/O or anyside")
        if anyside and (subject or obj):
            raise BadRequest("Illegal parameters: anyside cannot be combined with S/O")
        if anyside and predicate and type(anyside) in (list, tuple):
            raise BadRequest("Illegal parameters: anyside list cannot be combined with P")

        if query:
            query["query_args"]["id_only"] = id_only
            query["query_args"]["ds_sub"] = "assoc"
            # TODO: filter out retired
            return self.find_by_query(query)

        subject_id, object_id, anyside_ids = None, None, None
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

        #log.debug("find_associations(subject=%s, predicate=%s, object=%s, anyside=%s)", subject_id, predicate, object_id, anyside_ids)

        qual_ds_name = self._get_datastore_name()
        table = qual_ds_name + "_assoc"
        view_args = self._get_view_args(kwargs)

        if id_only:
            query = "SELECT id FROM " + table
        else:
            query = "SELECT id, doc, s, st, p, o, ot FROM " + table
        query_clause = " WHERE retired<>true AND "
        query_args = dict(s=subject_id, o=object_id, p=predicate)

        if subject and obj:
            query_clause += "s=%(s)s AND o=%(o)s"
            if predicate:
                query_clause += " AND p=%(p)s"
        elif subject:
            query_clause += "s=%(s)s"
            if predicate:
                query_clause += " AND p=%(p)s"
        elif obj:
            query_clause += "o=%(o)s"
            if predicate:
                query_clause += " AND p=%(p)s"
        elif anyside:
            if predicate:
                query_clause += "p=%(p)s AND (s=%(any)s OR o=%(any)s)"
                query_args["any"] = anyside
            elif type(anyside_ids[0]) is str:
                # keys are IDs of resources
                for i, key in enumerate(anyside_ids):
                    if i > 0:
                        query_clause += " OR "
                    argname = "id%s" % i
                    query_args[argname] = key
                    query_clause += "(s=%("+argname+")s OR o=%("+argname+")s)"
            else:
                # keys are tuples of (id, pred)
                for i, (key, pred) in enumerate(anyside_ids):
                    if i > 0:
                        query_clause += " OR "
                    argname_id = "id%s" % i
                    argname_p = "p%s" % i
                    query_args[argname_id] = key
                    query_args[argname_p] = pred
                    query_clause += "(p=%("+argname_p+")s AND (s=%("+argname_id+")s OR o=%("+argname_id+")s))"

        elif predicate:
            if predicate == "*":
                query_clause += "p is not null"
            else:
                query_clause += "p=%(p)s"
        else:
            raise BadRequest("Illegal arguments")

        extra_clause = view_args.get("extra_clause", "")
        sql = query + query_clause + extra_clause
        #print "find_associations(): SQL=", sql, query_args
        with self.pool.cursor(**self.cursor_args) as cur:
            cur.execute(sql, query_args)
            rows = cur.fetchall()

        if id_only:
            assocs = [self._prep_id(row[0]) for row in rows]
        else:
            assocs = [self._persistence_dict_to_ion_object(row[1]) for row in rows]
        #log.debug("find_associations() found %s associations", len(assocs))

        return assocs

    def _prepare_find_return(self, rows, res_assocs=None, id_only=True, **kwargs):
        if id_only:
            res_ids = [self._prep_id(row[0]) for row in rows]
            return res_ids, res_assocs
        else:
            res_docs = [self._persistence_dict_to_ion_object(row[-1]) for row in rows]
            return res_docs, res_assocs

    def _add_access_filter(self, view_args, tablename, query_clause, query_args, add_where=True):
        """Returns a Postgres SQL filter clause and referenced values for resource queries filtered
        by resource visibility and current actor role/facility membership/superuser status"""
        view_args = view_args if view_args is not None else {}
        current_actor_id = view_args.get("current_actor_id", None)
        superuser_actor_ids = view_args.get("superuser_actor_ids", None) or []

        access_filter = ""
        access_args = {}
        access_args["current_actor_id"] = current_actor_id
        assoc_tablename = tablename + "_assoc"
        if current_actor_id in superuser_actor_ids:
            # Current user is a superuser - no additional filter
            pass
        elif current_actor_id and current_actor_id != "anonymous":
            # Registered actor
            # - Return all PUBLIC, REGISTERED
            access_filter += tablename + ".visibility NOT IN (3,4)"  # 1, 2, null and other values
            # - Return all owned by user independent of visibility
            access_filter += " OR (" + tablename + ".id IN (SELECT s FROM " + assoc_tablename + \
                             " WHERE p='hasOwner' AND o=%(current_actor_id)s))"
            # - Return all FACILITY if user is in same facility
            access_filter += " OR (" + tablename + ".visibility=3 AND " + tablename + ".id IN (SELECT o FROM " + assoc_tablename + \
                             " WHERE p='hasResource' AND st='Org' AND s IN (SELECT s FROM " + assoc_tablename + \
                             " WHERE p='hasMembership' AND st='Org' AND o=%(current_actor_id)s)))"
        else:
            # Anonymous access
            # All public resources
            access_filter += tablename + ".visibility NOT IN (2,3,4)"

        if query_clause and access_filter:
            query_clause += " AND (" + access_filter + ")"
        elif not query_clause and access_filter:
            if add_where:
                query_clause = " WHERE " + access_filter
            else:
                query_clause = access_filter

        query_args.update(access_args)
        return query_clause

    def _add_deleted_filter(self, tablename, ds_sub, query_clause, query_args, show_all=False):
        if show_all:
            return query_clause
        deleted_filter = ""
        if not ds_sub:
            deleted_filter = tablename + ".lcstate<>'DELETED'"
        elif ds_sub == "assoc":
            deleted_filter = tablename + ".retired<>true"
        if query_clause and deleted_filter:
            query_clause += " AND " + deleted_filter
        elif not query_clause and deleted_filter:
            query_clause = deleted_filter
        return query_clause

    def find_resources(self, restype="", lcstate="", name="", id_only=True, access_args=None):
        return self.find_resources_ext(restype=restype, lcstate=lcstate, name=name, id_only=id_only, access_args=access_args)

    def find_resources_ext(self, restype="", lcstate="", name="",
                           keyword=None, nested_type=None,
                           attr_name=None, attr_value=None, alt_id=None, alt_id_ns=None,
                           limit=None, skip=None, descending=None, id_only=True, query=None, access_args=None):
        filter_kwargs = self._get_view_args(dict(limit=limit, skip=skip, descending=descending), access_args)
        if query:
            qargs = query["query_args"]
            if id_only is not None:
                qargs["id_only"] = id_only
            if limit is not None and limit != 0:
                qargs["limit"] = limit
            if skip is not None and skip != 0:
                qargs["skip"] = skip
            return self.find_by_query(query, access_args=access_args)
        elif name:
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
        qual_ds_name = self._get_datastore_name()
        if id_only:
            query = "SELECT id, name, type_, lcstate FROM " + qual_ds_name
        else:
            query = "SELECT id, name, type_, lcstate, doc FROM " + qual_ds_name
        query_clause = " WHERE lcstate<>'DELETED' "
        query_args = dict(type_=restype, lcstate=lcstate)

        if restype:
            query_clause += "AND type_=%(type_)s"
        else:
            # Returns ALL documents, only limited by filter
            query_clause = ""

        query_clause = self._add_access_filter(filter, qual_ds_name, query_clause, query_args)
        extra_clause = filter.get("extra_clause", "")
        with self.pool.cursor(**self.cursor_args) as cur:
            cur.execute(query + query_clause + extra_clause, query_args)
            rows = cur.fetchall()

        res_assocs = [dict(id=self._prep_id(row[0]), name=row[1], type=row[2]) for row in rows]
        log.debug("find_res_by_type() found %s objects", len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_lcstate(self, lcstate, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_lcstate(lcstate=%s, restype=%s)", lcstate, restype)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        if '_' in lcstate:
            log.warn("Search for compound lcstate restricted to maturity: %s", lcstate)
            lcstate,_ = lcstate.split("_", 1)
        filter = filter if filter is not None else {}
        qual_ds_name = self._get_datastore_name()
        if id_only:
            query = "SELECT id, name, type_, lcstate, availability FROM " + qual_ds_name
        else:
            query = "SELECT id, name, type_, lcstate, availability, doc FROM " + qual_ds_name
        query_clause = " WHERE "
        query_args = dict(type_=restype, lcstate=lcstate)

        is_maturity = lcstate not in AvailabilityStates
        if is_maturity:
            query_clause += "lcstate=%(lcstate)s"
        else:
            query_clause += "availability=%(lcstate)s"

        if restype:
            query_clause += " AND type_=%(type_)s"

        query_clause = self._add_access_filter(filter, qual_ds_name, query_clause, query_args)
        extra_clause = filter.get("extra_clause", "")
        with self.pool.cursor(**self.cursor_args) as cur:
            cur.execute(query + query_clause + extra_clause, query_args)
            rows = cur.fetchall()

        res_assocs = [dict(id=self._prep_id(row[0]), name=row[1], type=row[2], lcstate=row[3] if is_maturity else row[4]) for row in rows]
        log.debug("find_res_by_lcstate() found %s objects", len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_name(self, name, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_name(name=%s, restype=%s)", name, restype)
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        qual_ds_name = self._get_datastore_name()
        if id_only:
            query = "SELECT id, name, type_ FROM " + qual_ds_name
        else:
            query = "SELECT id, name, type_, doc FROM " + qual_ds_name
        query_clause = " WHERE lcstate<>'DELETED' "
        query_args = dict(name=name, type_=restype)

        query_clause += "AND name=%(name)s"
        if restype:
            query_clause += " AND type_=%(type_)s"

        query_clause = self._add_access_filter(filter, qual_ds_name, query_clause, query_args)
        extra_clause = filter.get("extra_clause", "")
        with self.pool.cursor(**self.cursor_args) as cur:
            cur.execute(query + query_clause + extra_clause, query_args)
            rows = cur.fetchall()

        res_assocs = [dict(id=self._prep_id(row[0]), name=row[1], type=row[2]) for row in rows]
        log.debug("find_res_by_name() found %s objects", len(res_assocs))

        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_keyword(self, keyword, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_keyword(keyword=%s, restype=%s)", keyword, restype)
        if not keyword or type(keyword) is not str:
            raise BadRequest('Argument keyword illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        qual_ds_name = self._get_datastore_name()
        if id_only:
            query = "SELECT id, type_ FROM " + qual_ds_name
        else:
            query = "SELECT id, type_, doc FROM " + qual_ds_name
        query_clause = " WHERE lcstate<>'DELETED' "
        query_args = dict(type_=restype, kw=[keyword])

        query_clause += "AND %(kw)s <@ json_keywords(doc)"
        if restype:
            query_clause += " AND type_=%(type_)s"

        query_clause = self._add_access_filter(filter, qual_ds_name, query_clause, query_args)
        extra_clause = filter.get("extra_clause", "")
        with self.pool.cursor(**self.cursor_args) as cur:
            cur.execute(query + query_clause + extra_clause, query_args)
            rows = cur.fetchall()

        res_assocs = [dict(id=self._prep_id(row[0]), type=row[1], keyword=keyword) for row in rows]
        log.debug("find_res_by_keyword() found %s objects", len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_nested_type(self, nested_type, restype=None, id_only=False, filter=None):
        log.debug("find_res_by_nested_type(nested_type=%s, restype=%s)", nested_type, restype)
        if not nested_type or type(nested_type) is not str:
            raise BadRequest('Argument nested_type illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        qual_ds_name = self._get_datastore_name()
        if id_only:
            query = "SELECT id, type_ FROM " + qual_ds_name
        else:
            query = "SELECT id, type_, doc FROM " + qual_ds_name
        query_clause = " WHERE lcstate<>'DELETED' "
        query_args = dict(type_=restype, nest=[nested_type])

        query_clause += "AND %(nest)s <@ json_nested(doc)"
        if restype:
            query_clause += " AND type_=%(type_)s"

        query_clause = self._add_access_filter(filter, qual_ds_name, query_clause, query_args)
        extra_clause = filter.get("extra_clause", "")
        with self.pool.cursor(**self.cursor_args) as cur:
            cur.execute(query + query_clause + extra_clause, query_args)
            rows = cur.fetchall()

        res_assocs = [dict(id=self._prep_id(row[0]), type=row[1], nested_type=nested_type) for row in rows]
        log.debug("find_res_by_nested_type() found %s objects", len(res_assocs))
        return self._prepare_find_return(rows, res_assocs, id_only=id_only)

    def find_res_by_attribute(self, restype, attr_name, attr_value=None, id_only=False, filter=None):
        log.debug("find_res_by_attribute(restype=%s, attr_name=%s, attr_value=%s)", restype, attr_name, attr_value)
        if not attr_name or type(attr_name) is not str:
            raise BadRequest('Argument attr_name illegal')
        if type(id_only) is not bool:
            raise BadRequest('id_only must be type bool, not %s' % type(id_only))
        filter = filter if filter is not None else {}
        qual_ds_name = self._get_datastore_name()
        if id_only:
            query = "SELECT id, type_, json_specialattr(doc) FROM " + qual_ds_name
        else:
            query = "SELECT id, type_, json_specialattr(doc), doc FROM " + qual_ds_name
        query_clause = " WHERE lcstate<>'DELETED' "
        query_args = dict(type_=restype, att=attr_name, val=attr_value)

        if attr_value:  # Note: cannot make None test here (and allow empty string because of default service args "")
            query_clause += "AND json_specialattr(doc)=%(spc)s"
            query_args['spc'] = "%s=%s" % (attr_name, attr_value)
        else:
            query_clause += "AND json_specialattr(doc) LIKE %(spc)s"
            query_args['spc'] = "%s=%%" % (attr_name, )
        if restype:
            query_clause += " AND type_=%(type_)s"

        query_clause = self._add_access_filter(filter, qual_ds_name, query_clause, query_args)
        extra_clause = filter.get("extra_clause", "")
        with self.pool.cursor(**self.cursor_args) as cur:
            cur.execute(query + query_clause + extra_clause, query_args)
            rows = cur.fetchall()

        res_assocs = [dict(id=self._prep_id(row[0]), type=row[1], attr_name=attr_name, attr_value=row[2].split("=",1)[-1]) for row in rows]
        log.debug("find_res_by_attribute() found %s objects", len(res_assocs))
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
        qual_ds_name = self._get_datastore_name()

        query = "SELECT id, type_, doc FROM " + qual_ds_name
        query_args = dict(aid=[alt_id], ans=[alt_id_ns])
        query_clause = " WHERE lcstate<>'DELETED' "

        if not alt_id and not alt_id_ns:
            query_clause += "AND json_altids_ns(doc) is not null"
        elif alt_id and not alt_id_ns:
            query_clause += "AND %(aid)s <@ json_altids_id(doc)"
        elif alt_id_ns and not alt_id:
            query_clause += "AND %(ans)s <@ json_altids_ns(doc)"
        else:
            query_clause += "AND %(aid)s <@ json_altids_id(doc) AND %(ans)s <@ json_altids_ns(doc)"

        query_clause = self._add_access_filter(filter, qual_ds_name, query_clause, query_args)
        extra_clause = filter.get("extra_clause", "")
        with self.pool.cursor(**self.cursor_args) as cur:
            cur.execute(query + query_clause + extra_clause, query_args)
            rows = cur.fetchall()

        # Need to fake the return format of the Couch view for alt_ids. One record per alt_id, not one per resource.
        res_assocs = []
        res_rows = []
        for row in rows:
            doc_id = self._prep_id(row[0])
            doc = row[-1]
            for aid in doc.get("alt_ids", []):
                aid_parts = aid.split(":", 1)
                aid_ns = aid_parts[0] if len(aid_parts)>1 else "_"
                aid_id = aid_parts[-1]
                if alt_id_ns and alt_id:
                    if alt_id_ns == aid_ns and alt_id == aid_id:
                        res_assocs.append(dict(id=doc_id, alt_id_ns=aid_ns, alt_id=aid_id))
                        res_rows.append((doc_id, doc))
                elif (not alt_id_ns and not alt_id) or (alt_id_ns and alt_id_ns == aid_ns) or (alt_id and alt_id == aid_id):
                    res_assocs.append(dict(id=doc_id, alt_id_ns=aid_ns, alt_id=aid_id))
                    res_rows.append((doc_id, doc))

        log.debug("find_res_by_alternative_id() found %s objects", len(res_assocs))
        return self._prepare_find_return(res_rows, res_assocs, id_only=id_only)

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

    def find_by_query(self, query, access_args=None):
        """
        Find resources given a datastore query expression dict.
        @param query  a dict representation of a datastore query
        @retval  list of resource ids or resource objects matching query (dependent on id_only value)
        """
        qual_ds_name = self._get_datastore_name()

        pqb = PostgresQueryBuilder(query, qual_ds_name)
        if self.profile == DataStore.DS_PROFILE.RESOURCES and not query["query_args"].get("ds_sub", None):
            pqb.where = self._add_access_filter(access_args, qual_ds_name, pqb.where, pqb.values, add_where=False)

        if self.profile == DataStore.DS_PROFILE.RESOURCES:
            pqb.where = self._add_deleted_filter(pqb.basetable, query["query_args"].get("ds_sub", None),
                                                 pqb.where, pqb.values,
                                                 show_all=query["query_args"].get("show_all", False))

        with self.pool.cursor(**self.cursor_args) as cur:
            exec_query = pqb.get_query()
            cur.execute(pqb.get_query(), pqb.get_values())
            rows = cur.fetchall()
            log.info("find_by_query() QUERY: %s (%s rows)", cur.query, cur.rowcount)
            query_res = {}
            query["_result"] = query_res
            query_res["statement_gen"] = exec_query
            query_res["statement_sql"] = cur.query
            query_res["rowcount"] = cur.rowcount

        id_only = query["query_args"].get("id_only", True)
        if id_only:
            res_ids = [self._prep_id(row[0]) for row in rows]
            return res_ids
        else:
            res_docs = [self._persistence_dict_to_ion_object(row[-1]) for row in rows]
            return res_docs


    # -------------------------------------------------------------------------
    # Internal operations

    def _ion_object_to_persistence_dict(self, ion_object):
        if ion_object is None:
            return None

        obj_dict = self._io_serializer.serialize(ion_object, update_version=True)
        return obj_dict

    def _persistence_dict_to_ion_object(self, obj_dict):
        if obj_dict is None:
            return None

        ion_object = self._io_deserializer.deserialize(obj_dict)
        return ion_object
