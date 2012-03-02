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

from prototype.sci_data.constructor_apis import StreamDefinitionConstructor
import hashlib

from pyon.util.log import log


"""
SWE meta data copied from SSDS:
http://marinemetadata.org/workshops/mmiworkshop06/materials/track1/sensorml/EXAMPLES/MBARI_CTD_SensorML
"""


def SBE37_CDM_stream_definition():

    sdc = StreamDefinitionConstructor(
        description='Parsed conductivity temperature and pressure observations from a Seabird 37 CTD',
        nil_value=-999.99,
        encoding='hdf5'
        )


    sdc.define_temporal_coordinates(
        reference_frame='http://www.opengis.net/def/trs/OGC/0/GPS',
        definition='http://www.opengis.net/def/property/OGC/0/SamplingTime',
        reference_time='1970-01-01T00:00:00Z',
        unit_code='s'
        )

    sdc.define_geospatial_coordinates(
        definition="http://www.opengis.net/def/property/OGC/0/PlatformLocation",
        reference_frame='urn:ogc:def:crs:EPSG::4979'

    )

    sdc.define_coverage(
        field_name='temperature',
        field_definition="urn:x-ogc:def:phenomenon:OGC:temperature", # Copied from SSDS
        field_units_code='Cel',
        field_range=[-10.0, 100.0]
        )

    sdc.define_coverage(
        field_name = 'conductivity',
        field_definition = "urn:x-ogc:def:phenomenon:OGC:conductivity", # Copied from SSDS
        field_units_code = 'mS/cm', # Check these units!
        field_range = [0.0, 100.0]
    )


    sdc.define_coverage(
        field_name = 'pressure',
        field_definition = "urn:x-ogc:def:phenomenon:OGC:pressure", # Copied from SSDS
        field_units_code = 'dBar',
        field_range = [0.0, 1000.0]
    )


    return sdc.close_structure()

# Keep the old method operational...
def ctd_stream_definition(stream_id = None):

    sd = SBE37_CDM_stream_definition()
    sd.stream_resource_id = stream_id or ''
    return sd


def SBE37_RAW_stream_definition():

    stream_definition = StreamDefinitionContainer(
        data_stream_id='data_stream',
    )

    ident = stream_definition.identifiables

    ident['data_stream'] = DataStream(
        description='Raw data from an SBE 37',
        element_count_id='record_count',
        element_type_id='element_type',
        encoding_id='stream_encoding',
        values=None
    )

    ident['stream_encoding'] = Encoding(
        encoding_type='raw', # add something here about the record separator and value separator
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
        definition='Raw SBE 37 data'
    )


    return stream_definition


def L0_conductivity_stream_definition():

    sdc = StreamDefinitionConstructor(
        description='L0 Conductivity observations from a Seabird 37 CTD',
        nil_value=-999.99,
        encoding='hdf5'
    )


    sdc.define_temporal_coordinates(
        reference_frame='http://www.opengis.net/def/trs/OGC/0/GPS',
        definition='http://www.opengis.net/def/property/OGC/0/SamplingTime',
        reference_time='1970-01-01T00:00:00Z',
        unit_code='s'
    )

    sdc.define_geospatial_coordinates(
        definition="http://www.opengis.net/def/property/OGC/0/PlatformLocation",
        reference_frame='urn:ogc:def:crs:EPSG::4979'

    )

    sdc.define_coverage(
        field_name = 'conductivity',
        field_definition = "urn:x-ogc:def:phenomenon:OGC:conductivity", # Copied from SSDS
        field_units_code = 'mS/cm', # Check these units!
        field_range = [0.0, 100.0]
    )


    return sdc.close_structure()

def L0_temperature_stream_definition():

    sdc = StreamDefinitionConstructor(
        description='L0 Temperature observations from a Seabird 37 CTD',
        nil_value=-999.99,
        encoding='hdf5'
    )


    sdc.define_temporal_coordinates(
        reference_frame='http://www.opengis.net/def/trs/OGC/0/GPS',
        definition='http://www.opengis.net/def/property/OGC/0/SamplingTime',
        reference_time='1970-01-01T00:00:00Z',
        unit_code='s'
    )

    sdc.define_geospatial_coordinates(
        definition="http://www.opengis.net/def/property/OGC/0/PlatformLocation",
        reference_frame='urn:ogc:def:crs:EPSG::4979'

    )

    sdc.define_coverage(
        field_name='temperature',
        field_definition="urn:x-ogc:def:phenomenon:OGC:temperature", # Copied from SSDS
        field_units_code='Cel',
        field_range=[-10.0, 100.0]
    )

    return sdc.close_structure()

def L0_pressure_stream_definition():

    sdc = StreamDefinitionConstructor(
        description='L0 Pressure observations from a Seabird 37 CTD',
        nil_value=-999.99,
        encoding='hdf5'
    )


    sdc.define_temporal_coordinates(
        reference_frame='http://www.opengis.net/def/trs/OGC/0/GPS',
        definition='http://www.opengis.net/def/property/OGC/0/SamplingTime',
        reference_time='1970-01-01T00:00:00Z',
        unit_code='s'
    )

    sdc.define_geospatial_coordinates(
        definition="http://www.opengis.net/def/property/OGC/0/PlatformLocation",
        reference_frame='urn:ogc:def:crs:EPSG::4979'

    )

    sdc.define_coverage(
        field_name = 'pressure',
        field_definition = "urn:x-ogc:def:phenomenon:OGC:pressure", # Copied from SSDS
        field_units_code = 'dBar',
        field_range = [0.0, 1000.0]
    )


    return sdc.close_structure()



