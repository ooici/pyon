#!/usr/bin/env python


'''
@package prototype.hdf.constructor_apis
@file prototype/hdf/constructor_apis.py
@author David Stuebe
@brief These constructor classes are only used when building the internal science object model from an external form.
 These are helper classes that contain implicit knowledge of what the user intends to do so that it is not repeated or
 implemented adhoc by the user.
'''



class StationDataStreamDefinitionConstructor(object):
    """
    A science object constructor for a station data stream. This constructor is the canonical way to build the metadata
    object that defines the supplements published to the stream.
    """

    def __init__(self,):
        """
        Instantiate a station dataset constructor.
        """

    @classmethod
    def LoadStationDefinition(cls, metadata_object):
        """
        Load an existing data structure
        """
        pass

    def define_reference_frame(self, temporal=None, geospatial=None):
        """
        define the reference frame for each and provide an absolute reference for each
        """


    def define_coverage(self, id=None, units=None, standard_name=None, coverage_dimensions=None):
        """
        @brief define a coverage (observed quantity) present in the station dataset
        """

    def add_nil_values(self, coverage_id=None, value=None, reason=None):
        """
        Add nil values to a particular coverage
        """


    def add_attribute(self, subject_id, id=None, value=None):
        """
        Create a new attribute for the subject by passing a new id and value
        Add an existing attribute to the subject by passing just the subject_id and the id
        """

    def __str__(self):
        """
        Print the dataset metadata for debug purposes.
        """
        pass

    def _encode_structure(self):
        """
        Method used to encode the station dataset metadata (structure)
        """
        pass


class StationSupplementConstructor(object):

    def __init__(self, station_definition=None, number_of_packets_in_record=None, packet_number_in_record=None):
        """
        @param station_definition is the metadata object defining the station record for this stream
        """


    def add_station(self, station_id=None, time=None, location=None):
        """
        Add a station to the dataset
        """

    def add_station_coverage(self, station_id=None, coverage_id=None, values=None, slice=None):
        """
        Add data for a particular coverage to a station. Slice represents the map to a know index structure for
        n-dimensional data.
        """

    def add_attribute(self, subject_id, id=None, value=None):
        """
        Create a new attribute for the subject by passing a new id and value
        Add an existing attribute to the subject by passing just the subject_id and the id
        """

    def _encode_supplement(self):
        """
        Method used to encode the station dataset supplement
        """


class StationTimeSeries(object):
    """
    A science object constructor for time series dataset at a station.
    """

class Trajectory(object):
    """
    A science object constructor for trajectory data.
    """

class StructuredMeshDataStreamDefinition(object):
    """
    A science object constructor for mesh data. This constructor is the canonical way to build the metadata
    object that defines the supplements published to the stream.
    """

    @classmethod
    def LoadStructuredMeshDefinition(cls, metadata_object):
        """
        Load an existing data structure
        """
        pass

    def define_reference_frame(self, temporal=None, geospatial=None):
        """
        define the reference frame for each and provide an absolute reference for each
        """

    def define_geospatial_domain(self, id=None, x_coordinate_values=None, y_coordinate_values=None, z_coordinate_values=None ):
        pass


    def define_coverage(self, id=None, units=None, standard_name=None, coverage_dimensions=None, mesh_location=None):
        pass

    def add_nil_values(self, coverage_id=None, value=None, reason=None):
        """
        Add nil values to a particular coverage
        """

    def add_attribute(self, subject_id, id=None, value=None):
        """
        Create a new attribute for the subject by passing a new id and value
        Add an existing attribute to the subject by passing just the subject_id and the id
        """

    def __str__(self):
        """
        Print the dataset metadata for debug purposes.
        """
        pass

    def _encode_structure(self):
        """
        Method used to encode the station dataset metadata (structure)
        """
        pass



class StructuredMeshSupplement(object):

    def __init__(self, station_definition=None, number_of_packets_in_record=None, packet_number_in_record=None):
        """
        @param station_definition is the metadata object defining the station record for this stream
        """

    def add_temporal_domain(self, values=None):
        """
        """


    def add_station_coverage(self, station_id=None, coverage_id=None, values=None, slice=None):
        """
        Add data for a particular coverage to a station. Slice represents the map to a know index structure for
        n-dimensional data.
        """

    def add_attribute(self, subject_id, id=None, value=None):
        """
        Create a new attribute for the subject by passing a new id and value
        Add an existing attribute to the subject by passing just the subject_id and the id
        """

    def _encode_supplement(self):
        """
        Method used to encode the station dataset supplement
        """
