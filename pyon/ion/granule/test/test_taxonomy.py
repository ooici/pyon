#!/usr/bin/env python

'''
@package pyon.ion.granule.test.test_taxonomy
@file pyon/ion/granule/test/test_taxonomy.py
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


import unittest
from nose.plugins.attrib import attr
from pyon.ion.granule.taxonomy import Taxonomy, TaxyTool

@attr('UNIT', group='dm')
class TaxonomyToolTestCase(unittest.TestCase):

    def test_init(self):
        """
        test initialization of the TaxyCab
        """

        tc = TaxyTool()
        self.assertRaises(KeyError, tc.get_handle, 'nick_name')
        self.assertRaises(KeyError,tc.get_names_by_handle, 0)


        tx = Taxonomy(map={1:('nick_name',{'nick_name','a'})})

        tc2 = TaxyTool(taxonomy=tx)
        self.assertEquals(tc2._cnt,1)
        self.assertEquals(tc2.get_handles('a'),{1,})
        self.assertEquals(tc2.get_handle('nick_name'),1)

        tc3 = TaxyTool(tx)
        self.assertEquals(tc3.get_names_by_handle(1),{'nick_name','a'})

    def test_eq(self):

        tx1 = Taxonomy(map={1:('nick_name',{'nick_name','a'}),
                           2:('nick2',{'nick2','a','b','cc'})} )

        # pass with tt1._t.map "is"
        tt1 = TaxyTool(tx1)
        tt2 = TaxyTool(tx1)
        self.assertEquals(tt1, tt2)

        # after changes - thy are still the same
        tt2.add_taxonomy_set('new_name','p','q','r')
        self.assertEquals(tt2,tt1)


        # pass with 'is'
        tt3 = tt1
        self.assertEquals(tt3, tt1)

        # after changes - thy are still the same
        tt3.add_taxonomy_set('new_name','p','q','r')
        self.assertEquals(tt1,tt3)


        # pass with tt1._t.map '=='
        tx1 = Taxonomy(map={1:('nick_name',{'nick_name','a'}),
                            2:('nick2',{'nick2','a','b','cc'})} )

        tx2 = Taxonomy(map={1:('nick_name',{'nick_name','a'}),
                            2:('nick2',{'nick2','a','b','cc'})} )
        self.assertNotEquals(tx1, tx2)
        self.assertEquals(tx1.map, tx2.map)

        tt1 = TaxyTool(tx1)
        tt2 = TaxyTool(tx2)
        self.assertEquals(tt1, tt2)

        # fail with tt1._t.map '=='
        tx2 = Taxonomy(map={1:('nick_name',{'nick_name','as'}),
                            2:('nick2',{'nick2','a','b','cc'})} )
        tt1 = TaxyTool(tx1)
        tt2 = TaxyTool(tx2)
        self.assertNotEquals(tt1, tt2)


        # Use the interface to build a complex one and test equality as they go in and out of sync...
        tt1 = TaxyTool()
        tt2 = TaxyTool()
        tt1.add_taxonomy_set('a name','junk','1','2')
        tt2.add_taxonomy_set('a name','junk','1','2')

        self.assertEquals(tt1, tt2)

        tt2.add_taxonomy_set('new_name','1')

        self.assertNotEquals(tt1,tt2)

        tt1.extend_names_by_nick_name('a name','3')
        tt2.extend_names_by_nick_name('a name','3')

        tt1.add_taxonomy_set('new_name','1')

        self.assertEquals(tt1, tt2)


    def test_taxonomy_set(self):

        nick_name = 'nick_name'
        a = 'a'
        b = 'b'
        c = 'c'
        tc = TaxyTool()
        tc.add_taxonomy_set(nick_name=nick_name)
        self.assertEquals(tc.get_handles('a name'), {-1,})
        self.assertRaises(KeyError,tc.get_names_by_handle,5)
        self.assertEquals(tc.get_names_by_handle(0), {nick_name,})


        tc = TaxyTool()
        tc.add_taxonomy_set(a)
        self.assertEquals(tc.get_handle(a),0)
        self.assertEquals(tc.get_names_by_handle(0),{a,})
        self.assertEquals(tc.get_names_by_nick_name(a),{a,})


        tc = TaxyTool()
        tc.add_taxonomy_set(a)
        tc.add_taxonomy_set(b)

        self.assertEquals(tc.get_handle(a),0)
        self.assertEquals(tc.get_names_by_handle(0),{a,})

        self.assertEquals(tc.get_handle(b),1)
        self.assertEquals(tc.get_names_by_handle(1),{b,})

        tc = TaxyTool()
        tc.add_taxonomy_set(nick_name, a, b, c)
        self.assertEquals(tc.get_handle(nick_name),0)
        self.assertEquals(tc.get_handles(a),{0,})
        self.assertEquals(tc.get_handles(b),{0,})
        self.assertEquals(tc.get_handles(c),{0,})
        self.assertEquals(tc.get_names_by_handle(0),{nick_name,a,b,c,})
        self.assertEquals(tc.get_names_by_nick_name(nick_name),{nick_name,a,b,c,})

    def test_get_nick_names(self):
        tc = TaxyTool()
        tc.add_taxonomy_set('1','a')
        tc.add_taxonomy_set('2','a')

        self.assertEquals(tc.get_nick_name(0),'1')
        self.assertEquals(tc.get_nick_names('a'),['1', '2'])
        self.assertEquals(tc.get_handle('1'),0)
        self.assertEquals(tc.get_handles('a'),{0,1})

    def test_extend_names(self):

        tc = TaxyTool()
        tc.add_taxonomy_set('1','a')
        tc.add_taxonomy_set('2','a')

        self.assertEquals(tc.get_handles('1'),{0,})
        self.assertEquals(tc.get_handles('2'),{1,})

        self.assertEquals(tc.get_names_by_handle(0),{'1', 'a',})
        self.assertEquals(tc.get_names_by_handle(1),{'2', 'a',})

        tc.extend_names_by_nick_name('1', 'c', 'e')
        tc.extend_names_by_nick_name('2', 'z', 'x')
        tc.extend_names_by_nick_name('1', 'd', 'f')

        self.assertEquals(tc.get_handles('a'),{0,1})
        self.assertEquals(tc.get_handles('z'),{1,})
        self.assertEquals(tc.get_handles('c'),{0,})

        #Test for a name that isn't in the taxonomy
        self.assertEquals(tc.get_handles('b'),{-1,})

        self.assertEquals(tc.get_names_by_handle(0),{'1', 'a', 'c', 'e', 'd', 'f',})
        self.assertEquals(tc.get_names_by_handle(1),{'2', 'a', 'z', 'x',})

        tc.extend_names_by_anyname('a', 'extend')
        self.assertEquals(tc.get_handles('extend'),{0,1,})

    def test_yamlize(self):

        tc = TaxyTool()
        tc.add_taxonomy_set('1','a')
        tc.add_taxonomy_set('2','b')

        tc.extend_names_by_nick_name('1','x')
        tc.extend_names_by_anyname('a','z')
        tc.extend_names_by_anyname('b','c')

        s = tc.dump()

        tc2 = TaxyTool.load(s)

        #@todo - a list is not a set and the yaml dump/ion serialization can not handle sets...
        self.assertEquals(tc2._cnt,1)
        self.assertEquals(tc2.get_names_by_handle(0),{'1','x','a','z',})
        self.assertEquals(tc2.get_names_by_handle(1),{'2','b','c',})

        self.assertEquals(tc._cnt,1)
        self.assertEquals(tc.get_names_by_handle(0),{'1','x','a','z',})
        self.assertEquals(tc.get_names_by_handle(1),{'2','b','c',})


