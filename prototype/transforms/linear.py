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
    def __init__(self):
        super(TransformLinearShift,self).__init__()
    '''
    Represents an algorithm of O(N)
    '''
    @staticmethod
    def shift(vector):
        validateIsInstance(vector,list)
        N = len(vector)
        x = list()
        for i in xrange(N):
            if i == 0:
                x.append(vector[N-1])
            else:
                x.append(vector[i-1])
        return x

    def process(self, packet):
        if not isinstance(packet,list):
            return
        self.publish(self.shift(packet))
