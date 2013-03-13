#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@file pyon/ion/stream.py
@date Fri Sep  7 14:31:28 EDT 2012
@brief Ion Stream-based publishing and subscribing
'''

import gevent

from pyon.core.exception import BadRequest
from pyon.net.endpoint import Publisher, Subscriber
from pyon.util.arg_check import validate_is_instance
from interface.services.dm.ipubsub_management_service import PubsubManagementServiceProcessClient
from pyon.util.log import log
from pyon.ion.service import BaseService
from interface.objects import StreamRoute


class StreamPublisher(Publisher):
    '''
    Stream Publisher maintains the "stream" concept and properly encapsulates outgoing messages in the streaming
    packet. Stream Publisher is intended to be used in an Ion Process.
    '''

    def __init__(self, process=None, stream_id='', stream_route=None, exchange_point='', routing_key=''):
        '''
        Creates a StreamPublisher which publishes to the specified stream by default and is attached to the
        specified process.
        @param process        The process which the subscriber is to be attached.
        @param stream_id      Stream identifier for the publishing stream.
        @param stream_route   A StreamRoute corresponding to the stream_id
        @param exchange_point The name of the exchange point, to be used in lieu of stream_route or stream_id
        @param routing_key    The routing key to be used in lieu of stream_route or stream_id
        '''
        super(StreamPublisher, self).__init__()
        validate_is_instance(process, BaseService, 'No valid process provided.')
        #--------------------------------------------------------------------------------
        # The important part of publishing is the stream_route and there are three ways
        # to the stream route
        #   - The Route is obtained from Pubsub Management with a stream id.
        #   - The Route is obtained by combining exchange_point and the routing_key
        #     but all other information is lost (credentials, etc.)
        #   - The Route is obtained by being provided directly to __init__
        #--------------------------------------------------------------------------------
        self.stream_id = stream_id
        if stream_id:
            # Regardless of what's passed in for stream_route look it up, prevents mismatching
            pubsub_cli = PubsubManagementServiceProcessClient(process=process, node=process.container.node)
            self.stream_route = pubsub_cli.read_stream_route(stream_id)

        elif not stream_route:
            self.stream_route = None
            if exchange_point and routing_key:
                self.stream_route = StreamRoute(exchange_point=exchange_point, routing_key=routing_key)
            else:
                pubsub_cli = PubsubManagementServiceProcessClient(process=process, node=process.container.node)
                stream_id, stream_route = pubsub_cli.create_stream(process.id, exchange_point=exchange_point or 'void')
                self.stream_id = stream_id
                self.stream_route = stream_route
        else:
            self.stream_route = stream_route
        validate_is_instance(self.stream_route, StreamRoute, 'No valid stream route provided to publisher.')

        self.container = process.container
        self.xp = self.container.ex_manager.create_xp(self.stream_route.exchange_point)
        self.xp_route = self.xp.create_route(self.stream_route.routing_key)

    def publish(self, msg, stream_id='', stream_route=None):
        '''
        Encapsulates and publishes a message; the message is sent to either the specified
        stream/route or the stream/route specified at instantiation
        '''
        xp = self.xp
        xp_route = self.xp_route
        log.trace('Exchange: %s', xp.exchange)
        if stream_route:
            xp = self.container.ex_manager.create_xp(stream_route.exchange_point)
            xp_route = xp.create_route(stream_route.routing_key)
        else:
            stream_route = self.stream_route
        log.trace('Publishing (%s,%s)', xp.exchange, stream_route.routing_key)
        super(StreamPublisher,self).publish(msg, to_name=xp_route, headers={'exchange_point':stream_route.exchange_point, 'stream':stream_id or self.stream_id})


class StreamSubscriber(Subscriber):
    '''
    StreamSubscriber is a subscribing class to be attached to an Ion process which adheres to the
    Ion based Stream Pubsub framework.

    The callback should accept three parameters:
      message      The incoming message
      stream_route The route from where the message came.
      stream_id    The identifier of the stream.

    Ex:
      def receive(msg, route, stream_id):
          pass
    '''
    def __init__(self, process, exchange_name, callback=None):
        '''
        Creates a new StreamSubscriber which will listen on the specified queue (exchange_name).
        @param process       The Ion Process to attach to.
        @param exchange_name The subscribing queue name.
        @param callback      The callback to execute upon receipt of a packet.
        '''
        validate_is_instance(process, BaseService, 'No valid process was provided.')
        self.container = process.container
        self.xn = self.container.ex_manager.create_xn_queue(exchange_name)
        self.started = False
        self.callback = callback or process.call_process
        super(StreamSubscriber, self).__init__(from_name=self.xn, callback=self.preprocess)

    def preprocess(self, msg, headers):
        '''
        De-encapsulates the incoming message and calls the callback.
        @param msg     The incoming packet.
        @param headers The headers of the incoming message.
        '''
        route = StreamRoute(headers['exchange_point'], headers['routing_key'])
        self.callback(msg, route, headers['stream'])

    def start(self):
        '''
        Begins consuming on the queue.
        '''
        self.started = True
        self.greenlet = gevent.spawn(self.listen)

    def stop(self):
        '''
        Ceases consuming on the queue.
        '''
        if not self.started:
            raise BadRequest("Subscriber is not running.")
        self.close()
        self.greenlet.join(timeout=10)
        self.greenlet.kill()
        self.started = False


class StandaloneStreamPublisher(Publisher):
    '''
    StandaloneStreamPublisher is a Publishing endpoint which uses Ion Streams but
    does not belong to a process.

    This endpoint is intended for testing and debugging not to be used in service
    or process implementations.
    '''
    def __init__(self, stream_id, stream_route):
        '''
        Creates a new StandaloneStreamPublisher
        @param stream_id    The stream identifier
        @param stream_route The StreamRoute to publish on.
        '''
        super(StandaloneStreamPublisher, self).__init__()
        from pyon.container.cc import Container
        self.stream_id = stream_id
        validate_is_instance(stream_route, StreamRoute, 'stream route is not valid')
        self.stream_route = stream_route

        self.xp = Container.instance.ex_manager.create_xp(stream_route.exchange_point)
        self.xp_route = self.xp.create_route(stream_route.routing_key)


    def publish(self, msg, stream_id='', stream_route=None):
        '''
        Encapsulates and publishes the message on the specified stream/route or
        the one specified at instantiation.
        @param msg          Outgoing message
        @param stream_id    Stream Identifier
        @param stream_route Stream Route
        '''
        from pyon.container.cc import Container
        stream_id = stream_id or self.stream_id
        xp = self.xp
        xp_route = self.xp_route
        if stream_route:
            xp = Container.instance.ex_manager.create_xp(stream_route.exchange_point)
            xp_route = xp.create_route(stream_route.routing_key)
        stream_route = stream_route or self.stream_route
        super(StandaloneStreamPublisher, self).publish(msg, to_name=xp_route, headers={'exchange_point': stream_route.exchange_point, 'stream': stream_id or self.stream_id})


class StandaloneStreamSubscriber(Subscriber):
    '''
    StandaloneStreamSubscriber is a Subscribing endpoint which uses Streams but
    does not belong to a process.

    This endpoint is intended for testing and debugging not to be used in service
    or process implementations.
    '''
    def __init__(self, exchange_name, callback):
        '''
        Creates a new StandaloneStreamSubscriber
        @param exchange_name The name of the queue to listen on.
        @param callback      The callback to execute on receipt of a packet
        '''
        from pyon.container.cc import Container
        self.xn = Container.instance.ex_manager.create_xn_queue(exchange_name)
        self.callback = callback
        self.started = False
        super(StandaloneStreamSubscriber, self).__init__(name=self.xn, callback=self.preprocess)

    def preprocess(self, msg, headers):
        '''
        Performs de-encapsulation of incoming packets and calls the callback.
        @param msg     The incoming packet.
        @param headers The headers of the incoming message.
        '''
        route = StreamRoute(headers['exchange_point'], headers['routing_key'])
        self.callback(msg, route, headers['stream'])

    def start(self):
        '''
        Begin consuming on the queue.
        '''
        self.started = True
        self.greenlet = gevent.spawn(self.listen)

    def stop(self):
        '''
        Cease consuming on the queue.
        '''
        if not self.started:
            raise BadRequest("Subscriber is not running.")
        self.close()
        self.greenlet.join(timeout=10)
        self.greenlet.kill()
        self.started = False

