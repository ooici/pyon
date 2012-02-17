#!/usr/bin/env python


'''
@package prototype.hdf.constructor_apis
@file prototype/hdf/constructor_apis.py
@author David Stuebe
@brief These constructor classes are only used when building the internal science object model from an external form.
 These are helper classes that contain implicit knowledge of what the user intends to do so that it is not repeated or
 implemented adhoc by the user.
'''

from interface.objects import CoordinateAxis
from interface.objects import CountElement
from interface.objects import Encoding
from interface.objects import QuantityRangeElement
from interface.objects import StreamGranuleContainer
import pyon

from prototype.hdf.hdf_codec import HDFEncoder, HDFEncoderException, HDFDecoder, HDFDecoderException
from pyon.util.log import log

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


class PointDataStreamDefinitionConstructor(object):
    """
    A science object constructor for a point data stream. This constructor is the canonical way to build the metadata
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


class PointSupplementConstructor(object):

    _record_count_index = 'record_count'
    _time_index = 'time'
    _time_bounds_index = 'time_bounds'
    _longitude_index = 'longitude'
    _longitude_bounds_index = 'longitude_bounds'
    _latitude_index = 'latitude'
    _latitude_bounds_index = 'latitude_bounds'

    def __init__(self, stream_id='', point_definition=None, number_of_packets_in_record=None, packet_number_in_record=None):
        """
        @param point_definition is the metadata object defining the point record for this stream
        """

        # do what ever you need to setup state based on the definition

        self._times = []
        self._longitudes = []
        self._latitudes = []
        self._values = {}

        self._ctd_container = StreamGranuleContainer(
            stream_resource_id=stream_id,
            data_stream_id= 'ctd_data'
        )

        self._ctd_container.identifiables[self._record_count_index] = CountElement()
        self._ctd_container.identifiables[self._time_index] = CoordinateAxis(bounds_id=self._time_bounds_index)
        self._ctd_container.identifiables[self._longitude_index] = CoordinateAxis(bounds_id=self._longitude_bounds_index)
        self._ctd_container.identifiables[self._latitude_index] = CoordinateAxis(bounds_id=self._latitude_bounds_index)

        self._ctd_container.identifiables[self._time_bounds_index] = QuantityRangeElement()
        self._ctd_container.identifiables[self._longitude_bounds_index] = QuantityRangeElement()
        self._ctd_container.identifiables[self._latitude_bounds_index] = QuantityRangeElement()

    def add_point(self, time=None, location=None):
        """
        Add a point to the dataset - one record

        @param time value of the current time step
        @param location tuple of (lon, lat)
        @retval point_id  is the record number of the point in this supplement
        """

        # calculate the bounds for time and location and create or update the bounds for the coordinate axis
        # hold onto the values so you can put them in an hdf...

        self._ctd_container.identifiables[self._record_count_index].value += 1

        if not time is None:
            # Time
            self._times.extend(time)
            time_range = []
            time_range = [min(self._times), max(self._times)]
            self._ctd_container.identifiables[self._time_bounds_index].value_pair = time_range

        if not location is None:
            for loc in location:
                if len(loc) == 2:
                    # Longitude
                    self._longitudes.extend(loc[0])
                    lons_range = [min(self._longitudes), max(self._longitudes)]
                    self._ctd_container.identifiables[self._longitude_bounds_index].value_pair = lons_range

                    # Latitude
                    self._latitudes.extend(loc[1])
                    lats_range = [min(self._latitudes), max(self._latitudes)]
                    self._ctd_container.identifiables[self._latitude_bounds_index].value_pair = lats_range

            return self._ctd_container.identifiables[self._record_count_index].value

    def add_point_coverage(self, point_id=None, coverage_id=None, values=None, slice=None):
        """
        Add data for a particular point coverage . Slice represents the map to a known index structure for
        n-dimensional data that may exist at a point.
        """
        # calculate the bounds for the values and create or update the bounds for the coverage
        # hold onto the values so you can put them in an hdf...
        if not coverage_id in self._values:
            self._values[coverage_id] = []

        self._values[coverage_id].extend(values)

        range = [min(self._values[coverage_id]), max(self._values[coverage_id])]

        if not coverage_id in self._ctd_container.identifiables:
            self._ctd_container.identifiables[coverage_id] = QuantityRangeElement()
        self._ctd_container.identifiables[coverage_id].value_pair = range

    def add_attribute(self, subject_id, id=None, value=None):
        """
        Create a new attribute for the subject by passing a new id and value
        Add an existing attribute to the subject by passing just the subject_id and the id
        """
        # ignore for now...

    def _encode_supplement(self):
        """
        Method used to encode the point dataset supplement
        """

        # build the hdf and return the ion-object...
        hdf_string = ''
        try:
            # Use inline import to put off making numpy a requirement
            import numpy as np

            encoder = HDFEncoder()
            if self._times is not None:
                encoder.add_hdf_dataset('coordinates/time', np.asanyarray(self._times))

            if self._latitudes is not None:
                encoder.add_hdf_dataset('coordinates/latitude', np.asanyarray(self._latitudes))

            if self._longitudes is not None:
                encoder.add_hdf_dataset('coordinates/longitude', np.asanyarray(self._longitudes))

            for k, v in self._values.iteritems():
                encoder.add_hdf_dataset('fields/' + k, np.asanyarray(v))

            hdf_string = encoder.encoder_close()

            sha1 = pyon.datastore.couchdb.couchdb_datastore.sha1hex(hdf_string)
            return Encoding(sha1=sha1)
        except :
            log.exception('HDF encoder failed. Please make sure you have it properly installed!')



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
