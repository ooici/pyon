#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

import unittest

from pyon.util.containers import DictModifier, DotDict

class Test_Containers(unittest.TestCase):

    def test_dot_dict(self):
        dotDict = DotDict({"foo": {"bar": {"bah": "fah"}}})
        dotDict.foo.bar.bah
        getattr(dotDict, "foo.bar.bah")
        self.assertEqual(dotDict["foo.bar.bah"], "fah")

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
