#!/usr/bin/env python

'''
@author: Tim Giguere <tgiguere@asascience.com>
@file: pyon/ion/transforma.py
@description: New Implementation for TransformBase class
'''

from gevent import spawn

from pyon.core.bootstrap import get_sys_name
from pyon.ion.process import SimpleProcess
from pyon.net.endpoint import Subscriber, Publisher
from pyon.event.event import EventSubscriber, EventPublisher

from pyon.util.log import log

class TransformBase(SimpleProcess):

    def on_start(self):
        super(TransformBase,self).on_start()

class TransformStreamProcess(TransformBase):
    pass

class TransformEventProcess(TransformBase):
    pass

class TransformStreamListener(TransformStreamProcess):

    def on_start(self):
        self.queue_name = self.CFG.get_safe('process.queue_name','')

        # @TODO: queue_name is really exchange_name, rename
        xn = self.container.ex_manager.create_xn_queue(self.queue_name)

        self.subscriber = Subscriber(name=xn, callback=self.recv_packet)
        self.greenlet = spawn(self.subscriber.listen)

        ## Assign a list of streams available
        #self.streams = self.CFG.get_safe('process.subscriber_streams',[])
        #log.warn('TransformStreamListener.on_start()')
        #self.subscribers = []
        #self.greenlets = []
        #for stream in self.streams:
        #    subscriber = Subscriber(name=stream, callback=self.recv_packet)
        #    self.subscribers.append(subscriber)
        #    self.greenlets.append(spawn(subscriber.listen))

    def recv_packet(self, msg, headers):
        raise NotImplementedError('Method recv_packet not implemented')

    def on_quit(self):
#        for subscriber in self.subscribers:
#            subscriber.close()
#
#        for greenlet in self.greenlets:
#            greenlet.join(timeout=10)
        self.subscriber.close()
        self.greenlet.join(timeout=10)

class TransformStreamPublisher(TransformStreamProcess):

    def on_start(self):
        self.exchange_point = self.CFG.get_safe('process.exchange_point', '')

        xp = self.container.ex_manager.create_xp(self.exchange_point)

        self.publisher = Publisher()
#        # Assign a list of streams available
#        self.streams = self.CFG.get_safe('process.publish_streams',[])
#        log.warn('TransformStreamPublisher.on_start()')
#        self.publishers = []
#        #self.greenlets = []
#        for stream in self.streams:
#            publisher = Publisher(name=(get_sys_name(), stream), node=self.container.node)
#            self.publishers.append(publisher)
#            #self.greenlets.append(spawn(publisher.publish))

    def publish(self, msg, to_name):
        raise NotImplementedError('Method publish not implemented')

    def on_quit(self):
        self.publisher.close()
#        for publisher in self.publishers:
#            publisher.close()

        #for greenlet in self.greenlets:
        #    greenlet.join(timeout=10)

class TransformEventListener(TransformEventProcess):

    def on_start(self):
        event_type = self.CFG.get_safe('process.event_type', '')

        self.listener = EventSubscriber(event_type=event_type, callback=self.process_event)
        self.listener.start()

    def process_event(self, msg, headers):
        raise NotImplementedError('Method process_event not implemented')

    def on_quit(self):
        self.listener.stop()

class TransformEventPublisher(TransformEventProcess):

    def on_start(self):
        event_type = self.CFG.get_safe('process.event_type', '')

        self.publisher = EventPublisher(event_type=event_type)

    def publish_event(self, *args, **kwargs):
        raise NotImplementedError('Method publish_event not implemented')

    def on_quit(self):
        self.publisher.close()

class TransformDatasetProcess(TransformBase):
    pass

class TransformDataProcess(TransformStreamListener, TransformStreamPublisher):

    def on_start(self):
        log.warn('TransformDataProcess.on_start()')
        TransformStreamListener.on_start(self)
        TransformStreamPublisher.on_start(self)

class TransformAlgorithm(object):

    @staticmethod
    def execute(*args, **kwargs):
        raise NotImplementedError('Method execute not implemented')#!/usr/bin/env python