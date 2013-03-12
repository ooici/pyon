#!/usr/bin/env python

class ContainerCapability(object):
    """
    Extension interface for container capability managers.
    """
    def __init__(self, container=None):
        self.container = container
    def start(self):
        pass
    def stop(self):
        pass
