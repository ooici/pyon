#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from pyon.util.containers import DictModifier, DotDict, create_unique_identifier, make_json, is_valid_identifier, is_basic_identifier, NORMAL_VALID
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr

@attr('UNIT')
class Test_Containers(IonIntegrationTestCase):

    def test_dot_dict(self):
        dotDict = DotDict({"foo": {"bar": {"bah": "fah"}}})
        val = dotDict.foo.bar.bah
        self.assertEqual(val, "fah")
        dotDict.a = "1"
        self.assertEqual(dotDict.a, "1")
        self.assertTrue('a' in dotDict)

    def test_dict_modifier(self):
        base = DotDict({"foo": "bar", "bah": "fah"})
        dict_modifier = DictModifier(base)
        self.assertEqual(dict_modifier["foo"], "bar")

        top = DotDict({"bah": "lah", "doh": "ray"})
        dict_modifier.update(top)
        saved_dict_modifier = dict_modifier
        self.assertEqual(dict_modifier["foo"], "bar")
        self.assertEqual(dict_modifier["bah"], "lah")
        self.assertEqual(dict_modifier["doh"], "ray")

        dict_modifier = DictModifier(dict_modifier)
        self.assertEqual(dict_modifier["foo"], "bar")
        self.assertEqual(dict_modifier["bah"], "lah")
        self.assertEqual(dict_modifier["doh"], "ray")
        self.assertEqual(dict_modifier.base, saved_dict_modifier)

        top = DotDict({"bah": "trah"})
        dict_modifier.update(top)
        saved_dict_modifier = dict_modifier
        self.assertEqual(dict_modifier["foo"], "bar")
        self.assertEqual(dict_modifier["bah"], "trah")
        self.assertEqual(dict_modifier["doh"], "ray")

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


if __name__ == "__main__":
    unittest.main()
