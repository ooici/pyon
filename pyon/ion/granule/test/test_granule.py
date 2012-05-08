#!/usr/bin/env python

'''
@package pyon.ion.granule.test.test_granule
@file pyon/ion/granule/test/test_granule.py
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


import unittest
import numpy
from nose.plugins.attrib import attr
from pyon.ion.granule.taxonomy import TaxyTool
from pyon.ion.granule.granule import build_granule
from pyon.ion.granule.record_dictionary import RecordDictionaryTool


@attr('UNIT', group='dm')
class GranuleTestCase(unittest.TestCase):

    def test_build_granule_and_load_from_granule(self):


        #Define a taxonomy and add sets. add_taxonomy_set takes one or more names and assigns them to one handle
        tx = TaxyTool()
        tx.add_taxonomy_set('temp', 'long_temp_name')
        tx.add_taxonomy_set('cond', 'long_cond_name')
        tx.add_taxonomy_set('pres', 'long_pres_name')
        tx.add_taxonomy_set('rdt')
        # map is {<local name>: <granule name or path>}

        #Use RecordDictionaryTool to create a record dictionary. Send in the taxonomy so the Tool knows what to expect
        rdt = RecordDictionaryTool(taxonomy=tx)

        #Create some arrays and fill them with random values
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        #Use the RecordDictionaryTool to add the values. This also would work if you used long_temp_name, etc.
        rdt['temp'] = temp_array
        rdt['cond'] = cond_array
        rdt['pres'] = pres_array

        #You can also add in another RecordDictionaryTool, providing the taxonomies are the same.
        rdt2 = RecordDictionaryTool(taxonomy=tx)
        rdt2['temp'] = temp_array
        rdt['rdt'] = rdt2


        g = build_granule(data_producer_id='john', taxonomy=tx, record_dictionary=rdt)

        l_tx = TaxyTool.load_from_granule(g)

        l_rd = RecordDictionaryTool.load_from_granule(g)

        # Make sure we got back the same Taxonomy Object
        self.assertEquals(l_tx._t, tx._t)
        self.assertEquals(l_tx.get_handles('temp'), tx.get_handles('temp'))
        self.assertEquals(l_tx.get_handles('testing_2'), tx.get_handles('testing_2'))


        # Now test the record dictionary object
        self.assertEquals(l_rd._rd, rdt._rd)
        self.assertEquals(l_rd._tx._t, rdt._tx._t)


        for k, v in l_rd.iteritems():
            for name in k:
                self.assertIn(name, rdt)

                if isinstance(v, numpy.ndarray):
                    self.assertTrue( (v == rdt[name]).all())

                else:
                    self.assertEquals(v._rd, rdt[name]._rd)

