#!/usr/bin/env python

"""Resource specific definitions"""
from pyon.util.config import Config
from pyon.util.containers import DotDict, named_any, get_ion_ts
from coverage_model.parameter import ParameterDictionary, ParameterContext
from coverage_model.parameter_types import QuantityType
from coverage_model.basic_types import AxisTypeEnum

# Resource Types
ParamDict = DotDict()
ParamType = DotDict()
PD = ParamType


def get_predicate_type_list():
    ParamDict = Config(["res/config/param_dict_defs.yml"]).data

#    for param_dict in param_dicts:
#        if param_dict['TempParamDict'] in param_dict:
#            name = param_dict['TempParamDict']
#            temp_param_dict = _create_parameter(name)
#
#        if param_dict['CondParamDict'] in param_dict:
#            pass
#        if param_dict['SalParamDict'] in param_dict:
#            pass
#
#        PD[param_dict['predicate']] = param_dict

    return ParamDict.keys()

def load_definitions():
    """Loads PD as a DotDict
    """
    # Param Dict Types
    pt_list = get_predicate_type_list()
    ParamType.clear()
    ParamType.update(zip(pt_list, pt_list))


def _create_parameter(name):

    pdict = ParameterDictionary()

    pdict = _add_location_time_ctxt(pdict)

    if name == 'conductivity':
        cond_ctxt = ParameterContext('conductivity', param_type=QuantityType(value_encoding=np.float32))
        cond_ctxt.uom = 'unknown'
        cond_ctxt.fill_value = 0e0
        pdict.add_context(cond_ctxt)

    elif name == "pressure":
        pres_ctxt = ParameterContext('pressure', param_type=QuantityType(value_encoding=np.float32))
        pres_ctxt.uom = 'Pascal'
        pres_ctxt.fill_value = 0x0
        pdict.add_context(pres_ctxt)

    elif name == "salinity":
        sal_ctxt = ParameterContext('salinity', param_type=QuantityType(value_encoding=np.float32))
        sal_ctxt.uom = 'PSU'
        sal_ctxt.fill_value = 0x0
        pdict.add_context(sal_ctxt)

    elif name == "temp":
        temp_ctxt = ParameterContext('temp', param_type=QuantityType(value_encoding=np.float32))
        temp_ctxt.uom = 'degree_Celsius'
        temp_ctxt.fill_value = 0e0
        pdict.add_context(temp_ctxt)

    return pdict

def _add_location_time_ctxt(pdict):

    t_ctxt = ParameterContext('time', param_type=QuantityType(value_encoding=np.int64))
    t_ctxt.reference_frame = AxisTypeEnum.TIME
    t_ctxt.uom = 'seconds since 1970-01-01'
    t_ctxt.fill_value = 0x0
    pdict.add_context(t_ctxt)

    lat_ctxt = ParameterContext('lat', param_type=QuantityType(value_encoding=np.float32))
    lat_ctxt.reference_frame = AxisTypeEnum.LAT
    lat_ctxt.uom = 'degree_north'
    lat_ctxt.fill_value = 0e0
    pdict.add_context(lat_ctxt)

    lon_ctxt = ParameterContext('lon', param_type=QuantityType(value_encoding=np.float32))
    lon_ctxt.reference_frame = AxisTypeEnum.LON
    lon_ctxt.uom = 'degree_east'
    lon_ctxt.fill_value = 0e0
    pdict.add_context(lon_ctxt)

    depth_ctxt = ParameterContext('depth', param_type=QuantityType(value_encoding=np.float32))
    depth_ctxt.reference_frame = AxisTypeEnum.HEIGHT
    depth_ctxt.uom = 'meters'
    depth_ctxt.fill_value = 0e0
    pdict.add_context(depth_ctxt)

    return pdict

