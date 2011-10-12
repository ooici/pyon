#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

import unittest

from pyon.util.containers import DictModifier, DotDict

class Test_Containers(unittest.TestCase):

    def test_dict_modifier(self):
        base = DotDict({"foo": "bar", "bah": "fah"})
        dict_modifier = DictModifier(base)
        val = dict_modifier["foo"]
        val = dict_modifier['foo']
        self.assertEqual(dict_modifier["foo"], "bar")
        top = DotDict({"bah": "lah", "doh": "ray"})
        dict_modifier.update(top)
        self.assertEqual(dict_modifier["foo"], "bar")
        self.assertEqual(dict_modifier["bah"], "lah")
        self.assertEqual(dict_modifier["doh"], "ray")

if __name__ == "__main__":
    unittest.main()
