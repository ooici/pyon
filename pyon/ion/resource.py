#!/usr/bin/env python

"""Resource specific definitions"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.containers import DotDict
from pyon.core.object import extendedall_objects
from pyon.util.config import Config

# Resource Types
RT_LIST = list(extendedall_objects.get('Resource', []))
RT = DotDict(zip(RT_LIST, RT_LIST))
ResourceTypes = RT

# Association Types
AssociationTypes = None
def get_association_type_list():
    global AssociationTypes
    AssociationTypes = Config(["res/config/associations.yml"]).data['AssociationTypes']
    at_list = [at['name'] for at in AssociationTypes]
    assert len(at_list) == len(AssociationTypes), "Association names must be unique"
    return at_list

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
