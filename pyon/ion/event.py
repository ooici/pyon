#!/usr/bin/env python

"""Events framework with publisher, subscriber and repository."""

__author__ = 'Dave Foster <dfoster@asascience.com>, Michael Meisinger'
__license__ = 'Apache 2.0'

import functools
import sys
import traceback
from gevent import event as gevent_event

from pyon.core import bootstrap
from pyon.core.exception import BadRequest, IonException, StreamException
from pyon.datastore.datastore import DataStore
from pyon.ion.identifier import create_unique_event_id
from pyon.net.endpoint import Publisher, Subscriber
from pyon.util.async import spawn
from pyon.util.containers import get_ion_ts, is_valid_ts
from pyon.util.log import log

from interface.objects import Event


# @TODO: configurable
EVENTS_XP = "pyon.events"
EVENTS_XP_TYPE = "topic"

#The event will be ignored if older than this time period
VALID_EVENT_TIME_PERIOD = 365 * 24 * 60 * 60 * 1000   # one year

def get_events_exchange_point():
    return "%s.%s" % (bootstrap.get_sys_name(), EVENTS_XP)


class EventError(IonException):
    status_code = 500


class EventPublisher(Publisher):

    def __init__(self, event_type=None, xp=None, **kwargs):
        """
        Constructs a publisher of events for a specific type.

        @param  event_type  The name of the event type object
        @param  xp          Exchange (AMQP) name, can be none, will use events default.
        """

        self.event_type = event_type

        if bootstrap.container_instance and getattr(bootstrap.container_instance, 'event_repository', None):
            self.event_repo = bootstrap.container_instance.event_repository
        else:
            self.event_repo = None

        # generate an exchange name to publish events to
        xp = xp or get_events_exchange_point()
        name = (xp, None)

        Publisher.__init__(self, to_name=name, **kwargs)

    def _topic(self, event_object):
        """
        Builds the topic that this event should be published to.
        """
        assert event_object
        base_types = event_object.base_types or []
        base_str = ".".join(reversed(base_types))
        sub_type = event_object.sub_type or "_"
        origin_type = event_object.origin_type or "_"
        routing_key = "%s.%s.%s.%s.%s" % (base_str, event_object._get_type(), sub_type, origin_type, event_object.origin)
        return routing_key


    def publish_event_object(self, event_object):
        """
        Publishes an event of given type for the given origin. Event_type defaults to an
        event_type set when initializing the EventPublisher. Other kwargs fill out the fields
        of the event. This operation will fail with an exception.
        @param event_object     the event object to be published
        @retval event_object    the event object which was published
        """
        assert event_object

        topic = self._topic(event_object)
        to_name = (self._send_name.exchange, topic)
        log.trace("Publishing event message to %s", to_name)

        current_time = int(get_ion_ts())

        #Ensure valid created timestamp if supplied
        if event_object.ts_created:

            if not is_valid_ts(event_object.ts_created):
                raise BadRequest("The ts_created value is not a valid timestamp: '%s'" % (event_object.ts_created))

            #Reject events that are older than specified time
            if int(event_object.ts_created) > ( current_time + VALID_EVENT_TIME_PERIOD ):
                raise BadRequest("This ts_created value is too far in the future:'%s'" % (event_object.ts_created))

            #Reject events that are older than specified time
            if int(event_object.ts_created) < (current_time - VALID_EVENT_TIME_PERIOD) :
                raise BadRequest("This ts_created value is too old:'%s'" % (event_object.ts_created))

        else:
            event_object.ts_created = str(current_time)

        #Validate this object
        #TODO - enable this once the resource agent issue sending a dict is figured out
        #event_object._validate()

        #Ensure the event object has a unique id
        if '_id' in event_object:
            raise BadRequest("The event object cannot contain a _id field '%s'" % (event_object))

        #Generate a unique ID for this event
        event_object._id = create_unique_event_id()

        try:
            self.publish(event_object, to_name=to_name)
        except Exception as ex:
            log.exception("Failed to publish event (%s): '%s'" % (ex.message, event_object))
            raise

        return event_object


    def publish_event(self, origin=None, event_type=None, **kwargs):
        """
        Publishes an event of given type for the given origin. Event_type defaults to an
        event_type set when initializing the EventPublisher. Other kwargs fill out the fields
        of the event. This operation will fail with an exception.
        @param origin     the origin field value
        @param event_type the event type (defaults to the EventPublisher's event_type if set)
        @param kwargs     additional event fields
        @retval event_object    the event object which was published
        """

        event_type = event_type or self.event_type
        assert event_type

        event_object = bootstrap.IonObject(event_type, origin=origin, **kwargs)
        event_object.base_types = event_object._get_extends()
        ret_val = self.publish_event_object(event_object)
        return ret_val





