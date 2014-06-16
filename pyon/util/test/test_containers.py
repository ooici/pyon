#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'


import copy
from nose.plugins.attrib import attr

from pyon.util.containers import DotDict, create_unique_identifier, make_json, is_valid_identifier, is_basic_identifier, NORMAL_VALID, is_valid_ts, get_ion_ts, dict_merge, DictDiffer
from pyon.util.containers import DICT_LOCKING_ATTR
from pyon.util.int_test import IonIntegrationTestCase

@attr('UNIT', group='util')
class Test_Containers(IonIntegrationTestCase):

    def test_dot_dict(self):
        dotDict = DotDict({"foo": {"bar": {"bah": "fah"}}})
        val = dotDict.foo.bar.bah
        self.assertEqual(val, "fah")
        dotDict.a = "1"
        self.assertEqual(dotDict.a, "1")
        self.assertTrue('a' in dotDict)

    def test_dot_dict_constant(self):
        d = DotDict({"foo": "bar"})
        self.assertEqual("bar", d.foo)
        d.foo = "somethingnew"
        self.assertEqual("somethingnew", d.foo)

        # DotDict only checks that an assignment operation is happening when it creates dummy entries
        # ... it doesn't check that the dummy entry is on the left hand side of the assignment
        k = d.foo1
        self.assertIn("foo1", dir(d))

        d.lock()

        # test assigning directly to a locked dict
        with self.assertRaises(AttributeError):
            d.foo = "somethingelse"
        self.assertEqual("somethingnew", d.foo)

        # test dummy-creation-on-assignment loophole
        with self.assertRaises(AttributeError):
            k = d.foo2
        self.assertNotIn("foo2", dir(d))

        # test alternate dummy creation method: calling a function with it
        with self.assertRaises(AttributeError):
            k = lambda _: True
            k(d.foo3)
        self.assertNotIn("foo3", dir(d))

        self.assertNotIn(DICT_LOCKING_ATTR, dir(d))

    def test_dotdict_copy(self):
        d = DotDict({"foo": "bar"})
        d2 = copy.copy(d)
        self.assertTrue(hasattr(d2, "foo"))
        self.assertEqual("bar", d2.foo)

        # output_streams = copy(self.CFG.get_safe('process.publish_streams'))
        v = "a12345"
        CFG = DotDict()
        CFG.process.publish_streams.salinity = v
        print "CFG =", CFG
        self.assertTrue(hasattr(CFG.process.publish_streams, "salinity"))
        self.assertEqual(v, CFG.process.publish_streams.salinity)
        self.assertEqual(v, CFG.get_safe("process.publish_streams").salinity)
        self.assertEqual(v, copy.copy(CFG.get_safe("process.publish_streams")).salinity)

        output_streams = copy.copy(CFG.get_safe("process.publish_streams"))
        print "output_streams =", output_streams
        self.assertTrue(hasattr(output_streams, "salinity"))
        print "output_streams.salinity =", output_streams.salinity
        self.assertEqual(v, output_streams.salinity)

        first_stream = output_streams.popitem()
        print "first_stream =", first_stream
        self.assertEqual(v, first_stream[1])

        d.lock()
        dl = copy.copy(d)
        self.assertTrue(hasattr(dl, "foo"))
        self.assertEqual("bar", dl.foo)
        with self.assertRaises(AttributeError):
            d.foo2 = "nope"


    def test_dotdict_chaining(self):
        base = DotDict({'test':None})
        base.chained.example.provides.utility = True
        self.assertTrue(base['chained']['example']['provides']['utility'])
        base.setting = True
        self.assertTrue(base.setting)
        self.assertTrue(base['setting'])

        base.map = {'key':'value'}
        self.assertIsInstance(base.map,DotDict, '%s' % type(base.map))
        self.assertTrue(base.map.key=='value')

    def test_dotdict_error(self):
        base = DotDict()
        with self.assertRaises(AttributeError):
            test_case = base.non_existent
        with self.assertRaises(KeyError):
            base['non_existent']

    def test_dotdict_builtin_error(self):
        # Ensures that you can not override the builtin methods
        base = DotDict()
        with self.assertRaises(AttributeError):
            base.pop = 'shouldnt work'
        with self.assertRaises(AttributeError):
            base.__getitem__ = 'really shouldnt work'

        with self.assertRaises(AttributeError):
            base.another.chained.pop = 'again should not work'

    def test_dict_merge(self):
        # dict_merge(base, upd, inplace=False):
        org_dict = {"a":"str_a", "d": {"d-x": 1, "d-y": None, "d-d": {"d-d-1": 1, "d-d-2": 2}}}

        base_dict = copy.deepcopy(org_dict)
        dd = DictDiffer(base_dict, org_dict)
        self.assertTrue(len(base_dict), 2)
        self.assertTrue(len(dd.unchanged()), len(base_dict))

        # Case 1: Add new value
        delta_dict = {"c" : "NEW_C"}
        mod_dict = dict_merge(base_dict, delta_dict)
        dd = DictDiffer(base_dict, org_dict)
        self.assertTrue(len(base_dict), 2)
        self.assertTrue(len(dd.unchanged()), len(base_dict))

        dd = DictDiffer(mod_dict, org_dict)
        self.assertTrue(len(mod_dict), 3)
        self.assertTrue(len(dd.unchanged()), len(org_dict))
        self.assertTrue(dd.added(), 1)

        # Case 2: Change simple type value
        delta_dict = {"a" : 5}
        base_dict = copy.deepcopy(org_dict)
        mod_dict = dict_merge(base_dict, delta_dict)

        dd = DictDiffer(mod_dict, org_dict)
        self.assertTrue(len(mod_dict), len(org_dict))
        self.assertTrue(len(dd.unchanged()), len(org_dict)-1)
        self.assertTrue(len(dd.changed()), 1)
        self.assertTrue(mod_dict['a'], 5)

        # Case 3: Add new value on lower level
        delta_dict = {"d": {"new":"NEW_ENTRY"}}
        base_dict = copy.deepcopy(org_dict)
        mod_dict = dict_merge(base_dict, delta_dict)

        dd = DictDiffer(mod_dict, org_dict)
        self.assertTrue(len(mod_dict), len(org_dict))
        self.assertTrue(len(mod_dict['d']), len(org_dict['d']) + 1)
        self.assertTrue(mod_dict['d']['new'], "NEW_ENTRY")
        dd = DictDiffer(mod_dict['d'], org_dict['d'])
        self.assertTrue(len(dd.unchanged()), len(org_dict['d']))
        self.assertTrue(dd.added(), 1)

        #import pprint
        #pprint.pprint(base_dict)
        #pprint.pprint(mod_dict)
        #print dd.added(), dd.removed(), dd.changed(), dd.unchanged()


    def test_is_basic_identifier(self):

        self.assertFalse(is_basic_identifier('abc 123'))
        self.assertTrue(is_basic_identifier('abc_123'))

    def test_is_valid_identifier(self):
        self.assertTrue(is_valid_identifier('jhwfjff.ef. hfieo()-ffeh', NORMAL_VALID))
        self.assertFalse(is_valid_identifier('jhwfjff.ef. hfieo()-ffeh', NORMAL_VALID, ';'))

    def test_make_json(self):
        j = make_json([{'abc':123, '456': 789.0}, 456.0403, 'now is the time'])
        self.assertEqual(''.join(j.split()),''.join('''
        [
                {
                "abc": 123,
                "456": 789.0
            },
            456.0403,
            "now is the time"
        ]'''.split()))


    def test_create_unique_identifier(self):
        id = create_unique_identifier('abc123')
        self.assertIn('abc123', id)
        id = create_unique_identifier()
        self.assertNotIn('abc123', id)


    def test_is_valid_ts(self):

        #Not a string
        self.assertEqual(is_valid_ts(1332424), False)

        #Too short
        self.assertEqual(is_valid_ts('1332424'), False)

        #Not numeric
        self.assertEqual(is_valid_ts('bfd1332424'), False)

        #Neither numeric or positive
        self.assertEqual(is_valid_ts('-332424'), False)

        #Too long
        self.assertEqual(is_valid_ts('109392939394556'), False)

        #Just right
        ts = get_ion_ts()
        self.assertEqual(is_valid_ts(ts), True)

