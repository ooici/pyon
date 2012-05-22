#!/usr/bin/env python
'''
@author Luke Campbel <LCampbell@ASAScience.com>
@file 
@date 03/28/12 14:59
@description Linear Phase Shift
'''
from pyon.ion.transform import TransformBenchTesting
from pyon.util.arg_check import validate_is_instance

from pyon.util.log import log
import numpy
from pyon.ion.granule.record_dictionary import RecordDictionaryTool
from pyon.ion.granule.taxonomy import TaxyTool
from pyon.ion.granule.granule import build_granule, Granule


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



class TransformInPlaceNewGranule(TransformBenchTesting):
    '''
    Represents an algorithm of O(1)
    '''
    @staticmethod
    def shift(vector):
        validate_is_instance(vector,numpy.ndarray)
        x = vector[-1]
        vector[1:] = vector[0:-1]
        vector[0] = x
        return vector

    def process(self, packet):
        if not isinstance(packet,Granule):
            log.warn('Invalid packet received: Type "%s"' % type(packet))
            return

        rd_in = RecordDictionaryTool.load_from_granule(packet)
        tt = TaxyTool.load_from_granule(packet)

        rd_out = RecordDictionaryTool(tt)
        for nickname, v_sequence in rd_in.iteritems():
            rd_out[nickname] = self.shift(v_sequence)

        g_out = build_granule(data_producer_id='dp_id',taxonomy=tt,record_dictionary=rd_out)
        self.publish(g_out)


class TransformLinearNewGranule(TransformInPlaceNewGranule):
    '''
    Represents an algorithm of O(N)
    '''
    @staticmethod
    def shift(vector):
        validate_is_instance(vector,numpy.ndarray)
        N = len(vector)
        x = numpy.zeros_like(vector)
        for i in xrange(N):
            if i == 0:
                x[i] = vector[N-1]
            else:
                x[i] = vector[i-1]
        return x


