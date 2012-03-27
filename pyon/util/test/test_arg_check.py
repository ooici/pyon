#!/usr/bin/env python
'''
@author Luke Campbel <LCampbell@ASAScience.com>
@file pyon/util/test/test_arg_check.py
@date 03/27/12 14:16
@description Tests for arg_check
'''
from pyon.core.exception import BadRequest
from pyon.util.containers import DotDict

from pyon.util.unit_test import PyonTestCase
import pyon.util.arg_check as arg_check

class ArgCheckTest(PyonTestCase):

    def test_assertions(self):
        with self.assertRaises(BadRequest):
            arg_check.assertTrue(False,'test')

        with self.assertRaises(BadRequest):
            arg_check.assertEqual(3,4,'test')

        with self.assertRaises(BadRequest):
            arg_check.assertNotEqual(4,4,'test')

        with self.assertRaises(BadRequest):
            arg_check.assertFalse(True,'test')

        with self.assertRaises(BadRequest):
            one = list()
            two = list()
            arg_check.assertIs(one,two,'test')

        with self.assertRaises(BadRequest):
            one = list()
            two = one
            arg_check.assertIsNot(one,two,'test')

        with self.assertRaises(BadRequest):
            c = None
            arg_check.assertIsNotNone(c,'test')

        with self.assertRaises(BadRequest):
            one = list([1,3])
            two = 2
            arg_check.assertIn(two,one,'test')

        with self.assertRaises(BadRequest):
            one = list([1,2,3])
            two = 2
            arg_check.assertNotIn(two,one,'test')

        with self.assertRaises(BadRequest):
            one = list()
            arg_check.assertIsInstance(one,dict,'test')

        with self.assertRaises(BadRequest):
            one = list()
            arg_check.assertNotIsInstance(one,list,'test')

