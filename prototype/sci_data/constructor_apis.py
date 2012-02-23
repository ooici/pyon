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
from interface.objects import DataStream
from interface.objects import Encoding
from interface.objects import QuantityRangeElement
from interface.objects import RangeSet
from interface.objects import StreamGranuleContainer
import hashlib
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

    def __init__(self, point_definition=None, number_of_packets_in_record=None, packet_number_in_record=None):
        """
        @param point_definition is the metadata object defining the point record for this stream
        """

        # do what ever you need to setup state based on the definition

        import numpy
        self._times = []
        self._longitudes = []
        self._latitudes = []
        self._ranges = {}
        self._coordinate_axes = {}
        self._fields = []
        self._coordinates = []
        self._values = {}

        self._packet_container = StreamGranuleContainer(
            stream_resource_id=point_definition.stream_resource_id,
            data_stream_id=point_definition.data_stream_id
        )

        #Get the point definition's DataStream object
        data_stream = point_definition.identifiables[point_definition.data_stream_id]
        #Create a new CountElement object to keep track of the number of records
        self._element_count_id = data_stream.element_count_id
        self._packet_container.identifiables[self._element_count_id] = CountElement()

        #Get the point definition's ElementType object, contains data_record_id
        element_type_id = data_stream.element_type_id
        element_type = point_definition.identifiables[element_type_id]

        #Get the point definition's DataRecord object, contains list of coverage names
        data_record_id = element_type.data_record_id
        data_record = point_definition.identifiables[data_record_id]

        #Loop through the field IDs to get a list of CoordinateAxis and Range objects, save for adding records
        self._fields = data_record.field_ids
        for field_id in self._fields:
            coverage = point_definition.identifiables[field_id]

            domain_id = coverage.domain_id
            domain = point_definition.identifiables[domain_id]

            coordinate_vector_id = domain.coordinate_vector_id
            coordinate_vector = point_definition.identifiables[coordinate_vector_id]

            coordinate_ids = coordinate_vector.coordinate_ids
            for coordinate_id in coordinate_ids:
                if not coordinate_id in self._packet_container.identifiables:
                    coordinate_axis = point_definition.identifiables[coordinate_id]
                    self._coordinate_axes[coordinate_id] = coordinate_axis
                    self._packet_container.identifiables[coordinate_id] = CoordinateAxis(bounds_id=coordinate_id + '_bounds')
                    self._packet_container.identifiables[coordinate_id + '_bounds'] = QuantityRangeElement()

            if not field_id in self._packet_container.identifiables:
                self._packet_container.identifiables[field_id] = RangeSet(bounds_id=field_id + '_bounds')
                self._packet_container.identifiables[field_id + 'bounds'] = QuantityRangeElement()

            self._values[field_id] = []

    def add_point(self, time=None, location=None):
        """
        Add a point to the dataset - one record

        @param time value of the current time step
        @param location tuple of (lon, lat)
        @retval point_id  is the record number of the point in this supplement
        """

        # calculate the bounds for time and location and create or update the bounds for the coordinate axis
        # hold onto the values so you can put them in an hdf...

        self._packet_container.identifiables[self._element_count_id].value += 1

        if not time is None:
            # Time
            self._times = [time]

        if not location is None:
            if len(location) >= 2:
                # Longitude
                self._longitudes = [location[0]]

                # Latitude
                self._latitudes = [location[1]]

        return self._packet_container.identifiables[self._element_count_id].value

    def add_point_coverage(self, point_id=None, coverage_id=None, values=None, slice=None):
        """
        Add data for a particular point coverage . Slice represents the map to a known index structure for
        n-dimensional data that may exist at a point.
        """
        # calculate the bounds for the values and create or update the bounds for the coverage
        # hold onto the values so you can put them in an hdf...

        self._values[coverage_id] = values

        range = [min(self._values[coverage_id]), max(self._values[coverage_id])]

        if not coverage_id in self._packet_container.identifiables:
            self._packet_container.identifiables[coverage_id] = RangeSet(bounds_id=coverage_id + '_bounds')

        if not coverage_id + '_bounds' in self._packet_container.identifiables:
            self._packet_container.identifiables[coverage_id + '_bounds'] = QuantityRangeElement()

        self._packet_container.identifiables[coverage_id + '_bounds'].value_pair = range

    def add_attribute(self, subject_id, id=None, value=None):
        """
        Create a new attribute for the subject by passing a new id and value
        Add an existing attribute to the subject by passing just the subject_id and the id
        """
        # ignore for now...

    def get_stream_granule(self):
        self._packet_container.identifiables[self._packet_container.data_stream_id] = DataStream(
            id=self._packet_container.stream_resource_id,
            values=self._encode_supplement() # put the hdf file here as bytes!
        )

        return self._packet_container

    def _encode_supplement(self):
        """
        Method used to encode the point dataset supplement
        """
        def listify(input):
            if hasattr(input, '__iter__'):
                return input
            else:
                return [input,]

        # build the hdf and return the ion-object...
        hdf_string = ''
        try:
            import numpy
            encoder = HDFEncoder()
            #Need to search through the coordinate_axes dictionary to find out what the values_path
            #will be for the coordinate axes.
            #This assumes the coordinate axis names as described below. Will probably need to be
            #changed to accommodate other labels.
            for key, coordinate_axis in self._coordinate_axes.iteritems():

                if self._times is not None and coordinate_axis.axis.lower() == 'time':
                    time_range = [min(self._times), max(self._times)]
                    self._packet_container.identifiables[key + '_bounds'].value_pair = time_range

                    times = listify(self._times)
                    encoder.add_hdf_dataset(coordinate_axis.values_path, numpy.asanyarray(times))

                if self._longitudes is not None and coordinate_axis.axis.lower() == 'longitude':
                    lons_range = [min(self._times), max(self._times)]
                    self._packet_container.identifiables[key + '_bounds'].value_pair = lons_range

                    lons = listify(self._longitudes)
                    encoder.add_hdf_dataset(coordinate_axis.values_path, numpy.asanyarray(lons))

                if self._latitudes is not None and coordinate_axis.axis.lower() == 'latitude':
                    lats_range = [min(self._times), max(self._times)]
                    self._packet_container.identifiables[key + '_bounds'].value_pair = lats_range

                    lats = listify(self._latitudes)
                    encoder.add_hdf_dataset(coordinate_axis.values_path, numpy.asanyarray(lats))

            #Loop through ranges, one for each coverage. Range objects contain the values_path variable,
            #so use that to add values to the hdf.
            for key, range in self._ranges.iteritems():
                if key in self._values:
                    v = self._values[key]
                    encoder.add_hdf_dataset(range.values_path, numpy.asanyarray(v))

            hdf_string = encoder.encoder_close()

            sha1 = hashlib.sha1(hdf_string).hexdigest().upper()
            self._packet_container.identifiables['stream_encoding'] = Encoding(
                encoding_type='hdf5',
                compression=None,
                sha1=sha1
            )

            return hdf_string

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
