#!/usr/bin/env python

'''
@author: Luke Campbell <lcampbell@asascience.com>
@file: pyon/ion/transform.py
@description: Implementation for TransformBase class
'''
import uuid
import time
import gevent
from pyon.event.event import EventPublisher

from pyon.ion.streamproc import StreamProcess
from pyon.net.endpoint import Subscriber, Publisher
from pyon.net.transport import NameTrio
from pyon.util.async import spawn
from pyon.util.log import log

class TransformBase(StreamProcess):
    """

    """

    def on_start(self):
        super(TransformBase,self).on_start()
        # Assign a name based on CFG, required for messaging
        self.name = self.CFG.get_safe('process.name',None)

        # Assign a list of streams available
        self.streams = self.CFG.get_safe('process.publish_streams',[])

        # Assign the transform resource id
        self._transform_id = self.CFG.get_safe('process.transform_id','Unknown_transform_id')



    def callback(self):
        pass

    def call_process(self, packet):
        try:
            self.process(packet)
        except Exception as e:
            log.exception('Unhandled caught in transform process')
            event_publisher = EventPublisher()
            event_publisher.publish_event(origin=self._transform_id, event_type='ExceptionEvent',
                exception_type=str(type(e)), exception_message=e.message)


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
            self._pub_init = True
            stream_names = list(k for k,v in self.streams.iteritems())
            self.publishers = []
            for stream in stream_names:
                self.publishers.append(getattr(self,stream))


        for publisher in self.publishers:
            publisher.publish(msg)
            


class TransformBenchTesting(TransformDataProcess):

    """
    Easiest way to run:
    from pyon.util.containers import DotDict
    tbt=cc.proc_manager._create_service_instance('55', 'tbt', 'pyon.ion.transform', 'TransformBenchTesting', DotDict({'process':{'name':'tbt', 'transform_id':'55'}}))
    tbt.init()
    tbt.start()
    """
    def __init__(self):
        super(TransformBenchTesting,self).__init__()
        self.count = 0
        
    def perf(self):
        then = time.time()
        ocount = self.count
        while True:
            gevent.sleep(5.)
            now = time.time()
            count = self.count
            delta_t = now - then
            delta_c = count - ocount

            print 'PERF - [%s] Iterations Per Second: %f' % (time.strftime("%H:%M:%s", time.gmtime()), delta_c / delta_t)
            then = now
            ocount = count
            
        
        
        
    def on_start(self):
        TransformDataProcess.__init__(self)

        # set up subscriber to *
        self._bt_sub = Subscriber(callback=lambda m, h: self.call_process(m),
                                  from_name=NameTrio('test_exchange', None, '*'))

        # spawn listener
        self._sub_gl = spawn(self._bt_sub.listen)

        # set up publisher to anything!
        self._bt_pub = Publisher(to_name=NameTrio('test_exchange', str(uuid.uuid4())[0:6]))

    def publish(self, msg):
        self._bt_pub.publish(msg)
        self.count+=1

    def _stop_listener(self):
        self._bt_sub.close()
        self._sub_gl.join(timeout=2)
        self._sub_gl.kill()

    def on_stop(self):
        TransformDataProcess.on_stop(self)
        self._stop_listener()

    def on_quit(self):
        TransformDataProcess.on_quit(self)
        self._stop_listener()



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


