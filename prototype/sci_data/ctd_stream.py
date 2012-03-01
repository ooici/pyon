#!/usr/bin/env python

'''
@author David Stuebe <dstuebe@asascience.com>
@file prototype/sci_data/ctd_stream.py
@description An example process producing a ctd data stream
'''

from interface.objects import StreamDefinitionContainer, StreamGranuleContainer #, DataContainer
from interface.objects import DataStream, ElementType, DataRecord, Vector, Coverage, RangeSet, Domain, Mesh, CoordinateAxis, Encoding
from interface.objects import UnitReferenceProperty, NilValue, AllowedValues #, ElapsedTime, AllowedTokens, AllowedTimes
from interface.objects import CategoryElement, CountElement #, BooleanElement, TextElement, CountRangeElement
from interface.objects import QuantityRangeElement #, QuantityElement, TimeElement, TimeRangeElement
#from interface.objects import AbstractIdentifiable, AbstractDataComponent, AbstractSimpleComponent
#from interface.objects import QualityQuantityProperty, QualityQuantityRangeProperty, QualityCatagoryProperty, QualityTextProperty

from prototype.hdf.hdf_codec import HDFEncoder #, HDFEncoderException, HDFDecoder, HDFDecoderException

import hashlib

from pyon.util.log import log


def ctd_stream_definition(stream_id=None):
    """
    ###
    ### This method is highly suspect and subject to revision. Do not lien heavily on it or you will suffer refactoring
    ###


    This is a convenience method to construct a CTD data stream definition object. More generic stream definition
     constructors will be added later.
    @brief creates an ion object containing the definition of a seabird ctd data stream
    @param stream_id is the resource id of the data stream for this definition
    @retval ctd_container is an ion object which contains the definition of the stream
    """

    # data stream id is the identifier for the DataStream object - the root of the data structure
    ctd_container = StreamDefinitionContainer(
        stream_resource_id=stream_id,
        data_stream_id= 'ctd_data',
        )


    ctd_container.identifiables['ctd_data'] = DataStream(
        label='Seabird CTD Data',
        description='Conductivity temperature and depth observations from a Seabird CTD',
        element_count_id='record_count',
        element_type_id='element_type',
        encoding_id='stream_encoding',
        values=None
        )

    ctd_container.identifiables['record_count'] = CountElement(value=0)

    ctd_container.identifiables['element_type'] = ElementType(
        definition="Ref to SeaBird data?",
        updatable=False,
        optional=False,
        data_record_id='data_record')


    ctd_container.identifiables['data_record'] = DataRecord(
        field_ids=['temperature','conductivity','pressure','latitude','longitude','time'],
        domain_ids=['time_domain'],
        definition = "Definition of a data record for a CTD",
        updatable=False,
        optional=False,
        )


    ctd_container.identifiables['nan_value'] = NilValue(
        reason= "No value recorded",
        value= -999.99
    )

    ctd_container.identifiables['temperature'] = Coverage(
            definition= "http://sweet.jpl.nasa.gov/2.0/physThermo.owl#Temperature",
            updatable=False,
            optional=True,

            domain_id='time_domain',
            range_id='temp_data'
            )

    ctd_container.identifiables['temp_data'] = RangeSet(
        definition= "http://sweet.jpl.nasa.gov/2.0/physThermo.owl#Temperature",
        nil_values_ids = ['nan_value',],
        mesh_location= CategoryElement(value='vertex'),
        constraint= AllowedValues(values=[[-10.0, 50.0],]),
        unit_of_measure= UnitReferenceProperty(code='Cel'),
        values_path="/fields/temp_data",
    )


    ctd_container.identifiables['conductivity'] = Coverage(
        definition= "http://sweet.jpl.nasa.gov/2.0/physThermo.owl#Conductivity", # No idea if this is the correct def to use!
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='cndr_data'
    )

    ctd_container.identifiables['cndr_data'] = RangeSet(
        definition= "http://sweet.jpl.nasa.gov/2.0/physThermo.owl#Conductivity",
        nil_values_ids = ['nan_value',],
        mesh_location= CategoryElement(value='vertex'),
        constraint= AllowedValues(values=[[0.0, 85.0],]), # Normal range for ocean
        unit_of_measure= UnitReferenceProperty(code='mS/cm'), # milli Siemens per centimeter
        values_path="/fields/cndr_data",
    )


    ctd_container.identifiables['time_domain'] = Domain(
        definition='Spec for ctd data time domain',
        updatable='False',
        optional='False',
        coordinate_vector_id='coordinate_vector',
        mesh_id='point_timeseries'
        )

    ctd_container.identifiables['coordinate_vector']= Vector(
        definition = "http://sweet.jpl.nasa.gov/2.0/space.owl#Location",
        # need a definition that includes pressure as a coordinate???
        coordinate_ids=['longitude_data','latitude_data','pressure_data','time_data'],
        reference_frame="http://www.opengis.net/def/crs/EPSG/0/4326"
    )

    ctd_container.identifiables['pressure'] = Coverage(
        definition= "http://sweet.jpl.nasa.gov/2.0/physThermo.owl#Pressure", # No idea if this is correct!
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='pressure_data'
    )

    ctd_container.identifiables['pressure_data'] = CoordinateAxis(
        definition= "http://sweet.jpl.nasa.gov/2.0/physThermo.owl#Pressure", # No idea if this is correct!
        nil_values_ids = ['nan_value',],
        axis = "Pressure",
        mesh_location= CategoryElement(value='vertex'),
        constraint= AllowedValues(values=[[0, 10000.0],]), # rough range, approximately 0 to 10km
        unit_of_measure= UnitReferenceProperty(code='dbar'), # bar is a unit of pressure used in oceanography
        values_path="/fields/pressure_data",
        reference_frame='Atmospheric pressure ?'
    )

    ctd_container.identifiables['latitude'] = Coverage(
        definition= "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Latitude",
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='latitude_data'
    )


    ctd_container.identifiables['latitude_data'] = CoordinateAxis(
        definition = "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Latitude",
        axis = "Latitude",
        constraint= AllowedValues(values=[[-90.0, 90.0],]),
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/latitude',
        unit_of_measure = UnitReferenceProperty(code='deg')
    )


    ctd_container.identifiables['longitude'] = Coverage(
        definition= "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#longitude",
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='longitude_data'
    )

    ctd_container.identifiables['longitude_data'] = CoordinateAxis(
        definition = "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Longitude",
        axis = "Longitude",
        constraint= AllowedValues(values=[[0.0, 360.0],]),
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/longitude',
        unit_of_measure = UnitReferenceProperty(code='deg')
    )


    ctd_container.identifiables['time'] = Coverage(
        definition= "http://www.opengis.net/def/property/OGC/0/SamplingTime",
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='time_data'
    )

    ctd_container.identifiables['time_data'] = CoordinateAxis(
        definition = "http://www.opengis.net/def/property/OGC/0/SamplingTime",
        axis = "Time",
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/time',
        unit_of_measure = UnitReferenceProperty(code='s'),
        reference_frame="http://www.opengis.net/def/trs/OGC/0/GPS"
    )
    
    ctd_container.identifiables['point_timeseries'] = Mesh(
        mesh_type = CategoryElement(value="Point Time Series"),
        values_path = "/topology/mesh",
        index_offset = 0,
        number_of_elements = 1,
        number_of_verticies = 1,
    )
    
    ctd_container.identifiables['stream_encoding'] = Encoding(
        encoding_type = 'hdf5',
        compression = None,
        sha1 = None
    )
    
    

    return ctd_container

