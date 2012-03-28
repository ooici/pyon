#!/usr/bin/env python
'''
@author Luke Campbel <LCampbell@ASAScience.com>
@file 
@date 03/28/12 14:59
@description Linear Phase Shift
'''
from pyon.ion.transform import TransformDataProcess
from pyon.util.arg_check import validateIsInstance

class TransformLinearShift(TransformDataProcess):
    def shift(self, vector):
        import numpy as np
        validateIsInstance(vector,)