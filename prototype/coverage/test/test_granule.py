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
from prototype.coverage.granule_and_record import RecordDictionaryTool, TaxyCab

@attr('UNIT', group='dmproto')
class RecordDictionaryToolTestCase(unittest.TestCase):

    def setUp(self):

        self._tx = TaxyCab()
        self._tx.add_taxonomy_set('temp', 'long_temp_name')
        self._tx.add_taxonomy_set('cond', 'long_cond_name')
        self._tx.add_taxonomy_set('pres', 'long_pres_name')
        self._tx.add_taxonomy_set('rdt')
        # map is {<local name>: <granule name or path>}

        self._rdt = RecordDictionaryTool(taxonomy=self._tx)

    def test_set_and_get(self):
        """
        make sure you can set and get items in the granule by name in the taxonomy
        """

        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._rdt['temp'] = temp_array
        self._rdt['cond'] = cond_array
        self._rdt['pres'] = pres_array

        self.assertTrue(numpy.allclose(self._rdt['temp'], temp_array))
        self.assertTrue(numpy.allclose(self._rdt['cond'], cond_array))
        self.assertTrue(numpy.allclose(self._rdt['pres'], pres_array))

        self.assertTrue(numpy.allclose(self._rdt['long_temp_name'], temp_array))
        self.assertTrue(numpy.allclose(self._rdt['long_cond_name'], cond_array))
        self.assertTrue(numpy.allclose(self._rdt['long_pres_name'], pres_array))

        # map is {<local name>: <granule name or path>}

        rdt = RecordDictionaryTool(taxonomy=self._tx)
        rdt['rdt'] = temp_array
        self._rdt['rdt'] = rdt

    def test_iteration(self):
        """
        Test all four iteration methods for items in the granule
        """

        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._rdt['temp'] = temp_array
        self._rdt['cond'] = cond_array
        self._rdt['pres'] = pres_array

        for k, v in self._rdt.iteritems():
            if isinstance(k, set):
                if 'long_temp_name' in k and 'temp' in k:
                    self.assertTrue(numpy.allclose(temp_array, v))
                elif 'cond' in k and 'long_cond_name' in k:
                    self.assertTrue(numpy.allclose(cond_array, v))
                elif 'pres' in k and 'long_pres_name' in k:
                    self.assertTrue(numpy.allclose(pres_array, v))
                else:
                    self.assertTrue(False)

        for k in self._rdt.iterkeys():
            if isinstance(k, set):
                if not(('temp' in k and 'long_temp_name' in k) or\
                   ('cond' in k and 'long_cond_name' in k) or\
                   ('pres' in k and 'long_pres_name' in k)):
                    self.assertTrue(False)

        for v in self._rdt.itervalues():
            if not numpy.allclose(temp_array, v) and not numpy.allclose(cond_array, v) and not numpy.allclose(pres_array, v):
                self.assertTrue(False)

        for k in self._rdt:
            if isinstance(k, set):
                if not(('temp' in k and 'long_temp_name' in k) or\
                       ('cond' in k and 'long_cond_name' in k) or\
                       ('pres' in k and 'long_pres_name' in k)):
                    self.assertTrue(False)

    def test_update(self):
        """
        Update this granule with the content of another.
        Assert that the taxonomies are the same...
        """

        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._rdt['temp'] = temp_array
        self._rdt['cond'] = cond_array
        self._rdt['pres'] = pres_array

        rdt2 = RecordDictionaryTool(taxonomy=self._tx)
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        rdt2['temp'] = temp_array
        rdt2['cond'] = cond_array
        rdt2['pres'] = pres_array

        self._rdt.update(E=rdt2)

    def test_len(self):
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._rdt['temp'] = temp_array
        self._rdt['cond'] = cond_array
        self._rdt['pres'] = pres_array

        self.assertTrue(len(self._rdt) > 0)

    def test_repr(self):
        """
        Come up with a reasonable string representation of the granule for debug purposes only
        """
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._rdt['temp'] = temp_array
        self._rdt['cond'] = cond_array
        self._rdt['pres'] = pres_array
        self.assertTrue(len(self._rdt.__repr__()) > 0)

    def test_delete(self):
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._rdt['temp'] = temp_array
        self._rdt['cond'] = cond_array
        self._rdt['pres'] = pres_array

        del self._rdt['pres']
        for k in self._rdt.iterkeys():
            if k == 'pres':
                self.assertTrue(False)

    def test_contains(self):
        if not 'temp' in self._rdt:
            self.assertTrue(False)

        if 'temp_not_found' in self._rdt:
            self.assertTrue(False)


def _workflow(self):
    #Define a taxonomy and add sets. add_taxonomy_set takes one or more names and assigns them to one handle
    tx = TaxyCab()
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
    rdt = RecordDictionaryTool(taxonomy=tx)
    rdt['temp'] = temp_array
    rdt['rdt'] = rdt

    #To iterate through the items in the RecordDictionaryTool, use iteritems
    for k, v in self._rdt.iteritems():
        if isinstance(k, set):  #The keys are returned as sets.
            if 'long_temp_name' in k and 'temp' in k:   #Determine which data we're looking at
                assert(v == temp_array) #Verify we have the correct data
            elif 'cond' in k and 'long_cond_name' in k:
                assert(v == cond_array) #Verify we have the correct data
            elif 'pres' in k and 'long_pres_name' in k:
                assert(v == pres_array) #Verify we have the correct data

    #you can get a string reprentation of the RecordDictionaryTool
    print rdt
    print repr(rdt)

    #Determine the length of the RecordDictionary using the len function
    print len(rdt)

    #Delete an item in the RecordDictionary
    del rdt['rdt']



