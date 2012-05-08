#!/usr/bin/env python

'''
@package pyon.ion.granule.record_dictionary
@file pyon/ion/granule/record_dictionary
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model

'''


import numpy
from interface.objects import Granule
from pyon.ion.granule.taxonomy import TaxyTool

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
        self._len = -1
        if length:
            self._len = length

        # hold onto the taxonomy - we need it to build the granule...
        self._tx = taxonomy

    @classmethod
    def load_from_granule(cls, g):
        result = cls(TaxyTool(g.taxonomy))
        result._rd = g.record_dictionary
        return result

    def __setitem__(self, name, vals):
        """
        Give the Record Dictionary Tool a dictionary like behavior
        """

        if isinstance(vals, RecordDictionaryTool):
            assert vals._tx == self._tx
            self._rd[self._tx.get_handle(name)] = vals._rd
        else:
            #@todo assert length matches self._len when setting value sequences
            if self._len == -1:
                self._len = len(vals)
            assert self._len == len(vals), 'Invalid value length'
            self._rd[self._tx.get_handle(name)] = vals


    def __getitem__(self, name):
        """
        Give the Record Dictionary Tool a dictionary like behavior
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
                yield self._tx.get_nick_name(k), result
            else:
                yield self._tx.get_nick_name(k), v

    def iterkeys(self):
        """ D.iterkeys() -> an iterator over the keys of D """
        for k in self._rd.iterkeys():
            yield self._tx.get_nick_name(k)

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
                    self[k] = E[k]
            else:
                for k, v in E.iteritems():
                    self[k] = v

        if F:
            for k in F.keys():
                self[k] = F[k]

    def __contains__(self, k):
        """ D.__contains__(k) -> True if D has a key k, else False """

        for handle in self._tx.get_handles(k):
            if handle in self._rd:
                return True

        return False

    def __delitem__(self, y):
        """ x.__delitem__(y) <==> del x[y] """
        #not sure if this is right, might just have to remove the name, not the whole handle
        del self._rd[self._tx.get_handle(y)]
        #will probably need to delete the name from _tx

    def __iter__(self):
        """ x.__iter__() <==> iter(x) """
        for k in self._rd.iterkeys():
            yield self._tx.get_nick_name(k)

    def __len__(self):
        """ x.__len__() <==> len(x) """
        return self._len

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
        result = ''
        for k, v in self.iteritems():
            if isinstance(v, RecordDictionaryTool):
                result += 'RDT %s contains:\n' % k
                result += v.pretty_print()
            else:
                result += '    item: %s\n    values: %s\n' % (k, v)

        return result

