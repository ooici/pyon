from pyon.core.bootstrap import IonObject
from pyon.datastore.representation import IonSerializerDictionaryRepresentation
from pyon.ion.resource import RT
from pyon.util.int_test import IonIntegrationTestCase
from pyon.datastore.id_factory import SaltedTimeIDFactory
from nose.plugins.attrib import attr

@attr('UNIT', group='datastore')
class RepresentationTest(IonIntegrationTestCase):

    def setUp(self):
        self.subject = IonSerializerDictionaryRepresentation(id_factory=SaltedTimeIDFactory())

    def test_encode_decode(self):
        obj = IonObject(RT.InstrumentDevice, name='SBE37IMDevice', description="SBE37IMDevice", serial_number="12345" )
        d = self.subject.encode(obj)
        print 'keys: ' + repr(d)
        self.assertFalse('_id' in d.keys())
        new_obj = self.subject.decode(d)
        self.assertEqual(obj, new_obj)
        d2 = self.subject.encode(new_obj, add_id=True)
        self.assertTrue('_id' in d2.keys(), msg=repr(d2.keys()))

        # retains key once added
        d3 = self.subject.encode(self.subject.decode(d2))
        self.assertTrue('_id' in d3.keys())

    def test_fails(self):
        d = {}
        try:
            self.subject.decode(d)
            self.fail('should not have worked')
        except:
            pass

        obj = IonObject(RT.InstrumentDevice, name='SBE37IMDevice', description="SBE37IMDevice", serial_number="12345" )
        d2 = self.subject.encode(obj)
        d2['more']='stuff'
        try:
            self.subject.decode(d2)
            self.fail('should not be able to decode')
        except:
            pass
