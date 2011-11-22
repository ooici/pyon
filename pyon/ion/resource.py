#!/usr/bin/env python

"""Resource specific definitions"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import sys_name
from pyon.util.containers import DotDict
from pyon.core.object import allextends
from pyon.util.config import Config

# Resource Types
RT_LIST = list(allextends.get('Resource', []))
RT_LIST.append('Resource')
RT = DotDict(zip(RT_LIST, RT_LIST))
ResourceTypes = RT

# Association Types
AssociationTypes = None
def get_association_type_list():
    global AssociationTypes
    AssociationTypes = Config(["res/config/associations.yml"]).data['AssociationTypes']
    return AssociationTypes.keys()

AT_LIST = get_association_type_list()
AT = DotDict(zip(AT_LIST, AT_LIST))
AssocTypes = AT

# Life cycle states
LCS_LIST = [
    'NEW',
    'REGISTERED',
    'DEVELOPED',
    'COMMISSIONED',
    'ACTIVE',
    'DECOMMISSIONED'
    ]
LCS = DotDict(zip(LCS_LIST, LCS_LIST))
LifeCycleStates = LCS
