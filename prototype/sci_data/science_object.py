#!/usr/bin/env python


'''
@package prototype.science_object
@file prototype/science_object.py
@author David Stuebe
@brief prototype interface to the science data object
'''

import uuid


def create_guid():
    """
    @retval Return global unique id string
    """
    # I find the guids more readable if they are UPPERCASE
    return str(uuid.uuid4()).upper()


class AbstractIdentifiable(object):

    def __init__(self, name, id=None):
        # an identifier for every object
        if id is None:
            id = create_guid()
        self._id = id
        self.name = name

class DataStream(AbstractIdentifiable):
    """
    SWE Data Stream - defines the content of a data stream
    """

    def __init__(self, name, stream_id, record_name):
        AbstractIdentifiable.__init__(self,name, id=stream_id)

        self._element_type = None
        self._element_count = -1 #no inf for integers
        self._encoding = None
        self._values = None


class ElementType(AbstractIdentifiable):
    """
    SWE Element Type - describes the content and aggregation of the data records in the stream
    """

    def __init__(self, name, stream_id, record_name):
        AbstractIdentifiable.__init__(self,name, id=stream_id)

        self._data_record = None

    @property
    def data_record(self):
        return self._data_record

class Attribute(AbstractIdentifiable):
    """
    Class for generic attribute information attached to a coverage or element type
    """
    def __init__(self, name, stream_id, record_name):
        AbstractIdentifiable.__init__(self,name, id=stream_id)


class DataRecord(AbstractIdentifiable):
    """
    SWE Data Record - defines the content of one record in the stream containing one or more coverages
    """
    def __init__(self, record_name=None, id=None):
        AbstractIdentifiable.__init__(self, name=record_name, id=id)

        self._coverages = {}

    def add_coverage(self, coverage):
        assert isinstance(coverage,BaseCoverage), "Add coverage argument must be an instance of BaseCoverage"

        self._coverages[coverage._id] = coverage
        return coverage

class BaseCoverage(AbstractIdentifiable):

    def __init__(self, domain=None, range=None, name=None, id=None):
        AbstractIdentifiable.__init__(self, name, id)

        self._domain = domain
        self._range = range
        self._meta_data = {}

    def add_attribute(self,attribute):
        assert isinstance(attribute,Attribute), "Add attribute argument must be an instance of Attribute"

        self._meta_data[attribute._id] = attribute

class Domain(AbstractIdentifiable):

    def __init__(self, mesh=None, name=None, id=None):
        AbstractIdentifiable.__init__(self, name, id)

        self._mesh = mesh

        self._coordiante_system = {}
        self._coordinates = {}


    def add_coordinate(self, coordinate_name, coordinate_array):
        self._coordiante_system[coordinate_name] = coordinate_array

class Range(AbstractIdentifiable):
    def __init__(self, array=None, definition=None, uom=None, name=None, id=None):
        AbstractIdentifiable.__init__(self, name, id)


class NilValues(AbstractIdentifiable):
    def __init__(self, name=None, id=None):
        AbstractIdentifiable.__init__(self, name, id)

        self._nils = {}

    def add_nil_val(self, value, reason):
        self._nils[reason] = value


class BaseMesh(AbstractIdentifiable):
    def __init__(self, topological_dimension, geometric_dimension, name=None, id=None):
        AbstractIdentifiable.__init__(self, name, id)

        self._topo_dim = topological_dimension
        self._geo_dim = geometric_dimension

        self.n_elements = -1
        self.n_verticies = -1


class ExplicitMesh(BaseMesh):

    def set_topology(self, array):
        pass



class ImplicitMesh(BaseMesh):
    pass


#class DataArray(AbstractIdentifiable):
#
#    def __init__(self):
#        AbstractIdentifiable.__init__(self)


class RecordPacketBuilder(object):
    """
    Class to construct a message for sending an entire record
    """

    def __init__(self, stream_record):

        self._stream_record = stream_record


    def add_coverage_range_data(self, coverage, values, map=None):
        pass

    def add_domain_coordinate_data(self, domain, coordinate_name, values, map=None):
       pass

