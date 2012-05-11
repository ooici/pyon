#!/usr/bin/env python

'''
@package pyon.ion.granule.test.test_record_dictionary
@file pyon/ion/granule/test/test_record_dictionary.py
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


import unittest
from nose.plugins.attrib import attr
import numpy
from pyon.ion.granule.record_dictionary import RecordDictionaryTool, TaxyTool

@attr('UNIT', group='dm')
class RecordDictionaryToolTestCase(unittest.TestCase):

    def setUp(self):

        self._tx = TaxyTool()
        self._tx.add_taxonomy_set('temp', 'long_temp_name')
        self._tx.add_taxonomy_set('cond', 'long_cond_name')
        self._tx.add_taxonomy_set('pres', 'long_pres_name')
        self._tx.add_taxonomy_set('rdt')
        self._tx.add_taxonomy_set('rdt2')
        # map is {<local name>: <granule name or path>}

        self._rdt = RecordDictionaryTool(taxonomy=self._tx)

    def test_init(self):

        # initialize with a taxonomy tool
        rdt = RecordDictionaryTool(taxonomy=self._tx)
        self.assertIsInstance(rdt._tx, TaxyTool)

        # initialize with a taxonomy object
        rdt = RecordDictionaryTool(taxonomy=self._tx._t)
        self.assertIsInstance(rdt._tx, TaxyTool)

        # initialize with pooo
        self.assertRaises(TypeError, RecordDictionaryTool, ['foo', 'barr'])

        # initialize with a valid length
        rdt = RecordDictionaryTool(taxonomy=self._tx, length=5)
        self.assertEquals(rdt._len, 5)

        # initialize with no length
        rdt = RecordDictionaryTool(taxonomy=self._tx)
        self.assertEquals(rdt._len, None)

        # initialize with pooo
        self.assertRaises(TypeError, RecordDictionaryTool, self._tx, 'not an int')



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

        #want to check to make sure a KeyError is raised when a non-nickname key is used, but it's not working correctly
        self.assertRaises(KeyError, self._rdt.__getitem__, 'long_temp_name')
        self.assertRaises(KeyError, self._rdt.__getitem__,'nonsense!')

        taxy_tool_obj =self._tx
        rdt = RecordDictionaryTool(taxonomy=taxy_tool_obj)
        rdt['temp'] = temp_array
        self._rdt['rdt'] = rdt

        # Now test when the Record Dictionary Tool is created with the Taxonomy object rather than the TaxyTool
        # This can fail if the == method for TaxyTool is implemented incorrectly

        taxonomy_ion_obj = self._tx._t
        rdt2 = RecordDictionaryTool(taxonomy=taxonomy_ion_obj)
        rdt2['temp'] = temp_array
        self._rdt['rdt2'] = rdt2


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
            if k == 'temp':
                self.assertTrue(numpy.allclose(temp_array, v))
            elif k == 'cond':
                self.assertTrue(numpy.allclose(cond_array, v))
            elif k == 'pres':
                self.assertTrue(numpy.allclose(pres_array, v))
            else:
                self.assertTrue(False)

        for k in self._rdt.iterkeys():
            self.assertTrue(k == 'temp' or k == 'cond' or k == 'pres')

        for v in self._rdt.itervalues():
            self.assertTrue(numpy.allclose(temp_array, v) or numpy.allclose(cond_array, v) or numpy.allclose(pres_array, v))

        for k in self._rdt:
            self.assertTrue(k == 'temp' or k == 'cond' or k == 'pres')

    def test_update(self):
        """
        Update this granule with the content of another.
        Assert that the taxonomies are the same...
        """


        pres_array = numpy.random.standard_normal(100)
        self._rdt['pres'] = pres_array

        rdt2 = RecordDictionaryTool(taxonomy=self._tx)
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)

        rdt2['temp'] = temp_array
        rdt2['cond'] = cond_array

        self._rdt.update(rdt2)

        self.assertIn('pres', self._rdt)
        self.assertIn('temp', self._rdt)
        self.assertIn('cond', self._rdt)

        self.assertTrue((self._rdt['pres'] == pres_array).all())
        self.assertTrue((self._rdt['cond'] == cond_array).all())
        self.assertTrue((self._rdt['temp'] == temp_array).all())

        self.assertEquals(len(self._rdt), 3)



    def test_len(self):
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._rdt['temp'] = temp_array
        self._rdt['cond'] = cond_array
        self._rdt['pres'] = pres_array

        self.assertEquals(len(self._rdt), 3)

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
        self.assertTrue(len(repr(self._rdt)) > 0)

    def test_delete(self):
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._rdt['temp'] = temp_array
        self._rdt['cond'] = cond_array
        self._rdt['pres'] = pres_array

        self.assertIn('pres', self._rdt)
        self.assertIn('temp', self._rdt)
        self.assertIn('cond', self._rdt)

        del self._rdt['pres']

        self.assertNotIn('pres', self._rdt)
        self.assertIn('temp', self._rdt)
        self.assertIn('cond', self._rdt)

    def test_contains(self):

        # foobar isn't even in the taxonomy!
        self.assertNotIn('foobar', self._rdt)

        # Temp is in the taxonomy but not the record dictionary
        self.assertNotIn('temp', self._rdt)


        # Now put in some data and make sure it works...
        temp_array = numpy.random.standard_normal(100)
        self._rdt['temp'] = temp_array

        self.assertIn('temp', self._rdt)


    def test_pretty_print(self):
        temp_array = numpy.random.standard_normal(100)
        cond_array = numpy.random.standard_normal(100)
        pres_array = numpy.random.standard_normal(100)

        self._rdt['temp'] = temp_array
        self._rdt['cond'] = cond_array
        self._rdt['pres'] = pres_array


        rdt = RecordDictionaryTool(taxonomy=self._tx)
        rdt['rdt'] = temp_array
        self._rdt['rdt'] = rdt

        self.assertGreater(len(self._rdt.pretty_print()), 0)



