#!/usr/bin/env python

'''
@package prototype.coverage.record_set
@file prototype/coverage/test/test_taxonomy.py
@author David Stuebe
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


import unittest
from nose.plugins.attrib import attr
from prototype.coverage.taxonomy import Taxonomy, TaxyCab

@attr('UNIT', group='dmproto2')
class GranuleBuilderTestCase(unittest.TestCase):

    def test_init(self):
        """
        test initialization of the TaxyCab
        """

        tc = TaxyCab()
        #@todo - replace this with a better exception?
        self.assertRaises(KeyError,tc.get_handles,0)
        self.assertRaises(KeyError,tc.get_names,'a')


        tx = Taxonomy(map={1:set(['a'])})

        tc2 = TaxyCab(taxonomy=tx)
        self.assertEquals(tc2._cnt,1)
        self.assertEquals(tc2.get_handle('a'),1)

        tc3 = TaxyCab(tx)
        self.assertEquals(tc2.get_names(1),set(['a']))


    def test_taxonomy_set(self):

        tc = TaxyCab()
        tc.add_taxonomy_set()
        self.assertRaises(KeyError,tc.get_handles,0)
        self.assertRaises(KeyError,tc.get_names,'a')


        tc = TaxyCab()
        tc.add_taxonomy_set('a')
        self.assertEquals(tc.get_handle('a'),0)
        self.assertEquals(tc.get_names(0),set(['a']))


        tc = TaxyCab()
        tc.add_taxonomy_set('a')
        tc.add_taxonomy_set('b')

        self.assertEquals(tc.get_handle('a'),0)
        self.assertEquals(tc.get_names(0),set(['a']))

        self.assertEquals(tc.get_handle('b'),1)
        self.assertEquals(tc.get_names(1),set(['b']))

        tc = TaxyCab()
        tc.add_taxonomy_set('a')
        tc.add_taxonomy_set('a')

        self.assertRaises(RuntimeError,tc.get_handle,'a')

        self.assertEquals(tc.get_handles('a'),set([0,1]))
        self.assertEquals(tc.get_names(0),set(['a']))
        self.assertEquals(tc.get_names(1),set(['a']))

        tc = TaxyCab()
        tc.add_taxonomy_set('a','b','c')
        self.assertEquals(tc.get_handle('a'),0)
        self.assertEquals(tc.get_handle('b'),0)
        self.assertEquals(tc.get_handle('c'),0)
        self.assertEquals(tc.get_names(0),set(['b','a','c']))


    def test_extend_names(self):

        tc = TaxyCab()
        tc.add_taxonomy_set('1','a')
        tc.add_taxonomy_set('1','b')

        self.assertEquals(tc.get_handles('1'),set([0,1]))

        self.assertEquals(tc.get_names(0),set(['1','a']))
        self.assertEquals(tc.get_names(1),set(['1','b']))

        tc.extend_names('1','2')
        tc.extend_names('a','z')
        tc.extend_names('b','c')

        self.assertEquals(tc.get_handles('2'),set([0,1]))


        self.assertEquals(tc.get_handles('a'),set([0]))
        self.assertEquals(tc.get_handles('z'),set([0]))
        self.assertEquals(tc.get_handles('b'),set([1]))
        self.assertEquals(tc.get_handles('c'),set([1]))

        self.assertEquals(tc.get_names(0),set(['1','2','a','z']))
        self.assertEquals(tc.get_names(1),set(['1','2','b','c']))


    def test_yamlize(self):

        tc = TaxyCab()
        tc.add_taxonomy_set('1','a')
        tc.add_taxonomy_set('1','b')

        tc.extend_names('1','2')
        tc.extend_names('a','z')
        tc.extend_names('b','c')


        s = tc.dump()

        tc2 = TaxyCab.load(s)

        #@todo - a list is not a set and the yaml dump/ion serialization can not handle sets...
        self.assertEquals(tc2._cnt,1)
        self.assertEquals(tc2.get_names(0),set(['1','2','a','z']))
        self.assertEquals(tc2.get_names(1),set(['1','2','b','c']))


        self.assertEquals(tc._cnt,1)
        self.assertEquals(tc.get_names(0),set(['1','2','a','z']))
        self.assertEquals(tc.get_names(1),set(['1','2','b','c']))


