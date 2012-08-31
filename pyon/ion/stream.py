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
from interface.services.dm.ipubsub_management_service import PubsubManagementServiceProcessClient
from pyon.core import bootstrap
from pyon.util.log import log
from interface.objects import StreamRoute

import gevent


class StreamPublisher(ProcessPublisher):
    """
    Data management abstraction of EndPoint layer for publishing messages to a stream
    """

    pass

class StreamPublisherRegistrar(object):
    """
    A Data Management level object for creating a publisher for a stream
    This object manages registration of publishers for different streams and creates the abstracted endpoint with the
    publish method
    """

    def __init__(self, process=None, container=None):
        """
        Use the process's exchange name to publish messages to a stream
        """
        self.process = process
        self.exchange_name = process.id
        self.container = container
        self.pubsub_client = PubsubManagementServiceProcessClient(process=process, node=container.node)

        xs_dot_xp = CFG.core_xps.science_data
        try:
            _, self.xp_base = xs_dot_xp.split('.')
            self._XS = self.container.ex_manager.default_xs
        except ValueError:
            raise PublisherError('Invalid CFG for core_xps.science_data: "%s"; must have "xs.xp" structure' % xs_dot_xp)


    def create_publisher(self, stream_id):
        """
        Call pubsub service to register this exchange name (endpoint) to publish on a particular stream
        Return a stream publisher object to publish (send) messages on a particular stream
        """
        log.debug('Creating publisher...')

        # Call the pubsub service to register the exchange name as a publisher for this stream
        stream_route = self.pubsub_client.register_producer(self.exchange_name, stream_id)

        # create an XP and XPRoute
        xp = self.container.ex_manager.create_xp(self.xp_base)
        xpr = xp.create_route(stream_route.routing_key)

        # Create the Stream publisher, ready to publish messages to the stream
        return StreamPublisher(to_name=xpr, process=self.process, node=self.container.node)


class StreamSubscriber(ProcessSubscriber):
    """
    Data management abstraction of the subscriber endpoint

    By default, routes messages into the attached process' call_process method.
    You can override this by specifying your own callback, taking a single parameter,
    the message received.

    Instead of managing your own greenlet, you should be using the IonProcessThread's add_endpoint.
    """
    class NoBindSubscriberChannel(SubscriberChannel):

        def _bind(self, binding):
            log.debug("StreamSubscriber passing on _bind: %s", binding)

        """
        # Once EMS exists - remove the declare!
        def _declare_exchange(self, xp):
            log.debug("StreamSubscriber passing on _declare_exchange: %s", xp)
        """

    channel_type = NoBindSubscriberChannel

    def __init__(self, **kwargs):
        """
        @param name is a tuple (xp, exchange_name)
        @param callback is a call back function
        @param Process is the subscribing process
        @param node is cc.node
        """
        assert "process" in kwargs
        if not kwargs.get('callback', None):
            kwargs = kwargs.copy()
            kwargs['callback'] = kwargs.get('process').call_process

        ProcessSubscriber.__init__(self, **kwargs)

    def start(self):
        """
        Start consuming from the queue
        """
        if self._chan is not None:
            try:
                self._chan.start_consume()
            except ChannelError:
                log.info('Subscriber is already started')

        else:
            self.gl = spawn(self.listen)

    def stop(self):
        """
        Stop consuming from the queue
        """

        if self._chan is not None:
            self._chan.stop_consume()
        else:

            raise SubscriberError('Can not stop the subscriber before it is started')

    def close(self):

        self.stop()
        if self._chan is not None:
            self._chan.close()

            # This does not work - it hangs - why?
            #if hasattr(self, 'gl'):
            #    self.gl.join()

class StreamSubscriberRegistrarError(StandardError):
    """
    Error class for the StreamSubscriberRegistrar
    """

