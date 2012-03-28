#!/usr/bin/env python
'''
@author Luke Campbel <LCampbell@ASAScience.com>
@file 
@date 03/27/12 15:30
@description DESCRIPTION
'''
from pyon.util.arg_check import assertIsInstance, assertIn, assertEqual, assertTrue


class ArgCheckService(object):
    '''
    Example Service illustrating how to use the various assertion mechanisms
    '''
    def __init__(self):
        pass

    def pass_integer(self, val=''):
        '''
        Say you were expecting an integer from the client...
        '''
        assertIsInstance(val,int,'Value is not an integer.')
        return val

    def pass_float(self, val=1.0):
        '''
        Say you were expecting an integer from the client
        '''
        assertIsInstance(val,float,'Value is not a float.')
        return val

    def handle_list(self, needle, haystack):
        '''
        You needed to be certain that something was in the list or dict
        '''
        assertIn(needle,haystack,'Can\'t find %s in %s.' % (needle, haystack))
        return needle

    def check_equality(self, a,b):
        '''
        You needed to be sure that two items we're equivalent
        '''
        assertEqual(a,b,'%s != %s' %(str(a), str(b)))
        return True

    def list_len(self,l):
        '''
        You needed to be certain that a list had len >0
        '''
        assertTrue(len(l)>0, 'list=%s was empty.' % str(l))

