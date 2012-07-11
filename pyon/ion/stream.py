#!/usr/bin/env python

"""ION stream endpoints/registrars"""
from pyon.util import log

__author__ = 'Michael Meisinger, David Stuebe, Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

from pyon.core.bootstrap import CFG, IonObject
from pyon.ion.endpoint import ProcessPublisher, ProcessSubscriber, PublisherError
from pyon.net.channel import PublisherChannel, SubscriberChannel, ChannelError
from pyon.util.async import  spawn
from interface.services.dm.ipubsub_management_service import PubsubManagementServiceProcessClient
from pyon.core import bootstrap
from pyon.util.log import log


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


