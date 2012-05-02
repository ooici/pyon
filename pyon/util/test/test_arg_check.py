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

    def test_validations(self):
        import pyon.util.arg_check as arg_check

        with self.assertRaises(BadRequest):
            arg_check.validate_true(False,'test')

        with self.assertRaises(BadRequest):
            arg_check.validate_equal(3,4,'test')

        with self.assertRaises(BadRequest):
            arg_check.validate_not_equal(4,4,'test')

        with self.assertRaises(BadRequest):
            arg_check.validate_false(True,'test')

        with self.assertRaises(BadRequest):
            one = list()
            two = list()
            arg_check.validate_is(one,two,'test')

        with self.assertRaises(BadRequest):
            one = list()
            two = one
            arg_check.validate_is_not(one,two,'test')

        with self.assertRaises(BadRequest):
            c = None
            arg_check.validate_is_not_none(c,'test')

        with self.assertRaises(BadRequest):
            one = list([1,3])
            two = 2
            arg_check.validate_in(two,one,'test')

        with self.assertRaises(BadRequest):
            one = list([1,2,3])
            two = 2
            arg_check.validate_not_in(two,one,'test')

        with self.assertRaises(BadRequest):
            one = list()
            arg_check.validate_is_instance(one,dict,'test')

        with self.assertRaises(BadRequest):
            one = list()
            arg_check.validate_not_is_instance(one,list,'test')

    def test_validates_success(self):
        import pyon.util.arg_check as ac
        fl = self._FakeLog()
        ac.log = fl
        try:
            ac.validate_true(False,'blah')
        except BadRequest as e:
            self.assertTrue(e.message == 'blah')

        self.assertEquals(fl.name,"pyon.util.test.test_arg_check")

