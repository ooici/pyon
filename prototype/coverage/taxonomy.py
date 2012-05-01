#!/usr/bin/env python

'''
@package prototype.coverage.record_set
@file prototype/coverage/record_set.py
@author David Stuebe
@author Don Brittain
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


import yaml
from pyon.core.object import ion_serializer, IonObjectDeserializer
from pyon.core.registry import IonObjectRegistry

from interface.objects import Granule, CompoundGranule, Taxonomy

class GenericTaxonomyDescription(dict):

    def __init__(self,*args, **kwargs):

        dict.__init__(self, *args, **kwargs)

        self['_taxonomy_description_type'] = self.__class__.__name__

class GMLTaxonomyDescription(GenericTaxonomyDescription):
    pass

class ISOTaxonomyDescription(GenericTaxonomyDescription):
    pass

class ReferenceTaxonomyDescription(GenericTaxonomyDescription):
    pass

ior = IonObjectRegistry()

ion_deserializer = IonObjectDeserializer(obj_registry=ior)



class TaxyCab(object):
    """
    Wraps up a Taxonomy (IONObject) in a class which uses that information

    Definition of the Taxonomy Ion Resource:
    Taxonomy: !Extends_InformationResource
      map: {}

    The map is a dictionary which contains handles as keys and name sets as values.

    A name set is a set of objects which can be hashed for inverse lookup and should be serializable for transport and persistence

    In practice they are strings for nicknames and Taxonomy Description objects for complex definitions

    """

    def __init__(self, taxonomy=None):

        # An internal counter for the handles of this taxonomy
        self._cnt = 0

        self._inv = {}

        if taxonomy is None:
            taxonomy = Taxonomy()
        else:
            self._cnt = max(taxonomy.map.keys())

            for h, name_set in taxonomy.map.iteritems():
                self._update_inverse(h, name_set)

        self._t = taxonomy


    def _update_inverse(self, h, name_set):
        """
        Utility method to update the inverse index of names to handles
        """
        for name in name_set:

            #@todo is it safe to use the builtin hash method?
            name_hash = name.__hash__()

            h_set = self._inv.get(name_hash,set())
            h_set.add(h)

            self._inv[name_hash] = h_set


    def add_taxonomy_set(self, *args):
        """
        @brief Add a new set of names in the taxonomy under a new handle
        @param *args is a list of input arguments. All should be hashable
        """
        h = self._cnt
        self._t.map[h] = set()

        self._extend_taxonomy_set(h, *args)

        self._cnt += 1


    def get_handles(self, name):
        """
        @brief Get the handles for a particular name
        @param name is a object which is hashable
        @return set of handles
        """
        #@todo handle key errors?
        return self._inv[name.__hash__()]

    def get_handle(self, name):
        """
        Only works if the name maps to a unique handle
        @todo fix the exceptions later
        """
        s = self.get_handles(name)
        if len(s) != 1:
            #@todo use a better exception? Something consistent?
            raise RuntimeError('More than one handle for the name: "%s"!' % name)

        # can not index a set - best way to get the value out?
        t = tuple(s)
        return t[0]


    def get_names(self, handle):
        """
        Get the set of names associated with this handle
        """
        #@todo handle key errors?
        return self._t.map[handle]

    def extend_names(self, name, *args):
        """
        For a given existing name in the taxonomy add the additional names in args everywhere that name already appears
        in the taxonomy
        """

        for handle in self.get_handles(name):
            self._extend_taxonomy_set(handle, *args)


    def _extend_taxonomy_set(self, handle, *args):
        """
        Utility method that does the work of extending the a set and updating the inverse
        """

        for item in args:
            assert item.__hash__ is not None

        tmp_set = self._t.map[handle]
        # handle the key error in the caller!

        name_set = tmp_set.union(set(args))

        self._t.map[handle] = name_set

        self._update_inverse(handle, name_set)


    def dump(self):
        """
        Prototype dumping a taxonomy as yaml for an instrument agent to store locally.
        """

        d = ion_serializer.serialize(self._t)
        return yaml.dump(d)


    @classmethod
    def load(cls,input):
        """
        Prototype loading the locally stored yaml for and instrument agent to use in a TaxyCab
        """

        d = yaml.load(input)
        t = ion_deserializer.deserialize(d)

        return cls(t)



