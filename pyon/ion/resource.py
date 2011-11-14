#!/usr/bin/env python

"""
Resource specific definitions
"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.util.containers import DotDict

RT_LIST = [
    "ExchangeSpace",
    "ExchangeName",
    "ExchangePoint",
    "Org",
    "Policy",
    "Instrument",
    ]

AT_LIST = [
    'HAS_A',
    'IS_A',
    'OWNER_OF',
    ]

RT = DotDict(zip(RT_LIST, RT_LIST))

AT = DotDict(zip(AT_LIST, AT_LIST))
