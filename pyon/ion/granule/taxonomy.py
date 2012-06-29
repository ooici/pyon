#!/usr/bin/env python

'''
@package pyon.ion.granule.taxonomy
@file pyon.ion.granule.taxonomy.py
@author David Stuebe
@author Don Brittain
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''


import yaml
from pyon.core.object import ion_serializer, IonObjectDeserializer
from pyon.core.registry import IonObjectRegistry

from interface.objects import Taxonomy
from pyon.util.log import log


# Create an IonObjectDeserializer used in the prototype loads method...
ior = IonObjectRegistry()
ion_deserializer = IonObjectDeserializer(obj_registry=ior)


class TaxyTool(object):
    """
    @brief Wraps up a Taxonomy (IONObject) in a class which uses that information
    Definition of the Taxonomy Ion Resource:
    Taxonomy: !Extends_InformationResource
      map: {}

    The map is a dictionary which contains handles as keys and name sets as values.

    A name set is a set of objects which can be hashed for inverse lookup and should be serializable for transport and persistence

    In practice they are strings for nicknames and Taxonomy Description objects for complex definitions

    """

    def __init__(self, taxonomy=None):
        """
        @brief Initialize the state of the TaxyTool wrapper. Can take an existing taxonomy as an argument.
        """
        self._cnt = -1 # Cnt is not the length it a unique id in a map...

        self._inv = {}

        self._by_nick_names = {}

        if taxonomy is None:
            taxonomy = Taxonomy()
        else:
            self._cnt = max(taxonomy.map.keys())

            for h, names in taxonomy.map.iteritems():
                nick_name, name_set =  names

                self._add_nickname(nick_name, h)
                self._update_inverse(h, name_set)

        self._t = taxonomy

    @classmethod
    def load_from_granule(cls, g):
        """
        Load a TaxyTool from a granule
        """
        return cls(g.taxonomy)

    def _update_inverse(self, h, name_set):
        """
        Utility method to update the inverse index of names to handles
        """
        for name in name_set:

            #@todo is it safe to use the builtin hash method?
            assert name.__hash__ is not None, 'This name has no hash method!'

            h_set = self._inv.get(name,set())
            h_set.add(h)

            self._inv[name] = h_set


    def _add_nickname(self, nick_name, h):
        if nick_name not in self._by_nick_names:
            self._by_nick_names[nick_name] = h
        else:
            raise KeyError('The nick name "%s" is not unique in this taxonomy' % nick_name)

    def add_taxonomy_set(self, nick_name, *args):
        """
        @brief Add a new set of names in the taxonomy under a new handle
        @param nick_name is the first positional argument, it is unique name in the taxonomy
        @param *args is a list of input arguments. All should be hashable
        """
        self._cnt += 1
        h = self._cnt

        self._add_nickname(nick_name, h)

        self._t.map[h] = (nick_name, {nick_name,})

        self._extend_taxonomy_set(h, *args)



    def get_handles(self, name):
        """
        @brief Get the handles for a name
        @param name is a string or object which is hashable
        @return set of handles that have that name
        """
        if name in self._inv:
            return self._inv[name]
        else:
            return {-1,}

    def get_handle(self, nick_name):
        """
        @brief Get the handle for a given nick name
        @param nick_name is a unique name in the taxonomy
        @return handle is a integer identifier
        """

        return self._by_nick_names[nick_name]

    def get_nick_names(self, name):
        """
        @brief Get the nick names for a given name in the taxonomy
        @param name is a string or object which is hashable
        @return A set of nick names which are unique in the taxonomy
        """
        handles = self.get_handles(name)

        return [self._t.map[h][0] for h in handles]

    def get_names_by_handle(self, handle):
        """
        @brief Get the set of names associated with a handle
        @param handle is a integer identifier
        @return A set of names which can be strings or hashable objects
        """
        return self._t.map[handle][1]

    def get_names_by_nick_name(self, nick_name):
        """
        @brief Get the set of names associated with this nick name
        @param nick_name is a unique name in the taxonomy
        @return A set of nick names which are unique in the taxonomy
        """
        handle = self.get_handle(nick_name)
        return self._t.map[handle][1]


    def get_nick_name(self, handle):
        """
        @brief Get the set of nick name associated with a handle
        @param handle is a integer identifier
        @return nick name is a unique name in the taxonomy
        """
        return self._t.map[handle][0]

    def extend_names_by_nick_name(self, nick_name, *args):
        """
        @brief For a given existing nick name in the taxonomy add the additional names in args
        @param nick_name is a unique name in the taxonomy
        @param args is a list of names which can be strings or hashable objects
        @return None
        """

        handle = self._by_nick_names[nick_name]
        self._extend_taxonomy_set(handle, *args)


    def extend_names_by_anyname(self, name, *args):
        """
        @breif For a given existing name in the taxonomy add the additional names in args everywhere that name already appears
        in the taxonomy
        @param name is a string or object which is hashable
        @param args is a list of names which can be strings or hashable objects
        @return None
        """

        for handle in self.get_handles(name):
            self._extend_taxonomy_set(handle, *args)


    def _extend_taxonomy_set(self, handle, *args):
        """
        Utility method that does the work of extending the a set and updating the inverse
        """

        for item in args:
            assert item.__hash__ is not None

        nick_name, tmp_set = self._t.map[handle]
        # handle the key error in the caller!

        name_set = tmp_set.union(set(args))

        self._t.map[handle] = (nick_name, name_set)

        self._update_inverse(handle, name_set)


    def pretty_print(self, offset=''):
        result = 'Start Pretty Print Taxonomy:'
        for k, v in self._t.map.iteritems():

            result += '\n= TX nick name: "%s"; handle "%s"' % (v[0], k)
            for name in v[1]:
                result += '\n= +name: %s' % name

        result += '\nEnd of Pretty Print'
        return result

    def dump(self):
        """
        @brief Prototype dumping a taxonomy as yaml for instance for an instrument agent to store locally.
        """

        #@todo - need to serialize sets to yaml???
        d = ion_serializer.serialize(self._t)
        return yaml.dump(d)


    @classmethod
    def load(cls,input):
        """
        @brief Prototype loading the locally stored yaml for instance for an instrument agent to use in a TaxyTool
        """

        d = yaml.load(input)
        t = ion_deserializer.deserialize(d)

        # We know the structure - turn the lists back into sets!
        try:
            for k, v in t.map.iteritems():
                t.map[k] = (v[0], set(v[1]))
        except IndexError:
            log.exception("Invalid taxonomy object structure: should be Key:(nickname, {alias',})")

        return cls(t)

    def __eq__(self, other):

        if self is other:
            return True

        if not isinstance(other, TaxyTool):
            return False

        if self._t is other._t:
            return True

        if self._t.map == other._t.map:
            return True

        return False

    def __ne__(self, other):
        return not self == other


