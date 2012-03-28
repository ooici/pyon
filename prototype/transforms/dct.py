#!/usr/bin/env python
'''
@author Luke Campbel <LCampbell@ASAScience.com>
@file prototype/transforms/dct.py
@date 03/28/12 13:05
@description Discrete Cosine Transform
'''
from pyon.ion.transform import TransformDataProcess

class TransformDCT(TransformDataProcess):
    '''
    Transform for computing the discrete cosine transform
    '''
    import numpy as np
    def dct(self, vector):
        x = np.zeros((1,len(vector)))
        for i in xrange(len(vector)):
            if i == 0:
                x[0] = (0.5) * np.sum(vector)