#!/usr/bin/env python

'''
@package prototype.coverage.record_set
@file prototype/coverage/record_set.py
@author David Stuebe
@author Swarbhanu Chatterjee
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


from pyon.public import log
from pyon.util.containers import DotDict
import numpy
from interface.objects import Granule, CompoundGranule, Taxonomy



class GranuleBuilder(object):
    """
    A granule is a unit of information which conveys part of a coverage.
    """
    def __init__(self,data_producer_id, taxonomy):
        """
        @todo - add docs...
        """

        # Create the ION object we are wrapping
        self._g = Granule(data_producer_id=data_producer_id, taxonomy_id=taxonomy.tx_id)

        # hold onto the taxonomy - we need it to build the granule...
        self._tx = taxonomy.map


    def __setitem__(self, name, vals):
        """
        Give the GB a dictionary like behavior
        """

        self._g.record_dictionary[self._tx[name]] = vals


    def __getitem__(self, name):
        """
        Give the GB a dictionary like behavior
        """

        return self._g.record_dictionary[self._tx[name]]


class CompoundGranuleBuilder(object):
    """
    A compound granule is the ability to send many granules as one messsage - a list.
    """

    def __init__(self):
        """
        @todo - add docs...
        """

        # Create the ION object we are wrapping
        self._cg = CompoundGranule(granules=[])


    def add_granule(self, data_producer_id, taxonomy):


        gb = GranuleBuilder(data_producer_id=data_producer_id, taxonomy=taxonomy)
        self._cg.granules.append(g._g)

        return gb



class IterableExpression(dict):
    """
    This class should inherit from arange and dict, but I can't do that yet... Need to figure out how for type builtin

    Current interface:
    ie = IterableExpression(1.0, 10.0)
    1.0 == ie.sequence[0]

    for val in ie.sequence:
        ...

    """

    def __init__(self, start=None, stop=None, stride=None, dtype=None):

        dict.__init__(self, start=start, stop=stop, stride=stride, dtype=dtype)


        self.sequence = numpy.arange(start, stop, stride, dtype)



temp_array = numpy.random.standard_normal(100)
cond_array = numpy.random.standard_normal(100)
pres_array = numpy.random.standard_normal(100)

compound_type = numpy.dtype('2f8')

compound = numpy.ndarray(shape=(50,),dtype=compound_type)


time = IterableExpression(start=0.0,stop=100.0)


### Prototype interface discussed with Michael etal on Tuesday, 4/24/12
# g = Granule(manifest=rm)
#
# g['temp'] = temp
#


### Example:

tx = Taxonomy(tx_id='junk')
tx.map={'temp':'bar','cond':'foo','pres':'pressure'}
# map is {<local name>: <granule name or path>}

gb = GranuleBuilder(data_producer_id='john', taxonomy=tx)

gb['temp'] = temp_array
gb['cond'] = cond_array
gb['pres'] = pres_array






