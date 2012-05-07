#!/usr/bin/env python

'''
@package prototype.coverage.record_set
@file prototype/coverage/record_set.py
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model

@todo - move to pyon.ion.granule.record_dictionary
'''


import numpy
from interface.objects import Granule
from pyon.ion.granule.taxonomy import TaxyCab

import pprint
import StringIO

class RecordDictionaryTool(object):
    """
    A granule is a unit of information which conveys part of a coverage.

    A granule contains a record dictionary. The record dictionary is composed of named value sequences.
    We want the Granule Builder to have a dictionary like behavior for building record dictionaries, using the taxonomy
    as a map from the name to the ordinal in the record dictionary.

    The fact that all of the keys are ordinals mapped by the taxonomy should never be exposed

    Don't worry about raising exceptions at this point - put an @todo for now
    """
    def __init__(self,taxonomy, length=None):
        """
        @todo - add docs...
        """

        self._rd = {}

        self._len = length
        #@todo make length required

        # hold onto the taxonomy - we need it to build the granule...
        self._tx = taxonomy

    @classmethod
    def load_from_granule(cls, g):
        result = cls(TaxyCab(g.taxonomy))
        result._rd = g.record_dictionary
        return result

    def __setitem__(self, name, vals):
        """
        Give the GB a dictionary like behavior
        """

        if isinstance(vals, RecordDictionaryTool):
            assert vals._tx == self._tx
            self._rd[self._tx.get_handle(name)] = vals._rd
        else:
            #@todo assert length matches self._len when setting value sequences
            self._rd[self._tx.get_handle(name)] = vals


    def __getitem__(self, name):
        """
        Give the GB a dictionary like behavior
        """
        if isinstance(self._rd[self._tx.get_handle(name)], dict):
            result = RecordDictionaryTool(taxonomy=self._tx)
            result._rd = self._rd[self._tx.get_handle(name)]
            return result
        else:
            return self._rd[self._tx.get_handle(name)]


    def iteritems(self):
        """ D.iteritems() -> an iterator over the (key, value) items of D """
        for k, v in self._rd.iteritems():
            if isinstance(v, dict):
                result = RecordDictionaryTool(taxonomy=self._tx)
                result._rd = v
                yield self._tx.get_names(k), result
            else:
                yield self._tx.get_names(k), v

    def iterkeys(self):
        """ D.iterkeys() -> an iterator over the keys of D """
        for k in self._rd.iterkeys():
            yield self._tx.get_names(k)

    def itervalues(self):
        """ D.itervalues() -> an iterator over the values of D """
        for v in self._rd.itervalues():
            if isinstance(v, dict):
                result = RecordDictionaryTool(taxonomy=self._tx)
                result._rd = v
                yield result
            else:
                yield v

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
                    t = tuple(k)
                    self[t[0]] = E[k]
            else:
                for k, v in E.iteritems():
                    t = tuple(k)    #need to use a better index than this, but it works
                    self[t[0]] = v

        if F:
            for k in F.keys():
                t = tuple(k)
                self[t[0]] = F[k(0)]

    def __contains__(self, k):
        """ D.__contains__(k) -> True if D has a key k, else False """
        return self._tx.get_handle(k) >= 0

    def __delitem__(self, y):
        """ x.__delitem__(y) <==> del x[y] """
        #not sure if this is right, might just have to remove the name, not the whole handle
        del self._rd[self._tx.get_handle(y)]
        #will probably need to delete the name from _tx

    def __iter__(self):
        """ x.__iter__() <==> iter(x) """
        for k in self._rd.iterkeys():
            yield self._tx.get_names(k)

    def __len__(self):
        """ x.__len__() <==> len(x) """
        return len(self._rd)

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

    def pretty_print(self):
        #@todo Add pretty print method that returns a string - here is a good start, but not sure if it works with numpy...

        fstream = StringIO.StringIO()
        pprint.pprint(self._rd, stream=fstream)
        result = fstream.getvalue()
        fstream.close()
        return result


def build_granule(data_producer_id, taxonomy, record_dictionary):
    """
    This method is a simple wrapper that knows how to produce a granule IonObject from a RecordDictionaryTool and a TaxonomyTool

    A granule is a unit of information which conveys part of a coverage.

    A granule contains a record dictionary. The record dictionary is composed of named value sequences.
    We want the Granule Builder to have a dictionary like behavior for building record dictionaries, using the taxonomy
    as a map from the name to the ordinal in the record dictionary.

    @todo move to pyon.ion.granule.granule
    @todo add test module for this method and test this method and RDT.load_from_granule and TaxyTool.load_from_granule
    """
    return Granule(data_producer_id=data_producer_id, record_dictionary=record_dictionary._rd, taxonomy=taxonomy._t)



#@todo - move this to a module in examples.granule

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

#g = Granule(data_producer_id='john', taxonomy=tx._t,record_dictionary=rdt._rd)