class BaseEventSubscriberMixin(object):
    """
    A mixin class for Event subscribers to facilitate inheritance.

    EventSubscribers must come in both standard and process level versions, which
    rely on common base code. It is difficult to multiple inherit due to both of
    them sharing a base class, so this mixin is preferred.
    """

    @staticmethod
    def _topic(event_type, origin, sub_type=None, origin_type=None):
        """
        Builds the topic that this event should be published to.
        If either side of the event_id.origin pair are missing, will subscribe to anything.
        """
        if event_type == "Event":
            event_type = "Event.#"
        elif event_type:
            event_type = "#.%s.#" % event_type
        else:
            event_type = "#"

        sub_type = sub_type or "*.#"
        origin_type = origin_type or "*"
        origin      = origin or "*"

        return "%s.%s.%s.%s" % (event_type, sub_type, origin_type, origin)

    def __init__(self, xp_name=None, event_type=None, origin=None, queue_name=None,
                 sub_type=None, origin_type=None, pattern=None):
        self.event_type = event_type
        self.sub_type = sub_type
        self.origin_type = origin_type
        self.origin = origin

        xp_name = xp_name or get_events_exchange_point()
        if pattern:
            binding = pattern
        else:
            binding = self._topic(event_type, origin, sub_type, origin_type)
        self.binding = binding

        # TODO: Provide a case where we can have multiple bindings (e.g. different event_types)

        # prefix the queue_name, if specified, with the sysname
        # this is because queue names transcend xp boundaries (see R1 OOIION-477)
        if queue_name is not None:
            if not queue_name.startswith(bootstrap.get_sys_name()):
                queue_name = "%s.%s" % (bootstrap.get_sys_name(), queue_name)
                log.warn("queue_name specified, prepending sys_name to it: %s", queue_name)

        # set this name to be picked up by inherited folks
        self._ev_recv_name = (xp_name, queue_name)


class EventSubscriber(Subscriber, BaseEventSubscriberMixin):

    ALL_EVENTS = "#"

    def __init__(self, xp_name=None, event_type=None, origin=None, queue_name=None, callback=None,
                 sub_type=None, origin_type=None, pattern=None, auto_delete=None, *args, **kwargs):
        """
        Initializer.

        If the queue_name is specified here, the sysname is prefixed automatically to it. This is because
        named queues are not namespaces to their exchanges, so two different systems on the same broker
        can cross-pollute messages if a named queue is used.

        Note: an EventSubscriber needs to be closed to free broker resources
        """
        self._cbthread = None
        self._auto_delete = auto_delete

        BaseEventSubscriberMixin.__init__(self, xp_name=xp_name, event_type=event_type, origin=origin,
                                          queue_name=queue_name, sub_type=sub_type, origin_type=origin_type, pattern=pattern)

        log.debug("EventPublisher events pattern %s", self.binding)

        Subscriber.__init__(self, from_name=self._ev_recv_name, binding=self.binding, callback=callback, **kwargs)

    def start(self):
        """
        Pass in a subscriber here, this will make it listen in a background greenlet.
        """
        assert not self._cbthread, "start called twice on EventSubscriber"
        gl = spawn(self.listen)
        self._cbthread = gl
        if not self._ready_event.wait(timeout=5):
            log.warning('EventSubscriber start timed out.')
        log.info("EventSubscriber started. Event pattern=%s" % self.binding)
        return gl

    def stop(self):
        self.close()
        self._cbthread.join(timeout=5)
        self._cbthread.kill()
        self._cbthread = None
        log.info("EventSubscriber stopped. Event pattern=%s" % self.binding)

    def __str__(self):
        return "EventSubscriber at %s:\n\trecv_name: %s\n\tcb: %s" % (hex(id(self)), str(self._recv_name), str(self._callback))

    def _create_channel(self, **kwargs):
        """
        Override to set the channel's queue_auto_delete property.
        """
        ch = Subscriber._create_channel(self, **kwargs)
        if self._auto_delete is not None:
            ch.queue_auto_delete = self._auto_delete

        return ch

