#!/usr/bin/env python
## coding: utf-8
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
        self.assertEqual(obj.time, "1341269890404")

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
        
        taskable_resource = self.registry.new('TaskableResource')
        taskable_resource.name = "Fooy"
        obj.abstract_val = taskable_resource
        self.assertRaises(AttributeError, obj._validate)
        
        user_info = self.registry.new('UserInfo')
        user_info.contact.first_name = "Fooy"
        obj.abstract_val = user_info
        obj._validate

    def test_decorator_validation(self):
        #
        # Test required values
        #
        obj = IonObject('Deco_Example', {"list1": [1], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "us_phone_number": "555-555-5555"})
        # Should fail because required value not provided
        self.assertRaises(AttributeError, obj._validate)

        obj.an_important_value = {"key": "value"}

        # Should work now that we have set a value for the required field
        obj._validate

        #
        # Test collection content types validation
        #
        # List
        obj = IonObject('Deco_Example', {"list1": ["Should be a numeric type"], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})
        self.assertRaises(AttributeError, obj._validate)

        obj.list1 = [1, 2]

        # Should work now that list content has been corrected
        obj._validate
        
        # Dict
        obj = IonObject('Deco_Example', {"list1": [1], "list2": ["One element"], "dict1": {"key1": "Should be a numeric type"}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})
        # Should fail because dict value contains non-numeric value
        self.assertRaises(AttributeError, obj._validate)

        obj.dict1 = {"key1": 1}

        # Should work now that dict value content has been corrected
        obj._validate
        
        #
        # Test collection length
        #
        # List
        obj = IonObject('Deco_Example', {"list1": [1,2], "list2": [], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})
        # Should fail since list has zero length
        self.assertRaises(AttributeError, obj._validate)

        obj.list2 = ["Item 1", "Item 2"]

        # Should work new that item length of list has been corrected
        obj._validate
        
        # Dict
        obj = IonObject('Deco_Example', {"list1": [1,2], "list2": [1,2], "dict1": {"key1": 1}, "dict2": {}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})
        # Should fail since dict has zero length
        self.assertRaises(AttributeError, obj._validate)

        obj.dict2 = {"key1": 1}

        # Should work new that item length of dict has been corrected
        obj._validate

        #
        # Test numeric value range
        #
        # int
        obj = IonObject('Deco_Example', {"list1": [1,2], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "unsigned_short_int": -1, "an_important_value": "good value", "us_phone_number": "555-555-5555"})
        self.assertRaises(AttributeError, obj._validate)

        obj.unsigned_short_int = 256

        # Should work
        obj._validate

        # float
        obj = IonObject('Deco_Example', {"list1": [1,2], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "a_float": 10.11, "an_important_value": "good value", "us_phone_number": "555-555-5555"})
        self.assertRaises(AttributeError, obj._validate)

        obj.a_float = 1.234

        # Should work
        obj._validate

        #
        # Test string pattern matching
        #
        obj = IonObject('Deco_Example', {"list1": [1,2], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "5555555555"})
        self.assertRaises(AttributeError, obj._validate)

        obj.us_phone_number = "555-555-5555"

        # Should work
        obj._validate

    def test_recursive_encoding(self):
        obj = self.registry.new('SampleObject')
        a_dict = {'1':u"♣ Temporal Domain ♥",
                  u'2Ĕ':u"A test data product Ĕ ∆",
                  3:{'1':u"♣ Temporal Domain ♥", u'2Ĕ':u"A test data product Ĕ ∆",
                        4:[u"♣ Temporal Domain ♥", {u'2Ĕ':u'one', 1:u"A test data product Ĕ ∆"}]},
                  'Four': u'४',
                  u'४': 'Four',
                  6:{u'1':'Temporal Domain', u'2Ĕ':u"A test data product Ĕ ∆",
                        4:[u"♣ Temporal Domain ♥", {u'४':'one', 1:'A test data product'}]}}

        type_str = type('a string')
        type_inner_element = type(a_dict[3][4][1][1])
        type_another_element = type(a_dict[6][4][1][1])
        top_level_element = a_dict['Four']
        type_top_level_element = type(top_level_element)


        # check that the type of the innermost element is not string originally
        self.assertNotEqual(type_inner_element, type_str)
        # check that the type of the innermost element is originally str
        self.assertEqual(type('a string'), type_another_element)
        # check that the type of the innermost element is not string originally
        self.assertNotEqual(type_top_level_element, type_str)
        # check that a unicode element isn't utf-8 encoded
        self.assertNotEqual(top_level_element,'\xe0\xa5\xaa')

        # apply recursive encoding
        obj.a_dict = a_dict

        # check types of the innermost elements
        type_inner_element = type(obj.a_dict[3][4][1][1])
        type_remains_str = type(obj.a_dict[6][4][1][1])

        # check that the type of the first innermost element is now type str
        self.assertEqual(type_inner_element, type_str)
        # check that the type of the other innermost element remains str
        self.assertEqual(type_another_element, type_remains_str)

        # check that a unicode element did get utf-8 encoded
        self.assertEqual(obj.a_dict['Four'],'\xe0\xa5\xaa')



    def test_bootstrap(self):
        """ Use the factory and singleton from bootstrap.py/public.py """
        obj = IonObject('SampleObject')
        self.assertEqual(obj.name, '')