def usgs_stream_definition(stream_id=None):
    """
    ###
    ### This method is highly suspect and subject to revision. Do not lien heavily on it or you will suffer refactoring
    ###


    This is a convenience method to construct a CTD data stream definition object. More generic stream definition
     constructors will be added later.
    @brief creates an ion object containing the definition of a seabird ctd data stream
    @param stream_id is the resource id of the data stream for this definition
    @retval ctd_container is an ion object which contains the definition of the stream
    """

    # data stream id is the identifier for the DataStream object - the root of the data structure
    ctd_container = StreamDefinitionContainer(
        stream_resource_id=stream_id,
        data_stream_id= 'usgs_data',
    )


    ctd_container.identifiables['usgs_data'] = DataStream(
        label='USGS water data',
        description='Connecticut River at Thompsonville CT (01184000) - Daily Value',
        element_count_id='record_count',
        element_type_id='element_type',
        encoding_id='stream_encoding',
        values=None
    )

    ctd_container.identifiables['record_count'] = CountElement(value=0)

    ctd_container.identifiables['element_type'] = ElementType(
        definition="Ref to USGS data?",
        updatable=False,
        optional=False,
        data_record_id='data_record')


    ctd_container.identifiables['data_record'] = DataRecord(
        #field_ids=['stnId','lon','lat','time','z','water_height','data_qualifier','water_temperature','streamflow','water_height_datum'],
        field_ids=['lon','lat','time','water_height','water_temperature','streamflow'],
        domain_ids=['time_domain'],
        definition = "Definition of a data record for USGS",
        updatable=False,
        optional=False,
    )


    ctd_container.identifiables['nan_value'] = NilValue(
        reason= "No value recorded",
        value= -999.99
    )

    ctd_container.identifiables['lon'] = Coverage(
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='lon_data'
    )

    ctd_container.identifiables['lon_data'] = CoordinateAxis(
        axis = "Longitude",
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/longitude',
        unit_of_measure = UnitReferenceProperty(code='deg'),
        reference_frame="http://www.opengis.net/def/trs/OGC/0/GPS"
    )


    ctd_container.identifiables['lat'] = Coverage(
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='lat_data'
    )

    ctd_container.identifiables['lat_data'] = CoordinateAxis(
        definition = "http://www.opengis.net/def/property/OGC/0/SamplingTime",
        axis = "Latitude",
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/latitude',
        unit_of_measure = UnitReferenceProperty(code='deg'),
        reference_frame="http://www.opengis.net/def/trs/OGC/0/GPS"
    )

    ctd_container.identifiables['time'] = Coverage(
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='time_data'
    )

    ctd_container.identifiables['time_data'] = CoordinateAxis(
        definition = "http://www.opengis.net/def/property/OGC/0/SamplingTime",
        axis = "Time",
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/time',
        unit_of_measure = UnitReferenceProperty(code='s'),
        reference_frame="http://www.opengis.net/def/trs/OGC/0/GPS"
    )

    ctd_container.identifiables['water_height'] = Coverage(
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='water_height_data'
    )

    ctd_container.identifiables['water_height_data'] = RangeSet(
        nil_values_ids = ['nan_value',],
        unit_of_measure= UnitReferenceProperty(code='ft'),
        values_path="/fields/water_height",
    )

    ctd_container.identifiables['water_temperature'] = Coverage(
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='water_temperature_data'
    )

    ctd_container.identifiables['water_temperature_data'] = RangeSet(
        nil_values_ids = ['nan_value',],
        unit_of_measure= UnitReferenceProperty(code='ft'),
        values_path="/fields/water_temperature",
    )

    ctd_container.identifiables['streamflow'] = Coverage(
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='streamflow_data'
    )

    ctd_container.identifiables['streamflow_data'] = RangeSet(
        nil_values_ids = ['nan_value',],
        unit_of_measure= UnitReferenceProperty(code='ft3 s-1'),
        values_path="/fields/streamflow",
    )

    ctd_container.identifiables['time_domain'] = Domain(
        definition='Spec for ctd data time domain',
        updatable='False',
        optional='False',
        coordinate_vector_id='coordinate_vector',
        mesh_id='point_timeseries'
    )

    ctd_container.identifiables['coordinate_vector']= Vector(
        definition="http://www.usgs.gov",
        # need a definition that includes pressure as a coordinate???
        coordinate_ids=['lon_data','lat_data','time_data'],
        reference_frame="http://www.opengis.net/def/crs/EPSG/0/4326"
    )

    ctd_container.identifiables['point_timeseries'] = Mesh(
        mesh_type = CategoryElement(value="Point Time Series"),
        values_path = "/topology/mesh",
        index_offset = 0,
        number_of_elements = 1,
        number_of_verticies = 1,
    )

    ctd_container.identifiables['stream_encoding'] = Encoding(
        encoding_type = 'hdf5',
        compression = None,
        sha1 = None
    )



    return ctd_container

