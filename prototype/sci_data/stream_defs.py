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

from prototype.sci_data.constructor_apis import StreamDefinitionConstructor, PointSupplementConstructor
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

def USGS_stream_definition():

    sdc = StreamDefinitionConstructor(
        description='CONNECTICUT RIVER AT THOMPSONVILLE CT (01184000) - Daily Value',
        nil_value=-9999.99,
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
        reference_frame='urn:ogc:def:crs:EPSG::4326'

    )

    sdc.define_coverage(
        field_name='water_height',
        field_definition="urn:x-ogc:def:phenomenon:OGC:water_height", # Copied from SSDS
        field_units_code='ft_us'
    )

    sdc.define_coverage(
        field_name = 'water_temperature',
        field_definition = "urn:x-ogc:def:phenomenon:OGC:water_temperature", # Copied from SSDS
        field_units_code = 'Cel'
    )


    sdc.define_coverage(
        field_name = 'streamflow',
        field_definition = "urn:x-ogc:def:phenomenon:OGC:streamflow", # Copied from SSDS
        field_units_code = 'cft_i/s'
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




def ctd_stream_packet(stream_id = None, c=None, t=None, p=None , lat=None, lon=None, height=None, time=None, create_hdf=True):
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

    stream_def = ctd_stream_definition(stream_id=stream_id)

    psc = PointSupplementConstructor(point_definition=stream_def, stream_id=stream_id)


    assert time
    assert lat
    assert lon

    def listify(input):
        if hasattr(input, '__iter__'):
            return input
        else:
            return [input,]

    length = False


    if c is not None:
        c = listify(c)
        if length:
            assert length == len(c), 'Conductivity input is the wrong length'
        else:
            length = len(c)

    if t is not None:
        t = listify(t)
        if length:
            assert length == len(t), 'Temperature input is the wrong length'
        else:
            length = len(t)

    if p is not None:
        p = listify(p)
        if length:
            assert length == len(p), 'Pressure input is the wrong length'
        else:
            length = len(p)

    if lat is not None:
        lat = listify(lat)
        if length:
            if 1 == len(lat):
                lat = lat*length
        else:
            length = len(lat)
    else:
        raise RuntimeError('Did not specify longitude')

    if lon is not None:
        lon = listify(lon)
        if length:
            if 1 == len(lon):
                lon = lon*length
        else:
            length = len(lon)
    else:
        raise RuntimeError('Did not specify longitude')

    if height is not None:
        height = listify(height)
        if length:
            if 1 == len(height):
                height = height*length
        else:
            length = len(height)
    else:
        height = [0,]*length

    if time is not None:
        time = listify(time)
        if length:
            if 1 == len(time):
                time = time*length
        else:
            length = len(time)
    else:
        raise RuntimeError('Did not specify time')


    for idx, time_val in enumerate(time):

        p_id = psc.add_point(time=time_val, location=(lon[idx], lat[idx], height[idx]))

        #putting the if inside the loop is slow - but this is a test method only!
        if t:
            psc.add_scalar_point_coverage(point_id=p_id, coverage_id='temperature', value=t[idx])
        if p:
            psc.add_scalar_point_coverage(point_id=p_id, coverage_id='pressure', value=p[idx])
        if c:
            psc.add_scalar_point_coverage(point_id=p_id, coverage_id='conductivity', value=c[idx])



    granule = psc.close_stream_granule()

    if not create_hdf:
        # Remove the hdf string from the granule

        data_stream = granule.identifiables['data_stream']
        data_stream.values = ''


    return granule