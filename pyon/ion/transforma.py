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
from pyon.ion.stream import SimpleStreamPublisher, SimpleStreamSubscriber

class TransformBase(SimpleProcess):
    def on_start(self):
        super(TransformBase,self).on_start()

class TransformStreamProcess(TransformBase):
    pass

class TransformEventProcess(TransformBase):
    pass

class TransformStreamListener(TransformStreamProcess):

    def on_start(self):
        self.queue_name = self.CFG.get_safe('process.queue_name',self.id)

        # @TODO: queue_name is really exchange_name, rename
        self.subscriber = SimpleStreamSubscriber.new_subscriber(self.container, self.queue_name, self.recv_packet)
        self.subscriber.start()

    def recv_packet(self, msg, headers):
        raise NotImplementedError('Method recv_packet not implemented')

    def on_quit(self):
        self.subscriber.stop()

class TransformStreamPublisher(TransformStreamProcess):

    def on_start(self):
        self.exchange_point = self.CFG.get_safe('process.exchange_point', '')

        self.publisher = SimpleStreamPublisher.new_publisher(self.container,self.exchange_point,'')

    def publish(self, msg, to_name):
        raise NotImplementedError('Method publish not implemented')

    def on_quit(self):
        self.publisher.close()

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
