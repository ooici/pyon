#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from pyon.core.registry import IonObjectRegistry
from pyon.core.bootstrap import IonObject
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr

@attr('UNIT')
class ObjectTest(IonIntegrationTestCase):
    def setUp(self):
        # TODO: Change the hacky hardcoded path once we have path management
        self.registry = IonObjectRegistry()
#        path = os.path.join('obj', 'data', 'sample.yml')
#        defs_yaml = open(path, 'r').read()
#        self.registry.register_yaml(defs_yaml)

    def test_new(self):
        obj = self.registry.new('SampleObject')
        
        self.assertEqual(obj.name, '')
        self.assertEqual(obj.time, "2011-07-27T02:59:43.1Z")

    def test_validate(self):
        obj = self.registry.new('SampleObject')
        self.name = 'monkey'
        self.int = 1
        obj._validate()

        obj.name = 3
        self.assertRaises(AttributeError, obj._validate)

        obj.name = 'monkey'
        assignment_failed = False
        try:
            obj.extra_field = 5
        except AttributeError:
            assignment_failed = True
        self.assertTrue(assignment_failed)

    def test_bootstrap(self):
        """ Use the factory and singleton from bootstrap.py/public.py """
        obj = IonObject('SampleObject')
        self.assertEqual(obj.name, '')
