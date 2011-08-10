#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from anode.core.util.config import Config
from anode.core.object import IonObjectRegistry

# Note: do we really want to do the res folder like this again?
conf_paths = ['res/config/ion.yml', 'res/config/ion.local.yml']
CONF = Config(conf_paths).data

obj_types = IonObjectRegistry()
