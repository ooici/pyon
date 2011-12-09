#!/usr/bin/env python

"""Resource specific definitions"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.containers import DotDict
from pyon.core.object import IonObjectRegistry
from pyon.util.config import Config

# Resource Types
ResourceTypes = DotDict()
RT = ResourceTypes

# Association Types
AssociationTypes = DotDict()
AssocTypes = DotDict()
AT = AssocTypes

# Life cycle states
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
    rt_list = list(IonObjectRegistry.allextends.get('Resource', []))
    rt_list.append('Resource')
    ResourceTypes.clear()
    ResourceTypes.update(zip(rt_list, rt_list))

    # Association Types
    at_list = get_association_type_list()
    AssocTypes.clear()
    AssocTypes.update(zip(at_list, at_list))

    # Life cycle states
    lcs_list = [
        'NEW',              # Newly created, potentially inconsistent
        'REGISTERED',       # Aggregate state: Consistent, ready for cross-referencing, not retired
         'UNDEPLOYED',      # Aggregate state: Not deployed in target environment
          'PLANNED',        # Consistent, with actual resource not yet present
          'DEVELOPED',      # The actual resource exists
          'TESTED',         # The actual resource is tested by provider
          'INTEGRATED',     # The actual resource is integrated into composite and tested
          'COMMISSIONED',   # The actual resource is certified commissioned

         'DEPLOYED',        # Aggregate state: Not Deployed in target environment
          'OFF',            # Aggregate state: Off
          'ON',             # Aggregate state: On
          'PUBLIC',         # Aggregate state: Announced, discoverable
          'PRIVATE',        # Aggregate state: Unannounced, not discoverable
           'OFFLINE',       # Inactive, unannounced
           'ONLINE',        # Active, unannounced
           'INACTIVE',      # Inactive, announced (public)
           'ACTIVE',        # Active, announced (public)
        'RETIRED',          # For historic reference only
        ]
    # ON, OFF, DEPLOYED, TESTED (various)
    LifeCycleStates.clear()
    LifeCycleStates.update(zip(lcs_list, lcs_list))
