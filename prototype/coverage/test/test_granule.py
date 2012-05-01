#!/usr/bin/env python

'''
@package prototype.coverage.record_set
@file prototype/coverage/record_set.py
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


import unittest
from nose.plugins.attrib import attr
import numpy
from prototype.coverage.granule_and_record import GranuleBuilder, Taxonomy

@attr('UNIT', group='dmproto')
class GranuleBuilderTestCase(unittest.TestCase):

    def setUp(self):

        self._tx = Taxonomy(tx_id='junk')
        self._tx.map={'temp':1,'cond':2,'pres':3}
        # map is {<local name>: <granule name or path>}

        self._gb = GranuleBuilder(data_producer_id='john', taxonomy=self._tx)

    def test_set_and_get(self):
        """
        make sure you can set and get items in the granule by name in the taxonomy
        """

        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._gb['temp'] = temp_array
        self._gb['cond'] = cond_array
        self._gb['pres'] = pres_array

        self.assertTrue(numpy.allclose(self._gb['temp'], temp_array))
        self.assertTrue(numpy.allclose(self._gb['cond'], cond_array))
        self.assertTrue(numpy.allclose(self._gb['pres'], pres_array))

    def test_iteration(self):
        """
        Test all four iteration methods for items in the granule
        """

        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._gb['temp'] = temp_array
        self._gb['cond'] = cond_array
        self._gb['pres'] = pres_array

        for k, v in self._gb.iteritems():
            if k == 'temp':
                self.assertTrue(numpy.allclose(temp_array, v))
            elif k == 'cond':
                self.assertTrue(numpy.allclose(cond_array, v))
            elif k == 'pres':
                self.assertTrue(numpy.allclose(pres_array, v))
            else:
                self.assertTrue(False)

        for k in self._gb.iterkeys():
            if k != 'temp' and k != 'cond' and k != 'pres':
                self.assertTrue(False)

        for v in self._gb.itervalues():
            if not numpy.allclose(temp_array, v) and not numpy.allclose(cond_array, v) and not numpy.allclose(pres_array, v):
                self.assertTrue(False)

        for k in self._gb:
            if k != 'temp' and k != 'cond' and k != 'pres':
                self.assertTrue(False)

    def test_update(self):
        """
        Update this granule with the content of another.
        Assert that the taxonomies are the same...
        """

        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._gb['temp'] = temp_array
        self._gb['cond'] = cond_array
        self._gb['pres'] = pres_array

        gb2 = GranuleBuilder(data_producer_id='john2', taxonomy=self._tx)
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        gb2['temp'] = temp_array
        gb2['cond'] = cond_array
        gb2['pres'] = pres_array

        self._gb.update(E=gb2)

    def test_len(self):
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._gb['temp'] = temp_array
        self._gb['cond'] = cond_array
        self._gb['pres'] = pres_array

        self.assertTrue(len(self._gb) > 0)

    def test_repr(self):
        """
        Come up with a reasonable string representation of the granule for debug purposes only
        """
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._gb['temp'] = temp_array
        self._gb['cond'] = cond_array
        self._gb['pres'] = pres_array
        self.assertTrue(len(self._gb.__repr__()) > 0)



