#!/usr/bin/env python
'''
@author Luke Campbel <LCampbell@ASAScience.com>
@file prototype/transforms/dct.py
@date 03/28/12 13:05
@description Discrete Cosine Transform
'''
from pyon.ion.transform import TransformBenchTesting
from pyon.util.arg_check import validateIsInstance

class TransformDCT(TransformBenchTesting):
    '''
    Transform for computing the discrete cosine transform
    O(N^2/2 + N)
    x[k] =
    '''
    @staticmethod
    def dct(vector):
        import numpy as np
        assert isinstance(vector,np.ndarray)
        N = vector.size

        x = np.zeros(N)
        for k in xrange(N):
            if k == 0:
                x[0] = np.sqrt(1./N) * np.sum(vector)
            else:
                v = np.vectorize(lambda n : np.cos(np.pi * k *  (2. * n + 1.)  / (2. * N)))
                x[k] = np.sqrt(2. / N) * np.sum(v(np.arange(0,N)) * vector)
        return x

    def process(self, packet):
        validateIsInstance(packet,list)
        for i in packet:
            validateIsInstance(packet[i],float)


        self.publish(self.dct(np.array(packet)))