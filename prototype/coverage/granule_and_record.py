#!/usr/bin/env python

'''
@package prototype.coverage.record_set
@file prototype/coverage/record_set.py
@author David Stuebe
@author Swarbhanu Chatterjee
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''

from operator import mul
from pyon.core.exception import NotFound, BadRequest
from pyon.public import log
import itertools



class Granule(dict):
    """
    A granule is an object which can be sent as a message on a stream
    """

    def __init__(self, infoset_id, toposet_id, **kwargs):
        """
        A Granule is composed of a header and content. The header contains references to supporting information sets.
        The content is a record set (possible nested).

        The kwargs are (ordinal:entity set)
        """
        self['__ion_granule__'] = True
        self['infoset_id'] = infoset_id
        self['toposet_id'] = toposet_id

        self._record_set(**kwargs)

    def _record_set(self,**kwargs):

        rs = RecordSet(**kwargs)

        self['record_set'] = rs




class RecordSet(dict):
    """
    A Record Set is a collection of entity sets which have a shape. A entity set member can be accessed by ordinal.
    The Record Set can be sliced by by record.


    Todo:
    Is this a dict a list or an ion object?
    How do we add methods to an ion object?
    How do we encode this object so that we can decode as a RecordSet object?
    """

    def __init__(self, **kwargs):

        dict.__init__(self, **kwargs)
        self['__RecordSet__']=True


    def get_entity_set(self, ordinal):
        """
        Get an entity set by ordinal
        """
        return self[ordinal]

    def get_entity_type(self, ordinal):
        """
        Get the type of an entity set by ordinal
        """
        return self[ordinal].dtype


    def get_entity_rank(self, ordinal):
        """
        Get the rank of an entity set by ordinal
        """
        pass


    def get_records(self, slice):
        """
        Get a record (dict) from a record set by specifying a slice across all entity sets
        """
        pass

    def get_values(self, slice):
        """
        Get a tuple of values from specific ordinals and a specific slice of entity sets.
        """
        pass


class InfoSet(dict):
    """
    Infoset is a mapping of parameter nickname to a tuple of parameter id and ordinal for a particular infoset

    @todo make this an ion object?
    """

    def __init__(self,**kwargs):
        """
        Takes a dict of nickname and parameter ids as keyword args and auto-magically assigns ordinals

        Do not make assumptions about what the value of the ordinal is!
        """

        self['__InfoSet__']=True
        self['_ord_cnt']=0

        for nickname, parameter_id in kwargs.iteritems():
            self[nickname] = (parameter_id, str(self['_ord_cnt']))
            self['_ord_cnt'] += 1


    def get_ordinal(self,nickname):
        """
        for a given nickname give me an ordinal
        """
        return self[nickname][1]

    def get_parameter_id(self,nickname):
        """
        for a given nickname give me a parameter id
        """
        return self[nickname][0]

    def list_nicknames(self):
        return self.keys()



infoset = InfoSet(
    temp = '<temperature parameter resource id>',
    cond = '<conductivity parameter resource id>',
    pres = '<pressure parameter resource id>',
    time = '<time parameter resource id>',
    lat = '<latitude parameter resource id>',
    lon = '<longitude parameter resource id>',
    height = '<height parameter resource id>')

### Create a resource out of the info set...

id1 = 'Resource id for infoset'
id2 = 'Resource id for toposet'

import numpy

temp = numpy.arange(100)
cond = numpy.arange(100)
pres = numpy.arange(100)
time = numpy.arange(100)

ord_T = infoset.get_ordinal('temp')
ord_P = infoset.get_ordinal('pres')
ord_C = infoset.get_ordinal('cond')
ord_t = infoset.get_ordinal('time')

g = Granule(id1, id2, **{ord_T:temp, ord_C:cond, ord_P:pres, ord_t:time})