#!/usr/bin/env python
'''
@author Luke Campbel <LCampbell@ASAScience.com>
@file 
@date 03/28/12 14:59
@description Linear Phase Shift
'''
from pyon.ion.transform import TransformBenchTesting
from pyon.util.arg_check import validate_is_instance

class TransformLinear(TransformBenchTesting):
    '''
    Represents an algorithm of O(N)
    '''
    @staticmethod
    def shift(vector):
        validate_is_instance(vector,list)
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


class TransformSquare(TransformBenchTesting):
    '''
    Represents an algorithm of O(N^2)
    '''

    @staticmethod
    def shift(vector):
        validate_is_instance(vector, list)
        N = len(vector)
        x = list()
        for i in xrange(N):
            v = 0
            for j in xrange(N):
                v += vector[i] - vector[j]
            x.append(v)
        return x

    def process(self, packet):
        if not isinstance(packet, list):
            return
        self.publish(self.shift(packet))

class TransformInPlace(TransformBenchTesting):
    '''
    Represents an algorithm of O(1)
    '''
    @staticmethod
    def shift(vector):
        validate_is_instance(vector,list)
        N = len(vector)
        x = vector[0]
        vector[0] = vector[N-1]
        vector[N-1] = x
        return vector

    def process(self, packet):
        if not isinstance(packet, list):
            return
        self.publish(self.shift(packet))

