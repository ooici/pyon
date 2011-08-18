import unittest

from anode.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from anode.datastore.couchdb.couchdb_datastore import CouchDB_DataStore
from anode.datastore.datastore import NotFoundError
from anode.core.bootstrap import AnodeObject

class Test_DataStores(unittest.TestCase):

    def do_test(self, data_store):

        # Just in case previous run failed without cleaning up,
        # delete data store
        try:
            data_store.delete_datastore()
        except NotFoundError:
            pass

        # Create should succeed and report True
        self.assertTrue(data_store.create_datastore())

        # Should see new data
        self.assertIn('my_ds', data_store.list_datastores())

        # Something should be returned
        self.assertTrue(data_store.info_datastore() != None)

        # Construct user role objects
        admin_role = {
            "Name":"Admin",
            "Description":"Super user"
        }
        adminRoleObj = AnodeObject('UserRole', admin_role)
        adminRoleTuple = data_store.create(adminRoleObj)
        self.assertTrue(len(adminRoleTuple) == 2)

        data_provider_role = {
            "Name":"Data Provider",
            "Description":"User allowed to ingest data sets"
        }
        dataProviderRoleObj = AnodeObject('UserRole', data_provider_role)
        dataProviderRoleTuple = data_store.create(dataProviderRoleObj)
        self.assertTrue(len(dataProviderRoleTuple) == 2)

        marine_operator_role = {
            "Name":"Marine Operator",
            "Description":"User allowed to administer instruments"
        }
        marineOperatorRoleObj = AnodeObject('UserRole', marine_operator_role)
        marineOperatorRoleTuple = data_store.create(marineOperatorRoleObj)
        self.assertTrue(len(marineOperatorRoleTuple) == 2)

        # Construct three user info objects and assign them roles
        hvl_user_info = {
            "Name": "Heitor Villa-Lobos",
            "Variables": {
                "Claim To Fame": "Legendary Brazilian composer"
            }
        }
        hvl_user_info["roles"] = [adminRoleTuple[0]]
        hvlUserInfoObj = AnodeObject('UserInfo', hvl_user_info)
        hvlUserInfoTuple = data_store.create(hvlUserInfoObj)
        self.assertTrue(len(hvlUserInfoTuple) == 2)

        HeitorVillaLobos_OOI_ID = hvlUserInfoTuple[0]

        ats_user_info = {
            "Name": "Andres Torres Segovia",
            "Variables": {
                "Claim To Fame": "Legendary Concert Guitarist"
            }
        }
        ats_user_info["roles"] = [dataProviderRoleTuple[0]]
        atsUserInfoObj = AnodeObject('UserInfo', ats_user_info)
        atsUserInfoTuple = data_store.create(atsUserInfoObj)
        self.assertTrue(len(atsUserInfoTuple) == 2)

        pok_user_info = {
            "Name": "Per-Olov Kindgren",
            "Variables": {
                "Claim To Fame": "Composer and YouTube star"
            }
        }
        pok_user_info["roles"] = [marineOperatorRoleTuple[0]]
        pokUserInfoObj = AnodeObject('UserInfo', pok_user_info)
        pokUserInfoTuple = data_store.create(pokUserInfoObj)
        self.assertTrue(len(pokUserInfoTuple) == 2)

        # List all objects in data store and confirm there are six docs
        res = data_store.list_objects()
        self.assertTrue(len(res) == 6)

        # Find all the UserInfo records
        res = data_store.find("UserInfo")
        self.assertTrue(len(res) == 3)

        # Find only the UserInfo record for user Heitor Villa-Lobos
        res = data_store.find("UserInfo", "Name", "Heitor Villa-Lobos")
        self.assertTrue(len(res) == 1)
        userInfoObj = res[0]
        self.assertTrue(userInfoObj.Name == "Heitor Villa-Lobos")

        # Create an Anode object with default values set (if any)
        dataSet = AnodeObject('DataSet')
        self.assertTrue(dataSet.type_ == 'DataSet')

        # Assign values to object fields
        dataSet.Description = "Real-time water data for Choptank River near Greensboro, MD"
        dataSet.ContactInstitution = "USGS NWIS"
        dataSet.ContactName = "Heitor Villa-Lobos"
        dataSet.ContactEmail = "HeitorVillaLobos@composers.org"
        dataSet.Title = "CHOPTANK RIVER NEAR GREENSBORO MD (01491000) - Instantaneous Value"
        dataSet.MinLatitude = 38.9971961
        dataSet.MaxLatitude = 38.9971961
        dataSet.MinLongitude = -75.785804
        dataSet.MaxLongitude = -75.785804
        dataSet.UpperBound = 0
        dataSet.LowerBound = 0
        dataSet.VerticalPositive = "down"
        dataSet.MinDatetime = "2011-08-04T13:15:00Z"
        dataSet.MaxDatetime = "2011-08-09T19:15:00Z"
        dataSet.Variables = {
                "Name":"water_height",
                "Value":"ft"
        }
        dataSet.owner_ = HeitorVillaLobos_OOI_ID
        dataSet.lastmodified_ = HeitorVillaLobos_OOI_ID

        # Write DataSet object"
        writeTuple1 = data_store.create(dataSet)
        self.assertTrue(len(writeTuple1) == 2)

        # Save off the object UUID
        DataSet_UUID = writeTuple1[0]

        # Read back the HEAD version of the object and validate fields
        dataSetReadObj = data_store.read(DataSet_UUID)
        self.assertTrue(dataSetReadObj._id == DataSet_UUID)
        self.assertTrue(dataSetReadObj.type_ == "DataSet")
        self.assertTrue(dataSetReadObj.Description == "Real-time water data for Choptank River near Greensboro, MD")

        # Update DataSet's Description field and write
        dataSetReadObj.Description = "Updated Description"
        writeTuple2 = data_store.update(dataSetReadObj)
        self.assertTrue(len(writeTuple2) == 2)

        # Retrieve the updated DataSet
        dataSetReadObj2 = data_store.read(DataSet_UUID)
        self.assertTrue(dataSetReadObj2._id == DataSet_UUID)
        self.assertTrue(dataSetReadObj2.Description == "Updated Description")

        # List all the revisions of DataSet in data store, should be two
        res = data_store.list_object_revisions(DataSet_UUID)
        self.assertTrue(len(res) == 2)

        # Do another update to the object
        dataSetReadObj2.Description = "USGS instantaneous value data for station 01491000"
        writeTuple3 = data_store.update(dataSetReadObj2)

        # List revisions of DataSet in data store, should now be three
        res = data_store.list_object_revisions(DataSet_UUID)
        self.assertTrue(len(res) == 3)

        # Retrieve original version of DataSet
        obj1 = data_store.read(DataSet_UUID, rev_id=writeTuple1[1])
        self.assertTrue(obj1._id == DataSet_UUID)
        self.assertTrue(obj1.Description == "Real-time water data for Choptank River near Greensboro, MD")

        # Retrieve second version of DataSet
        obj2 = data_store.read(DataSet_UUID, rev_id=writeTuple2[1])
        self.assertTrue(obj2._id == DataSet_UUID)
        self.assertTrue(obj2.Description == "Updated Description")

        # Retrieve third version of DataSet
        obj3 = data_store.read(DataSet_UUID, rev_id=writeTuple3[1])
        self.assertTrue(obj3._id == DataSet_UUID)
        self.assertTrue(obj3.Description == "USGS instantaneous value data for station 01491000")

        # Retrieve HEAD version of DataSet
        head = data_store.read(DataSet_UUID)
        self.assertTrue(head._id == DataSet_UUID)
        self.assertTrue(head.Description == "USGS instantaneous value data for station 01491000")

        # Delete DataSet
        self.assertTrue(data_store.delete(head))

        # List all objects in data store, should be back to six
        res = data_store.list_objects()
        self.assertTrue(len(res) == 6)

        # List revisions of now deleted DataSet, should be empty list
        res = data_store.list_object_revisions(DataSet_UUID)
        self.assertTrue(len(res) == 0)

        # Delete data store to clean up
        self.assertTrue(data_store.delete_datastore())

        # Assert data store is now gone
        self.assertNotIn('my_ds', data_store.list_datastores())

    def test_non_persistent(self):
        self.do_test(MockDB_DataStore(dataStoreName='my_ds'))

    def test_persistent(self):
        self.do_test(CouchDB_DataStore(dataStoreName='my_ds'))

if __name__ == "__main__":
    unittest.main()
