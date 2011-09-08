#!/usr/bin/env python

"""
Entry point for importing common Anode packages. Most files should only need to import from here.
"""

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

__all__ = []

# Tell the magic import log setup to pass through this file
from anode.util.log import import_paths
import_paths.append(__name__)

from anode.util.log import log
__all__ += ['log']

from anode.core.bootstrap import CFG, SERVICE_CFG, obj_registry, AnodeObject
__all__ += ['CFG', 'SERVICE_CFG', 'obj_registry', 'AnodeObject']

from anode.util.async import spawn, switch
__all__ += ['spawn', 'switch']

from anode.core.process import AnodeProcessError, GreenProcess, GreenProcessSupervisor, PythonProcess
__all__ += ['AnodeProcessError', 'GreenProcess', 'GreenProcessSupervisor', 'PythonProcess']

from anode.net import messaging, channel
__all__ += ['messaging', 'channel']

from anode.container.cc import Container
__all__ += ['Container']
