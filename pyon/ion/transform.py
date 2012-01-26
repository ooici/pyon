#!/usr/bin/env python

'''
@author: Luke Campbell <lcampbell@asascience.com>
@file: pyon/ion/transform.py
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
        self.streams = self.CFG.get('process',{}).get('publish_streams',[])

    def callback(self):
        pass

    def process(self, packet):
        pass

class TransformProcessAdaptor(TransformBase):
    """
    Models a transform adaptor to an external transform process
    """
    def __init__(self, *args, **kwargs):
        super(TransformProcessAdaptor, self).__init__()
        #@todo: Initialize IO, pipes or some variant of IPC

    def callback(self):
        pass

    def process(self, packet):
        pass



class TransformDataProcess(TransformBase):
    """Model for a TransformDataProcess

    """
    def __init__(self):
        super(TransformDataProcess,self).__init__()
        self._pub_init = False

    def on_start(self):
        super(TransformDataProcess,self).on_start()

    def process(self, packet):
        pass

    def callback(self):
        pass

    def publish(self,msg):
        self._publish_all(msg)


    def _publish_all(self, msg):
        '''Publishes a message on all output streams (publishers)
        '''
        # Ensure the publisher list is only initialized once
        if not self._pub_init:
            stream_names = list(k for k,v in self.streams.iteritems())
            self.publishers = []
            for stream in stream_names:
                self.publishers.append(getattr(self,stream))


        for publisher in self.publishers:
            publisher.publish(msg)



class TransformFunction(TransformDataProcess):
    """ Represents a transform function
    Input is given to the transform, it runs until the transform is complete
    and the output is returned.

    Input can be obtained from a stream, and output can be sent to a stream

    A TransformFunction is interchangeable with a TransformProcess but it is also able to be called explicitly to run

    """
    def execute(self, input):
        pass

    def process(self, packet):
        ret = self.execute(packet)
        if len(self.streams)>0:
            self.publish(ret)


