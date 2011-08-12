from anode.datastore.mockdb.mockdb_datastore import MockDB_DataStore
from anode.datastore.couchdb.couchdb_datastore import CouchDB_DataStore

from anode.datastore.datastore import NotFoundError

import unittest

class Test_DataStores(unittest.TestCase):

    def doTestDataSource(self, data_source):

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

        # User registration documents
        user_list_doc = {
            "_id":"Registered Users",
            "type_":"RegisteredUsers",
            "UserIds":["JoeBob, BillyBob, BillyJoeBob"],
            "Admins":["JoeBob"]
        }

        user_info_doc1 = {
            "_id":"JoeBob",
            "type_":"UserInfo",
            "Name":"Joe Bob",
            "Roles":["Admin"]
        }

        personal_email_contact_doc1 = {
            "_id":"joebob@gmail.com",
            "type_":"EmailInfo",
            "userid_":"JoeBob",
            "EmailType":"personal"
        }

        work_email_contact_doc1 = {
            "_id":"jbob@mit.edu",
            "type_":"EmailInfo",
            "userid_":"JoeBob",
            "EmailType":"work"
        }

        personal_phone_contact_doc1 = {
            "_id":"555-555-5554",
            "type_":"PhoneInfo",
            "userid_":"JoeBob",
            "PhoneType":"personal"
        }

        work_phone_contact_doc1 = {
            "_id":"555-555-5555",
            "type_":"PhoneInfo",
            "userid_":"JoeBob",
            "PhoneType":"work"
        }

        user_info_doc2 = {
            "_id":"BillyBob",
            "type_":"UserInfo",
            "Name":"Billy Bob",
            "Roles":["Early Adopter"]
        }

        personal_email_contact_doc2 = {
            "_id":"billybob@gmail.com",
            "type_":"EmailInfo",
            "userid_":"BillyBob",
            "EmailType":"personal"
        }

        work_email_contact_doc2 = {
            "_id":"bbob@mit.edu",
            "type_":"EmailInfo",
            "userid_":"BillyBob",
            "EmailType":"work"
        }

        personal_phone_contact_doc2 = {
            "_id":"555-555-5553",
            "type_":"PhoneInfo",
            "userid_":"BillyBob",
            "PhoneType":"personal"
        }

        work_phone_contact_doc2 = {
            "_id":"555-555-5552",
            "type_":"PhoneInfo",
            "userid_":"BillyBob",
            "PhoneType":"work"
        }

        print "\nCreate registered users document"
        tuple1 = data_source.write_object(user_list_doc)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nCreate user info document"
        tuple1 = data_source.write_object(user_info_doc1)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nCreate user email (personal) document"
        tuple1 = data_source.write_object(personal_email_contact_doc1)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nCreate user email (work) document"
        tuple1 = data_source.write_object(work_email_contact_doc1)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nCreate user phone (personal) document"
        tuple1 = data_source.write_object(personal_phone_contact_doc1)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nCreate user phone (work) document"
        tuple1 = data_source.write_object(work_phone_contact_doc1)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nCreate user info document"
        tuple1 = data_source.write_object(user_info_doc2)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nCreate user email (personal) document"
        tuple1 = data_source.write_object(personal_email_contact_doc2)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nCreate user email (work) document"
        tuple1 = data_source.write_object(work_email_contact_doc2)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nCreate user phone (personal) document"
        tuple1 = data_source.write_object(personal_phone_contact_doc2)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nCreate user phone (work) document"
        tuple1 = data_source.write_object(work_phone_contact_doc2)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nFind all EmailInfo objects"
        res = data_source.find_objects("EmailInfo")
        print 'Query results: ' + str(res)

        print "\nFind all EmailInfo objects specifically for user 'JoeBob'"
        res = data_source.find_objects("EmailInfo", "userid_", "JoeBob")
        print 'Query results: ' + str(res)

        # Data Source definition.
        datasource_doc= {
                "_id":"USGS Choptank",
                "type_":"DataSet",
                "owner_":"JoeBob",
                "lastmodified_":"JoeBob",
                "Descrption":"<TODO>",
                "Contact Institution":"USGS NWIS",
                "Contact Name":"Joe Bob",
                "Contact Email":"jbob@mit.edu",
                "Title":"CHOPTANK RIVER NEAR GREENSBORO MD (01491000) - Instantaneous Value",
                "GeospatialCoverage":{
                    "MinLatitude":38.9971961,
                    "MaxLatitude":38.9971961,
                    "MinLongitude":-75.785804,
                    "MaxLongitude":-75.785804,
                    "UpperBound":0,"LowerBound":0,
                    "VerticalPositive":"down"
                },
                "TemporalCoverage":{
                    "MinDatetime":"2011-08-04T13:15:00Z",
                    "MaxDatetime":"2011-08-09T19:15:00Z"
                },
                "Variable":{
                        "Name":"water_height",
                        "Value":"ft"
                }
              }

        print "\nCreate object 'USGS Choptank' in data store 'my_data_source'"
        tuple1 = data_source.write_object(datasource_doc)
        print 'Write returned tuple: ' + str(tuple1)

        print "\nList all objects in data store"
        print data_source.list_objects()

        print "\nRetrieve object 'USGS Choptank' in data store"
        obj = data_source.read_object('USGS Choptank')
        print 'Returned object: ' + str(obj)

        # An update to the data source definition
        datasource_doc["Descrption"] = "USGS instantaneous vaule data for station 01491000"

        print "Doc before update 1: " + str(datasource_doc)
        print "\nUpdate object 'USGS Choptank' in data store:"
        tuple2 = data_source.write_object(datasource_doc)
        print 'Write returned tuple: ' + str(tuple2)

        print "\nList all object types in data store"
        print data_source.list_objects()

        print "\nList revisions of object 'USGS Choptank' in data store"
        res = data_source.list_object_revisions('USGS Choptank')
        print 'Versions: ' + str(res)

         # Another update to the document to fix a typo
        datasource_doc["Descrption"] = "USGS instantaneous value data for station 01491000"

        print "Doc before update 2: " + str(datasource_doc)
        print "\nUpdate object 'USGS Choptank' in data store"
        tuple3 = data_source.write_object(datasource_doc)
        print 'Write returned tuple: ' + str(tuple3)

        print "\nList all object types in data store"
        print data_source.list_objects()

        print "\nList revisions of object 'USGS Choptank' in data store"
        res = data_source.list_object_revisions('USGS Choptank')
        print 'Versions: ' + str(res)

        print "\nRetrieve version " + str(tuple1[1]) + " of object 'USGS Choptank' in data store"
        obj1 = data_source.read_object('USGS Choptank', rev_id=tuple1[1])
        print 'Returned object: ' + str(obj1)
        print 'Returned object rev: ' + str(obj1["_rev"])

        print "\nRetrieve version " + str(tuple2[1]) + " of object 'USGS Choptank' in data store"
        obj2 = data_source.read_object('USGS Choptank', rev_id=tuple2[1])
        print 'Returned object: ' + str(obj2)
        print 'Returned object rev: ' + str(obj2["_rev"])

        print "\nRetrieve version " + str(tuple3[1]) + " of object 'USGS Choptank' in data store"
        obj3 = data_source.read_object('USGS Choptank', rev_id=tuple3[1])
        print 'Returned object: ' + str(obj3)
        print 'Returned object rev: ' + str(obj3["_rev"])

        print "\nRetrieve HEAD version of object 'USGS Choptank' in data store"
        head = data_source.read_object('USGS Choptank')
        print 'Returned object: ' + str(head)
        print 'Returned object rev: ' + str(head["_rev"])

        print "\n2 Delete object 'USGS Choptank' in data store"
        ret = data_source.delete_object(head)
        print 'Delete returned: ' + str(ret)

        print "\nList all objects in data store"
        print data_source.list_objects()

        print "\nList revisions of object 'USGS Choptank' in data store"
        res = data_source.list_object_revisions('USGS Choptank')
        print 'Versions: ' + str(res)

        print "\nList info about data store"
        print data_source.info_datastore()

        print "\nDelete data store"
        print data_source.delete_datastore()

        print "\nList data store on server:"
        print data_source.list_datastores()

    def test_non_persistent(self):
        self.doTestDataSource(MockDB_DataStore(dataStoreName='my_ds'))

    def test_persistent(self):
        self.doTestDataSource(CouchDB_DataStore(dataStoreName='my_ds'))

if __name__ == "__main__":
    unittest.main()
