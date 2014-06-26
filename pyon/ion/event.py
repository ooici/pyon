#!/usr/bin/env python

"""Events framework with publisher, subscriber and repository."""

__author__ = 'Dave Foster <dfoster@asascience.com>, Michael Meisinger'

import functools
import sys
import traceback
from gevent import event as gevent_event

from pyon.core import bootstrap
from pyon.core.exception import BadRequest, IonException, StreamException
from pyon.datastore.datastore import DataStore
from pyon.datastore.datastore_query import QUERY_EXP_KEY, DatastoreQueryBuilder, DQ
from pyon.ion.identifier import create_unique_event_id, create_simple_unique_id
from pyon.net.endpoint import Publisher, Subscriber, BaseEndpoint
from pyon.net.transport import XOTransport, NameTrio
from pyon.util.async import spawn
from pyon.util.containers import get_ion_ts_millis, is_valid_ts
from pyon.util.log import log

from interface.objects import Event


# @TODO: configurable
EVENTS_XP = "ioncore.events"
EVENTS_XP_TYPE = "topic"

#The event will be ignored if older than this time period
VALID_EVENT_TIME_PERIOD = 365 * 24 * 60 * 60 * 1000   # one year

def get_events_exchange_point():
    # match with default output of XOs
    return ".".join([bootstrap.get_sys_name(), 'ion.xs.ioncore.xp', EVENTS_XP])

class EventError(IonException):
    status_code = 500


class EventPublisher(Publisher):

    def __init__(self, event_type=None, xp=None, process=None, **kwargs):
        """
        Constructs a publisher of events for a specific type.

        @param  event_type  The name of the event type object
        @param  xp          Exchange (AMQP) name, can be none, will use events default.
        """

        self.event_type = event_type
        self.process = process

        if bootstrap.container_instance and getattr(bootstrap.container_instance, 'event_repository', None):
            self.event_repo = bootstrap.container_instance.event_repository
        else:
            self.event_repo = None

        # generate an exchange name to publish events to
        container = (hasattr(self, '_process') and hasattr(self._process, 'container') and self._process.container) or BaseEndpoint._get_container_instance()
        if container and container.has_capability(container.CCAP.EXCHANGE_MANAGER):   # might be too early in chain
            xp = xp or container.create_xp(EVENTS_XP)
            to_name = xp
        else:
            xp = xp or get_events_exchange_point()
            to_name = (xp, None)

        Publisher.__init__(self, to_name=to_name, **kwargs)

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
        if not event_object:
            raise BadRequest("Must provide event_object")

        event_object.base_types = event_object._get_extends()

        topic = self._topic(event_object)  # Routing key generated using type_, base_types, origin, origin_type, sub_type
        container = (hasattr(self, '_process') and hasattr(self._process, 'container') and self._process.container) or BaseEndpoint._get_container_instance()
        if container and container.has_capability(container.CCAP.EXCHANGE_MANAGER):
            # make sure we are an xp, if not, upgrade
            if not isinstance(self._send_name, XOTransport):

                default_nt = NameTrio(get_events_exchange_point())
                if isinstance(self._send_name, NameTrio) \
                   and self._send_name.exchange == default_nt.exchange \
                   and self._send_name.queue == default_nt.queue \
                   and self._send_name.binding == default_nt.binding:
                    self._send_name = container.create_xp(EVENTS_XP)
                else:
                    self._send_name = container.create_xp(self._send_name)

            xp = self._send_name
            to_name = xp.create_route(topic)
        else:
            to_name = (self._send_name.exchange, topic)

        current_time = get_ion_ts_millis()

        # Ensure valid created timestamp if supplied
        if event_object.ts_created:

            if not is_valid_ts(event_object.ts_created):
                raise BadRequest("The ts_created value is not a valid timestamp: '%s'" % (event_object.ts_created))

            # Reject events that are older than specified time
            if int(event_object.ts_created) > ( current_time + VALID_EVENT_TIME_PERIOD ):
                raise BadRequest("This ts_created value is too far in the future:'%s'" % (event_object.ts_created))

            # Reject events that are older than specified time
            if int(event_object.ts_created) < (current_time - VALID_EVENT_TIME_PERIOD) :
                raise BadRequest("This ts_created value is too old:'%s'" % (event_object.ts_created))

        else:
            event_object.ts_created = str(current_time)

        # Set the actor id based on
        if not event_object.actor_id:
            event_object.actor_id = self._get_actor_id()

        #Validate this object - ideally the validator should pass on problems, but for now just log
        #any errors and keep going, since seeing invalid situations are better than skipping validation.
        try:
            event_object._validate()
        except Exception, e:
            log.exception(e)


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
        if not event_type:
            raise BadRequest("No event_type provided")

        event_object = bootstrap.IonObject(event_type, origin=origin, **kwargs)
        ret_val = self.publish_event_object(event_object)
        return ret_val

    def _get_actor_id(self):
        """Returns the current ion-actor-id from incoming process headers"""
        actor_id = ""
        try:
            if self.process:
                ctx = self.process.get_context()
                actor_id = ctx.get('ion-actor-id', None) or ""
        except Exception as ex:
            pass

        return actor_id


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

        # establish names for xp, binding/pattern/topic, queue_name
        xp_name = xp_name or EVENTS_XP
        if pattern:
            binding = pattern
        else:
            binding = self._topic(event_type, origin, sub_type, origin_type)

        # create queue_name if none passed in
        if queue_name is None:
            queue_name = create_simple_unique_id()

        # prepend proc name to queue name if we have one
        if hasattr(self, "_process") and self._process:
            queue_name = "%s_%s" % (self._process._proc_name, queue_name)

        # do we have a container/ex_manager?
        container = (hasattr(self, '_process') and hasattr(self._process, 'container') and self._process.container) or BaseEndpoint._get_container_instance()
        if container:
            xp = container.create_xp(xp_name)
            xne = container.create_xn_event(queue_name,
                                            pattern=binding,
                                            xp=xp)

            self._ev_recv_name = xne
            self.binding = None

        else:
            self.binding = binding

            # TODO: Provide a case where we can have multiple bindings (e.g. different event_types)

            # prefix the queue_name, if specified, with the sysname
            queue_name = "%s.%s" % (bootstrap.get_sys_name(), queue_name)

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

        # sets self._ev_recv_name, self.binding
        BaseEventSubscriberMixin.__init__(self, xp_name=xp_name, event_type=event_type, origin=origin,
                                          queue_name=queue_name, sub_type=sub_type, origin_type=origin_type, pattern=pattern)

        log.debug("EventPublisher events pattern %s", self.binding)

        from_name = self._get_from_name()
        binding   = self._get_binding()

        Subscriber.__init__(self, from_name=from_name, binding=binding, callback=callback, **kwargs)

    def _get_from_name(self):
        """
        Returns the from_name that the base Subscriber should listen on.
        This is overridden in the process level.
        """
        return self._ev_recv_name

    def _get_binding(self):
        """
        Returns the binding that the base Subscriber should use.
        This is overridden in the process level.
        """
        return self.binding

    def start(self):
        """
        Pass in a subscriber here, this will make it listen in a background greenlet.
        """
        assert not self._cbthread, "start called twice on EventSubscriber"
        gl = spawn(self.listen)
        gl._glname = "EventSubscriber"
        self._cbthread = gl
        if not self._ready_event.wait(timeout=5):
            log.warning('EventSubscriber start timed out.')
        log.debug("EventSubscriber started. Event pattern=%s", self.binding)
        return gl

    def stop(self):
        self.close()
        self._cbthread.join(timeout=5)
        self._cbthread.kill()
        self._cbthread = None
        log.debug("EventSubscriber stopped. Event pattern=%s", self.binding)

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
        event_id = event.__dict__.pop("_id", None)
        return self.event_store.create(event, event_id)

    def put_events(self, events):
        log.debug("Store %s events persistently", len(events))
        if type(events) is not list:
            raise BadRequest("events must be type list, not %s" % type(events))
        if not all([isinstance(event, Event) for event in events]):
            raise BadRequest("events must all be type Event")

        if events:
            return self.event_store.create_mult(events, allow_ids=True)
        else:
            return None

    def get_event(self, event_id):
        log.trace("Retrieving persistent event for id=%s", event_id)
        event_obj = self.event_store.read(event_id)
        return event_obj

    def find_events(self, event_type=None, origin=None, start_ts=None, end_ts=None, id_only=False, **kwargs):
        log.trace("Retrieving persistent event for event_type=%s, origin=%s, start_ts=%s, end_ts=%s, descending=%s, limit=%s",
                  event_type, origin, start_ts, end_ts, kwargs.get("descending", None), kwargs.get("limit", None))
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
                                               id_only=id_only, **kwargs)
        return events

    def find_events_query(self, query, id_only=False):
        """
        Find events or event ids by using a standard datastore query. This function fills in datastore and
        profile entries, so these can be omitted from the datastore query.
        """
        if not query or not isinstance(query, dict) or not QUERY_EXP_KEY in query:
            raise BadRequest("Illegal events query")
        qargs = query["query_args"]
        qargs["datastore"] = DataStore.DS_EVENTS
        qargs["profile"] = DataStore.DS_PROFILE.EVENTS
        qargs["id_only"] = id_only
        events = self.event_store.find_by_query(query)
        log.debug("find_events_query() found %s events", len(events))
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