def scalar_point_stream_definition(description='', field_name='', field_definition='', field_units_code='', field_range=[]):
    """
    ###
    ### This method is highly suspect and subject to revision. Do not lien heavily on it or you will suffer refactoring
    ###


    This is a convenience method to construct a scalar point stream definition object for a single signal.
    More generic stream definition constructors will be added later.

    Does this really make sense? Can we have an interface like this to build a stream def? I don't think so. I think
    Steam defs must be highly specialized to the data they contain.

    @brief creates an ion object containing the definition of a scalar value stream
    @param description is a top level human readable description of the stream content
    @retval stream_def is an ion object which contains the definition of the stream
    """

    # data stream id is the identifier for the DataStream object - the root of the data structure
    stream_def = StreamDefinitionContainer(
        data_stream_id= 'scalar_stream',
    )


    stream_def.identifiables['scalar_stream'] = DataStream(
        description=description,
        element_count_id='record_count',
        element_type_id='element_type',
        encoding_id='stream_encoding',
        values=None
    )

    stream_def.identifiables['record_count'] = CountElement(value=0)

    stream_def.identifiables['element_type'] = ElementType(
        updatable=False,
        optional=False,
        data_record_id='data_record')


    stream_def.identifiables['data_record'] = DataRecord(
        field_ids=[field_name,'pressure','latitude','longitude','time'],
        domain_ids=['time_domain'],
        updatable=False,
        optional=False,
    )


    stream_def.identifiables['nan_value'] = NilValue(
        reason= "No value recorded",
        value= -999.99
    )

    # appending _data is a handycap not a convention!
    field_range_name ='%s_data' % field_name

    stream_def.identifiables[field_name] = Coverage(
        definition= field_definition,
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id=field_range_name
    )

    stream_def.identifiables[field_range_name] = RangeSet(
        definition= field_definition,
        nil_values_ids = ['nan_value',],
        mesh_location= CategoryElement(value='vertex'),
        constraint= AllowedValues(values=[field_range,]),
        unit_of_measure= UnitReferenceProperty(code=field_units_code),
        values_path="/fields/%s" % field_range_name,
    )


    stream_def.identifiables['time_domain'] = Domain(
        definition='Spec for ctd data time domain',
        updatable='False',
        optional='False',
        coordinate_vector_id='coordinate_vector',
        mesh_id='point_timeseries'
    )

    stream_def.identifiables['coordinate_vector']= Vector(
        definition = "http://sweet.jpl.nasa.gov/2.0/space.owl#Location",
        # need a definition that includes pressure as a coordinate???
        coordinate_ids=['longitude','latitude','pressure_data','time'],
        reference_frame="http://www.opengis.net/def/crs/EPSG/0/4326"
    )

    stream_def.identifiables['pressure'] = Coverage(
        definition= "http://sweet.jpl.nasa.gov/2.0/physThermo.owl#Pressure", # No idea if this is correct!
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='pressure_data'
    )

    stream_def.identifiables['pressure_data'] = CoordinateAxis(
        definition= "http://sweet.jpl.nasa.gov/2.0/physThermo.owl#Pressure", # No idea if this is correct!
        nil_values_ids = ['nan_value',],
        axis = "Pressure",
        mesh_location= CategoryElement(value='vertex'),
        constraint= AllowedValues(values=[[0, 10000.0],]), # rough range, approximately 0 to 10km
        unit_of_measure= UnitReferenceProperty(code='dbar'), # bar is a unit of pressure used in oceanography
        values_path="/fields/pressure_data",
        reference_frame='Atmospheric pressure ?'
    )

    stream_def.identifiables['latitude'] = Coverage(
        definition= "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Latitude",
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='latitude_data'
    )


    stream_def.identifiables['latitude_data'] = CoordinateAxis(
        definition = "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Latitude",
        axis = "Latitude",
        constraint= AllowedValues(values=[[-90.0, 90.0],]),
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/latitude',
        unit_of_measure = UnitReferenceProperty(code='deg')
    )


    stream_def.identifiables['longitude'] = Coverage(
        definition= "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#longitude",
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='longitude_data'
    )

    stream_def.identifiables['longitude_data'] = CoordinateAxis(
        definition = "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Longitude",
        axis = "Longitude",
        constraint= AllowedValues(values=[[0.0, 360.0],]),
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/longitude',
        unit_of_measure = UnitReferenceProperty(code='deg')
    )

    stream_def.identifiables['time'] = Coverage(
        definition= "http://www.opengis.net/def/property/OGC/0/SamplingTime",
        updatable=False,
        optional=True,

        domain_id='time_domain',
        range_id='time_data'
    )

    stream_def.identifiables['time_data'] = CoordinateAxis(
        definition = "http://www.opengis.net/def/property/OGC/0/SamplingTime",
        axis = "Time",
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/fields/time',
        unit_of_measure = UnitReferenceProperty(code='s'),
        reference_frame="http://www.opengis.net/def/trs/OGC/0/GPS"
    )


    stream_def.identifiables['point_timeseries'] = Mesh(
        mesh_type = CategoryElement(value="Point Time Series"),
        values_path = "/topology/mesh",
        index_offset = 0,
        number_of_elements = 1,
        number_of_verticies = 1,
    )

    stream_def.identifiables['stream_encoding'] = Encoding(
        encoding_type = 'hdf5',
        compression = None,
        sha1 = None
    )



    return stream_def




