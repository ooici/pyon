#!/usr/bin/env python

"""ION stream endpoints/registrars"""
from pyon.util import log

__author__ = 'Michael Meisinger, David Stuebe, Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import CFG, IonObject
from pyon.core.exception import BadRequest
from pyon.ion.endpoint import ProcessPublisher, ProcessSubscriber, PublisherError
from pyon.net.endpoint import Publisher, Subscriber
from pyon.net.channel import PublisherChannel, SubscriberChannel, ChannelError
from pyon.util.async import  spawn
from pyon.util.arg_check import validate_is_instance
from pyon.ion.exchange import ExchangePoint
from interface.services.dm.ipubsub_management_service import PubsubManagementServiceClient
from pyon.core import bootstrap
from pyon.util.log import log
from interface.objects import StreamRoute, Packet

import gevent

class StreamPublisher(Publisher):
    def __init__(self, stream_id='', stream_route=None, exchange_point='', routing_key=''):
        super(StreamPublisher,self).__init__()
        from pyon.container.cc import Container
        self.stream_id = stream_id
        if stream_id:
            # Regardless of what's passed in for stream_route look it up, prevents mismatching
            pubsub_cli=PubsubManagementServiceClient()
            self.stream_route = pubsub_cli.read_stream_route(stream_id)

        if not stream_route:
            if exchange_point and routing_key:
                self.stream_route = StreamRoute(exchange_point=exchange_point,routing_key=routing_key)
        else:
            self.stream_route = stream_route
        validate_is_instance(self.stream_route, StreamRoute, 'No valid stream route provided to publisher.')

        cc = Container.instance
        self.xp = cc.ex_manager.create_xp(self.stream_route.exchange_point)

    def publish(self, msg, stream_id='', stream_route=None):
        xp = self.xp
        if stream_route:
            from pyon.container.cc import Container
            cc = Container.instance
            xp = cc.ex_manager.create_xp(stream_route.exchange_point)
        else:
            stream_route = self.stream_route
        packet = Packet(route=stream_route or self.stream_route, stream_id=stream_id or self.stream_id, body=msg)
        xp = self.xp
        super(StreamPublisher,self).publish(packet, to_name=xp.create_route(stream_route.routing_key))

class StreamSubscriber(Subscriber):
    def __init__(self, exchange_name, callback):
        from pyon.container.cc import Container
        cc = Container.instance
        self.xn = cc.ex_manager.create_xn_queue(exchange_name)
        self.started = False
        self.callback = callback
        super(StreamSubscriber,self).__init__(name=self.xn,callback=self.preprocess)

    def preprocess(self, msg, headers):
        packet = msg
        if not isinstance(packet, Packet): 
            log.warn('Received non-packet on stream.')
            return
        self.callback(packet.body, packet.route, packet.stream_id)
   
    def start(self):
        self.started = True
        self.greenlet = gevent.spawn(self.listen)
    
    def stop(self):
        if not self.started: 
            raise BadRequest("Subscriber is not running.")
        self.close()
        self.greenlet.join(timeout=10)
        self.started = False



        

class StreamSubscriberRegistrar(object):
    pass

class StreamPublisherRegistrar(object):
    pass

