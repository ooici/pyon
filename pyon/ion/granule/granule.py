#!/usr/bin/env python

'''
@package pyon.ion.granule.granule
@file pyon/ion/granule/granule
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


from interface.objects import Granule


def build_granule(data_producer_id, taxonomy, record_dictionary):
    """
    This method is a simple wrapper that knows how to produce a granule IonObject from a RecordDictionaryTool and a TaxonomyTool

    A granule is a unit of information which conveys part of a coverage.

    A granule contains a record dictionary. The record dictionary is composed of named value sequences.
    We want the Granule Builder to have a dictionary like behavior for building record dictionaries, using the taxonomy
    as a map from the name to the ordinal in the record dictionary.
    """

    #@todo If the taxonomy has an id_ and rev_ send only that.
    return Granule(data_producer_id=data_producer_id, record_dictionary=record_dictionary._rd, taxonomy=taxonomy._t)


