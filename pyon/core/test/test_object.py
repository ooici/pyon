#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from pyon.core.object import IonObjectRegistry
from pyon.core.bootstrap import IonObject
from pyon.test.pyontest import PyonTestCase

import os
import datetime

class ObjectTest(PyonTestCase):
    def setUp(self):
        # TODO: Change the hacky hardcoded path once we have path management
        self.registry = IonObjectRegistry()
        path = os.path.join('obj', 'data', 'sample.yml')
        defs_yaml = open(path, 'r').read()
        self.registry.register_yaml(defs_yaml)

    def test_new(self):
        obj = self.registry.new('SampleObject')

        sample_type = self.registry.type_by_name['SampleObject']
        sample_def = sample_type.latest_def
        obj = self.registry.new(sample_def)
        obj = self.registry.new(sample_def.hash)
        obj = self.registry.new(sample_def.type.name)
        
        self.assertEqual(obj.name, '')
        self.assertEqual(obj.time, datetime.datetime(2011, 7, 27, 2, 59, 43, 100000))

    def test_validate(self):
        obj = self.registry.new('SampleObject')
        self.name = 'monkey'
        self.int = 1
        obj._validate()

        obj.name = 3
        self.assertRaises(AttributeError, obj._validate)

        obj.name = 'monkey'
        obj.extra_field = 5
        
        self.assertRaises(AttributeError, obj._validate)

    def test_bootstrap(self):
        """ Use the factory and singleton from bootstrap.py/public.py """
        obj = IonObject('SampleObject')
        self.assertEqual(obj.name, '')
