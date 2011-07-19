#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from tables import *
from tables.netcdf3 import NetCDFFile

filename = 'sresa1b_ncar_ccsm3_0_run1_200001.nc'
#h5file = openFile(filename, mode='r')
file = NetCDFFile(filename, 'r')
print file.variables