class EventRepository(object):
    """
    Class that uses a data store to provide a persistent repository for ION events.
    """

    def __init__(self, datastore_manager=None, container=None):
        self.container = container or bootstrap.container_instance

        # Get an instance of datastore configured as directory.
        # May be persistent or mock, forced clean, with indexes
        datastore_manager = datastore_manager or self.container.datastore_manager
        self.event_store = datastore_manager.get_datastore("events", DataStore.DS_PROFILE.EVENTS)

    def start(self):
        pass

    def stop(self):
        self.close()

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.event_store.close()

    def put_event(self, event):
        log.trace("Store event persistently %s", event)
        if not isinstance(event, Event):
            raise BadRequest("event must be type Event, not %s" % type(event))
        return self.event_store.create(event)

    def put_events(self, events):
        log.debug("Store %s events persistently", len(events))
        if type(events) is not list:
            raise BadRequest("events must be type list, not %s" % type(events))
        if not all([isinstance(event, Event) for event in events]):
            raise BadRequest("events must all be type Event")

        if events:
            return self.event_store.create_mult(events)
        else:
            return None

    def get_event(self, event_id):
        log.trace("Retrieving persistent event for id=%s", event_id)
        event_obj = self.event_store.read(event_id)
        return event_obj

    def find_events(self, event_type=None, origin=None, start_ts=None, end_ts=None, **kwargs):
        log.trace("Retrieving persistent event for event_type=%s, origin=%s, start_ts=%s, end_ts=%s, descending=%s, limit=%s",
                  event_type,origin,start_ts,end_ts,kwargs.get("descending", None),kwargs.get("limit",None))
        events = None

        design_name = "event"
        view_name = None
        start_key = []
        end_key = []
        if origin and event_type:
            view_name = "by_origintype"
            start_key = [origin, event_type]
            end_key = [origin, event_type]
        elif origin:
            view_name = "by_origin"
            start_key = [origin]
            end_key = [origin]
        elif event_type:
            view_name = "by_type"
            start_key = [event_type]
            end_key = [event_type]
        elif start_ts or end_ts:
            view_name = "by_time"
            start_key = []
            end_key = []
        else:
            view_name = "by_time"
            if kwargs.get("limit", 0) < 1:
                kwargs["limit"] = 100
                log.warn("Querying all events, no limit given. Set limit to 100")

        if start_ts:
            start_key.append(start_ts)
        if end_ts:
            end_key.append(end_ts)

        events = self.event_store.find_by_view(design_name, view_name, start_key=start_key, end_key=end_key,
                                               id_only=False, **kwargs)
        events = [(docid, indexkey, doc) for docid, indexkey, value, doc in events]
        return events


class EventGate(EventSubscriber):
    def __init__(self, *args, **kwargs):
        EventSubscriber.__init__(self, *args, callback=self.trigger_cb, **kwargs)

    def trigger_cb(self, event):
        self.stop()
        self.gate.set()

    def await(self, timeout=None):
        self.gate = gevent_event.Event()
        self.start()
        return self.gate.wait(timeout)

    def check_or_await(self):
        pass



def handle_stream_exception(iorigin="stream_exception"):
    """
    decorator for stream exceptions
    """
    def real_decorator(fn):
        @functools.wraps(fn)
        def wrapped(*args, **kwargs):
            try:
                fn(*args, **kwargs)
            except StreamException as e:
                info = "".join(traceback.format_tb(sys.exc_info()[2]))
                pub = EventPublisher(event_type="ExceptionEvent")
                pub.publish_event(origin=iorigin, description="stream exception event", exception_type=str(type(e)), message=info)
        return wrapped
    return real_decorator

