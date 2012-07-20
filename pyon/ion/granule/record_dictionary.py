#!/usr/bin/env python

'''
@package pyon.ion.granule.record_dictionary
@file pyon/ion/granule/record_dictionary
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''

import StringIO
from pyon.ion.granule.taxonomy import TaxyTool, Taxonomy
from pyon.util.log import log
import numpy

_NoneType = type(None)
class RecordDictionaryTool(object):
    """
    A granule is a unit of information which conveys part of a coverage. It is composed of a taxonomy and a nested
    structure of record dictionaries.

    The record dictionary is composed of named value sequences and other nested record dictionaries.

    The fact that all of the keys in the record dictionary are handles mapped by the taxonomy should never be exposed.
    The application user refers to everything in the record dictionary by the unique nick name from the taxonomy.

    """
    def __init__(self,taxonomy, shape=None):
        """
        @brief Initialize a new instance of Record Dictionary Tool with a taxonomy and an optional fixed length
        @param taxonomy is an instance of a TaxonomyTool or Taxonomy (IonObject) used in this record dictionary
        @param length is an optional fixed length for the value sequences of this record dictionary
        """
        if not isinstance(shape, (_NoneType, int, tuple)):
            raise TypeError('Invalid shape argument, received type "%s"; should be None or int or tuple' % type(shape))


        self._rd = {}
        self._shp = shape

        if isinstance(self._shp, int):
            self._shp = (self._shp,)

        # hold onto the taxonomy - we need it to build the granule...

        if isinstance(taxonomy, TaxyTool):
            self._tx = taxonomy
        elif isinstance(taxonomy, Taxonomy):
            self._tx = TaxyTool(taxonomy)
        else:
            raise TypeError('Invalid taxonomy argument, received type "%s"; should be Taxonomy or TaxyTool' % type(taxonomy))

    @classmethod
    def load_from_granule(cls, g):
        """
        @brief return an instance of Record Dictionary Tool from a granule. Used when a granule is received in a message
        """
        result = cls(TaxyTool(g.taxonomy))
        result._rd = g.record_dictionary
        if result._rd.has_key(0):
            result._shp = result._rd[0].shape
        return result

    def __setitem__(self, name, vals):
        """
        Set an item by nick name in the record dictionary
        """

        if isinstance(vals, RecordDictionaryTool):
            assert vals._tx == self._tx
            self._rd[self._tx.get_handle(name)] = vals._rd
        elif isinstance(vals, numpy.ndarray):
            #Otherwise it is a value sequence which should have the correct length

            # Matthew says: Assert only equal shape 5/17/12

            if vals.ndim == 0:
                raise ValueError('The rank of a value sequence array in a record dictionary must be greater than zero. Got name "%s" with rank "%d"' % (name, vals.ndim))

            # Set _shp if it is None
            if self._shp is None:
                self._shp = vals.shape

            # Test new value sequence length
            if self._shp != vals.shape:
                raise ValueError('Invalid array shape "%s" for name "%s"; Record dictionary defined shape is "%s"' % (vals.shape, name, self._shp))

            self._rd[self._tx.get_handle(name)] = vals

        else:

            raise TypeError('Invalid type "%s" in Record Dictionary Tool setitem with name "%s". Valid types are numpy.ndarray and RecordDictionaryTool' % (type(vals),name))

    def __getitem__(self, name):
        """
        Get an item by nick name from the record dictionary.
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
        @brief Dictionary update method exposed for Record Dictionaries
        @param E is another record dictionary
        @param F is a dictionary of nicknames and value sequences
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

    def __contains__(self, nick_name):
        """ D.__contains__(k) -> True if D has a key k, else False """

        try:
            handle = self._tx.get_handle(nick_name)
        except KeyError as ke:
            # if the nick_name is not in the taxonomy, it is certainly not in the record dictionary
            return False
        return handle in self._rd

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
        """
        @brief Pretty Print the record dictionary for debug or log purposes.
        """

        fid = StringIO.StringIO()
        # Use string IO inside a try block in case of exceptions or a large return value.
        try:
            fid.write('Start Pretty Print Record Dictionary:\n')
            self._pprint(fid,offset='')
            fid.write('End of Pretty Print')
        except Exception, ex:
            log.exception('Unexpected Exception in Pretty Print Wrapper!')
            fid.write('Exception! %s' % ex)

        finally:
            result = fid.getvalue()
            fid.close()


        return result

    def _pprint(self, fid, offset=None):
        """
        Utility method for pretty print
        """
        for k, v in self.iteritems():
            if isinstance(v, RecordDictionaryTool):
                fid.write('= %sRDT nick named "%s" contains:\n' % (offset,k))
                new_offset = offset + '+ '
                v._pprint(fid, offset=new_offset)
            else:
                fid.write('= %sRDT nick name: "%s"\n= %svalues: %s\n' % (offset,k, offset, repr(v)))
