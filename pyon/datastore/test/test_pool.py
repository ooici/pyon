from pyon.datastore.pool import Pool
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr

@attr('UNIT', group='datastore')
class SwimTest(IonIntegrationTestCase):

    _id = 0
    def _create_object(self,name):
        self._id += 1
        return 'thing'+str(self._id)

    def test_check_out(self):
        subject = Pool('testpool',self._create_object)

        o1 = subject.check_out()
        o2 = subject.check_out()

        self.assertNotEqual(o1,o2)
        self.assertTrue(o1 in subject._used)
        self.assertFalse(o1 in subject._unused)

        subject.check_in(o1)
        self.assertFalse(o1 in subject._used)
        self.assertTrue(o1 in subject._unused)

        o3 = subject.check_out()
        self.assertEqual(o1,o3)

    def test_limit(self):
        subject = Pool('testpool',self._create_object, max_connections=3)

        # check out max
        for n in xrange(3):
            o = subject.check_out()
            self.assertTrue(o is not None)

        # should fail if try for one more
        try:
            o = subject.check_out()
            self.fail('should not checkout more than max')
        except:
            pass

        # return one, now can check out more
        subject.check_in(o)
        o2 = subject.check_out()
