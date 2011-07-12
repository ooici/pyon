#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from ion.core.util.config import Config

conf_paths = ['res/config/ion.yml', 'res/config/ion.local.yml']
CONF = Config(conf_paths).data
