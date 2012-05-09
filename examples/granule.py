#!/usr/bin/env python

'''
@package examples.granule
@file examples/granule.py
@author Tim Giguere
@author David Stuebe
@brief Basic example workflow for creating a RecordDictionaryTool

'''

import numpy

from pyon.ion.granule.taxonomy import TaxyTool
from pyon.ion.granule.record_dictionary import RecordDictionaryTool
from pyon.ion.granule.granule import build_granule

def granule_example(nsdict):
    """
    Usage:
    from examples.granule import granule_example
    granule_example(locals())

    tx, g, rdt, rdt2... etc, are now local variables in your shell!
    """

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


    #you can get a string representation of the RecordDictionaryTool
    print rdt
    print rdt.pretty_print()

    #Determine the length of the RecordDictionary using the len function
    print len(rdt)

    #Delete an item in the RecordDictionary
    del rdt['temp']


    g = build_granule(data_producer_id='john', taxonomy=tx, record_dictionary=rdt)


    nsdict.update(locals())
