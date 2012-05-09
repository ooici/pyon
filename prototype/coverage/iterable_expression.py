#!/usr/bin/env python

'''
@package prototype.coverage.record_set
@file prototype/coverage/record_set.py
@author David Stuebe
@author Tim Giguere
@brief https://confluence.oceanobservatories.org/display/CIDev/R2+Construction+Data+Model
'''

import numpy



class IterableExpression(dict):
    """
    This class should inherit from arange and dict, but I can't do that yet... Need to figure out how for type builtin

    Current interface:
    ie = IterableExpression(1.0, 10.0)
    1.0 == ie.sequence[0]

    for val in ie.sequence:
        ...

    """

    def __init__(self, start=None, stop=None, stride=None, dtype=None):

        dict.__init__(self, start=start, stop=stop, stride=stride, dtype=dtype)


        self.sequence = numpy.arange(start, stop, stride, dtype)




time = IterableExpression(start=0.0,stop=100.0)

for t in time.sequence:
    print t