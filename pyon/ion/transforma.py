#!/usr/bin/env python

'''
@author: Tim Giguere <tgiguere@asascience.com>
@file: pyon/ion/transforma.py
@description: New Implementation for TransformBase class
'''

from pyon.ion.process import SimpleProcess
from pyon.event.event import EventSubscriber, EventPublisher
from pyon.ion.stream import StreamPublisher, StreamSubscriber
from pyon.net.endpoint import RPCServer, RPCClient
from pyon.util.log import log
import gevent


class TransformBase(SimpleProcess):
    '''
    TransformBase is the base class for all Transform Processes
    '''
    def __init__(self):
        super(TransformBase, self).__init__()
        self._stats = {}  # Container for statistics information

    def on_start(self):
        '''
        Begins listening for incoming RPC calls.
        '''
        log.info('TransformBase on_start called')
        super(TransformBase, self).on_start()
        self._rpc_server = RPCServer(self, from_name=self.id)
        self._listener = gevent.spawn(self._rpc_server.listen)

    def on_quit(self):
        '''
        Closes the listener.
        '''
        self._rpc_server.close()
        self._listener.join(5)
        super(TransformBase, self).on_quit()

    def _stat(self):
        return self._stats

    @classmethod
    def stats(cls, pid):
        '''
        RPC Method for querying a Transform's internal statistics
        '''
        rpc_cli = RPCClient(to_name=pid)
        return rpc_cli.request({}, op='_stat')


class TransformStreamProcess(TransformBase):
    '''
    Transforms which interact with Ion Streams.
    '''
    def __init__(self):
        super(TransformStreamProcess, self).__init__()

    def on_start(self):
        super(TransformStreamProcess, self).on_start()


class TransformEventProcess(TransformBase):
    '''
    Transforms which interact with Ion Events.
    '''
    def __init__(self):
        super(TransformEventProcess, self).__init__()

    def on_start(self):
        super(TransformEventProcess, self).on_start()


class TransformStreamListener(TransformStreamProcess):
    '''
    Transforms which listen to a queue for incoming
    Ion Streams.

    Parameters:
      process.queue_name Name of the queue to listen on.
    '''
    def __init__(self):
        super(TransformStreamListener, self).__init__()

    def on_start(self):
        '''
        Sets up the subscribing endpoint and begins consuming.
        '''
        super(TransformStreamListener, self).on_start()
        self.queue_name = self.CFG.get_safe('process.queue_name', self.id)

        self.subscriber = StreamSubscriber(process=self, exchange_name=self.queue_name, callback=self.recv_packet)
        self.subscriber.start()

    def recv_packet(self, msg, stream_route, stream_id):
        '''
        To be implemented by the transform developer.
        This method is called on receipt of an incoming message from a stream.
        '''
        raise NotImplementedError('Method recv_packet not implemented')

    def on_quit(self):
        '''
        Stops consuming on the queue.
        '''
        self.subscriber.stop()
        super(TransformStreamListener, self).on_quit()


class TransformStreamPublisher(TransformStreamProcess):
    '''
    Transforms which publish on a stream.

    Parameters:
      process.stream_id      Outgoing stream identifier.
      process.exchange_point Route's exchange point.
      process.routing_key    Route's routing key.

    Either the stream_id or both the exchange_point and routing_key need to be provided.
    '''
    def __init__(self):
        super(TransformStreamPublisher, self).__init__()

    def on_start(self):
        '''
        Binds the publisher to the transform
        '''
        super(TransformStreamPublisher, self).on_start()
        self.stream_id      = self.CFG.get_safe('process.stream_id', '')
        self.exchange_point = self.CFG.get_safe('process.exchange_point', 'science_data')
        self.routing_key    = self.CFG.get_safe('process.routing_key', '')

        self.publisher = StreamPublisher(process=self, stream_id=self.stream_id, exchange_point=self.exchange_point, routing_key=self.routing_key)

    def publish(self, msg, to_name):
        '''
        To be implemented by the transform developer.
        '''
        raise NotImplementedError('Method publish not implemented')

    def on_quit(self):
        self.publisher.close()
        super(TransformStreamPublisher, self).on_quit()


class TransformEventListener(TransformEventProcess):

    def __init__(self):
        super(TransformEventListener, self).__init__()

    def on_start(self):
        super(TransformEventListener, self).on_start()
        event_type = self.CFG.get_safe('process.event_type', '')

        self.listener = EventSubscriber(event_type=event_type, callback=self.process_event)
        self.listener.start()

    def process_event(self, msg, headers):
        raise NotImplementedError('Method process_event not implemented')

    def on_quit(self):
        self.listener.stop()
        super(TransformEventListener, self).on_quit()


class TransformEventPublisher(TransformEventProcess):

    def __init__(self):
        super(TransformEventPublisher, self).__init__()

    def on_start(self):
        super(TransformEventPublisher, self).on_start()
        event_type = self.CFG.get_safe('process.event_type', '')

        self.publisher = EventPublisher(event_type=event_type)

    def publish_event(self, *args, **kwargs):
        raise NotImplementedError('Method publish_event not implemented')

    def on_quit(self):
        self.publisher.close()
        super(TransformEventPublisher, self).on_quit()


class TransformDatasetProcess(TransformBase):

    def __init__(self):
        super(TransformDatasetProcess, self).__init__()


class TransformDataProcess(TransformStreamListener, TransformStreamPublisher):
    '''
    Transforms which have an incoming stream and an outgoing stream.

    Parameters:
      process.stream_id      Outgoing stream identifier.
      process.exchange_point Route's exchange point.
      process.routing_key    Route's routing key.
      process.queue_name     Name of the queue to listen on.

    Either the stream_id or both the exchange_point and routing_key need to be provided.
    '''

    def __init__(self):
        super(TransformDataProcess, self).__init__()

    def on_start(self):
        super(TransformDataProcess, self).on_start()

    def on_quit(self):
        super(TransformDataProcess, self).on_quit()


class TransformAlgorithm(object):

    @staticmethod
    def execute(*args, **kwargs):
        raise NotImplementedError('Method execute not implemented')
