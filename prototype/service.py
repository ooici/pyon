#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from anode.base import log
from interface.services.sample_service import ISampleService

class SampleService(ISampleService):
    def doc_fields_(name='text_', time='datetime_', an_int='int_', a_float='float_', a_string='text_', none='???', a_dict='dict_', a_list='list_'):
        pass

    def sample_ping(name='', time='2011-07-27 02:59:43.100000', an_int=0, a_float=0.0, a_str='', none=None, a_dict={}, a_list=[]):
        pass

    def sample_other_op(foo='bar', num=84):
        pass
