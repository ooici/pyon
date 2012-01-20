#!/usr/bin/env python

'''
@author: Luke Campbell <lcampbell@asascience.com>
@file: pyon/ion/transform_base.py
@description: Implementation for TransformBase class
'''

from pyon.ion.streamproc import StreamProcess

class TransformBase(StreamProcess):
    """

    """
    def on_start(self):
        super(TransformBase,self).on_start()
        # Assign a name based on CFG, required for messaging
        self.name = self.CFG.get('process',{}).get('name',None)

        # Assign a list of streams available
        self.streams = self.CFG.get('process',{}).get('publish_streams',None)

    def callback(self):
        pass

    def process(self, packet):
        pass


class TransformDataProcess(TransformBase):
    """

    """
    def __init__(self):
        super(TransformDataProcess,self).__init__()

    def on_start(self):
        super(TransformDataProcess,self).on_start()

        self.publishers = []
        for stream in self.streams:
            self.publishers += getattr(self,stream)


    def process(self, packet):
        pass

    def callback(self):
        pass

    def publish(self):
        pass