#!/usr/bin/env python

"""
Resource specific definitions
"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.containers import DotDict
from pyon.core.object import resource_objects

RT_LIST = resource_objects

LCS_LIST = [
    'NEW',
    'REGISTERED',
    'DEVELOPED',
    'COMMISSIONED',
    'ACTIVE',
    'DECOMMISSIONED'
    ]

AT_LIST = [
    'HAS_A',
    'IS_A',
    'OWNER_OF',
    ]

RT = DotDict(zip(RT_LIST, RT_LIST))

AT = DotDict(zip(AT_LIST, AT_LIST))

LCS = DotDict(zip(LCS_LIST, LCS_LIST))
