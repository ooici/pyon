#!/usr/bin/env python
## coding: utf-8

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from pyon.core.registry import IonObjectRegistry
from pyon.core.bootstrap import IonObject
from pyon.core.object import IonObjectSerializer, IonObjectDeserializer
from pyon.core.bootstrap import get_obj_registry
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr
import unittest


@attr('UNIT')
class ObjectTest(IonIntegrationTestCase):
    def setUp(self):
        self.patch_cfg('pyon.core.bootstrap.CFG', {'container':{'objects':{'validate':{'setattr': True}}}})
        self.registry = IonObjectRegistry()

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

    def test_persisted_version(self):

        # create an initial version of SampleResource
        io_serializer = IonObjectSerializer()
        obj = IonObject('SampleResource', {'num': 9, 'other_field': 'test value'})
        obj_dict = io_serializer.serialize(obj,True)
        self.assertEquals(obj_dict['persisted_version'], 1)
        # verify that the simulated previous version does not have new_attribute
        self.assertEquals('new_attribute' in obj_dict, False)

        # simulate version increment to SampleResource that adds new_attribute
        obj_dict['type_'] = 'SampleResource_V2'
        # simulate reading the previous version after version increment
        io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
        obj = io_deserializer.deserialize(obj_dict)
        # verify that “new_attribute” is added and initialized with default value
        self.assertEquals(obj.new_attribute['key'], 'value')
        # verify that old attributes are still there and retain values
        self.assertEquals(obj.num, 9)
        # verify that old attributes are still there and retain values
        self.assertEquals(obj.other_field, 'test value')
        # verify that persisted_version is not updated at read
        self.assertEquals(obj_dict['persisted_version'], 1)

        # simulate update
        obj_dict = io_serializer.serialize(obj,True)
        # verify that version is updated
        self.assertEquals(obj_dict['persisted_version'], 2)


    def test_version_del_attrib(self):

        io_serializer = IonObjectSerializer()

        # verify that extraneous fields given while creating an IonObject raises an error.
        with self.assertRaises(AttributeError):
            IonObject('SampleResource_V2', {'num': 9, 'other_field': 'test value','more_new_attribute': {'key':'value'}})
        # simulate creating a version 2 of SampleResource that has "new_attribute"
        obj = IonObject('SampleResource_V2', {'num': 9, 'other_field': 'test value','new_attribute': {'key':'value'}})
        obj_dict = io_serializer.serialize(obj,True)
        # verify that version is 2
        self.assertEquals(obj_dict['persisted_version'], 2)
        # verify that the simulated version 2 data does have new_attribute
        self.assertEquals('new_attribute' in obj_dict, True)


        # simulate incrementing to version 3 that does not have "new_attribute"
        obj_dict['type_'] = 'SampleResource_V3'

        # simulate reading after version increment to 3
        io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
        obj = io_deserializer.deserialize(obj_dict)

        # verify that new attribute is deleted
        self.assertFalse('new_attribute' in obj)
        # verify that the simulated next version data does have more_new_attribute
        self.assertEquals(obj.another_new_attribute['key'], 'new_value')

        # verify that old attributes are still there and retain their data
        self.assertEquals(obj.num, 9)
        # verify that old attributes are still there and retain their data
        self.assertEquals(obj.other_field, 'test value')
        # verify that persisted_version is not yet updated i.e. it is still 2
        self.assertEquals(obj_dict['persisted_version'], 2)

        # simulate update
        obj_dict = io_serializer.serialize(obj,True)
        # verify that version is updated
        self.assertEquals(obj_dict['persisted_version'], 3)


    def test_event_version(self):

        io_serializer = IonObjectSerializer()
        obj = IonObject('SampleEvent', {'num': 9, 'other_field': 'test value'})
        obj_dict = io_serializer.serialize(obj,True)
        self.assertEquals(obj_dict['persisted_version'], 1)
        # simulate a previous version data of SampleEvent_V2
        obj_dict['type_'] = 'SampleEvent_V2'

        # verify that the simulated previous version data does not have new_attribute
        self.assertEquals('new_attribute' in obj_dict, False)
        # simulate reading the previous version that does not have new_attribute
        io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
        obj = io_deserializer.deserialize(obj_dict)
        # verify that new attribute is added and initialized with default value
        self.assertEquals(obj.new_attribute['key'], 'value')
        # verify that old attributes are still there
        self.assertEquals(obj.num, 9)
        # verify that old attributes are still there
        self.assertEquals(obj.other_field, 'test value')
        # verify that on read version is not yet updated
        self.assertEquals(obj_dict['persisted_version'], 1)

        # simulate create/update
        obj_dict = io_serializer.serialize(obj,True)
        # verify that version is updated
        self.assertEquals(obj_dict['persisted_version'], 2)


    def test_event_version_del_attrib(self):

        io_serializer = IonObjectSerializer()

        # verify that extraneous fields given while creating an IonObject raises an error.
        with self.assertRaises(AttributeError):
            IonObject('SampleEvent_V2', {'num': 9, 'other_field': 'test value','more_new_attribute': {'key':'value'}})

        obj = IonObject('SampleEvent_V2', {'num': 9, 'other_field': 'test value','new_attribute': {'key':'value'}})
        obj_dict = io_serializer.serialize(obj,True)
        self.assertEquals(obj_dict['persisted_version'], 2)
        # simulate a next version data of SampleEvent_V2
        obj_dict['type_'] = 'SampleEvent_V3'

        # verify that the simulated previous version data does have new_attribute
        self.assertEquals('new_attribute' in obj_dict, True)
        # simulate reading the next version that does not have new_attribute
        io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
        obj = io_deserializer.deserialize(obj_dict)

        # verify that new attribute is deleted
        self.assertFalse('new_attribute' in obj)
        # verify that the simulated next version data does have more_new_attribute
        self.assertEquals(obj.another_new_attribute['key'], 'new_value')

        # verify that old attributes are still there
        self.assertEquals(obj.num, 9)
        # verify that old attributes are still there
        self.assertEquals(obj.other_field, 'test value')
        # verify that on read version is not yet updated
        self.assertEquals(obj_dict['persisted_version'], 2)

        # simulate create/update
        obj_dict = io_serializer.serialize(obj,True)
        # verify that version is updated
        self.assertEquals(obj_dict['persisted_version'], 3)

    def test_complex_version(self):

        io_serializer = IonObjectSerializer()
        obj = IonObject('SampleComplexEvent', {'num': 9, 'other_field': 'test value'})
        obj_dict = io_serializer.serialize(obj,True)
        self.assertEquals(obj_dict['persisted_version'], 1)
        # simulate a previous version data of SampleComplexEvent_V2
        obj_dict['type_'] = 'SampleComplexEvent_V2'

        # verify that the simulated previous version data has resource
        self.assertEquals('resource' in obj_dict, True)
        # verify that the simulated previous version data does not have new_attribute
        self.assertEquals('new_resource' in obj_dict, False)
        # simulate reading the previous version that does not have new_attribute
        io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
        obj = io_deserializer.deserialize(obj_dict)
        # verify that new attribute is added and initialized with default value
        self.assertEquals(obj.new_resource.new_attribute['key'], 'value')
        # verify that old attributes are still there
        self.assertEquals(obj.num, 9)
        # verify that old attributes are still there
        self.assertEquals(obj.other_field, 'test value')
        # verify that on read version is not yet updated
        self.assertEquals(obj_dict['persisted_version'], 1)

        # simulate create/update
        obj_dict = io_serializer.serialize(obj,True)
        # verify that version is updated
        self.assertEquals(obj_dict['persisted_version'], 2)

    # test cases when an attribute in a resource (not the resource itself)
    # undergoes a type change. For example new_resource has changed its type
    # from SampleResource_V2 to SampleResource_V3
    # (note: here SampleResource versions are used as different types not different versions)
    @unittest.skip("type safety is not accounted for anymore")
    def test_complex_version_del_attrib(self):

        io_serializer = IonObjectSerializer()
        # verify that extraneous fields given while creating an IonObject raises an error.
        with self.assertRaises(AttributeError):
            IonObject('SampleComplexEvent_V2', {'num': 9, 'other_field': 'test value','more_new_resource': {'key':'value'}})

        obj = IonObject('SampleComplexEvent_V2', {'num': 9, 'other_field': 'test value','new_resource': {'num': 9, 'other_field': 'test value','new_attribute':{'key':'value'}}})
        # create simulated saved data
        obj_dict = io_serializer.serialize(obj,True)
        self.assertEquals(obj_dict['persisted_version'], 2)
        # simulate a next version data of SampleComplexEvent_V2
        obj_dict['type_'] = 'SampleComplexEvent_V3'

        # verify that the simulated previous version data does have new_resource
        self.assertEquals('new_resource' in obj_dict, True)
        # note the schema version of new_resource
        self.assertEquals(obj_dict['new_resource']['persisted_version'], 2)

        # simulate reading the next version that has a new type of new_resource
        io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
        obj = io_deserializer.deserialize(obj_dict)

        # verify that new_resource exists
        self.assertTrue('new_resource' in obj)
        # however, verify that new_resource does not have new_attribute since type of new_resource has changed
        self.assertFalse('new_attribute' in obj.new_resource)
        # verify that the new type of new_resource has another_new_attribute that is initialized to default data
        self.assertEquals(obj.new_resource.another_new_attribute['key'], 'new_value')
        # verify on read that the schema version of new_resource replaces the old persisted_version
        self.assertEquals(obj.new_resource.persisted_version, 3)

        # verify that old attributes values of new_resource have been thrown away
        self.assertNotEquals(obj.new_resource.num, 9)
        # verify that attributes values of new_resource have been initialized to default values
        self.assertEquals(obj.new_resource.num, 0)

        # However, verify that old attributes of the resource (SampleComplexEvent) are still there
        self.assertEquals(obj.num, 9)
        # verify that old attributes are still there
        self.assertEquals(obj.other_field, 'test value')
        # verify that on read, version is not yet updated
        self.assertEquals(obj.persisted_version, 2)


        # simulate create/update
        obj_dict = io_serializer.serialize(obj,True)
        # verify that version is updated
        self.assertEquals(obj_dict['persisted_version'], 3)
        # verify that version is updated fo the subsumed object
        self.assertEquals(obj_dict['new_resource']['persisted_version'], 3)

    # test cases when an attribute in a resource (not the resource itself)
    # undergoes a version change. For example new_resource's version has changed not its type
    def test_attribute_version(self):

        io_serializer = IonObjectSerializer()

        # verify that extraneous fields given while creating an IonObject raises an error.
        with self.assertRaises(AttributeError):
            IonObject('SampleComplexEvent_V2', {'num': 9, 'other_field': 'test value','more_new_resource':
                {'key':'value'}})

        obj = IonObject('SampleComplexEvent_V2', {'num': 9, 'other_field': 'test value','new_resource':
            {'num': 9, 'other_field': 'test value','new_attribute':{'key':'value'}}})
        obj_dict = io_serializer.serialize(obj,True)
        self.assertEquals(obj_dict['persisted_version'], 2)

        # verify that the simulated previous version data does have new_resource
        self.assertEquals('new_resource' in obj_dict, True)
        # verify that the new_resource has type SampleResource_V2
        self.assertEquals(obj_dict['new_resource']['type_'],"SampleResource_V2")

        # set type to SampleComplexEvent_V3
        obj_dict['type_']="SampleComplexEvent_V3"
        obj_dict['persisted_version']=3
        # set new_resource's type to SampleResource_V3
        # so we pretend that version, not the type, of the attribute has been changed
        obj_dict['new_resource']['type_']="SampleResource_V3"

        # simulate reading SampleComplexEvent_V3 after a new version of new_resource has been introduced
        io_deserializer = IonObjectDeserializer(obj_registry=get_obj_registry())
        obj = io_deserializer.deserialize(obj_dict)

        # verify that new resource is not deleted
        self.assertTrue('new_resource' in obj)
        # verify that new resource does not have new_attribute
        self.assertFalse('new_attribute' in obj.new_resource)
        # verify that the next version of new_resource has default data in the another_new_attribute
        self.assertEquals(obj.new_resource.another_new_attribute['key'], 'new_value')
        # verify that old attributes values of new_resource have not been thrown away
        self.assertEquals(obj.new_resource.num, 9)
        # verify that values from old attributes of SampleComplexEvent_V2 are still there
        self.assertEquals(obj.num, 9)
        self.assertEquals(obj.other_field, 'test value')

        # verify that on read version is not yet updated for the subsumed object
        self.assertEquals(obj.new_resource.persisted_version, 2)

        # simulate create/update
        obj_dict = io_serializer.serialize(obj,True)
        # verify that versions are unchanged
        self.assertEquals(obj_dict['persisted_version'], 3)
        # verify that versions are updated in the subsumed object
        self.assertEquals(obj_dict['new_resource']['persisted_version'], 3)


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

    @unittest.skip("no more recursive encoding on set")
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
