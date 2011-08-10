#!/usr/bin/env python

"""
Entry point for importing common Anode packages. Most files should only need to import from here.
"""

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

__all__ = []

# Tell the magic import log setup to pass through this file
from anode.core.util.log import import_paths
import_paths.append(__name__)

from anode.core.util.log import log
__all__ += ['log']

from anode.core.bootstrap import CONF
__all__ += ['CONF']

from anode.util.async import spawn, switch
__all__ += ['spawn', 'switch']


