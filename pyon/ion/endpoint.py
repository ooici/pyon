#!/usr/bin/env python

"""ION messaging endpoints"""

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.net.endpoint import ProcessRPCClient, ProcessRPCServer, Publisher, Subscriber

class ProcessPublisher(Publisher):
    def __init__(self, process=None, **kwargs):
        self._process = process
        Publisher.__init__(self, **kwargs)

class StreamPublisher(ProcessPublisher):
    """
    Data management abstraction of EndPoint layer for publishing messages to a stream
    TODO: Could be an object that uses a publisher?
    """

    def __init__(self, stream_route, **kwargs):
        self._stream_route = stream_route

        ProcessPublisher.__init__(self, name=stream_route.exchange_name, **kwargs) # not correct interface yet!
        # @TODO Cant distinguish my exchange name from the to_name in the endpoint layer. Need a concept of FROM

class StreamPublisherRegistrar(object):
    """
    A Data Management level object for creating a publisher for a stream
    This object manages registration of publishers for different streams and creates the abstracted endpoint with the
    publish method
    """

    def __init__(self, process):
        """
        Use the process's exchange name to publish messages to a stream
        """
        self.process = process
        self.exchange_name = process.id
        self.pubsub_client = process.clients.pubsub_management

    def create_publisher(self, stream_id):
        """
        Call pubsub service to register this exchange name (endpoint) to publish on a particular stream
        Return a stream publisher object to publish (send) messages on a particular stream
        """

        # Call the pubsub service to register the exchange name as a publisher for this stream
        stream_route = self.pubsub_client.register_producer(self.exchange_name, stream_id)

        # Create the Stream publisher, ready to publish messages to the stream
        return StreamPublisher(stream_route, process, node=process.container.node)

class ProcessSubscriber(Subscriber):
    def __init__(self, process=None, **kwargs):
        self._process = process
        Subscriber.__init__(self, **kwargs)

class StreamSubscriber(ProcessSubscriber):
    """
    Data management abstraction of the subscriber endpoint
    """
    def __init__(self, subscriber, subscription_id=None, **kwargs):
        ProcessSubscriber.__init__(self, **kwargs)
        self._subscriber = subscriber
        self._subscription_id = subscription_id

    def start(self):
        """
        Start consuming from the queue
        """
        # I now believe this is incorrect - how can this be implemented properly?
        channel = self._subscriber_endpoint.channel
        self._subscriber_endpoint.attach_channel(channel)
        # what should the correct behavior be for already attached?

    def stop(self):
        """
        Stop consuming from the queue
        """
        # @TODO - not implemented in the endpoint layer yet.

class StreamSubscriberRegistrar(object):
    """
    Class to create and register subscriptions in the pubsub service, create a StreamSubscriber
    """

    def __init__(self, process):
        self.process = process
        self.pubsub_client = process.clients.pubsub_management

    def subscribe(self, exchange_name='', callback=None, query=None):
        """
        This method creates a new subscriber, a new exchange_name if it does not already exist, and a new subscription
        if a query is provided.
        """

        # @TODO what about node - do I need to pass that?
        # @TODO what about an anonymous exchange name - how can we allow that?
        # Is there automatically a binding for the exchange name when it is created? We want the pubsub service to
        # control routes for this exchange name
        # Will this No-op if the exhange name already exists? That is what I intended...
        s = Subscriber(callback=callback, name=exchange_name)

        # @TODO - Is the subscriber already attached - is that the correct behavior?

        sub_id = None
        if query is not None:
            # Call the pubsub service to create a subscription if a query is provided
            subscription = IonObject("Subscription", {'exchange_name':exchange_name,'query':query})
            sub_id = self.pubsub_client.subscribe(subscription)

        return StreamSubscriber(s, sub_id, self.process)

    def activate_subscription(self, stream_subscriber):
        """
        Call the pubsub service to activate the subscription
        """
        self.pubsub_client.activate_subscription(stream_subscriber._subscription_id)

    def deactivate_subscription(self, stream_subscriber):
        """
        Call the pubsub service to deactivate the subscription
        """
        self.pubsub_client.deactivate_subscription(stream_subscriber._subscription_id)



