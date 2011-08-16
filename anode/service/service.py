#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

from anode.base import messaging, channel

class BaseService(object):
    """
    Services do work. This work usually comes from a message queue. This work always has a service namespace.
    Service implementation classes will derive from both this class and a generated interface class.
    """

    def __init__(self, name):
        self.node, ioloop_process = messaging.makeNode()
        self.name = name

    def serve_forever(self):
        self.ch = node.channel(channel.Bidirectional)
        self.ch.bind(('amq.direct', self.name))
        self.ch.listen()
        while True:
            connected_ch = ch.accept()
            data = connected_ch.recv()
            print 'Message recvd: ', data
            connected_ch.send('hola')
