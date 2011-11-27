#!/usr/bin/env python

"""ION messaging endpoints"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.net.endpoint import ProcessRPCClient, ProcessRPCServer, Publisher, Subscriber, BinderListener


class StreamPublisher(Publisher):
    pass

class StreamSubscriber(Subscriber):
    pass
