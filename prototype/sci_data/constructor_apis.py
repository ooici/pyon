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


    def __init__(self, point_definition=None, stream_id=None, number_of_packets_in_record=None, packet_number_in_record=None):
        """
        @param point_definition is the metadata object defining the point record for this stream
        @todo implement number_of_packets_in_record and packet_number_in_record
        """

        # do what ever you need to setup state based on the definition

        import numpy
        self._ranges = {}
        self._fields = []
        self._coordinates = {}

        self._granule = StreamGranuleContainer(
            stream_resource_id=point_definition.stream_resource_id or stream_id,
            data_stream_id=point_definition.data_stream_id
        )


        #Get the point definition's DataStream object
        data_stream = point_definition.identifiables[point_definition.data_stream_id]

        self._encoding_id = data_stream.encoding_id

        #Create a new CountElement object to keep track of the number of records
        self._element_count = CountElement()
        self._granule.identifiables[data_stream.element_count_id] = self._element_count

        #Get the point definition's ElementType object, contains data_record_id
        element_type_id = data_stream.element_type_id
        element_type = point_definition.identifiables[element_type_id]

        #Get the point definition's DataRecord object, contains list of coverage names
        data_record_id = element_type.data_record_id
        data_record = point_definition.identifiables[data_record_id]

        # Get the domain of the stream def
        domain_ids = data_record.domain_ids
        if len(domain_ids) is not 1:
            raise RuntimeError('PointSupplementConstructor does not support multiple domains per record')

        domain = point_definition.identifiables[domain_ids[0]]

        coordinate_vector_id = domain.coordinate_vector_id
        coordinate_vector = point_definition.identifiables[coordinate_vector_id]

        self.coordinate_axis = (None,)
        if coordinate_vector.definition == "http://sweet.jpl.nasa.gov/2.0/space.owl#Location":
            #@todo deal with this is a better way! Add more definitions too!
            self.coordinate_axis = ('Time','Longitude','Latitude','Pressure') # Don't think pressure really even belongs here!
            # These are in order - we use the order when adding points
        else:
            raise RuntimeError('Unknown coordinate vector definition for this stream definition')

        #Loop through the field IDs to get a list of CoordinateAxis and Range objects, save for adding records
        self._fields = data_record.field_ids
        for field_id in self._fields:

            coverage = point_definition.identifiables[field_id]

            obj = point_definition.identifiables[coverage.range_id]


            if isinstance(obj, CoordinateAxis): # Must check this first - CAxis inherits from RangeSet!
                # Get the name of the axis so we know what to do with it...
                index = self.coordinate_axis.index(obj.axis)

                self._coordinates[self.coordinate_axis[index]] = {'id':coverage.range_id,'obj':CoordinateAxis(bounds_id = field_id+'_bounds'),'records':[],'values_path':obj.values_path}

            elif isinstance(obj, RangeSet):
                self._ranges[field_id] = {'id':coverage.range_id,'obj':RangeSet(bounds_id = field_id+'_bounds'),'records':[],'values_path':obj.values_path}

            else:
                # this should never happen
                raise RuntimeError('Just checking!')


    def add_point(self, time=None, location=None):
        """
        Add a point to the dataset - one record

        @param time value of the current time step
        @param location tuple assumes order (x or lon, y or lat, (z or depth or pressure) )
        @retval point_id  is the record number of the point in this supplement
        """

        # calculate the bounds for time and location and create or update the bounds for the coordinate axis
        # hold onto the values so you can put them in an hdf...

        self._element_count.value += 1

        assert time, 'Can not create a point without a time value'

        assert location and len(location) == (len(self.coordinate_axis)-1), 'Must provide the correct number of location values'

        #@todo add some more type checking!

        self._coordinates[self.coordinate_axis[0]]['records'].append(time)

        for ind in xrange(len(location)):
            self._coordinates[self.coordinate_axis[ind+1]]['records'].append(location[ind])

        return self._element_count.value -1 # the actual index into the records list

    def add_scalar_point_coverage(self, point_id=None, coverage_id=None, value=None):
        """
        Add data for a particular point coverage.
        """
        # calculate the bounds for the values and create or update the bounds for the coverage
        # hold onto the values so you can put them in an hdf...

        try:
            records = self._ranges[coverage_id]['records']
        except KeyError:
            raise RuntimeError('Unexpected coverage_id for this stream definition!')

        if point_id < len(records):
            records[point_id] = value

        elif point_id == (len(records)):
            records.append(value)

        else:
            dlen = point_id - len(records)
            tup = [float('nan') for i in xrange(dlen) ] # is this even more efficient than append in a for loop?
            records.extend(tup)
            records[point_id] = value


    def add_attribute(self, subject_id, id=None, value=None):
        """
        Create a new attribute for the subject by passing a new id and value
        Add an existing attribute to the subject by passing just the subject_id and the id
        """
        # ignore for now...

    def close_stream_granule(self):

        import numpy

        encoder = HDFEncoder()

        for coverage_info in self._coordinates.itervalues():

            self._granule.identifiables[coverage_info['id']] = coverage_info['obj']
            array = numpy.asarray(coverage_info['records']) # Turn the list into an array
            range = [float(numpy.nanmin(array)), float(numpy.nanmax(array))]
            self._granule.identifiables[coverage_info['obj'].bounds_id] = QuantityRangeElement(value_pair=range)
            encoder.add_hdf_dataset(name=coverage_info['values_path'],nparray=array)

        for range_info in self._ranges.itervalues():

            self._granule.identifiables[range_info['id']] = range_info['obj']
            array = numpy.asarray(range_info['records']) # Turn the list into an array
            range = [float(numpy.nanmin(array)), float(numpy.nanmax(array))]
            self._granule.identifiables[range_info['obj'].bounds_id] = QuantityRangeElement(value_pair=range)
            encoder.add_hdf_dataset(name=range_info['values_path'],nparray=array)

        hdf_string = encoder.encoder_close()

        sha1 = hashlib.sha1(hdf_string).hexdigest().upper()
        self._granule.identifiables[self._encoding_id] = Encoding(
            encoding_type='hdf5',
            compression=None,
            sha1=sha1
        )

        self._granule.identifiables[self._granule.data_stream_id] = DataStream(
            values=hdf_string
        )

        return self._granule



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
