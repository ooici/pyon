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
    return ParamDict.keys()

def load_definitions():
    """Loads PD as a DotDict
    """
    # Param Dict Types
    pt_list = get_predicate_type_list()
    ParamType.clear()
    ParamType.update(zip(pt_list, pt_list))

