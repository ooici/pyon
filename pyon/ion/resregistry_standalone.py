#!/usr/bin/env python

__author__ = 'Michael Meisinger'

from pyon.core.exception import NotFound, BadRequest
from pyon.datastore.datastore_common import DatastoreFactory, DataStore
from pyon.ion.identifier import create_unique_resource_id, create_unique_association_id
from pyon.util.containers import get_ion_ts, get_default_sysname, get_safe


class ResourceRegistryStandalone(object):
    """
    Resource Registry service standalone class
    """
    def __init__(self, sysname=None, orgname=None, config=None):
        self.orgname = orgname or get_safe(config, 'system.root_org', 'ION')
        sysname = sysname or get_default_sysname()
        self.datastore_name = "resources"
        self.datastore = DatastoreFactory.get_datastore(datastore_name=self.datastore_name, config=config,
                                                        scope=sysname, profile=DataStore.DS_PROFILE.RESOURCES,
                                                        variant=DatastoreFactory.DS_BASE)

    def close(self):
        self.datastore.close()
        self.datastore = None

    def create(self, object=None, actor_id=None, lcstate=None):
        if object is None:
            raise BadRequest("Object not present")
        if not "type_" in object:
            raise BadRequest("Object is not an IonObject")
        cur_time = get_ion_ts()
        object['lcstate'] =  lcstate or "DEPLOYED"
        object['availability'] =  lcstate or "AVAILABLE"
        object['visibility'] = object.get('visibility', 1)
        object['ts_created'] = cur_time
        object['ts_updated'] = cur_time
        new_res_id = create_unique_resource_id()
        res_id, rev = self.datastore.create_doc(object, new_res_id)

        if actor_id and actor_id != 'anonymous':
            self.create_association(res_id, "hasOwner", actor_id)

        return res_id, rev

    def create_mult(self, res_list, lcstate=None):
        cur_time = get_ion_ts()
        for resobj in res_list:
            resobj['lcstate'] = lcstate or "DEPLOYED"
            resobj['availability'] = lcstate or "AVAILABLE"
            resobj['visibility'] = resobj.get('visibility', 1)
            resobj['ts_created'] = cur_time
            resobj['ts_updated'] = cur_time

        id_list = [create_unique_resource_id() for i in xrange(len(res_list))]
        res = self.datastore.create_doc_mult(res_list, id_list)
        res_list = [(rid,rrv) for success,rid,rrv in res]

        return res_list

    def read(self, object_id='', rev_id=''):
        if not object_id:
            raise BadRequest("The object_id parameter is an empty string")

        return self.datastore.read_doc(object_id, rev_id)

    def read_mult(self, object_ids=None):
        if object_ids is None:
            raise BadRequest("The object_ids parameter is empty")
        return self.datastore.read_doc_mult(object_ids)

    def create_association(self, subject=None, predicate=None, object=None, assoc_type=None):
        """
        Create an association between two IonObjects with a given predicate
        """
        if not subject or not predicate or not object:
            raise BadRequest("Association must have all elements set")
        if type(subject) is str:
            subject_id = subject
            subject = self.read(subject_id)
        else:
            if "_id" not in subject:
                raise BadRequest("Subject id not available")
            subject_id = subject._id
        st = subject.type_

        if type(object) is str:
            object_id = object
            object = self.read(object_id)
        else:
            if "_id" not in object:
                raise BadRequest("Object id not available")
            object_id = object._id
        ot = object.type_

        # Check that subject and object type are permitted by association definition
        # Note: Need import here, so that import orders are not screwed up
        from pyon.core.registry import getextends
        from pyon.ion.resource import Predicates
        from pyon.core.bootstrap import IonObject

        assoc = dict(type_="Association",
            s=subject_id, st=st,
            p=predicate,
            o=object_id, ot=ot,
            ts=get_ion_ts())
        return self.datastore.create_doc(assoc, create_unique_association_id())

    def find_by_type(self, restype, id_only=False, **kwargs):
        start_key = [restype]
        end_key = [restype]
        res = self.datastore.find_docs_by_view('resource', 'by_type',
            start_key=start_key, end_key=end_key, id_only=id_only, **kwargs)

        if id_only:
            match = [docid for docid, indexkey, doc in res]
        else:
            match = [doc for docid, indexkey, doc in res]
        return match
