from anode.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from anode.datastore.couchdb.couchdb_datastore import CouchDB_DataStore

from anode.datastore.datastore import NotFoundError

import unittest

from anode.core.bootstrap import AnodeObject

class Test_DataStores(unittest.TestCase):

    def doTestdata_source(self, data_source):

        print "\nDelete data store:"
        try:
            data_source.delete_datastore()
        except NotFoundError:
            pass

        print "\nCreate data store"
        data_source.create_datastore()

        print "\nList data stores on server"
        print data_source.list_datastores()

        print "\nList info about data store"
        print data_source.info_datastore()

        # Construct user role objects
        admin_role = {
            "Name":"Admin",
            "Description":"Super user"
        }
        adminRoleObj = AnodeObject('UserRole', admin_role)
        print "Creating Admin role object"
        adminRoleTuple = data_source.create(adminRoleObj)

        data_provider_role = {
            "Name":"Data Provider",
            "Description":"User allowed to ingest data sets"
        }
        dataProviderRoleObj = AnodeObject('UserRole', data_provider_role)
        print "Creating Data Provider role object"
        dataProviderRoleTuple = data_source.create(dataProviderRoleObj)

        marine_operator_role = {
            "Name":"Marine Operator",
            "Description":"User allowed to administer instruments"
        }
        marineOperatorRoleObj = AnodeObject('UserRole', marine_operator_role)
        print "Creating Marine Operator role object"
        marineOperatorRoleTuple = data_source.create(marineOperatorRoleObj)

        # Construct a couple user info objects and assign them roles
        hvl_user_info = {
            "Name": "Heitor Villa-Lobos",
            "Variables": {
                "Claim To Fame": "Legendary Brazilian composer"
            }
        }
        hvl_user_info["roles"] = [adminRoleTuple[0]]
        hvlUserInfoObj = AnodeObject('UserInfo', hvl_user_info)
        print "Creating Heitor Villa-Lobos UserInfo object"
        hvlUserInfoTuple = data_source.create(hvlUserInfoObj)

        HeitorVillaLobos_OOI_ID = hvlUserInfoTuple[0]

        ats_user_info = {
            "Name": "Andres Torres Segovia",
            "Variables": {
                "Claim To Fame": "Legendary Concert Guitarist"
            }
        }
        ats_user_info["roles"] = [dataProviderRoleTuple[0]]
        atsUserInfoObj = AnodeObject('UserInfo', ats_user_info)
        print "Creating Andres Torres Segovia UserInfo object"
        atsUserInfoTuple = data_source.create(atsUserInfoObj)

        pok_user_info = {
            "Name": "Per-Olov Kindgren",
            "Variables": {
                "Claim To Fame": "Composer and YouTube star"
            }
        }
        pok_user_info["roles"] = [marineOperatorRoleTuple[0]]
        pokUserInfoObj = AnodeObject('UserInfo', pok_user_info)
        print "Creating Per-Olov Kindgren UserInfo object"
        pokUserInfoTuple = data_source.create(pokUserInfoObj)

        print "\nFind all UserInfo objects"
        res = data_source.find("UserInfo")
        print 'Query results: ' + str(res)
        self.assertTrue(len(res) == 3)

        print "\nFind UserInfo object specifically for user 'Heitor Villa-Lobos'"
        res = data_source.find("UserInfo", "Name", "Heitor Villa-Lobos")
        print 'Query results: ' + str(res)
        self.assertTrue(len(res) == 1)
        userInfoObj = res[0]
        self.assertTrue(userInfoObj.Name == "Heitor Villa-Lobos")

        print "\nCreate a sample data set object"
        dataSet = AnodeObject('DataSet')

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

        print "Writing DataSet object"
        writeTuple1 = data_source.create(dataSet)

        DataSet_UUID = writeTuple1[0]

        dataSetReadObj = data_source.read(DataSet_UUID)
        self.assertTrue(dataSetReadObj._id == DataSet_UUID)
        self.assertTrue(dataSetReadObj.type_ == "DataSet")
        self.assertTrue(dataSetReadObj.Description == "Real-time water data for Choptank River near Greensboro, MD")

        dataSetReadObj.Description = "Updated Description"

        print "\nUpdate DataSet"
        writeTuple2 = data_source.update(dataSetReadObj)

        print "\nList all objects in data store"
        print data_source.list_objects()

        print "\nRetrieve updated DataSet"
        dataSetReadObj2 = data_source.read(DataSet_UUID)
        self.assertTrue(dataSetReadObj2._id == DataSet_UUID)
        self.assertTrue(dataSetReadObj2.Description == "Updated Description")

        print "\nList revisions of DataSet in data store"
        res = data_source.list_object_revisions(DataSet_UUID)

         # Another update to the object
        dataSetReadObj2.Description = "USGS instantaneous value data for station 01491000"

        print "\nUpdate DataSet again"
        writeTuple3 = data_source.update(dataSetReadObj2)

        print "\nList all object types in data store"
        print data_source.list_objects()

        print "\nList revisions of DataSet in data store"
        res = data_source.list_object_revisions(DataSet_UUID)
        print 'Versions: ' + str(res)

        print "\nRetrieve version " + str(writeTuple1[1]) + " of DataSet"
        obj1 = data_source.read(DataSet_UUID, rev_id=writeTuple1[1])
        self.assertTrue(obj1._id == DataSet_UUID)
        self.assertTrue(obj1.Description == "Real-time water data for Choptank River near Greensboro, MD")

        print "\nRetrieve version " + str(writeTuple2[1]) + " of DataSet"
        obj2 = data_source.read(DataSet_UUID, rev_id=writeTuple2[1])
        self.assertTrue(obj2._id == DataSet_UUID)
        self.assertTrue(obj2.Description == "Updated Description")

        print "\nRetrieve version " + str(writeTuple3[1]) + " of DataSet"
        obj3 = data_source.read(DataSet_UUID, rev_id=writeTuple3[1])
        self.assertTrue(obj3._id == DataSet_UUID)
        self.assertTrue(obj3.Description == "USGS instantaneous value data for station 01491000")

        print "\nRetrieve HEAD version of DataSet"
        head = data_source.read(DataSet_UUID)
        self.assertTrue(head._id == DataSet_UUID)
        self.assertTrue(head.Description == "USGS instantaneous value data for station 01491000")

        print "\nDelete DataSet"
        ret = data_source.delete(head)

        print "\nList all objects in data store"
        print data_source.list_objects()

        print "\nList revisions of now deleted DataSet"
        res = data_source.list_object_revisions(DataSet_UUID)
        self.assertTrue(len(res) == 0)

        print "\nList info about data store"
        print data_source.info_datastore()

        print "\nDelete data store"
        self.assertTrue(data_source.delete_datastore())

        print "\nList data store on server:"
        print data_source.list_datastores()

    def test_non_persistent(self):
        self.doTestdata_source(MockDB_DataStore(dataStoreName='my_ds'))

    def test_persistent(self):
        self.doTestdata_source(CouchDB_DataStore(dataStoreName='my_ds'))

if __name__ == "__main__":
    unittest.main()
