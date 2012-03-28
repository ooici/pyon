#!/usr/bin/env python
'''
@author Luke Campbel <LCampbell@ASAScience.com>
@file pyon/util/test/test_arg_check.py
@date 03/27/12 14:16
@description Tests for arg_check
'''
from pyon.core.exception import BadRequest
from pyon.util.containers import DotDict
from nose.plugins.attrib import attr

from pyon.util.unit_test import PyonTestCase

@attr('UNIT')
class ArgCheckTest(PyonTestCase):

    class _FakeLog(object):
        def __init__(self):
            self.name = ''
            self.messages = list()
        def exception(self, message, *args):
            self.messages.append(message)

    def test_assertions(self):
        import pyon.util.arg_check as arg_check

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

    def test_asserts_success(self):
        import pyon.util.arg_check as ac
        fl = self._FakeLog()
        ac.log = fl
        try:
            ac.assertTrue(False,'blah')
        except BadRequest as e:
            self.assertTrue(e.message == 'blah')

        self.assertEquals(fl.name,"pyon.util.test.test_arg_check")

