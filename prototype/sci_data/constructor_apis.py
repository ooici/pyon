#!/usr/bin/env python


'''
@package prototype.hdf.constructor_apis
@file prototype/hdf/constructor_apis.py
@author David Stuebe
@brief These constructor classes are only used when building the internal science object model from an external form.
 These are helper classes that contain implicit knowledge of what the user intends to do so that it is not repeated or
 implemented adhoc by the user.
'''

from interface.objects import CoordinateAxis, StreamDefinitionContainer, ElementType, DataRecord, NilValue, Coverage, CategoryElement, UnitReferenceProperty, AllowedValues, Domain, Vector
from interface.objects import CountElement
from interface.objects import DataStream
from interface.objects import Encoding
from interface.objects import QuantityRangeElement
from interface.objects import RangeSet
from interface.objects import StreamGranuleContainer
import hashlib
import pyon
from pyon.core.object import ionprint

from prototype.hdf.hdf_codec import HDFEncoder, HDFEncoderException, HDFDecoder, HDFDecoderException
from pyon.util.log import log

class DefinitionTree(dict):
    """
    This is a utility class designed to allow easy access to the graph structure of the Stream IonObjects
    It is experimental, to support the needs of the data retriever service which builds stream definitions and
    stream granules on the fly.
    """

    def __init__(self, **kwargs):
        for k,v in kwargs.iteritems():
            if isinstance(v, dict):
                self[k] = DefinitionTree(**v)
            else:
                self[k] = v
    def __getattr__(self, key):
        if not hasattr(self, key):
            return None
        return self[key]
    def __setattr__(self, key,val):
        self[key] = val
    def __dir__(self):
        v = dir(super(DefinitionTree,self))
        return v + self.keys()

    @staticmethod
    def key(definition, key):
        try:
            retval = definition['identifiables'][key]
        except TypeError:
            print definition['identifiables']
            print key

        return definition['identifiables'][key]


    @staticmethod
    def traverse(definition, node_id):
        tmp = DefinitionTree.key(definition,node_id)
        root = DefinitionTree(**tmp)
        for k,v in tmp.iteritems():
            if k.endswith('_id'):
                if v:
                    root[k] = DefinitionTree.traverse(definition,v)
                    root[k].id = v
            elif k.endswith('_ids'):
                tmp = []
                for value in v:
                    if value:
                        t = DefinitionTree.traverse(definition,value)
                        t.id = value
                        tmp.append(t)
                root[k] = tmp
        return root

    @staticmethod
    def get(definition, key_path, node=None):
        '''
        Reduce for getting a specific value from a stream definition
        '''
        keys = key_path.split('.')
        if not node:
            key = keys.pop(0)
            node = definition.identifiables[key]
            return DefinitionTree.get(definition=definition,key_path='.'.join(keys),node=node)
        if len(keys) == 1:
            # Last key, this is the desired value
            key = keys.pop(0)
            return getattr(node,key)
        else:
            key = keys.pop(0)
            node = definition.identifiables[getattr(node,key)]
            return DefinitionTree.get(definition=definition,key_path='.'.join(keys),node=node)





    @staticmethod
    def obj_to_tree(definition):
        from pyon.core.object import IonObjectSerializer
        if not isinstance(definition,StreamDefinitionContainer):
            return
        serializer = IonObjectSerializer()
        definition = serializer.serialize(definition)
        tree = DefinitionTree.traverse(definition,definition['data_stream_id'])
        return tree


def insert_2d_geographic_coordinates(ident, vector, domain_name):
    """
    Add the geographic coordinate axis objects to the definition
    'http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Geographic'
    """

    vector.coordinate_ids = ['longitude_data','latitude_data']

    ident['latitude'] = Coverage(
        definition= "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Latitude",
        updatable=False,
        optional=True,

        domain_id=domain_name,
        range_id='latitude_data'
    )


    ident['latitude_data'] = CoordinateAxis(
        definition = "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Latitude",
        axis = "Latitude",
        constraint= AllowedValues(values=[[-90.0, 90.0],]),
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/latitude',
        unit_of_measure = UnitReferenceProperty(code='deg')
    )


    ident['longitude'] = Coverage(
        definition= "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#longitude",
        updatable=False,
        optional=True,

        domain_id=domain_name,
        range_id='longitude_data'
    )

    ident['longitude_data'] = CoordinateAxis(
        definition = "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Longitude",
        axis = "Longitude",
        constraint= AllowedValues(values=[[0.0, 360.0],]),
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/longitude',
        unit_of_measure = UnitReferenceProperty(code='deg')
    )

    # return a list of the coverages
    return ['latitude', 'longitude']



