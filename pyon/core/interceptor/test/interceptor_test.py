#!/usr/bin/env python


'''
@author Luke Campbell <lcampbell@asascience.com>
@file pyon/core/interceptor/test/interceptor_test.py
@description test lib for interceptor
'''
import unittest
from pyon.core.interceptor.encode import EncodeInterceptor
from pyon.core.interceptor.validate import ValidateInterceptor
from pyon.core.interceptor.interceptor import Invocation
from pyon.core.exception import BadRequest
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
from pyon.public import IonObject

try:
    import numpy as np
    _have_numpy = True
except ImportError as e:
    _have_numpy = False

@attr('UNIT')
class InterceptorTest(PyonTestCase):
    @unittest.skipIf(not _have_numpy,'No numpy')
    def test_numpy_codec(self):

        a = np.array([90,8010,3,14112,3.14159265358979323846264],dtype='float32')

        invoke = Invocation()
        invoke.message = a
        codec = EncodeInterceptor()

        mangled = codec.outgoing(invoke)

        received = codec.incoming(mangled)

        b = received.message
        self.assertTrue((a==b).all())

        # Rank 1, length 1 works:
        a = np.array([90,8010,3,14112,3.14159265358979323846264],dtype='float32')
        mangled = codec.outgoing(invoke)

        received = codec.incoming(mangled)

        b = received.message
        self.assertTrue((a==b).all())


    @unittest.skipIf(not _have_numpy,'No numpy')
    def test_packed_numpy(self):
        a = np.array([(90,8010,3,14112,3.14159265358979323846264)],dtype='float32')
        invoke = Invocation()
        invoke.message = {'double stuffed':[a,a,a]}
        codec = EncodeInterceptor()

        mangled = codec.outgoing(invoke)

        received = codec.incoming(mangled)

        b = received.message
        c = b.get('double stuffed')
        for d in c:
            self.assertTrue((a==d).all())

    def test_set(self):
        a = {1,2}
        invoke = Invocation()
        invoke.message = a
        codec = EncodeInterceptor()

        mangled = codec.outgoing(invoke)
        received = codec.incoming(mangled)
        b = received.message

        self.assertEquals(a,b)

    def test_scalars(self):
        a = np.uint64(312)
        invoke = Invocation()
        invoke.message = a
        codec = EncodeInterceptor()

        mangled = codec.outgoing(invoke)
        received = codec.incoming(mangled)
        b = received.message

        self.assertEquals(a,b)

    def test_slice(self):
        a = slice(5,20,2)
        invoke = Invocation()
        invoke.message = a
        codec = EncodeInterceptor()

        mangled = codec.outgoing(invoke)
        received = codec.incoming(mangled)
        b = received.message

        self.assertEquals(a,b)
    
    def test_dtype(self):
        a = np.dtype('float32')
        invoke = Invocation()
        invoke.message = a
        codec = EncodeInterceptor()

        mangled = codec.outgoing(invoke)
        received = codec.incoming(mangled)
        b = received.message

        self.assertEquals(a,b)
        
        a = np.dtype('object')
        invoke = Invocation()
        invoke.message = a
        codec = EncodeInterceptor()

        mangled = codec.outgoing(invoke)
        received = codec.incoming(mangled)
        b = received.message

        self.assertEquals(a,b)



    def test_decorator_validation(self):
        #
        # Test required values
        #
        validate_interceptor = ValidateInterceptor()
        validate_interceptor.configure({"enabled": True})
        
        decorator_obj = IonObject('Deco_Example', {"list1": [1], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "us_phone_number": "555-555-5555"})

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should fail because required field not set
        with self.assertRaises(BadRequest):
            validate_interceptor.incoming(invoke)

        decorator_obj.an_important_value = {"key": "value"}

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should work now that we have set a value for the required field
        validate_interceptor.incoming(invoke)

        #
        # Test collection content types validation
        #
        # List
        decorator_obj = IonObject('Deco_Example', {"list1": ["Should be a numeric type"], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should fail because list contains non-numeric value
        with self.assertRaises(BadRequest):
            validate_interceptor.incoming(invoke)

        decorator_obj.list1 = [1, 2]

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should work now that list content has been corrected
        validate_interceptor.incoming(invoke)

        #Validate with an ION object as content
        decorator_obj = IonObject('Deco_Example', {"list1": [{"phone_number": "858.822.5141", "phone_type": "work", "type_": "Phone", "sms": False}], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})


        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should work now that list content has been corrected
        validate_interceptor.incoming(invoke)

        #Validate with an ION object as content
        decorator_obj = IonObject('Deco_Example', {"list1": [{"phone_number": "858.822.5141", "phone_type": "work", "type_": "ExtendedPhone", "sms": False}], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})


        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should work now that list content has been corrected
        validate_interceptor.incoming(invoke)

        #Validate with an ION object as content
        decorator_obj = IonObject('Deco_Example', {"list1": [{"phone_number": "858.822.5141", "phone_type": "work", "type_": "Bad_Phone", "sms": False}], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})


        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should catch a bad ION object type
        with self.assertRaises(BadRequest):
            validate_interceptor.incoming(invoke)


        # Dict
        decorator_obj = IonObject('Deco_Example', {"list1": [1], "list2": ["One element"], "dict1": {"key1": "Should be a numeric type"}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should fail because dict value contains non-numeric value
        with self.assertRaises(BadRequest):
            validate_interceptor.incoming(invoke)

        decorator_obj.dict1 = {"key1": 1}

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should work now that dict value content has been corrected
        validate_interceptor.incoming(invoke)
        
        #
        # Test collection length
        #
        # List
        decorator_obj = IonObject('Deco_Example', {"list1": [1,2], "list2": [], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should fail since list has zero length
        with self.assertRaises(BadRequest):
            validate_interceptor.incoming(invoke)

        decorator_obj.list2 = ["Item 1", "Item 2"]

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should work new that item length of list has been corrected
        validate_interceptor.incoming(invoke)
        
        # Dict
        decorator_obj = IonObject('Deco_Example', {"list1": [1,2], "list2": [1,2], "dict1": {"key1": 1}, "dict2": {}, "an_important_value": "good value", "us_phone_number": "555-555-5555"})

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should fail since dict has zero length
        with self.assertRaises(BadRequest):
            validate_interceptor.incoming(invoke)

        decorator_obj.dict2 = {"key1": 1}

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should work new that item length of dict has been corrected
        validate_interceptor.incoming(invoke)

        #
        # Test numeric value range
        #
        # int
        decorator_obj = IonObject('Deco_Example', {"list1": [1,2], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "unsigned_short_int": -1, "an_important_value": "good value", "us_phone_number": "555-555-5555"})

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should fail
        with self.assertRaises(BadRequest):
            validate_interceptor.incoming(invoke)

        decorator_obj.unsigned_short_int = 256

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should work
        validate_interceptor.incoming(invoke)

        # float
        decorator_obj = IonObject('Deco_Example', {"list1": [1,2], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "a_float": 10.11, "an_important_value": "good value", "us_phone_number": "555-555-5555"})

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should fail
        with self.assertRaises(BadRequest):
            validate_interceptor.incoming(invoke)

        decorator_obj.a_float = 1.234

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should work
        validate_interceptor.incoming(invoke)

        #
        # Test string pattern matching
        #
        decorator_obj = IonObject('Deco_Example', {"list1": [1,2], "list2": ["One element"], "dict1": {"key1": 1}, "dict2": {"key1": 1}, "an_important_value": "good value", "us_phone_number": "5555555555"})

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should fail
        with self.assertRaises(BadRequest):
            validate_interceptor.incoming(invoke)

        decorator_obj.us_phone_number = "555-555-5555"

        invoke = Invocation()
        invoke.message = decorator_obj
        invoke.headers["validate"] = True

        # Should work
        validate_interceptor.incoming(invoke)

        #Check to see if the class level decorators were set properly
        deco_value = decorator_obj.get_class_decorator_value('SpecialObject')
        self.assertEqual(deco_value,'')
        deco_value = decorator_obj.get_class_decorator_value('OriginResourceType')
        self.assertEqual(deco_value,'MyObject')
        deco_value = decorator_obj.get_class_decorator_value('Unknown')
        self.assertEqual(deco_value,None)


