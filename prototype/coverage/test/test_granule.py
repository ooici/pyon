#!/usr/bin/env python

'''
@package prototype.coverage.record_set
@file prototype/coverage/record_set.py
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


import unittest
from prototype.coverage.granule_and_record import GranuleBuilder, Granule, CompoundGranule, CompoundGranuleBuilder


class GranuleBuilderTestCase(unittest.TestCase):


    def test_set_and_get(self):
        """
        make sure you can set and get items in the granule by name in the taxonomy
        """

        pass


    def test_iteration(self):
        """
        Test all four iteration methods for items in the granule
        """

        pass


    def test_update(self):
        """
        Update this granule with the content of another.
        Assert that the taxonomies are the same...
        """

    def test_len(self):
        pass

    def test_repr(self):
        """
        Come up with a reasonable string representation of the granule for debug purposes only
        """