def ctd_stream_packet(stream_id = None, c=None, t=None, p=None , lat=None, lon=None, time=None, create_hdf=True):
    """
    ###
    ### This method is highly suspect and likely to be completely removed. It is only for early experimentation
    ###


    This is a simple interface for creating a packet of ctd data for a given stream defined by the method above.
    The string names of content are tightly coupled to the method above.
    To send actual data you must have hdf5, numpy and h5py installed.

    @brief build a demo ctd data packet as an ion object. All values arguments are optional, but any argument provided
    should have the same length.
    
    @param stream_id should be the same as the stream_id for the definition - the stream resource ID
    @param c is a list, tuple or ndarray of conductivity values
    @param t is a list, tuple or ndarray of temperature values
    @param p is a list, tuple or ndarray of presure values
    @param lat is a list, tuple or ndarray of latitude values
    @param lon is a list, tuple or ndarray of longitude values
    @param time is a list, tuple or ndarray of time values

    """
    length = False

    def listify(input):
        if hasattr(input, '__iter__'):
            return input
        else:
            return [input,]


    c_range = []
    if c is not None:
        c = listify(c)
        c_range = [min(c), max(c)]
        if length:
            assert length == len(c), 'Conductivity input is the wrong length'
        else:
            length = len(c)

    t_range = []
    if t is not None:
        t = listify(t)
        t_range = [min(t), max(t)]
        if length:
            assert length == len(t), 'Temperature input is the wrong length'
        else:
            length = len(t)

    p_range = []
    if p is not None:
        p = listify(p)
        p_range = [min(p), max(p)]
        if length:
            assert length == len(p), 'Pressure input is the wrong length'
        else:
            length = len(p)

    lat_range = []
    if lat is not None:
        lat = listify(lat)
        lat_range = [min(lat), max(lat)]
        if length:
            assert length == len(lat), 'Latitude input is the wrong length'
        else:
            length = len(lat)

    lon_range = []
    if lon is not None:
        lon = listify(lon)
        lon_range = [min(lon), max(lon)]
        if length:
            assert length == len(lon), 'Longitude input is the wrong length'
        else:
            length = len(lon)

    time_range = []
    if time is not None:
        time = listify(time)
        time_range = [min(time), max(time)]
        if length:
            assert length == len(time), 'Time input is the wrong length'
        else:
            length = len(time)


    hdf_string = ''
    if create_hdf:
        try:
            # Use inline import to put off making numpy a requirement
            import numpy as np

            encoder = HDFEncoder()
            if t is not None:
                encoder.add_hdf_dataset('/fields/temp_data', np.asanyarray(t))


            if c is not None:
                encoder.add_hdf_dataset('/fields/cndr_data', np.asanyarray(c))

            if p is not None:
                encoder.add_hdf_dataset('/fields/pressure_data',np.asanyarray(p))

            if lat is not None:
                encoder.add_hdf_dataset('/fields/latitude', np.asanyarray(lat))

            if lon is not None:
                encoder.add_hdf_dataset('/fields/longitude',np.asanyarray(lon))

            if time is not None:
                encoder.add_hdf_dataset('/fields/time',np.asanyarray(time))

            hdf_string = encoder.encoder_close()
        except :
            log.exception('HDF encoder failed. Please make sure you have it properly installed!')



    # build a hdf file here

    # data stream id is the identifier for the DataStream object - the root of the data structure
    ctd_container = StreamGranuleContainer(
        stream_resource_id=stream_id,
        data_stream_id= 'ctd_data'
    )


    ctd_container.identifiables['ctd_data'] = DataStream(
        id=stream_id,
        values=hdf_string # put the hdf file here as bytes!
        )

    sha1 = hashlib.sha1(hdf_string).hexdigest().upper() if hdf_string else ''

    ctd_container.identifiables['stream_encoding'] = Encoding(
        encoding_type = 'hdf5',
        compression = None,
        sha1 = sha1,
    )


    ctd_container.identifiables['record_count'] = CountElement(
        value= length or -1,
        )

    # Time
    if time is not None :
        ctd_container.identifiables['time'] = CoordinateAxis(
            bounds_id='time_bounds'
        )

        ctd_container.identifiables['time_bounds'] = QuantityRangeElement(
            value_pair=time_range
        )

    # Latitude
    if lat is not None:
        ctd_container.identifiables['latitude'] = CoordinateAxis(
            bounds_id='latitude_bounds'
        )

        ctd_container.identifiables['latitude_bounds'] = QuantityRangeElement(
            value_pair=lat_range
        )

    # Longitude
    if lon is not None:
        ctd_container.identifiables['longitude'] = CoordinateAxis(
            bounds_id='longitude_bounds'
        )

        ctd_container.identifiables['longitude_bounds'] = QuantityRangeElement(
            value_pair=lon_range
        )


    # Pressure
    if p is not None:
        ctd_container.identifiables['pressure_data'] = CoordinateAxis(
            bounds_id='pressure_bounds'
        )

        ctd_container.identifiables['pressure_bounds'] = QuantityRangeElement(
            value_pair=p_range
        )

    # Temperature
    if t is not None:
        ctd_container.identifiables['temp_data'] = RangeSet(
            bounds_id=['temp_bounds']
        )

        ctd_container.identifiables['temp_bounds'] = QuantityRangeElement(
            value_pair=t_range
        )

    # Conductivity
    if c is not None:
        ctd_container.identifiables['cndr_data'] = RangeSet(
            bounds_id='cndr_bounds'
        )

        ctd_container.identifiables['cndr_bounds'] = QuantityRangeElement(
            value_pair=c_range
        )


    return ctd_container