class StreamSubscriberRegistrar(object):
    """
    Class to create and register subscriptions in the pubsub service, create a StreamSubscriber
    """

    def __init__(self, process=None, container=None):
        self.process = process
        self.container = container
        self._subscriber_cnt = 0

        xs_dot_xp = CFG.core_xps.science_data
        try:
            _, self.xp_base = xs_dot_xp.split('.')
            self._XS = self.container.ex_manager.default_xs

        except ValueError:
            raise PublisherError('Invalid CFG for core_xps.science_data: "%s"; must have "xs.xp" structure' % xs_dot_xp)


    def create_subscriber(self, exchange_name=None, callback=None):
        """
        This method creates a new subscriber, a new exchange_name if it does not already exist.
        """

        if not exchange_name:
            #@todo - remove this! it does not belong here!

            # if not create a new one based on the process id
            exchange_name =  '%s_subscriber_%d' % (self.process.id, self._subscriber_cnt)
            self._subscriber_cnt += 1

        # create an XN
        xn = self.container.ex_manager.create_xn_queue(exchange_name)

        # create an XP
        # xp = self.container.ex_manager.create_xp(self.xp_base)
        # bind it on the XP
        # xn.bind(exchange_name, xp)

        return StreamSubscriber(from_name=xn, process=self.process, callback=callback, node=self.container.node)



class SimpleStreamPublisher(Publisher):
    def __init__(self,exchange_point, stream_id):
        validate_is_instance(exchange_point,ExchangePoint)
        self.stream_id = stream_id
        self.exchange_point = exchange_point
        super(SimpleStreamPublisher,self).__init__()

    def publish(self, msg, stream_id=''):
        if not stream_id:
            stream_id = self.stream_id
        return super(SimpleStreamPublisher,self).publish(msg,to_name=self.exchange_point.create_route('%s.data' % stream_id))

    @classmethod
    def new_publisher(cls,container,exchange_point,stream_id):
        xp = container.ex_manager.create_xp(exchange_point)
        return cls(xp,stream_id)

class SimpleStreamRoutePublisher(Publisher):
    def __init__(self,exchange_point, routing_key):
        validate_is_instance(exchange_point,ExchangePoint)
        self.routing_key = routing_key
        self.exchange_point = exchange_point
        super(SimpleStreamRoutePublisher,self).__init__()

    def publish(self, msg, routing_key=''):
        if not routing_key:
            routing_key = self.routing_key
        return super(SimpleStreamRoutePublisher,self).publish(msg,to_name=self.exchange_point.create_route('%s' % routing_key))

    @classmethod
    def new_publisher(cls,container,stream_route):
        validate_is_instance(stream_route,StreamRoute)
        xp = container.ex_manager.create_xp(stream_route.exchange_point)
        return cls(xp,stream_route.routing_key)

class SimpleStreamSubscriber(Subscriber):
    def __init__(self,*args, **kwargs):
        self.started = False
        super(SimpleStreamSubscriber,self).__init__(*args,**kwargs)
    def start(self):
        self.started = True
        self.greenlet = gevent.spawn(self.listen)
    def stop(self):
        if not self.started:
            raise BadRequest('Can\'t stop a subscriber that hasn\'t started.')

        self.close()
        self.greenlet.join(timeout=10)
        self.started = False
    @classmethod
    def new_subscriber(cls, container, exchange_name, callback):
        xn = container.ex_manager.create_xn_queue(exchange_name)
        instance = cls(name=xn,callback=callback)
        setattr(instance,'xn',xn)
        return instance

class SimpleStreamRouteSubscriber(Subscriber):
    def __init__(self,*args, **kwargs):
        self.started = False
        super(SimpleStreamRouteSubscriber,self).__init__(*args,**kwargs)
    def start(self):
        self.started = True
        self.greenlet = gevent.spawn(self.listen)
    def stop(self):
        if not self.started:
            raise BadRequest('Can\'t stop a subscriber that hasn\'t started.')

        self.close()
        self.greenlet.join(timeout=10)
        self.started = False
    @classmethod
    def new_subscriber(cls, container, exchange_name,stream_route,callback):
        xp = container.ex_manager.create_xp(stream_route.exchange_point)
        xn = container.ex_manager.create_xn_queue(exchange_name)
        xn.bind(stream_route.routing_key, xp)
        instance = cls(name=xn,callback=callback)
        setattr(instance,'xn',xn)
        return instance
