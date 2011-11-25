#!/usr/bin/env python

"""Resource specific definitions"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import sys_name
from pyon.util.containers import DotDict
from pyon.core.object import IonObjectRegistry
from pyon.util.config import Config

# Resource Types
RT_LIST = list()
ResourceTypes = DotDict()
RT = ResourceTypes

# Association Types
AssociationTypes = DotDict()
AT_LIST = list()
AssocTypes = DotDict()
AT = AssocTypes

# Life cycle states
LCS_LIST = list()
LifeCycleStates = DotDict()
LCS = LifeCycleStates

def get_association_type_list():
    AssociationTypes.clear()
    AssociationTypes.update(Config(["res/config/associations.yml"]).data['AssociationTypes'])
    return AssociationTypes.keys()

def load_definitions():
    """Loads constants for resource, association and life cycle states.
    Make sure global module variable objects are updated, not replaced, because other modules had already
    imported them (BAD).
    """
    # Resource Types
    del RT_LIST[:]
    RT_LIST.extend(IonObjectRegistry.allextends.get('Resource', []))
    RT_LIST.append('Resource')
    ResourceTypes.clear()
    ResourceTypes.update(zip(RT_LIST, RT_LIST))

    # Association Types
    del AT_LIST[:]
    AT_LIST.extend(get_association_type_list())
    AssocTypes.clear()
    AssocTypes.update(zip(AT_LIST, AT_LIST))

    # Life cycle states
    del LCS_LIST[:]
    LCS_LIST.extend([
        'NEW',
        'REGISTERED',
        'DEVELOPED',
        'COMMISSIONED',
        'ACTIVE',
        'DECOMMISSIONED'
        ])
    LifeCycleStates.clear()
    LifeCycleStates.update(zip(LCS_LIST, LCS_LIST))
