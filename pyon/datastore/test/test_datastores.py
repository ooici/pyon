#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import obj_registry, IonObject
from pyon.core.exception import NotFound
from pyon.datastore.datastore import DataStore
from pyon.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from pyon.util.int_test import IonIntegrationTestCase
from pyon.public import RT, AT, LCS

from unittest import SkipTest

OWNER_OF = "XOWNER_OF"
HAS_A = "XHAS_A"
BASED_ON = "XBASED_ON"

class Test_DataStores(IonIntegrationTestCase):

    def test_non_persistent(self):
        self._do_test(MockDB_DataStore(datastore_name='my_ds'))
        
        self._do_test_views(MockDB_DataStore(datastore_name='my_ds'))

    def test_persistent(self):
        import socket
        try:
            self._do_test(CouchDB_DataStore(datastore_name='my_ds'))

            self._do_test_views(CouchDB_DataStore(datastore_name='my_ds'), is_persistent=True)
        except socket.error:
            raise SkipTest('Failed to connect to CouchDB')

    def _do_test(self, data_store):
        self.data_store = data_store
        self.resources = {}
        # Just in case previous run failed without cleaning up,
        # delete data store
        try:
            data_store.delete_datastore()
        except NotFound:
            pass

        # Create should succeed and report True
        self.assertTrue(data_store.create_datastore())

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

        # Construct three user info objects and assign them roles
        hvl_user_info = {
            "name": "Heitor Villa-Lobos",
            "variables": {
                "name": "Claim To Fame", "value": "Legendary Brazilian composer"
            }
        }
        hvl_user_info["roles"] = [admin_role_ooi_id]
        hvl_user_info_obj = IonObject('UserInfo', hvl_user_info)
        hvl_user_info_tuple = data_store.create(hvl_user_info_obj)
        self.assertTrue(len(hvl_user_info_tuple) == 2)

        heitor_villa_lobos_ooi_id = hvl_user_info_tuple[0]

        ats_user_info = {
            "name": "Andres Torres Segovia",
            "variables": {
                "name": "Claim To Fame", "value": "Legendary Concert Guitarist"
            }
        }
        ats_user_info["roles"] = [data_provider_role_ooi_id]
        ats_user_info_obj = IonObject('UserInfo', ats_user_info)
        ats_user_info_tuple = data_store.create(ats_user_info_obj)
        self.assertTrue(len(ats_user_info_tuple) == 2)

        pok_user_info = {
            "name": "Per-Olov Kindgren",
            "variables": {
                "name": "Claim To Fame", "value": "Composer and YouTube star"
            }
        }
        pok_user_info["roles"] = [marine_operator_role_ooi_id]
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
        self.assertTrue(user_info_obj.name == "Heitor Villa-Lobos")

        # Find role(s) for user Heitor Villa-Lobos
        res = data_store.find_by_idref([["type_", DataStore.EQUAL, "UserInfo"], DataStore.AND, ["name", DataStore.EQUAL, "Heitor Villa-Lobos"]], "roles")
        self.assertTrue(len(res) == 1)
        user_role_obj = res[0]
        self.assertTrue(user_role_obj.name == "Admin")

        # Find role association(s) for user Heitor Villa-Lobos
        res = data_store.resolve_idref(heitor_villa_lobos_ooi_id, 'roles', "")
        self.assertTrue(len(res) == 1)
        user_role_obj = res[0][2]
        self.assertTrue(user_role_obj.name == "Admin")

        # Assert Admin role association exists for user Heitor Villa-Lobos
        res = data_store.resolve_idref(heitor_villa_lobos_ooi_id, 'roles', admin_role_ooi_id)
        self.assertTrue(len(res) == 1)
        user_role_obj = res[0][2]
        self.assertTrue(user_role_obj.name == "Admin")

        # Find every subject with an association to the Admin role
        res = data_store.resolve_idref("", 'roles', admin_role_ooi_id)
        self.assertTrue(len(res) == 1)
        user_info_obj = res[0][0]
        self.assertTrue(user_info_obj.name == "Heitor Villa-Lobos")

        # Find every association involving object
        res = data_store.resolve_idref("", "", admin_role_ooi_id)
        self.assertTrue(len(res) == 1)
        user_info_obj = res[0][0]
        self.assertTrue(user_info_obj.name == "Heitor Villa-Lobos")
        predicate = res[0][1]
        self.assertTrue(predicate == "roles")

        # Find every association between the subject and object
        res = data_store.resolve_idref(heitor_villa_lobos_ooi_id, "", admin_role_ooi_id)
        self.assertTrue(len(res) == 1)
        predicate = res[0][1]
        self.assertTrue(predicate == "roles")

        # Create an Ion object with default values set (if any)
        data_set = IonObject('DataSet')
        self.assertTrue(data_set._def.type.name == 'DataSet')

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
        self.assertTrue(data_set_read_obj._def.type.name == "DataSet")
        self.assertTrue(data_set_read_obj.Description == "Real-time water data for Choptank River near Greensboro, MD")

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

        # Delete DataSet
        self.assertTrue(data_store.delete(head))

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
        self.assertTrue(data_store.delete_datastore())

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

        # Create should succeed and report True
        self.assertTrue(data_store.create_datastore())

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

        admin_user_id = self._create_resource(RT.UserIdentity, 'John Doe', description='Marine Operator', lcstate=LCS.ACTIVE)

        admin_profile_id = self._create_resource(RT.UserInfo, 'J.D. Profile', description='Profile')

        other_user_id = self._create_resource(RT.UserIdentity, 'Paul Smithy', description='Other user')

        plat1_obj_id = self._create_resource(RT.PlatformDevice, 'Buoy1', description='My Platform')

        inst1_obj_id = self._create_resource(RT.InstrumentDevice, 'CTD1', description='My Instrument')

        inst2_obj_id = self._create_resource(RT.InstrumentDevice, 'CTD2', description='Other Instrument')

        ds1_obj_id = self._create_resource(RT.DataSet, 'DS_CTD_L0', description='My Dataset CTD L0', lcstate=LCS.ACTIVE)

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
        self.assertTrue(obj_ids1a[0]._def)
        self.assertEquals(len(obj_ids1a), 3)
        self.assertEquals(len(obj_assocs1a), 3)
        self.assertEquals(set([o._id for o in obj_ids1a]), set([inst1_obj_id, ds1_obj_id, admin_profile_id]))
        self.assertEquals(set([o._def.type.name for o in obj_ids1a]), set([RT.UserInfo, RT.InstrumentDevice, RT.DataSet]))

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
        self.assertTrue(sub_ids1a[0]._def)
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

        # Find resources by type
        res_ids1, res_assoc1 = data_store.find_res_by_type(RT.UserIdentity, id_only=True)
        self.assertEquals(len(res_ids1), 2)
        self.assertEquals(len(res_assoc1), 2)
        self.assertEquals(set(res_ids1), set([admin_user_id, other_user_id]))

        res_ids1a, res_assoc1a = data_store.find_res_by_type(RT.UserIdentity, id_only=False)
        self.assertTrue(res_ids1a[0]._def)
        self.assertEquals(len(res_ids1a), 2)
        self.assertEquals(len(res_assoc1a), 2)
        self.assertEquals(set([o._id for o in res_ids1a]), set([admin_user_id, other_user_id]))
        self.assertEquals(set([o.lcstate for o in res_ids1a]), set([LCS.NEW, LCS.ACTIVE]))

        res_ids2, res_assoc2 = data_store.find_res_by_type(RT.UserIdentity, LCS.ACTIVE, id_only=True)
        self.assertEquals(len(res_ids2), 1)
        self.assertEquals(len(res_assoc2), 1)
        self.assertEquals(set(res_ids2), set([admin_user_id]))

        res_ids2n, res_assoc2n = data_store.find_res_by_type("NONE##", LCS.ACTIVE, id_only=True)
        self.assertEquals(len(res_ids2n), 0)
        self.assertEquals(len(res_assoc2n), 0)

        # Find resources by lcstate
        res_ids1, res_assoc1 = data_store.find_res_by_lcstate(LCS.ACTIVE, id_only=True)
        self.assertEquals(len(res_ids1), 2)
        self.assertEquals(len(res_assoc1), 2)
        self.assertEquals(set(res_ids1), set([admin_user_id, ds1_obj_id]))

        res_ids1a, res_assoc1a = data_store.find_res_by_lcstate(LCS.ACTIVE, id_only=False)
        self.assertTrue(res_ids1a[0]._def)
        self.assertEquals(len(res_ids1a), 2)
        self.assertEquals(len(res_assoc1a), 2)
        self.assertEquals(set([o._id for o in res_ids1a]), set([admin_user_id, ds1_obj_id]))
        self.assertEquals(set([o._def.type.name for o in res_ids1a]), set([RT.UserIdentity, RT.DataSet]))

        res_ids2, res_assoc2 = data_store.find_res_by_lcstate( LCS.ACTIVE, RT.UserIdentity, id_only=True)
        self.assertEquals(len(res_ids2), 1)
        self.assertEquals(len(res_assoc2), 1)
        self.assertEquals(set(res_ids2), set([admin_user_id]))

        res_ids2n, res_assoc2n = data_store.find_res_by_type("NONE##", "XXXXX", id_only=True)
        self.assertEquals(len(res_ids2n), 0)
        self.assertEquals(len(res_assoc2n), 0)

        # Find resources by name
        res_ids1, res_assoc1 = data_store.find_res_by_name('CTD1', id_only=True)
        self.assertEquals(len(res_ids1), 1)
        self.assertEquals(len(res_assoc1), 1)
        self.assertEquals(set(res_ids1), set([inst1_obj_id]))

        res_ids1a, res_assoc1a = data_store.find_res_by_name('CTD2', id_only=False)
        self.assertTrue(res_ids1a[0]._def)
        self.assertEquals(len(res_ids1a), 1)
        self.assertEquals(len(res_assoc1a), 1)
        self.assertEquals(set([o._id for o in res_ids1a]), set([inst2_obj_id]))
        self.assertEquals(set([o._def.type.name for o in res_ids1a]), set([RT.InstrumentDevice]))

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
        self.assertEquals(assocs[0]._def.type.name, "Association")

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
