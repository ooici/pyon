from pyon.util.int_test import IonIntegrationTestCase
from pyon.datastore.id_factory import IDFactory, SaltedTimeIDFactory
from nose.plugins.attrib import attr

@attr('UNIT', group='datastore')
class GeneratorTest(IonIntegrationTestCase):

    def test_length(self):
        subject = SaltedTimeIDFactory()
        id = subject.create_id()
        self.assertEqual(10, len(id))

        sub2 = SaltedTimeIDFactory(salt_chars=5)
        id = sub2.create_id()
        self.assertEqual(12, len(id))

    def test_increasing(self):
        subject = SaltedTimeIDFactory()
        id1 = subject.create_id()
        for n in xrange(20):
            id2 = subject.create_id()
            self.assertTrue(id2>id1, msg='%s v %s'%(id1,id2))
            id1=id2

    def test_change_salt(self):
        # use unusually large salt to make it
        # nearly impossible 2 random salts will be equal
        subject = SaltedTimeIDFactory(salt_chars=10)
        id1 = subject.create_id()
        id2 = subject.replace_duplicate()
        self.assertTrue(id1[-10:]!=id2[-10:])

