#!/usr/bin/env python

"""
Entry point for importing common ION packages. Most files should only need to import from here.
"""

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

__all__ = []

# Tell the magic import log setup to pass through this file
from ion.core.util.ionlog import import_paths
import_paths.append(__name__)

from ion.core.util.ionlog import log
__all__ += ['log']

from ion.core.bootstrap import CONF
__all__ += ['CONF']

from ion.util.async import spawn, switch
__all__ += ['spawn', 'switch']


