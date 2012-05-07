__author__ = 'Tim Giguere'

import numpy

from pyon.ion.granule.taxonomy import TaxyTool
from pyon.ion.granule.record_dictionary import RecordDictionaryTool


#Basic workflow for creating a RecordDictionaryTool
def _workflow(self):
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