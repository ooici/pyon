#!/usr/bin/env python

'''
@package pyon.ion.granule.granule
@file pyon/ion/granule/granule
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


from interface.objects import Granule
from pyon.core.exception import BadRequest
from pyon.util.arg_check import validate_is_instance
from pyon.ion.granule.record_dictionary import RecordDictionaryTool
from pyon.ion.granule.taxonomy import TaxyTool

import numpy as np


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

def combine_granules(granule_a, granule_b):
    """
    This is a method that combines granules in a very naive manner
    """
    validate_is_instance(granule_a,Granule, 'granule_a is not a proper Granule')
    validate_is_instance(granule_b,Granule, 'granule_b is not a proper Granule')

    tt_a = TaxyTool.load_from_granule(granule_a)
    tt_b = TaxyTool.load_from_granule(granule_b)

    if tt_a != tt_b:
        raise BadRequest('Can\'t combine the two granules, they do not have the same taxonomy.')

    rdt_new = RecordDictionaryTool(tt_a)
    rdt_a = RecordDictionaryTool.load_from_granule(granule_a)
    rdt_b = RecordDictionaryTool.load_from_granule(granule_b)


    for k in rdt_a.iterkeys():
        rdt_new[k] = np.append(rdt_a[k], rdt_b[k])
    return build_granule(granule_a.data_producer_id, tt_a, rdt_new)



