#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>, Thomas R. Lennan'
__license__ = 'Apache 2.0'

class Invocation(object):
    """
    Container object for parameters of events/messages passed to internal
    capability container processes
    """

    # Event outbound processing path
    PATH_OUT = 'outgoing'

    # Event inbound processing path
    PATH_IN = 'incoming'

    def __init__(self, **kwargs):
        self.args = kwargs
        self.path = kwargs.get('path')
        self.message = kwargs.get('message')
        self.headers = kwargs.get('headers') or {}  # ensure dict

        self.message_annotations = {}


    #Returns the value of of the specified header or the specified default value
    def get_header_value(self, header_name, default_value):
        value = self.headers[header_name] if self.headers.has_key(header_name) and self.headers[header_name] != '' else default_value
        return value

    #This function is used to parse the two value tuple of sysname,servicename
    def get_service_name(self, header_value):
        value_list = [x.strip() for x in header_value.split(',')]
        value =  value_list[1] if len(value_list) > 1 else value_list[0]
        return value

class Interceptor(object):
    """
    Basic interceptor model.
    """
    def configure(self, config):
        pass

    def outgoing(self, invocation):
        pass

    def incoming(self, invocation):
        pass

def process_interceptors(interceptors, invocation):
    for interceptor in interceptors:
        func = getattr(interceptor, invocation.path)
        invocation = func(invocation)
    return invocation