class EventQuery(DatastoreQueryBuilder):
    """
    Helper class to build datastore queries for the event repository.
    Based on the DatastoreQueryBuilder
    """
    def __init__(self):
        super(EventQuery, self).__init__(datastore=DataStore.DS_EVENTS, profile=DataStore.DS_PROFILE.EVENTS)

    def filter_type(self, type_expr, cmpop=None):
        return self.txt_cmp(DQ.ATT_TYPE, type_expr, cmpop)

    def filter_origin(self, origin_expr, cmpop=None):
        return self.txt_cmp(DQ.EA_ORIGIN, origin_expr, cmpop)

    def filter_origin_type(self, origin_expr, cmpop=None):
        return self.txt_cmp(DQ.EA_ORIGIN_TYPE, origin_expr, cmpop)

    def filter_sub_type(self, type_expr, cmpop=None):
        return self.txt_cmp(DQ.EA_SUB_TYPE, type_expr, cmpop)

    def filter_ts_created(self, from_expr=None, to_expr=None):
        from_expr = self._make_ion_ts(from_expr)
        to_expr = self._make_ion_ts(to_expr)

        if from_expr and to_expr:
            return self.and_(self.gte(DQ.EA_TS_CREATED, from_expr),
                             self.lte(DQ.EA_TS_CREATED, to_expr))
        elif from_expr:
            return self.gte(DQ.EA_TS_CREATED, from_expr)
        elif to_expr:
            return self.lte(DQ.EA_TS_CREATED, to_expr)
