#!/usr/bin/env python

'''
@package prototype.coverage.record_set
@file prototype/coverage/record_set.py
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


from pyon.public import log
from pyon.util.containers import DotDict
import numpy
from interface.objects import Granule, CompoundGranule, Taxonomy



class GranuleBuilder(object):
    """
    A granule is a unit of information which conveys part of a coverage.

    A granule contains a record dictionary. The record dictionary is composed of named value sequences.
    We want the Granule Builder to have a dictionary like behavior for building record dictionaries, using the taxonomy
    as a map from the name to the ordinal in the record dictionary.

    The fact that all of the keys are ordinals mapped by the taxonomy should never be exposed

    Don't worry about raising exceptions at this point - put an @todo for now
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


    def iteritems(self):
        """ D.iteritems() -> an iterator over the (key, value) items of D """
        pass

    def iterkeys(self):
        """ D.iterkeys() -> an iterator over the keys of D """
        pass

    def itervalues(self):
        """ D.itervalues() -> an iterator over the values of D """
        pass

    def update(self, E=None, **F):
        """
        D.update(E, **F) -> None.  Update D from dict/iterable E and F.
        If E has a .keys() method, does:     for k in E: D[k] = E[k]
        If E lacks .keys() method, does:     for (k, v) in E: D[k] = v
        In either case, this is followed by: for k in F: D[k] = F[k]
        """
        pass

    def __contains__(self, k):
        """ D.__contains__(k) -> True if D has a key k, else False """
        return False

    def __delitem__(self, y):
        """ x.__delitem__(y) <==> del x[y] """
        pass

    def __iter__(self):
        """ x.__iter__() <==> iter(x) """
        pass

    def __len__(self):
        """ x.__len__() <==> len(x) """
        pass

    def __repr__(self):
        """ x.__repr__() <==> repr(x) """
        pass

    __hash__ = None



class CompoundGranuleBuilder(object):
    """
    A compound granule is the ability to send many granules as one messsage - a list.

    @Tim G - ignore this for now....
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





temp_array = numpy.random.standard_normal(100)
cond_array = numpy.random.standard_normal(100)
pres_array = numpy.random.standard_normal(100)

compound_type = numpy.dtype('2f8')

compound = numpy.ndarray(shape=(50,),dtype=compound_type)



### Prototype interface discussed with Michael etal on Tuesday, 4/24/12
# g = Granule(manifest=rm)
#
# g['temp'] = temp
#


### Example:

tx = Taxonomy(tx_id='junk')
tx.map={'temp':1,'cond':2,'pres':3}
# map is {<local name>: <granule name or path>}

gb = GranuleBuilder(data_producer_id='john', taxonomy=tx)

gb['temp'] = temp_array
gb['cond'] = cond_array
gb['pres'] = pres_array






