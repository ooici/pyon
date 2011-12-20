#!/usr/bin/env python

"""Events and Notification"""

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

EVENTS_XP = "pyon.events"
EVENTS_XP_TYPE = "topic"

from pyon.net.endpoint import Publisher, Subscriber, PublisherEndpointUnit, SubscriberEndpointUnit
from pyon.net.channel import PubChannel, SubscriberChannel
from pyon.util.log import log

class EventPublisher(Publisher):

    event_name = "BASE_EVENT"       # override this in your derived publisher

    def __init__(self, xp=None, **kwargs):

        # generate a name
        xp = xp or EVENTS_XP
        name = (xp, self.event_name)

        Publisher.__init__(self, name=name, **kwargs)

    def _topic(self, origin):
        """
        Builds the topic that this event should be published to.
        """
        assert self.event_name and origin
        return "%s.%s" % (str(self.event_name), str(origin))

    def create_event(self, **kwargs):
        pass

    def publish_event(self, event_msg, origin=None, **kwargs):
        assert origin

        to_name=self._topic(origin)
        log.debug("Publishing message to %s", to_name)

        ep = self.publish(event_msg, to_name=routing_key)
        ep.close()

    def create_and_publish_event(self, origin=None, **kwargs):
        msg = self.create_event(**kwargs)
        self.publish_event(msg, origin=origin)

