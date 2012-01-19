#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import obj_registry, IonObject
from pyon.core.exception import BadRequest, NotFound
from pyon.datastore.datastore import DataStore
from pyon.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from pyon.util.int_test import IonIntegrationTestCase
from pyon.ion.resource import RT, AT, LCS
from nose.plugins.attrib import attr
from unittest import SkipTest
import socket

import interface.objects

OWNER_OF = "XOWNER_OF"
HAS_A = "XHAS_A"
BASED_ON = "XBASED_ON"

@attr('UNIT', group='datastore')
class Test_DataStores(IonIntegrationTestCase):

    def test_non_persistent(self):
        self._do_test(MockDB_DataStore(datastore_name='my_ds'))
        
        self._do_test_views(MockDB_DataStore(datastore_name='my_ds'))

    def test_persistent(self):
        import socket
        try:
            ds = CouchDB_DataStore(datastore_name='my_ds')
            self._do_test(ds)

            # CouchDB does not like upper case characters for database names
            create_failed = False
            try:
                ds.create_datastore("BadDataStoreNamePerCouchDB")
            except BadRequest:
                create_failed = True
            self.assertTrue(create_failed)

            delete_failed = False
            try:
                ds.delete_datastore("BadDataStoreNamePerCouchDB")
            except BadRequest:
                delete_failed = True
            self.assertTrue(delete_failed)

            info_failed = False
            try:
                ds.info_datastore("BadDataStoreNamePerCouchDB")
            except BadRequest:
                info_failed = True
            self.assertTrue(info_failed)

            list_objects_failed = False
            try:
                ds.list_objects("BadDataStoreNamePerCouchDB")
            except BadRequest:
                list_objects_failed = True
            self.assertTrue(list_objects_failed)

            list_object_revisions_failed = False
            try:
                ds.list_object_revisions("badid", "BadDataStoreNamePerCouchDB")
            except BadRequest:
                list_object_revisions_failed = True
            self.assertTrue(list_object_revisions_failed)

            create_failed = False
            try:
                ds.create_doc({"foo": "bar"}, "BadDataStoreNamePerCouchDB")
            except BadRequest:
                create_failed = True
            self.assertTrue(create_failed)

            create_mult_failed = False
            try:
                ds.create_doc_mult([{"foo": "bar"}], "BadDataStoreNamePerCouchDB")
            except BadRequest:
                create_mult_failed = True
            self.assertTrue(create_mult_failed)

            read_failed = False
            try:
                ds.read_doc("badid", "3", "BadDataStoreNamePerCouchDB")
            except BadRequest:
                read_failed = True
            self.assertTrue(read_failed)

            read_mult_failed = False
            try:
                ds.read_doc_mult("badid", "BadDataStoreNamePerCouchDB")
            except BadRequest:
                read_mult_failed = True
            self.assertTrue(read_mult_failed)

            update_failed = False
            try:
                ds.update_doc({"foo": "bar"}, "BadDataStoreNamePerCouchDB")
            except BadRequest:
                update_failed = True
            self.assertTrue(update_failed)

            delete_failed = False
            try:
                ds.delete_doc("badid", "BadDataStoreNamePerCouchDB")
            except BadRequest:
                delete_failed = True
            self.assertTrue(delete_failed)

            find_failed = False
            try:
                ds.find_doc([['type_', DataStore.EQUAL, 'foo']], "BadDataStoreNamePerCouchDB")
            except BadRequest:
                find_failed = True
            self.assertTrue(find_failed)

            find__by_idref_failed = False
            try:
                ds.find_by_idref_doc([['type_', DataStore.EQUAL, 'UserInfo'], DataStore.AND, ['name', DataStore.EQUAL, 'foo']], 'roles', "BadDataStoreNamePerCouchDB")
            except BadRequest:
                find__by_idref_failed = True
            self.assertTrue(find__by_idref_failed)

            resolve_idref_failed = False
            try:
                ds.resolve_idref_doc("Subject", "Predicate", "Object", "BadDataStoreNamePerCouchDB")
            except BadRequest:
                resolve_idref_failed = True
            self.assertTrue(resolve_idref_failed)

            self._do_test_views(CouchDB_DataStore(datastore_name='my_ds'), is_persistent=True)
        except socket.error:
            raise SkipTest('Failed to connect to CouchDB')

    def _do_test(self, data_store):
        self.data_store = data_store
        self.resources = {}
        # Just in case previous run failed without cleaning up,
        # delete data store
        deleteFailed = False
        try:
            data_store.delete_datastore()
        except NotFound:
            deleteFailed = True
        self.assertFalse(deleteFailed)

        # Create should succeed and not throw error
        data_store.create_datastore()

        # Create should throw exception the second time
        createFailed = False
        try:
            data_store.create_datastore()
        except BadRequest:
            createFailed = True
        self.assertTrue(createFailed)

        # Call ops with wrong object type and make sure exception is thrown
        createFailed = False
        try:
            data_store.create({"foo": "bar"})
        except BadRequest:
            createFailed = True
        self.assertTrue(createFailed)

        createMultFailed = False
        try:
            data_store.create_mult([{"foo": "bar"}])
        except BadRequest:
            createMultFailed = True
        self.assertTrue(createMultFailed)

        readFailed = False
        try:
            data_store.read({"foo": "bar"})
        except BadRequest:
            readFailed = True
        self.assertTrue(readFailed)

        readMultFailed = False
        try:
            data_store.read_mult([{"foo": "bar"}])
        except BadRequest:
            readMultFailed = True
        self.assertTrue(readMultFailed)

        updateFailed = False
        try:
            data_store.update({"foo": "bar"})
        except BadRequest:
            updateFailed = True
        self.assertTrue(updateFailed)

        deleteFailed = False
        try:
            data_store.delete({"foo": "bar"})
        except BadRequest:
            deleteFailed = True
        self.assertTrue(deleteFailed)

        # Should see new data
        self.assertIn('my_ds', data_store.list_datastores())

        # Something should be returned
        self.assertTrue(data_store.info_datastore() is not None)

        res = data_store.list_objects()
        numcoredocs = len(res)

        # Construct user role objects
        admin_role = {
            "name":"Admin",
            "description":"Super user"
        }
        admin_role_obj = IonObject('UserRole', admin_role)
        admin_role_tuple = data_store.create(admin_role_obj)
        self.assertTrue(len(admin_role_tuple) == 2)

        admin_role_ooi_id = admin_role_tuple[0]

        data_provider_role = {
            "name":"Data Provider",
            "description":"User allowed to ingest data sets"
        }
        data_provider_role_obj = IonObject('UserRole', data_provider_role)
        data_provider_role_tuple = data_store.create(data_provider_role_obj)
        self.assertTrue(len(data_provider_role_tuple) == 2)

        data_provider_role_ooi_id = data_provider_role_tuple[0]

        marine_operator_role = {
            "name":"Marine Operator",
            "description":"User allowed to administer instruments"
        }
        marine_operator_role_obj = IonObject('UserRole', marine_operator_role)
        marine_operator_role_tuple = data_store.create(marine_operator_role_obj)
        self.assertTrue(len(marine_operator_role_tuple) == 2)

        marine_operator_role_ooi_id = marine_operator_role_tuple[0]

        role_objs = data_store.read_mult([admin_role_ooi_id, data_provider_role_ooi_id, marine_operator_role_ooi_id])
            
        self.assertTrue(len(role_objs) == 3)
        self.assertTrue(role_objs[0]._id == admin_role_ooi_id)
        self.assertTrue(role_objs[1]._id == data_provider_role_ooi_id)
        self.assertTrue(role_objs[2]._id == marine_operator_role_ooi_id)

        # Construct three user info objects and assign them roles
        hvl_contact_info = {
            "name": "Heitor Villa-Lobos",
            "email": "prelude1@heitor.com",
            "variables": {
                "name": "Claim To Fame", "value": "Legendary Brazilian composer"
            }
        }
        hvl_contact_info_obj = IonObject('ContactInformation', hvl_contact_info)
        hvl_user_info = {
            "name": "Heitor Villa-Lobos",
            "contact": hvl_contact_info_obj
        }
        hvl_user_info_obj = IonObject('UserInfo', hvl_user_info)
        hvl_user_info_tuple = data_store.create(hvl_user_info_obj)
        self.assertTrue(len(hvl_user_info_tuple) == 2)

        heitor_villa_lobos_ooi_id = hvl_user_info_tuple[0]

        ats_contact_info = {
            "name": "Andres Torres Segovia",
            "email": "asturas@andres.com",
            "variables": {
                "name": "Claim To Fame", "value": "Legendary Concert Guitarist"
            }
        }
        ats_contact_info_obj = IonObject('ContactInformation', ats_contact_info)
        ats_user_info = {
            "name": "Andres Torres Segovia",
            "contact": ats_contact_info_obj
        }
        ats_user_info_obj = IonObject('UserInfo', ats_user_info)
        ats_user_info_tuple = data_store.create(ats_user_info_obj)
        self.assertTrue(len(ats_user_info_tuple) == 2)

        pok_contact_info = {
            "name": "Per-Olov Kindgren",
            "email": "etude6@per.com",
            "variables": {
                "name": "Claim To Fame", "value": "Composer and YouTube star"
            }
        }
        pok_contact_info_obj = IonObject('ContactInformation', pok_contact_info)
        pok_user_info = {
            "name": "Per-Olov Kindgren",
            "contact": pok_contact_info_obj
        }
        pok_user_info_obj = IonObject('UserInfo', pok_user_info)
        pok_user_info_tuple = data_store.create(pok_user_info_obj)
        self.assertTrue(len(pok_user_info_tuple) == 2)

        # List all objects in data store and confirm there are six docs
        res = data_store.list_objects()
        # There are indices. Therefore can't could all docs
        self.assertTrue(len(res) == 6 + numcoredocs)

        # Find all the UserInfo records
        res = data_store.find([["type_", "==", "UserInfo"]])
        self.assertTrue(len(res) == 3)

        # Find only the UserInfo record for user Heitor Villa-Lobos
        res = data_store.find([["type_", DataStore.EQUAL, "UserInfo"], DataStore.AND, ["name", DataStore.EQUAL, "Heitor Villa-Lobos"]])
        self.assertTrue(len(res) == 1)
        user_info_obj = res[0]
        self.assertTrue(user_info_obj.contact.name == "Heitor Villa-Lobos")

        # Create an Ion object with default values set (if any)
        data_set = IonObject('DataSet')
        self.assertTrue(isinstance(data_set, interface.objects.DataSet))

        # Assign values to object fields
        data_set.Description = "Real-time water data for Choptank River near Greensboro, MD"
        data_set.ContactInstitution = "USGS NWIS"
        data_set.ContactName = "Heitor Villa-Lobos"
        data_set.ContactEmail = "HeitorVillaLobos@composers.org"
        data_set.Title = "CHOPTANK RIVER NEAR GREENSBORO MD (01491000) - Instantaneous Value"
        data_set.MinLatitude = 38.9971961
        data_set.MaxLatitude = 38.9971961
        data_set.MinLongitude = -75.785804
        data_set.MaxLongitude = -75.785804
        data_set.UpperBound = 0
        data_set.LowerBound = 0
        data_set.VerticalPositive = "down"
        data_set.MinDatetime = "2011-08-04T13:15:00Z"
        data_set.MaxDatetime = "2011-08-09T19:15:00Z"
        data_set.Variables = {
                "Name":"water_height",
                "Value":"ft"
        }
        data_set.owner_ = heitor_villa_lobos_ooi_id
        data_set.lastmodified_ = heitor_villa_lobos_ooi_id

        # Write DataSet object"
        write_tuple_1 = data_store.create(data_set)
        self.assertTrue(len(write_tuple_1) == 2)

        # Save off the object UUID
        data_set_uuid = write_tuple_1[0]

        # Read back the HEAD version of the object and validate fields
        data_set_read_obj = data_store.read(data_set_uuid)
        self.assertTrue(data_set_read_obj._id == data_set_uuid)
        self.assertTrue(isinstance(data_set_read_obj, interface.objects.DataSet))
        self.assertTrue(data_set_read_obj.Description == "Real-time water data for Choptank River near Greensboro, MD")
        self.assertTrue(not 'type_' in data_set_read_obj)

        # Update DataSet's Description field and write
        data_set_read_obj.Description = "Updated Description"
        write_tuple_2 = data_store.update(data_set_read_obj)
        self.assertTrue(len(write_tuple_2) == 2)

        # Retrieve the updated DataSet
        data_set_read_obj_2 = data_store.read(data_set_uuid)
        self.assertTrue(data_set_read_obj_2._id == data_set_uuid)
        self.assertTrue(data_set_read_obj_2.Description == "Updated Description")

        # List all the revisions of DataSet in data store, should be two
        res = data_store.list_object_revisions(data_set_uuid)
        self.assertTrue(len(res) == 2)

        # Do another update to the object
        data_set_read_obj_2.Description = "USGS instantaneous value data for station 01491000"
        write_tuple_3 = data_store.update(data_set_read_obj_2)

        # List revisions of DataSet in data store, should now be three
        res = data_store.list_object_revisions(data_set_uuid)
        self.assertTrue(len(res) == 3)

        # Retrieve original version of DataSet
        obj1 = data_store.read(data_set_uuid, rev_id=write_tuple_1[1])
        self.assertTrue(obj1._id == data_set_uuid)
        self.assertTrue(obj1.Description == "Real-time water data for Choptank River near Greensboro, MD")

        # Retrieve second version of DataSet
        obj2 = data_store.read(data_set_uuid, rev_id=write_tuple_2[1])
        self.assertTrue(obj2._id == data_set_uuid)
        self.assertTrue(obj2.Description == "Updated Description")

        # Retrieve third version of DataSet
        obj3 = data_store.read(data_set_uuid, rev_id=write_tuple_3[1])
        self.assertTrue(obj3._id == data_set_uuid)
        self.assertTrue(obj3.Description == "USGS instantaneous value data for station 01491000")

        # Retrieve HEAD version of DataSet
        head = data_store.read(data_set_uuid)
        self.assertTrue(head._id == data_set_uuid)
        self.assertTrue(head.Description == "USGS instantaneous value data for station 01491000")

        # Delete DataSet by object id
        data_store.delete(head)

        # Try to re-delete DataSet by object id.  Should throw exception.
        delete_failed = False
        try:
            data_store.delete(head._id)
        except NotFound:
            delete_failed = True
        self.assertTrue(delete_failed == True)

        # List all objects in data store, should be back to six
        res = data_store.list_objects()
        self.assertTrue(len(res) == 6 + numcoredocs)

        # List revisions of now deleted DataSet, should be empty list
        res = data_store.list_object_revisions(data_set_uuid)
        self.assertTrue(len(res) == 0)

        o1 = IonObject("DataSet", name="One more")
        o2 = IonObject("DataSet", name="Another one")
        res = data_store.create_mult((o1, o2))
        self.assertTrue(all([success for success, oid, rev in res]))

        res = data_store.list_objects()
        self.assertTrue(len(res) == 8 + numcoredocs)

        # Delete data store to clean up
        data_store.delete_datastore()

        # Assert data store is now gone
        self.assertNotIn('my_ds', data_store.list_datastores())

    def _do_test_views(self, data_store, is_persistent=False):
        self.data_store = data_store
        self.resources = {}
        # Just in case previous run failed without cleaning up,
        # delete data store
        try:
            data_store.delete_datastore()
        except NotFound:
            pass

        # Create should succeed and not throw exception
        data_store.create_datastore()

        res = data_store.list_objects()
        numcoredocs = len(res)

        if is_persistent:
            self.assertTrue(numcoredocs > 1)
            data_store._update_views()

        # HACK: Both AssociationTypes so that this test works
        from pyon.ion.resource import AssociationTypes
        AssociationTypes[OWNER_OF] = dict(domain=[RT.UserIdentity], range=[RT.InstrumentDevice, RT.DataSet])
        AssociationTypes[HAS_A] = dict(domain=[RT.Resource], range=[RT.Resource])
        AssociationTypes[BASED_ON] = dict(domain=[RT.DataSet], range=[RT.DataSet])

        admin_user_id = self._create_resource(RT.UserIdentity, 'John Doe', description='Marine Operator', lcstate=LCS.AVAILABLE)

        admin_profile_id = self._create_resource(RT.UserInfo, 'J.D. Profile', description='Profile')

        other_user_id = self._create_resource(RT.UserIdentity, 'Paul Smithy', description='Other user')

        plat1_obj_id = self._create_resource(RT.PlatformDevice, 'Buoy1', description='My Platform')

        inst1_obj_id = self._create_resource(RT.InstrumentDevice, 'CTD1', description='My Instrument')

        inst2_obj_id = self._create_resource(RT.InstrumentDevice, 'CTD2', description='Other Instrument')

        ds1_obj_id = self._create_resource(RT.DataSet, 'DS_CTD_L0', description='My Dataset CTD L0', lcstate=LCS.AVAILABLE)

        ds2_obj_id = self._create_resource(RT.DataSet, 'DS_CTD_L1', description='My Dataset CTD L1')

        aid1, _ = data_store.create_association(admin_user_id, OWNER_OF, inst1_obj_id)

        data_store.create_association(admin_user_id, HAS_A, admin_profile_id)

        data_store.create_association(admin_user_id, OWNER_OF, ds1_obj_id)

        data_store.create_association(other_user_id, OWNER_OF, inst2_obj_id)

        data_store.create_association(plat1_obj_id, HAS_A, inst1_obj_id)

        data_store.create_association(inst1_obj_id, HAS_A, ds1_obj_id)

        data_store.create_association(ds1_obj_id, BASED_ON, ds1_obj_id)

        # Subject -> Object direction
        obj_ids1, obj_assocs1 = data_store.find_objects(admin_user_id, id_only=True)
        self.assertEquals(len(obj_ids1), 3)
        self.assertEquals(len(obj_assocs1), 3)
        self.assertEquals(set(obj_ids1), set([inst1_obj_id, ds1_obj_id, admin_profile_id]))

        obj_ids1n, obj_assocs1n = data_store.find_objects("Non_Existent", id_only=True)
        self.assertEquals(len(obj_ids1n), 0)
        self.assertEquals(len(obj_assocs1n), 0)

        obj_ids1a, obj_assocs1a = data_store.find_objects(admin_user_id, id_only=False)
        self.assertEquals(len(obj_ids1a), 3)
        self.assertEquals(len(obj_assocs1a), 3)
        self.assertEquals(set([o._id for o in obj_ids1a]), set([inst1_obj_id, ds1_obj_id, admin_profile_id]))
        self.assertEquals(set([type(o).__name__ for o in obj_ids1a]), set([RT.UserInfo, RT.InstrumentDevice, RT.DataSet]))

        obj_ids1an, obj_assocs1an = data_store.find_objects("Non_Existent", id_only=False)
        self.assertEquals(len(obj_ids1an), 0)
        self.assertEquals(len(obj_assocs1an), 0)

        obj_ids2, obj_assocs2 = data_store.find_objects(admin_user_id, OWNER_OF, id_only=True)
        self.assertEquals(len(obj_ids2), 2)
        self.assertEquals(len(obj_assocs2), 2)
        self.assertEquals(set(obj_ids2), set([inst1_obj_id, ds1_obj_id]))

        obj_ids3, _ = data_store.find_objects(admin_user_id, OWNER_OF, RT.InstrumentDevice, id_only=True)
        self.assertEquals(len(obj_ids3), 1)
        self.assertEquals(obj_ids3[0], inst1_obj_id)

        # Object -> Subject direction
        sub_ids1, sub_assoc1 = data_store.find_subjects(None, None, inst1_obj_id, id_only=True)
        self.assertEquals(len(sub_ids1), 2)
        self.assertEquals(len(sub_assoc1), 2)
        self.assertEquals(set(sub_ids1), set([admin_user_id, plat1_obj_id]))

        sub_ids1a, sub_assoc1a = data_store.find_subjects(None, None, inst1_obj_id, id_only=False)
        self.assertEquals(len(sub_ids1a), 2)
        self.assertEquals(len(sub_assoc1a), 2)
        self.assertEquals(set([o._id for o in sub_ids1a]), set([admin_user_id, plat1_obj_id]))

        sub_ids1an, sub_assoc1an = data_store.find_subjects(None, None, "Non_Existent", id_only=False)
        self.assertEquals(len(sub_ids1an), 0)
        self.assertEquals(len(sub_assoc1an), 0)

        sub_ids2, sub_assoc2 = data_store.find_subjects(None, OWNER_OF, inst1_obj_id, id_only=True)
        self.assertEquals(len(sub_ids2), 1)
        self.assertEquals(len(sub_assoc2), 1)
        self.assertEquals(set(sub_ids2), set([admin_user_id]))

        sub_ids3, _ = data_store.find_subjects(RT.UserIdentity, OWNER_OF, inst1_obj_id, id_only=True)
        self.assertEquals(len(sub_ids3), 1)
        self.assertEquals(set(sub_ids3), set([admin_user_id]))

        if is_persistent:
            data_store._update_views()

        # Find all resources
        res_ids1, res_assoc1 = data_store.find_res_by_type(None, None, id_only=True)
        self.assertEquals(len(res_ids1), 8)
        self.assertEquals(len(res_assoc1), 8)

        # Find resources by type
        res_ids1, res_assoc1 = data_store.find_res_by_type(RT.UserIdentity, id_only=True)
        self.assertEquals(len(res_ids1), 2)
        self.assertEquals(len(res_assoc1), 2)
        self.assertEquals(set(res_ids1), set([admin_user_id, other_user_id]))

        res_ids1a, res_assoc1a = data_store.find_res_by_type(RT.UserIdentity, id_only=False)
        self.assertEquals(len(res_ids1a), 2)
        self.assertEquals(len(res_assoc1a), 2)
        self.assertEquals(set([o._id for o in res_ids1a]), set([admin_user_id, other_user_id]))
        self.assertEquals(set([o.lcstate for o in res_ids1a]), set([LCS.DRAFT, LCS.AVAILABLE]))

        res_ids2, res_assoc2 = data_store.find_res_by_type(RT.UserIdentity, LCS.AVAILABLE, id_only=True)
        self.assertEquals(len(res_ids2), 1)
        self.assertEquals(len(res_assoc2), 1)
        self.assertEquals(set(res_ids2), set([admin_user_id]))

        res_ids2n, res_assoc2n = data_store.find_res_by_type("NONE##", LCS.AVAILABLE, id_only=True)
        self.assertEquals(len(res_ids2n), 0)
        self.assertEquals(len(res_assoc2n), 0)

        # Find resources by lcstate
        res_ids1, res_assoc1 = data_store.find_res_by_lcstate(LCS.AVAILABLE, id_only=True)
        self.assertEquals(len(res_ids1), 2)
        self.assertEquals(len(res_assoc1), 2)
        self.assertEquals(set(res_ids1), set([admin_user_id, ds1_obj_id]))

        res_ids1a, res_assoc1a = data_store.find_res_by_lcstate(LCS.AVAILABLE, id_only=False)
        self.assertEquals(len(res_ids1a), 2)
        self.assertEquals(len(res_assoc1a), 2)
        self.assertEquals(set([o._id for o in res_ids1a]), set([admin_user_id, ds1_obj_id]))
        self.assertEquals(set([type(o).__name__ for o in res_ids1a]), set([RT.UserIdentity, RT.DataSet]))

        res_ids2, res_assoc2 = data_store.find_res_by_lcstate( LCS.AVAILABLE, RT.UserIdentity, id_only=True)
        self.assertEquals(len(res_ids2), 1)
        self.assertEquals(len(res_assoc2), 1)
        self.assertEquals(set(res_ids2), set([admin_user_id]))

        res_ids2n, res_assoc2n = data_store.find_res_by_type("NONE##", "XXXXX", id_only=True)
        self.assertEquals(len(res_ids2n), 0)
        self.assertEquals(len(res_assoc2n), 0)

        # Find resources by lcstate - hierarchical
        res_ids1, res_assoc1 = data_store.find_res_by_lcstate(LCS.PUBLIC, id_only=True)
        self.assertEquals(len(res_ids1), 2)
        self.assertEquals(len(res_assoc1), 2)
        self.assertEquals(set(res_ids1), set([admin_user_id, ds1_obj_id]))

        res_ids1, res_assoc1 = data_store.find_res_by_lcstate(LCS.REGISTERED, id_only=True)
        self.assertEquals(len(res_ids1), 2)
        self.assertEquals(len(res_assoc1), 2)
        self.assertEquals(set(res_ids1), set([admin_user_id, ds1_obj_id]))

        res_ids1, res_assoc1 = data_store.find_res_by_lcstate(LCS.UNDEPLOYED, id_only=True)
        self.assertEquals(len(res_ids1), 0)
        self.assertEquals(len(res_assoc1), 0)

        # Find resources by name
        res_ids1, res_assoc1 = data_store.find_res_by_name('CTD1', id_only=True)
        self.assertEquals(len(res_ids1), 1)
        self.assertEquals(len(res_assoc1), 1)
        self.assertEquals(set(res_ids1), set([inst1_obj_id]))

        res_ids1a, res_assoc1a = data_store.find_res_by_name('CTD2', id_only=False)
        self.assertEquals(len(res_ids1a), 1)
        self.assertEquals(len(res_assoc1a), 1)
        self.assertEquals(set([o._id for o in res_ids1a]), set([inst2_obj_id]))
        self.assertEquals(set([type(o).__name__ for o in res_ids1a]), set([RT.InstrumentDevice]))

        res_ids2, res_assoc2 = data_store.find_res_by_name( 'John Doe', RT.UserIdentity, id_only=True)
        self.assertEquals(len(res_ids2), 1)
        self.assertEquals(len(res_assoc2), 1)
        self.assertEquals(set(res_ids2), set([admin_user_id]))

        res_ids2n, res_assoc2n = data_store.find_res_by_name("NONE##", "XXXXX", id_only=True)
        self.assertEquals(len(res_ids2n), 0)
        self.assertEquals(len(res_assoc2n), 0)

        # Find associations by triple
        assocs = data_store.find_associations(admin_user_id, OWNER_OF, inst1_obj_id, id_only=True)
        self.assertEquals(len(assocs), 1)
        self.assertEquals(assocs[0], aid1)

        assocs = data_store.find_associations(admin_user_id, OWNER_OF, inst1_obj_id, id_only=False)
        self.assertEquals(len(assocs), 1)
        self.assertEquals(type(assocs[0]).__name__, "Association")

        assocs = data_store.find_associations(admin_user_id, None, inst1_obj_id, id_only=True)
        self.assertEquals(len(assocs), 1)
        self.assertEquals(assocs[0], aid1)

        assocs = data_store.find_associations(None, OWNER_OF, None, id_only=True)
        self.assertEquals(len(assocs), 3)

    def _create_resource(self, restype, name, *args, **kwargs):
        res_obj = IonObject(restype, dict(name=name, **kwargs))
        res_obj_res = self.data_store.create(res_obj)
        res_obj._id = res_obj_res[0]
        self.resources[name] = res_obj
        return res_obj_res[0]


if __name__ == "__main__":
    unittest.main()
