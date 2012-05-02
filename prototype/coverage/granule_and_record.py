#!/usr/bin/env python

'''
@package prototype.coverage.record_set
@file prototype/coverage/record_set.py
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


import numpy
from interface.objects import Granule, CompoundGranule, Taxonomy
from prototype.coverage.taxonomy import TaxyCab



class RecordDictionaryTool(object):
    """
    A granule is a unit of information which conveys part of a coverage.

    A granule contains a record dictionary. The record dictionary is composed of named value sequences.
    We want the Granule Builder to have a dictionary like behavior for building record dictionaries, using the taxonomy
    as a map from the name to the ordinal in the record dictionary.

    The fact that all of the keys are ordinals mapped by the taxonomy should never be exposed

    Don't worry about raising exceptions at this point - put an @todo for now
    """
    def __init__(self,taxonomy):
        """
        @todo - add docs...
        """

        self._rd = {}

        # hold onto the taxonomy - we need it to build the granule...
        self._tx = taxonomy


    def __setitem__(self, name, vals):
        """
        Give the GB a dictionary like behavior
        """

        #@todo - reflect on the type and determine how to add it. For a value sequence it is simple, for a nested record dictionary what should we do?
        self._rd[self._tx.get_handle(name)] = vals


    def __getitem__(self, name):
        """
        Give the GB a dictionary like behavior
        """
        #@todo - reflect on the return type and determine how to wrap it. For a value sequence it is simple, for a nested record dictionary what should we do?

        return self._rd[self._tx.get_handle(name)]


    def iteritems(self):
        """ D.iteritems() -> an iterator over the (key, value) items of D """
        for k, v in self._tx.iteritems():
            yield k, self._g.record_dictionary[v]

    def iterkeys(self):
        """ D.iterkeys() -> an iterator over the keys of D """
        for k in self._tx.iterkeys():
            yield k

    def itervalues(self):
        """ D.itervalues() -> an iterator over the values of D """
        for k in self._tx.iterkeys():
            yield self._g.record_dictionary[self._tx[k]]

    def update(self, E=None, **F):
        """
        D.update(E, **F) -> None.  Update D from dict/iterable E and F.
        If E has a .keys() method, does:     for k in E: D[k] = E[k]
        If E lacks .keys() method, does:     for (k, v) in E: D[k] = v
        In either case, this is followed by: for k in F: D[k] = F[k]
        """
        if E:
            if hasattr(E, "keys"):
                for k in E:
                    self._g.record_dictionary[self._tx[k]] = E[k]
            else:
                for k, v in E.iteritems():
                    self._g.record_dictionary[self._tx[k]] = v

        if F:
            for k in F.keys():
                self._g.record_dictionary[self._tx[k]] = F[k]

    def __contains__(self, k):
        """ D.__contains__(k) -> True if D has a key k, else False """
        return self._tx.has_key(k)

    def __delitem__(self, y):
        """ x.__delitem__(y) <==> del x[y] """
        del self._g.record_dictionary[self._tx[y]]
        del self._tx[y]

    def __iter__(self):
        """ x.__iter__() <==> iter(x) """
        for k in self._tx.iterkeys():
            yield k

    def __len__(self):
        """ x.__len__() <==> len(x) """
        return len(self._tx)

    def __repr__(self):
        """ x.__repr__() <==> repr(x) """
        result = "{"
        for k, v in self.iteritems():
            result += "\'{0}\': {1},".format(k, v)

        if len(result) > 1:
            result = result[:-1] + "}"

        return result

    def __str__(self):
        result = "{"
        for k, v in self.iteritems():
            result += "\'{0}\': {1},".format(k, v)

        if len(result) > 1:
            result = result[:-1] + "}"

        return result

    __hash__ = None


class GranuleBuilder(object):
    """
    A granule is a unit of information which conveys part of a coverage.

    A granule contains a record dictionary. The record dictionary is composed of named value sequences.
    We want the Granule Builder to have a dictionary like behavior for building record dictionaries, using the taxonomy
    as a map from the name to the ordinal in the record dictionary.

    @todo - what goes here? Anything?
    """





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

tx = TaxyCab()
tx.add_taxonomy_set('temp','long name for temp')
tx.add_taxonomy_set('cond','long name for cond')
tx.add_taxonomy_set('pres','long name for pres')
tx.add_taxonomy_set('group1')



rdt = RecordDictionaryTool(taxonomy=tx)

rdt['temp'] = temp_array
rdt['cond'] = cond_array
rdt['pres'] = pres_array


rdt2 = RecordDictionaryTool(taxonomy=tx)
rdt2['pres'] = pres_array

rdt['group1'] = rdt2



g = Granule(data_producer_id='john', taxonomy=tx._t,record_dictionary=rdt._rd)







