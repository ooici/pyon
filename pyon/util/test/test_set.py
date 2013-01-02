#!/usr/bin/env/python

'''
@author Luke Campbell <LCampbell (at) ASAScience.com>
@file pyon/util/test/test_set.py
@date Wed Jan  2 10:46:48 EST 2013
'''

from pyon.util.set import OrderedSet
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr
from copy import copy

@attr('UNIT')
class OrderedSetTest(PyonTestCase):
    def test_set_ops(self):
        # Verify unique keys and order is maintained
        os = OrderedSet([3,1,5,2,2,1,9,8,12,18])
        compare_list = [3,1,5,2,9,8,12,18]
        self.assertEquals(list(os), compare_list)


        # Verify addition doesn't violate unique keys
        os.add(2)
        self.assertEquals(list(os), compare_list)

        # Verify a valid addition doesn't violate order
        os.add(21)
        self.assertEquals(list(os), compare_list + [21])
        
        # Pop
        val = os.pop()
        self.assertEquals(val, 21)
        self.assertEquals(list(os), compare_list)

        # Verify list comprehension doesn't violate order
        self.assertEquals([i for i in os], compare_list)

        # Lenght assertions
        self.assertEquals(len(list(os)), len(os))

        # Reversed
        cmpval = copy(compare_list)
        cmpval.reverse()
        self.assertEquals([i for i in reversed(os)], cmpval)

        
        # Comparisons
        self.assertTrue(os == compare_list)
        os2 = OrderedSet(compare_list)
        self.assertTrue(os == os2)

        
        # Discarding
        self.assertTrue(8 in os)
        os.discard(8)
        self.assertFalse(8 in os)


        with self.assertRaises(KeyError):
            os2 = OrderedSet([])
            os2.pop()
