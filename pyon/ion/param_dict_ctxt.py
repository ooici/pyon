#!/usr/bin/env python

"""A module to load as DotDicts the parameter dictionary and context definitions from their respective yml files"""
from pyon.util.config import Config
from pyon.util.containers import DotDict

# Parameter Dictionaries loaded from param_dict_defs.yml
ParamDict = DotDict()

# PD = A DotDict containing all the defined parameter dictionaries defined in the param_dict_defs.yml
ParamDictType = DotDict()
PD = ParamDictType

# PD_CTXT = A DotDict that maps each parameter dictionary to relevant parameter contexts
# This is also loaded from the contents of param_dict_defs.yml
ParamDictToCtxt = DotDict()
PD_CTXT = ParamDictToCtxt

# PCTXT = A DotDict containing all the parameter context defined in the param_context_defs.yml
ParamContextType = DotDict()
PCTXT = ParamContextType

ParamDict = Config(["res/config/param_dict_defs.yml"]).data
ParamContext = Config(["res/config/param_context_defs.yml"]).data

def get_param_dict_list():
    return ParamDict.keys()

def get_param_ctxt_for_param_dict():
    for k,v in ParamDict.items():
        ParamDictToCtxt[k] = v.keys()
    return ParamDictToCtxt

def get_param_context_list():
    return ParamContext.keys()

def load_definitions():
    """Loads PD as a DotDict
    """
    # Param Dict Types
    pt_list = get_param_dict_list()
    pctxt_list = get_param_context_list()

    ParamDictType.clear()
    ParamDictType.update(zip(pt_list, pt_list))

    ParamContextType.clear()
    ParamContextType.update(zip(pctxt_list, pctxt_list))

    ParamDictToCtxt = get_param_ctxt_for_param_dict()


