from pyon.core.bootstrap import IonObject
from pyon.datastore.couchdb.couch_pool import CouchDBPoolDict
from pyon.datastore.id_factory import SaltedTimeIDFactory
from pyon.datastore.repository import Repository
from pyon.ion.resource import RT
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr

@attr('INT', group='datastore')
class TestCouchStore(IonIntegrationTestCase):
    def setUp(self):
        id_factory = SaltedTimeIDFactory()
        self.pools = CouchDBPoolDict(prefix='testcouchstore'+id_factory.create_id().lower(), can_create=True, must_create=True)
        self.repo = Repository(self.pools)

    def tearDown(self):
        for pool in self.pools.values():
            try:
                db = pool.check_out()
                db.drop()
            except:
                pass

    def test_crud_obj(self):
        """ crud operations using objects where possible """
        obj = IonObject(RT.InstrumentDevice, name='SBE37IMDevice', description="SBE37IMDevice", serial_number="12345" )
        success,id,ex = self.repo.insert('sample', obj)
        self.assertTrue(success)
        self.assertFalse('_id' in obj.__dict__.keys())
        success,id,obj2 = self.repo.read('sample', id)
        self.assertTrue(success)
        for key in ['name', 'description', 'serial_number']:
            self.assertEqual(obj.__dict__[key],obj2.__dict__[key], msg='objects do not have the same '+key)

        obj2.name='new name'
        success,id,ex = self.repo.update('sample', obj2)
        self.assertTrue(success)
        success,id,obj3 = self.repo.read('sample', obj2)
        self.assertTrue(success)
        for key in ['description', 'serial_number']:
            self.assertEqual(obj.__dict__[key],obj3.__dict__[key], msg='objects do not have the same '+key)
        for key in ['_id', 'name', 'description', 'serial_number']:
            self.assertEqual(obj2.__dict__[key],obj3.__dict__[key], msg='objects do not have the same '+key)

        success,id,ex = self.repo.delete('sample', obj3)
        self.assertTrue(success)


    def test_crud_ids(self):
        """ crud operations using objects where possible """
        obj = IonObject(RT.InstrumentDevice, name='SBE37IMDevice', description="SBE37IMDevice", serial_number="12345" )
        success,id,ex = self.repo.insert('sample', obj)
        self.assertTrue(success)
        self.assertFalse('_id' in obj.__dict__.keys())
        success,id,obj2 = self.repo.read('sample', id)
        self.assertTrue(success)
        for key in ['name', 'description', 'serial_number']:
            self.assertEqual(obj.__dict__[key],obj2.__dict__[key], msg='objects do not have the same '+key)

        obj2.name='new name'
        success,id,ex = self.repo.update('sample', obj2)
        self.assertTrue(success)
        success,id,obj3 = self.repo.read('sample', id)
        self.assertTrue(success)
        for key in ['description', 'serial_number']:
            self.assertEqual(obj.__dict__[key],obj3.__dict__[key], msg='objects do not have the same '+key)
        for key in ['_id', 'name', 'description', 'serial_number']:
            self.assertEqual(obj2.__dict__[key],obj3.__dict__[key], msg='objects do not have the same '+key)

        success,id,ex = self.repo.delete('sample', id)
        self.assertTrue(success)

    def test_crud_list_obj(self):
        """ crud operations using objects where possible """
        obj1 = IonObject(RT.InstrumentDevice, name='SBE37IMDevice', description="SBE37IMDevice", serial_number="12345" )
        obj2 = IonObject(RT.Observatory, name='mount spaghetti', description='covered with snow')
        objs = [obj1,obj2]
        tuples = self.repo.insert('sample', objs)

        for t in tuples:
            self.assertTrue(t[0])
            self.assertTrue(t[1] is not None)

        ids = [ tuples[0][1], tuples[1][1], 'howdy' ]
        tuples = self.repo.read('sample', ids)
        self.assertTrue(tuples[0][0])
        self.assertTrue(tuples[1][0])
        self.assertFalse(tuples[2][0])

        obj3 = tuples[0][2]
        obj4 = tuples[1][2]
        obj3.name = 'no longer SBE'
        obj4.description = 'no more snow'
        obj1._id = 'abc123'
        objs = [ obj3, obj4, obj1 ]
        tuples = self.repo.update('sample', objs)
        self.assertTrue(tuples[0][0])
        self.assertTrue(tuples[1][0])
        self.assertFalse(tuples[2][0])

        tuples = self.repo.read('sample', objs)
        self.assertTrue(tuples[0][0])
        self.assertTrue(tuples[1][0])
        self.assertFalse(tuples[2][0])
        obj5 = tuples[0][2]
        obj6 = tuples[1][2]
        for key in ['_id', 'name', 'description', 'serial_number']:
            self.assertEqual(obj3.__dict__[key],obj5.__dict__[key], msg='objects do not have the same '+key)

        objs = [ obj4, obj5 ]  # 4 has obsolete _rev
        tuples = self.repo.delete('sample', objs)
        self.assertFalse(tuples[0][0])
        self.assertTrue(tuples[1][0], msg='failed: '+str(tuples[1][2]) +'\nobj: ' + repr(obj5.__dict__))

        objs = [ obj5, obj6 ]  # 5 is already deleted
        tuples = self.repo.delete('sample', objs)
        self.assertFalse(tuples[0][0])
        self.assertTrue(tuples[1][0], msg='failed: '+str(tuples[1][2]) +'\nobj: ' + repr(obj5.__dict__))


    def test_crud_list_ids(self):
        """ crud operations using objects where possible """
        obj1 = IonObject(RT.InstrumentDevice, name='SBE37IMDevice', description="SBE37IMDevice", serial_number="12345" )
        obj2 = IonObject(RT.Observatory, name='mount spaghetti', description='covered with snow')
        objs = [obj1,obj2]
        tuples = self.repo.insert('sample', objs)

        for t in tuples:
            self.assertTrue(t[0])
            self.assertTrue(t[1] is not None)

        ids = [ tuples[0][1], tuples[1][1], 'howdy' ]
        tuples = self.repo.read('sample', ids)
        self.assertTrue(tuples[0][0])
        self.assertTrue(tuples[1][0])
        self.assertFalse(tuples[2][0])

        obj3 = tuples[0][2]
        obj4 = tuples[1][2]
        obj3.name = 'no longer SBE'
        obj4.description = 'no more snow'
        obj1._id = 'abc123'
        objs = [ obj3, obj4, obj1 ]
        tuples = self.repo.update('sample', objs)
        self.assertTrue(tuples[0][0])
        self.assertTrue(tuples[1][0])
        self.assertFalse(tuples[2][0])

        tuples = self.repo.read('sample', ids)
        self.assertTrue(tuples[0][0])
        self.assertTrue(tuples[1][0])
        self.assertFalse(tuples[2][0])
        obj5 = tuples[0][2]
        obj6 = tuples[1][2]
        for key in ['_id', 'name', 'description', 'serial_number']:
            self.assertEqual(obj3.__dict__[key],obj5.__dict__[key], msg='objects do not have the same '+key)

        ids = [ 'badID', obj5._id ]  # 4 has obsolete _rev
        tuples = self.repo.delete('sample', ids)
        self.assertFalse(tuples[0][0])
        self.assertTrue(tuples[1][0], msg='failed: '+str(tuples[1][2]) +'\nobj: ' + repr(obj5.__dict__))

        objs = [ obj5, obj6 ]  # 5 is already deleted
        tuples = self.repo.delete('sample', [ o._id for o in objs ])
#        self.assertFalse(tuples[0][0]) -- couch will allow second delete operation!
        self.assertTrue(tuples[1][0], msg='failed: '+str(tuples[1][2]) +'\nobj: ' + repr(obj5.__dict__))

    def test_expected_errors(self):
        obj1 = IonObject(RT.InstrumentDevice, name='SBE37IMDevice', description="SBE37IMDevice", serial_number="12345")

        try:
            self.repo.insert('bad name', obj1)
            self.fail('should fail')
        except:
            pass

        try:
            self.repo.insert('sample', None)
            self.fail('should fail')
        except:
            pass

        try:
            self.repo.insert('sample', "not ion obj")
            self.fail('should fail')
        except:
            pass


        success,id,ex = self.repo.insert('sample', obj1)
        _,__,obj2 = self.repo.read('sample', id)
        try:
            success,_,__ = self.repo.insert('sample', obj2)
            self.fail('should not succeed')
        except:
            pass
        self.assertFalse(success)

