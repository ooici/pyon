#!/usr/bin/env python

'''
@author David Stuebe <dstuebe@asascience.com>
@file prototype/sci_data/ctd_stream.py
@description An example process producing a ctd data stream
'''

from interface.objects import DataContainer
from interface.objects import UnitReferenceProperty, NilValue, ElapsedTime, AllowedTokens, AllowedValues, AllowedTimes
from interface.objects import AbstractIdentifiable, AbstractDataComponent, AbstractSimpleComponent
from interface.objects import BooleanElement, TextElement, CategoryElement, CountElement, CountRangeElement
from interface.objects import QuantityElement, QuantityRangeElement, TimeElement, TimeRangeElement
from interface.objects import QualityQuantityProperty, QualityQuantityRangeProperty, QualityCatagoryProperty, QualityTextProperty
from interface.objects import DataStream, ElementType, DataRecord, Vector, Coverage, RangeSet, Domain, Mesh, CoordinateAxis, Encoding





def ctd_stream_definition(stream_id=None):
    """
    @brief creates an ion object containing the definition of a seabird ctd data stream
    @param stream_id is the resource id of the data stream for this definition
    @retval ctd_container is an ion object which contains the definition of the stream
    """

    ctd_container = DataContainer(stream_id='ctd_data')


    ctd_container.identifiables['ctd_data'] = DataStream(
        id=stream_id,
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
        data_record_id='ctd_data')


    ctd_container.identifiables['element_type'] = ElementType(
        data_record_id='data_record',
        definition='Defintion of CTD element?',
        updatable=False
        )

    ctd_container.identifiables['data_record'] = DataRecord(
        field_ids=['temperature','conductivity','depth'],
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


    ctd_container.identifiables['time_domain'] = Domain(
        definition='Spec for ctd data time domain',
        updatable='False',
        optional='False',
        coordinate_vector_id='coordiante_vector',
        mesh_id='point_timeseries'
        )

    ctd_container.identifiables['coordinate_vector']= Vector(
        definition = "http://sweet.jpl.nasa.gov/2.0/space.owl#Location",
        # need a definition that includes pressure as a coordinate???
        coordinate_ids=['longitude','latitude','pressure_data','time'],
        reference_frame="http://www.opengis.net/def/crs/EPSG/0/4326"
    )
    
    ctd_container.identifiables['latitude'] = CoordinateAxis(
        definition = "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Latitude",
        axis = "Latitude",
        constraint= AllowedValues(values=[[-90.0, 90.0],]),
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/coordinates/latitude',
        unit_of_measure = UnitReferenceProperty(code='deg')
    )

    ctd_container.identifiables['longitude'] = CoordinateAxis(
        definition = "http://sweet.jpl.nasa.gov/2.0/spaceCoordinates.owl#Longitude",
        axis = "Longitude",
        constraint= AllowedValues(values=[[0.0, 360.0],]),
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/coordinates/longitude',
        unit_of_measure = UnitReferenceProperty(code='deg')
    )

    ctd_container.identifiables['time'] = CoordinateAxis(
        definition = "http://www.opengis.net/def/property/OGC/0/SamplingTime",
        axis = "time",
        nil_values_ids = ['nan_value'],
        mesh_location = CategoryElement(value='vertex'),
        values_path= '/coordiantes/time',
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


def ctd_stream_packet(stream_id = None, c=None, t=None, p=None , lat=None, lon=None, time=None):

    c_range = []
    if c is not None:
        c_range = [min(c), max(c)]

    t_range = []
    if t is not None:
        t_range = [min(t), max(t)]

    p_range = []
    if p is not None:
        p_range = [min(p), max(p)]

    lat_range = []
    if lat is not None:
        lat_range = [min(lat), max(lat)]

    lon_range = []
    if lon is not None:
        lon_range = [min(lon), max(lon)]

    time_range = []
    if time is not None:
        time_range = [min(time), max(time)]


    # build a hdf file here


    ctd_container = DataContainer(stream_id='ctd_data')


    ctd_container.identifiables['ctd_data'] = DataStream(
        id=stream_id,
        values=None # put the hdf file here as bytes!
    )

    ctd_container.identifiables['record_count'] = CountElement(
        value=1,
        constraint=AllowedValues(intervals=[time_range,])
        )

    # Time
    ctd_container.identifiables['time'] = CoordinateAxis(
        bounds_id='time_bounds'
    )

    ctd_container.identifiables['time_bounds'] = QuantityRangeElement(
        value_pair=time_range
    )

    # Latitude
    ctd_container.identifiables['latitude'] = CoordinateAxis(
        bounds_id='latitude_bounds'
    )

    ctd_container.identifiables['latitude_bounds'] = QuantityRangeElement(
        value_pair=lat_range
    )

    # Longitude
    ctd_container.identifiables['longitude'] = CoordinateAxis(
        bounds_id='longitude_bounds'
    )

    ctd_container.identifiables['longitude_bounds'] = QuantityRangeElement(
        value_pair=lon_range
    )


    # Pressure
    ctd_container.identifiables['pressure_data'] = CoordinateAxis(
        bounds_id='pressure_bounds'
    )

    ctd_container.identifiables['pressure_bounds'] = QuantityRangeElement(
        value_pair=p_range
    )

    # Temperature
    ctd_container.identifiables['temp_data'] = RangeSet(
        bounds_id=['temp_bounds']
    )

    ctd_container.identifiables['temp_bounds'] = QuantityRangeElement(
        value_pair=t_range
    )

    # Conductivity
    ctd_container.identifiables['cndr_data'] = RangeSet(
        bounds_id='cndr_bounds'
    )

    ctd_container.identifiables['cndr_bounds'] = QuantityRangeElement(
        value_pair=c_range
    )


    return ctd_container