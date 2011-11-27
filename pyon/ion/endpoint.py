#!/usr/bin/env python

"""ION messaging endpoints"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.net.endpoint import ProcessRPCClient, ProcessRPCServer, Publisher, Subscriber, BinderListener


class StreamPublisher(Publisher):
    def __init__(self, process=None, **kwargs):
        self._process = process
        Publisher.__init__(self, **kwargs)

class StreamSubscriber(Subscriber):
    def __init__(self, process=None, **kwargs):
        self._process = process
        Subscriber.__init__(self, **kwargs)
