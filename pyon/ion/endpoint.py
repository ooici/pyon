#!/usr/bin/env python

"""ION messaging endpoints"""
from pyon.util import log

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.net.endpoint import ProcessRPCClient, ProcessRPCServer, Publisher, Subscriber
from pyon.public import CFG, IonObject
from pyon.util.log import log
from pyon.net.channel import PublisherChannel, SubscriberChannel, ChannelError
from pyon.util.async import  spawn
from interface.services.dm.ipubsub_management_service import PubsubManagementServiceProcessClient

class ProcessPublisher(Publisher):
    def __init__(self, process=None, **kwargs):
        self._process = process
        Publisher.__init__(self, **kwargs)


class PublisherError(StandardError):
    """
    An exception class for errors in the subscriber
    """


class StreamPublisher(ProcessPublisher):
    """
    Data management abstraction of EndPoint layer for publishing messages to a stream
    """

    class NoDeclarePublisherChannel(PublisherChannel):

        """
        # Once EMS exists - remove the declare!
        def _declare_exchange_point(self, xp):
            log.debug("StreamPublisher passing on _declare_exchange_point: %s", xp)
        """
    channel_type = NoDeclarePublisherChannel

    '''
    def __init__(self, **kwargs):
        """
        @param stream_route is a stream_route object
        @param process is the publishing process
        @param node is cc.node
        """

        self._stream_route = stream_route


        ProcessPublisher.__init__(self, **kwargs)
    '''


class StreamPublisherRegistrar(object):
    """
    A Data Management level object for creating a publisher for a stream
    This object manages registration of publishers for different streams and creates the abstracted endpoint with the
    publish method
    """

    def __init__(self, process=None, node=None):
        """
        Use the process's exchange name to publish messages to a stream
        """
        self.process = process
        self.exchange_name = process.id
        self.node = node
        self.pubsub_client = PubsubManagementServiceProcessClient(process=process, node=node)

        xs_dot_xp = CFG.core_xps.science_data
        try:
            self.XS, self.XP = xs_dot_xp.split('.')
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

        # Create the Stream publisher, ready to publish messages to the stream
        return StreamPublisher(name=(self.XP, stream_route.routing_key), process=self.process, node=self.node)



class SubscriberError(StandardError):
    """
    An exception class for errors in the subscriber
    """


class ProcessSubscriber(Subscriber):
    def __init__(self, process=None, **kwargs):
        self._process = process
        Subscriber.__init__(self, **kwargs)


class StreamSubscriber(ProcessSubscriber):
    """
    Data management abstraction of the subscriber endpoint
    """
    class NoBindSubscriberChannel(SubscriberChannel):

        def _bind(self, binding):
            log.debug("StreamSubscriber passing on _bind: %s", binding)

        """
        # Once EMS exists - remove the declare!
        def _declare_exchange_point(self, xp):
            log.debug("StreamSubscriber passing on _declare_exchange_point: %s", xp)
        """

    channel_type = NoBindSubscriberChannel


    def __init__(self, subscription_id=None, **kwargs):
        """
        @param name is a tuple (xp, exchange_name)
        @param callback is a call back function
        @param Process is the subscribing process
        @param node is cc.node
        """
        ProcessSubscriber.__init__(self, **kwargs)
        self.subscription_id = subscription_id

    def start(self):
        """
        Start consuming from the queue
        """
        if hasattr(self, '_chan'):
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

        if hasattr(self, '_chan'):
            self._chan.stop_consume()
        else:

            raise SubscriberError('Can not stop the subscriber before it is started')

    def close(self):

        self.stop()
        if hasattr(self, '_chan'):
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

    def __init__(self, process=None, node=None):
        self.process = process
        self.node = node
        self.pubsub_client = PubsubManagementServiceProcessClient(process=process, node=node)

        self._subscriber_cnt = 0

        xs_dot_xp = CFG.core_xps.science_data
        try:
            self.XS, self.XP = xs_dot_xp.split('.')
        except ValueError:
            raise PublisherError('Invalid CFG for core_xps.science_data: "%s"; must have "xs.xp" structure' % xs_dot_xp)


    def subscribe(self, exchange_name=None, callback=None, query=None):
        """
        This method creates a new subscriber, a new exchange_name if it does not already exist, and a new subscription
        if a query is provided.
        """

        if not exchange_name:
            # if not create a new one based on the process id
            exchange_name =  '%s_subscriber_%d' % (self.process.id, self._subscriber_cnt)
            self._subscriber_cnt += 1

            if query is None:
                # one or the other must be provided
                raise StreamSubscriberRegistrarError('You can not register a new subscriber without a name or a query!')

        sub_id = None
        if query is not None:
            # Call the pubsub service to create a subscription if a query is provided
            subscription = IonObject("Subscription", {'exchange_name':exchange_name,'query':query})
            sub_id = self.pubsub_client.create_subscription(subscription)

        return StreamSubscriber(subscription_id=sub_id, name=(self.XP, exchange_name), process=self.process, callback=callback, node=self.node)

    def activate_subscription(self, stream_subscriber):
        """
        Call the pubsub service to activate the subscription
        """
        if stream_subscriber._subscription_id is None:
            raise StreamSubscriberRegistrarError('You can not activate a subscription if you do not own the subscription')
        self.pubsub_client.activate_subscription(stream_subscriber._subscription_id)

    def deactivate_subscription(self, stream_subscriber):
        """
        Call the pubsub service to deactivate the subscription
        """
        if stream_subscriber._subscription_id is None:
            raise StreamSubscriberRegistrarError('You can not deactivate a subscription if you do not own the subscription')
        self.pubsub_client.deactivate_subscription(stream_subscriber._subscription_id)