def L1_conductivity_stream_definition():

    sdc = StreamDefinitionConstructor(
        description='L1 Conductivity observations from a Seabird 37 CTD',
        nil_value=-999.99,
        encoding='hdf5'
    )


    sdc.define_temporal_coordinates(
        reference_frame='http://www.opengis.net/def/trs/OGC/0/GPS',
        definition='http://www.opengis.net/def/property/OGC/0/SamplingTime',
        reference_time='1970-01-01T00:00:00Z',
        unit_code='s'
    )

    sdc.define_geospatial_coordinates(
        definition="http://www.opengis.net/def/property/OGC/0/PlatformLocation",
        reference_frame='urn:ogc:def:crs:EPSG::4979'

    )

    sdc.define_coverage(
        field_name = 'conductivity',
        field_definition = "urn:x-ogc:def:phenomenon:OGC:conductivity", # Copied from SSDS
        field_units_code = 'mS/cm', # Check these units!
        field_range = [0.0, 100.0]
    )


    return sdc.close_structure()

def L1_temperature_stream_definition():

    sdc = StreamDefinitionConstructor(
        description='L1 Temperature observations from a Seabird 37 CTD',
        nil_value=-999.99,
        encoding='hdf5'
    )


    sdc.define_temporal_coordinates(
        reference_frame='http://www.opengis.net/def/trs/OGC/0/GPS',
        definition='http://www.opengis.net/def/property/OGC/0/SamplingTime',
        reference_time='1970-01-01T00:00:00Z',
        unit_code='s'
    )

    sdc.define_geospatial_coordinates(
        definition="http://www.opengis.net/def/property/OGC/0/PlatformLocation",
        reference_frame='urn:ogc:def:crs:EPSG::4979'

    )

    sdc.define_coverage(
        field_name='temperature',
        field_definition="urn:x-ogc:def:phenomenon:OGC:temperature", # Copied from SSDS
        field_units_code='Cel',
        field_range=[-10.0, 100.0]
    )

    return sdc.close_structure()

def L1_pressure_stream_definition():

    sdc = StreamDefinitionConstructor(
        description='L1 Pressure observations from a Seabird 37 CTD',
        nil_value=-999.99,
        encoding='hdf5'
    )


    sdc.define_temporal_coordinates(
        reference_frame='http://www.opengis.net/def/trs/OGC/0/GPS',
        definition='http://www.opengis.net/def/property/OGC/0/SamplingTime',
        reference_time='1970-01-01T00:00:00Z',
        unit_code='s'
    )

    sdc.define_geospatial_coordinates(
        definition="http://www.opengis.net/def/property/OGC/0/PlatformLocation",
        reference_frame='urn:ogc:def:crs:EPSG::4979'

    )

    sdc.define_coverage(
        field_name = 'pressure',
        field_definition = "urn:x-ogc:def:phenomenon:OGC:pressure", # Copied from SSDS
        field_units_code = 'dBar',
        field_range = [0.0, 1000.0]
    )


    return sdc.close_structure()


def L2_practical_salinity_stream_definition():

    sdc = StreamDefinitionConstructor(
        description='L2 practical salinity observations',
        nil_value=-999.99,
        encoding='hdf5'
    )


    sdc.define_temporal_coordinates(
        reference_frame='http://www.opengis.net/def/trs/OGC/0/GPS',
        definition='http://www.opengis.net/def/property/OGC/0/SamplingTime',
        reference_time='1970-01-01T00:00:00Z',
        unit_code='s'
    )

    sdc.define_geospatial_coordinates(
        definition="http://www.opengis.net/def/property/OGC/0/PlatformLocation",
        reference_frame='urn:ogc:def:crs:EPSG::4979'

    )

    sdc.define_coverage(
        field_name = 'salinity',
        field_definition = "urn:x-ogc:def:phenomenon:OGC:practical_salinity", # Copied from SSDS
        field_units_code = '', # practical salinity has no units
        field_range = [0.1, 40.0]
    )


    return sdc.close_structure()


def L2_density_stream_definition():

    sdc = StreamDefinitionConstructor(
        description='L2 practical salinity observations',
        nil_value=-999.99,
        encoding='hdf5'
    )


    sdc.define_temporal_coordinates(
        reference_frame='http://www.opengis.net/def/trs/OGC/0/GPS',
        definition='http://www.opengis.net/def/property/OGC/0/SamplingTime',
        reference_time='1970-01-01T00:00:00Z',
        unit_code='s'
    )

    sdc.define_geospatial_coordinates(
        definition="http://www.opengis.net/def/property/OGC/0/PlatformLocation",
        reference_frame='urn:ogc:def:crs:EPSG::4979'

    )

    sdc.define_coverage(
        field_name = 'density',
        field_definition = "urn:x-ogc:def:phenomenon:OGC:density", # Copied from SSDS
        field_units_code = 'kg/m3', # practical salinity has no units
        field_range = [1000.0, 1050.0]
    )


    return sdc.close_structure()




def ctd_stream_packet(stream_id = None, c=None, t=None, p=None , lat=None, lon=None, time=None, create_hdf=True):
    """
    ###
    ### This method is deprecated!
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