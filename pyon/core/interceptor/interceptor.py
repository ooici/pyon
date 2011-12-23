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

