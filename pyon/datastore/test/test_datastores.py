#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound
from pyon.datastore.datastore import DataStore
from pyon.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from pyon.datastore.couchdb.couchdb_datastore import CouchDB_DataStore

import unittest

class Test_DataStores(unittest.TestCase):

    def _do_test(self, data_store):
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

        # Construct user role objects
        admin_role = {
            "name":"Admin",
            "description":"Super user"
        }
        admin_role_obj = IonObject('UserRole', admin_role)
        admin_role_tuple = data_store.create(admin_role_obj)
        self.assertTrue(len(admin_role_tuple) == 2)

        data_provider_role = {
            "name":"Data Provider",
            "description":"User allowed to ingest data sets"
        }
        data_provider_role_obj = IonObject('UserRole', data_provider_role)
        data_provider_role_tuple = data_store.create(data_provider_role_obj)
        self.assertTrue(len(data_provider_role_tuple) == 2)

        marine_operator_role = {
            "name":"Marine Operator",
            "description":"User allowed to administer instruments"
        }
        marine_operator_role_obj = IonObject('UserRole', marine_operator_role)
        marine_operator_role_tuple = data_store.create(marine_operator_role_obj)
        self.assertTrue(len(marine_operator_role_tuple) == 2)

        # Construct three user info objects and assign them roles
        hvl_user_info = {
            "name": "Heitor Villa-Lobos",
            "variables": {
                "name": "Claim To Fame", "value": "Legendary Brazilian composer"
            }
        }
        hvl_user_info["roles"] = [admin_role_tuple[0]]
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
        ats_user_info["roles"] = [data_provider_role_tuple[0]]
        ats_user_info_obj = IonObject('UserInfo', ats_user_info)
        ats_user_info_tuple = data_store.create(ats_user_info_obj)
        self.assertTrue(len(ats_user_info_tuple) == 2)

        pok_user_info = {
            "name": "Per-Olov Kindgren",
            "variables": {
                "name": "Claim To Fame", "value": "Composer and YouTube star"
            }
        }
        pok_user_info["roles"] = [marine_operator_role_tuple[0]]
        pok_user_info_obj = IonObject('UserInfo', pok_user_info)
        pok_user_info_tuple = data_store.create(pok_user_info_obj)
        self.assertTrue(len(pok_user_info_tuple) == 2)

        # List all objects in data store and confirm there are six docs
        res = data_store.list_objects()
        self.assertTrue(len(res) == 6)

        # Find all the UserInfo records
        res = data_store.find([("type_", "==", "UserInfo")])
        self.assertTrue(len(res) == 3)

        # Find only the UserInfo record for user Heitor Villa-Lobos
        res = data_store.find([("type_", DataStore.EQUAL, "UserInfo"), DataStore.AND, ("name", DataStore.EQUAL, "Heitor Villa-Lobos")])
        self.assertTrue(len(res) == 1)
        user_info_obj = res[0]
        self.assertTrue(user_info_obj.name == "Heitor Villa-Lobos")

        # Find role(s) for user Heitor Villa-Lobos
        res = data_store.find_by_association([("type_", DataStore.EQUAL, "UserInfo"), DataStore.AND, ("name", DataStore.EQUAL, "Heitor Villa-Lobos")], "roles")
        self.assertTrue(len(res) == 1)
        user_role_obj = res[0]
        self.assertTrue(user_role_obj.name == "Admin")

        # Create an Ion object with default values set (if any)
        data_set = IonObject('DataSet')
        self.assertTrue(data_set.type_ == 'DataSet')

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
        self.assertTrue(data_set_read_obj.type_ == "DataSet")
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
        self.assertTrue(len(res) == 6)

        # List revisions of now deleted DataSet, should be empty list
        res = data_store.list_object_revisions(data_set_uuid)
        self.assertTrue(len(res) == 0)

        # Delete data store to clean up
        self.assertTrue(data_store.delete_datastore())

        # Assert data store is now gone
        self.assertNotIn('my_ds', data_store.list_datastores())

    def test_non_persistent(self):
        self._do_test(MockDB_DataStore(datastore_name='my_ds'))

    def test_persistent(self):
        self._do_test(CouchDB_DataStore(datastore_name='my_ds'))

if __name__ == "__main__":
    unittest.main()
