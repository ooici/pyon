#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from pyon.util.containers import DictModifier, DotDict
from pyon.test.pyontest import PyonTestCase

class Test_Containers(PyonTestCase):

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

if __name__ == "__main__":
    unittest.main()