def insert_3d_geographic_coordinates(ident, vector, domain_name):
    """
    Add the geographic coordinate axis objects to the definition
    'http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Geographic'
    """

    coverage_names = insert_2d_geographic_coordinates(ident,vector,domain_name)

    vector.coordinate_ids.append('height_data')



    ident['height'] = Coverage(
        definition= "http://sweet.jpl.nasa.gov/2.0/spaceExtent.owl#Height",
        updatable=False,
        optional=True,

        domain_id=domain_name,
        range_id='height_data'
    )

    ident['height_data'] = CoordinateAxis(
        definition = "http://sweet.jpl.nasa.gov/2.0/spaceExtent.owl#Height",
        axis = "Height",
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/height',
        unit_of_measure = UnitReferenceProperty(code='deg')
    )

    # return a list of the coverages
    coverage_names.append('height')

    return coverage_names




class StreamDefinitionConstructor(object):
    """
    A science object constructor for a data stream definitions. This constructor is the canonical way to build the metadata
    object that defines the supplements published to the stream.
    """

    def __init__(self, description='', nil_value=None, encoding='hdf5'):
        """
        Instantiate a station dataset constructor.
        """
        self._stream_definition = StreamDefinitionContainer(
            data_stream_id='data_stream'
        )

        ident = self._stream_definition.identifiables

        ident['data_stream'] = DataStream(
            description=description,
            element_count_id='record_count',
            element_type_id='element_type',
            encoding_id='stream_encoding',
            values=None
        )

        ident['stream_encoding'] = Encoding(
            encoding_type=encoding,
            compression=None,
            sha1=None
        )

        ident['record_count'] = CountElement(
            value=0,
            optional=False,
            updatable=True
        )

        ident['element_type'] = ElementType(
            updatable=False,
            optional=False,
            data_record_id='data_record'
        )

        self._data_record = DataRecord()
        ident['data_record'] = self._data_record

        self._nil_value_name = []
        if nil_value is not None:
            self._nil_value_name = ['nan_value']
            ident['nan_value'] = NilValue(
                reason='No value recorded.',
                value=nil_value
            )




        # For ease of access in building data structure
        self._ident = ident

        # optional structure to use in building definition
        self.__domain =None
        self._domain_name = 'domain'

    @property
    def _domain(self):
        """
        Lazy initialize this component and add it to the identifiables
        """
        if self.__domain is None:
            self.__domain = Domain(
                definition='Need domain definition?',
                updatable='False',
                optional='False',
            )
            self._ident[self._domain_name] = self.__domain
            self._data_record.domain_ids = [self._domain_name,]
        return self.__domain


    @classmethod
    def LoadDefinition(cls, metadata_object):
        """
        Load an existing data structure
        """
        pass

    def define_temporal_coordinates(self, definition='', reference_frame='', reference_time=None, unit_code=''):
        """
        Complete definition of the temporal coordinates for this stream including its reference frame.
        """

        # Create the temporal coordinate vector
        self._domain.temporal_coordinate_vector_id = 'time_coordinates'

        self._ident['time_coordinates'] = Vector(
            definition = definition,
            coordinate_ids=['time_data',],
            reference_frame=reference_frame # Using coordinate
        )

        #@todo add switch on reference frame and definition to handle special cases
        #@todo check input values to make sure they are valid


        self._ident['time'] = Coverage(
            definition= definition,
            updatable=False,
            optional=False,
            domain_id=self._domain_name, # declared in _domain property above...
            range_id='time_data'
        )

        self._ident['time_data'] = CoordinateAxis(
            definition = definition,
            axis = "Time",
            nil_values_ids = ['nan_value'],
            mesh_location = CategoryElement(value='vertex'),
            values_path= '/fields/time',
            unit_of_measure = UnitReferenceProperty(code=unit_code),
            reference_frame = reference_frame,
            reference_value = reference_time
        )

        self._data_record.field_ids.append('time')

    def define_geospatial_coordinates(self, definition='', reference_frame=''):
        """
        Complete definition of the geospatial coordinates of this dataset including its reference frame
        """

        self._domain.geospatial_coordinate_vector_id = 'geo_coordinates'

        coord_vector = Vector(
            definition = definition,
            reference_frame = reference_frame, # Using coordinate
            updatable=False,
        )

        self._ident['geo_coordinates'] = coord_vector

        #@todo Use an EPSG CRS library for this!

        coverage_names = []

        if reference_frame == 'urn:ogc:def:crs:EPSG::4326':

            coverage_names = insert_2d_geographic_coordinates(self._ident, coord_vector, self._domain_name)

        elif reference_frame == 'urn:ogc:def:crs:EPSG::4979':

            coverage_names = insert_3d_geographic_coordinates(self._ident, coord_vector, self._domain_name)

        else:
            raise RuntimeError('Only two coordinate reference systems are supported at present: EPSG 4326 and 4979')

        self._data_record.field_ids.extend(coverage_names)


    def define_coverage(self, field_name='', field_definition='', field_units_code='', field_range=[]):
        """
        @brief define a coverage (observed quantity) present in the station dataset
        """
        self._add_coverage(
            name=field_name,
            definition=field_definition,
            updatable=False,
            optional=True
        )
        self._add_range(
            coverage_id=field_name,
            definition=field_definition,
            name='%s_data' % field_name,
            constraint=AllowedValues(values=[field_range,]),
            values_path='/fields/%s' % field_name,
            unit_of_measure_code=field_units_code,

        )


    def _add_coverage(self, name=None, definition=None, updatable=False, optional=True):
        if name in self._ident:
            log.warn('Field name "%s" already in identifiables!' % name)
            return 0

        coverage = Coverage(
            definition=definition,
            updatable=updatable,
            optional=optional,
            domain_id=self._domain_name,
            )



        self._data_record.field_ids.append(name)
        self._ident[name] = coverage


    def _add_range(self, coverage_id=None,
                  name=None,
                  definition=None,
                  axis=None,
                  constraint=None,
                  mesh_location='vertex',
                  values_path=None,
                  unit_of_measure_code=None,
                  ):
        """
        @brief Adds a coordinate axis range set to a coverage
        @param name The name of this range, i.e. temp_data
        @param definition URL to definition
        @param axis Name of physical Axis, i.e. Temperature, Time etc.
        @param constraint A constraint object
        @param mesh_location
        @param values_path Location of data points in HDF e.g. /fields/temp
        @param unit_of_measure_code Code for unit of measure
        """
        if name in self._ident:
            log.warn('Field name "%s" already in identifiables!' % name)
            return 0
        range = RangeSet(
            definition=definition,
            constraint=constraint,
            nil_values_ids= self._nil_value_name,
            mesh_location=CategoryElement(value=mesh_location),
            values_path=values_path,
            unit_of_measure=UnitReferenceProperty(code=unit_of_measure_code)
        )
        self._ident[name] = range
        coverage = self._ident[coverage_id]
        coverage.range_id = name


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
        return ionprint(self._stream_definition)

    def close_structure(self):
        """
        Method used to encode the station dataset metadata (structure)
        """
        return self._stream_definition


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

        time_coordinate_vector_id = domain.temporal_coordinate_vector_id
        time_coordinate_vector = point_definition.identifiables[time_coordinate_vector_id]

        assert time_coordinate_vector.reference_frame == 'http://www.opengis.net/def/trs/OGC/0/GPS'
        assert time_coordinate_vector.definition == 'http://www.opengis.net/def/property/OGC/0/SamplingTime'

        time_coord_axis = point_definition.identifiables[time_coordinate_vector.coordinate_ids[0]]

        time_axis = time_coord_axis.axis

        geo_coordinate_vector_id = domain.geospatial_coordinate_vector_id
        geo_coordinate_vector = point_definition.identifiables[geo_coordinate_vector_id]

        self.coordinate_axis = (None,)
        #@todo deal with this is a better way! Add more definitions too!
        if geo_coordinate_vector.reference_frame == 'urn:ogc:def:crs:EPSG::4326':

            # Use defined axis names from the CRS definition
            self.coordinate_axis = (time_axis,'Longitude','Latitude')
            # These are in order - we use the order when adding points
        elif geo_coordinate_vector.reference_frame == 'urn:ogc:def:crs:EPSG::4979':

            # Use defined axis names from the CRS definition
            self.coordinate_axis = (time_axis,'Longitude','Latitude','Height')
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

            records = coverage_info['records'] # Turn the list into an array
            if not records:
                log.warn('Coverage name "%s" has no values!' % coverage_info['id'])
                continue

            array = numpy.asarray(records) # Turn the list into an array

            # Add the coverage
            self._granule.identifiables[coverage_info['id']] = coverage_info['obj']

            # Add the range
            range = [float(numpy.nanmin(array)), float(numpy.nanmax(array))]
            self._granule.identifiables[coverage_info['obj'].bounds_id] = QuantityRangeElement(value_pair=range)

            # Add the data
            encoder.add_hdf_dataset(name=coverage_info['values_path'],nparray=array)

        for range_info in self._ranges.itervalues():

            records = range_info['records'] # Turn the list into an array
            if not records:
                log.warn('Range name "%s" has no values!' % range_info['id'])
                continue

            array = numpy.asarray(records) # Turn the list into an array

            # Add the coverage
            self._granule.identifiables[range_info['id']] = range_info['obj']

            # Add the range
            range = [float(numpy.nanmin(array)), float(numpy.nanmax(array))]
            self._granule.identifiables[range_info['obj'].bounds_id] = QuantityRangeElement(value_pair=range)

            # Add the data
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
