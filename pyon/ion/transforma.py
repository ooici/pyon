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
    """

    """

    pass

class TransformStreamProcess(TransformBase):
    pass

class TransformEventProcess(TransformBase):
    pass

class TransformStreamListener(TransformStreamProcess):

    def on_start(self):
        # Assign a list of streams available
        self.streams = self.CFG.get_safe('process.subscriber_streams',[])

        self.subscribers = []
        self.greenlets = []
        for stream in self.streams:
            subscriber = Subscriber(name=(get_sys_name(), stream), callback=self.recv_packet)
            self.subscribers.append(subscriber)
            self.greenlets.append(spawn(subscriber.listen))

    def recv_packet(self, packet, stream_id):
        raise NotImplementedError('Method recv_packet not implemented')

    def on_quit(self):
        for subscriber in self.subscribers:
            subscriber.close()

class TransformStreamPublisher(TransformStreamProcess):

    def on_start(self):
        # Assign a list of streams available
        self.streams = self.CFG.get_safe('process.publish_streams',[])

        self.publishers = []
        self.greenlets = []
        for stream in self.streams:
            publisher = Publisher(name=(get_sys_name(), stream), callback=self.publish)
            self.publishers.append(publisher)
            self.greenlets.append(spawn(publisher.publish))

    def publish(self, msg, headers):
        raise NotImplementedError('Method publish not implemented')

    def on_quit(self):
        for publisher in self.publishers:
            publisher.close()

class TransformEventListener(TransformEventProcess):

    def on_start(self):
        event_type = self.CFG.get_safe('process.event_type', '')

        self.greenlets = []

        self.listener = EventSubscriber(event_type=event_type, callback=self.process_event)
        self.greenlets.append(spawn(self.listener.listen))

    def process_event(self):
        raise NotImplementedError('Method process_event not implemented')

    def on_quit(self):
        self.listener.close()

class TransformEventPublisher(TransformEventProcess):

    def on_start(self):
        event_type = self.CFG.get_safe('process.event_type', '')

        self.publisher = EventPublisher(event_type=event_type)

    def publish_event(self, origin, sub_type, description):
        self.publisher.publish_event(origin=origin, sub_type=sub_type, description=description)

    def on_quit(self):
        self.publisher.close()

class TransformDatasetProcess(TransformBase):
    pass

class TransformDataProcess(TransformStreamListener, TransformStreamPublisher):
    pass