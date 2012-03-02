#!/usr/bin/env python

"""Events and Notification"""

__author__ = 'Dave Foster <dfoster@asascience.com>, Michael Meisinger'
__license__ = 'Apache 2.0'

import time

from pyon.core import bootstrap
from pyon.core.exception import BadRequest
from pyon.datastore.datastore import DataStore
from pyon.net.endpoint import Publisher, Subscriber, PublisherEndpointUnit, SubscriberEndpointUnit, ListeningBaseEndpoint
from pyon.util.log import log

from interface.objects import Event


# @TODO: configurable
EVENTS_XP = "pyon.events"
EVENTS_XP_TYPE = "topic"
def get_events_exchange_point():
    return "%s.%s" % (bootstrap.get_sys_name(), EVENTS_XP)

class EventError(StandardError):
    pass

class EventPublisher(Publisher):

    event_name  = "BASE_EVENT"      # override this in your derived publisher
    msg_type    = "Event"           # same

    def __init__(self, xp=None, event_repo=None, **kwargs):
        """
        Constructs a publisher of events.

        @param  xp          Exchange (AMQP) name, can be none, will use events default.
        @param  event_repo  An optional repository for published events. If None, will not store
                            published events. Use the Container.event_repository for this
                            parameter if you have one.
        """

        # generate a name
        xp = xp or get_events_exchange_point()
        name = (xp, None)

        self.event_repo = event_repo

        Publisher.__init__(self, to_name=name, **kwargs)

    def _topic(self, origin):
        """
        Builds the topic that this event should be published to.
        """
        assert self.event_name and origin
        return "%s.%s" % (str(self.event_name), str(origin))

    def _set_event_msg_fields(self, msg, msgargs):
        """
        Helper method to set fields of an event message instance. Used by create_event.

        @param msg      The Message instance to set fields on.
        @param msgargs  The dict of field -> values to set fields on the msg with.
        @returns        A set of field names in msgargs that were NOT set on the object.
        """
        set_fields = set()

        for k,v in msgargs.items():
            if k in msg.__dict__:
                setattr(msg, k, v)
                set_fields.add(k)

        rem_fields = set(msgargs.iterkeys())
        return rem_fields.difference(set_fields)

    def create_event(self, **kwargs):
        assert self.msg_type
        kwargs = kwargs.copy()
        if 'ts_created' not in kwargs:
            kwargs['ts_created'] = time.time()

        msg = bootstrap.IonObject(self.msg_type)
        rem = self._set_event_msg_fields(msg, kwargs)

        if len(rem):
            raise EventError("create_event: unused kwargs remaining (%s) for event type %s" % (str(rem), self.msg_type))

        return msg

    def publish_event(self, event_msg, origin=None, **kwargs):
        assert origin

        to_name = (self._send_name.exchange, self._topic(origin))
        log.debug("Publishing message to %s", to_name)

        ep = self.publish(event_msg, to_name=to_name)
        ep.close()

        # store published event but only if we specified an event_repo
        if self.event_repo:
            self.event_repo.put_event(event_msg)

    def create_and_publish_event(self, origin=None, **kwargs):
        msg = self.create_event(origin=origin, **kwargs)
        self.publish_event(msg, origin=origin)


class EventSubscriber(Subscriber):
    event_name = None       # either set this in your derived class or use None for everything

    def _topic(self, origin):
        """
        Builds the topic that this event should be published to.
        If either side of the event_id.origin pair are missing, will subscribe to anything.
        """
        event_name  = self._event_name or "*"
        origin      = origin or "#"

        return "%s.%s" % (str(event_name), str(origin))

    def __init__(self, xp_name=None, event_name=None, origin=None, queue_name=None, callback=None, *args, **kwargs):
        """
        Initializer.

        If the queue_name is specified here, the sysname is prefixed automatically to it. This is becuase
        named queues are not namespaces to their exchanges, so two different systems on the same broker
        can cross-pollute messages if a named queue is used.
        """
        self._event_name = event_name or self.event_name

        xp_name = xp_name or get_events_exchange_point()
        binding = self._topic(origin)

        # prefix the queue_name, if specified, with the sysname
        # this is because queue names transcend xp boundaries (see R1 OOIION-477)
        if queue_name is not None:
            if not queue_name.startswith(bootstrap.get_sys_name()):
                queue_name = "%s.%s" % (bootstrap.get_sys_name(), queue_name)
                log.warn("queue_name specified, prepending sys_name to it: %s" % queue_name)

        name = (xp_name, queue_name)

        Subscriber.__init__(self, from_name=name, binding=binding, callback=callback, **kwargs)

#############################################################################
#
# Specific EventPublisher and EventSubscriber pairs
#
#############################################################################

class ResourceLifecycleEventPublisher(EventPublisher):
    """
    Event Notification Publisher for Resource lifecycle events. Used as a concrete derived class, and as a base for
    specializations such as ContainerLifecycleEvents and ProcessLifecycleEvents.

    The "origin" parameter in this class' initializer should be the resource id (UUID).
    """
    msg_type    = "ResourceLifecycleEvent"
    event_name  = "RESOURCE_LIFECYCLE_EVENT"

class ResourceLifecycleEventSubscriber(EventSubscriber):
    event_name  = "RESOURCE_LIFECYCLE_EVENT"

#############################################################################

class ContainerLifecycleEventPublisher(ResourceLifecycleEventPublisher):
    """
    Event Notification Publisher for Container lifecycle events.

    The "origin" parameter in this class' initializer should be the container name.
    """
    event_name  = "CONTAINER_LIFECYCLE_EVENT"

class ContainerLifecycleEventSubscriber(ResourceLifecycleEventSubscriber):
    event_name = "CONTAINER_LIFECYCLE_EVENT"

#############################################################################

class ProcessLifecycleEventPublisher(ResourceLifecycleEventPublisher):
    """
    Event Notification Publisher for Process lifecycle events.

    The "origin" parameter in this class' initializer should be the process' exchange name.
    """
    event_name = "PROCESS_LIFECYCLE_EVENT"

class ProcessLifecycleEventSubscriber(ResourceLifecycleEventSubscriber):
    event_name = "PROCESS_LIFECYCLE_EVENT"

#############################################################################

class InfrastructureEventPublisher(EventPublisher):
    """
    Event Notification Publisher for infrastructure related events. An abstract base class, should be
    inherited and overridden.
    """
    pass

class AppLoaderEventPublisher(InfrastructureEventPublisher):
    """
    Event Notification Publisher for Applications starting and stopping.

    The "origin" parameter in this class' initializer should be the application's name.
    """
    msg_type    = "AppLoaderEvent"
    event_name  = "APP_LOADER_EVENT"

class ContainerStartupEventPublisher(InfrastructureEventPublisher):
    """
    Event Notification Publisher for a Container finishing its running and startup apps.

    The "origin" parameter in this class' initializer should be the application's name.
    """
    msg_type    = "ContainerStartupEvent"
    event_name  = "CONTAINER_STARTUP_EVENT"

class InfrastructureEventSubscriber(EventSubscriber):
    """
    Event Notification Subscriber for infrastructure related events. An abstract base class, should be
    inherited and overridden.
    """
    pass

class AppLoaderEventSubscriber(InfrastructureEventSubscriber):
    """
    Event Notification Subscriber for Applications starting and stopping.

    The "origin" parameter in this class' initializer should be the application's name.
    """
    event_name  = "APP_LOADER_EVENT"

class ContainerStartupEventSubscriber(InfrastructureEventSubscriber):
    """
    Event Notification Subscriber for a Container finishing its running and startup apps.

    The "origin" parameter in this class' initializer should be the application's name.
    """
    event_name  = "CONTAINER_STARTUP_EVENT"

#############################################################################

class TriggerEventPublisher(EventPublisher):
    """
    Base Publisher class for "triggered" Event Notifications.
    """
    msg_type = "TRIGGER_EVENT"

class DatasourceUpdateEventPublisher(TriggerEventPublisher):
    """
    Event Notification Publisher for Datasource updates.

    The "origin" parameter in this class' initializer should be the datasource resource id (UUID).
    """
    event_name = "DATASOURCE_UPDATE_EVENT"

class ScheduleEventPublisher(TriggerEventPublisher):
    """
    Event Notification Publisher for Scheduled events (ie from the Scheduler service).
    """
    event_name  = "SCHEDULE_EVENT"

class TriggerEventSubscriber(EventSubscriber):
    """
    Base Subscriber class for "triggered" Event Notifications.
    """
    pass

class DatasourceUpdateEventSubscriber(TriggerEventSubscriber):
    """
    Event Notification Subscriber for Datasource updates.

    The "origin" parameter in this class' initializer should be the datasource resource id (UUID).
    """
    event_name = "DATASOURCE_UPDATE_EVENT"

class ScheduleEventSubscriber(TriggerEventSubscriber):
    """
    Event Notification Subscriber for Scheduled events (ie from the Scheduler service).
    """
    event_name = "DATASOURCE_UPDATE_EVENT"

#############################################################################

class ResourceModifiedEventPublisher(EventPublisher):
    """
    Base Publisher class for resource modification Event Notifications. This is distinct from resource lifecycle state
    Event Notifications.
    """
    msg_type    = "ResourceModifiedEvent"

class DatasourceUnavailableEventPublisher(ResourceModifiedEventPublisher):
    """
    Event Notification Publisher for the Datasource Unavailable event.
    """
    event_name  = "DATASOURCE_UNAVAILABLE_EVENT"
    msg_type    = "DatasourceUnavailableEvent"

class DatasetSupplementAddedEventPublisher(ResourceModifiedEventPublisher):
    """
    Event Notification Publisher for Dataset Supplement Added.

    The "origin" parameter in this class' initializer should be the dataset resource id (UUID).
    """
    event_name  = "DATASET_SUPPLEMENT_ADDED_EVENT"
    msg_type    = "DatasetSupplementAddedEvent"

class BusinessStateModificationEventPublisher(ResourceModifiedEventPublisher):
    """
    Event Notification Publisher for Dataset Modifications.

    The "origin" parameter in this class' initializer should be the process' exchange name (TODO: correct?)
    """
    event_name  = "BUSINESS_STATE_MODIFICATION_EVENT"

class DatasetChangeEventPublisher(ResourceModifiedEventPublisher):
    """
    Event Notification Publisher for Dataset Change Event - Will Cause AIS to clear the cache for this UUID.

    The "origin" parameter in this class' initializer should be the dataset resource id (UUID).
    """
    event_name  = "DATASET_CHANGE_EVENT"
    msg_type    = "DatasetChangeEvent"

class DatasourceChangeEventPublisher(ResourceModifiedEventPublisher):
    """
    Event Notification Publisher for Datasource Change Event - Will Cause AIS to clear the cache for this UUID.

    The "origin" parameter in this class' initializer should be the datasource resource id (UUID).
    """
    event_name  = "DATASOURCE_CHANGE_EVENT"
    msg_type    = "DatasourceChangeEvent"

class IngestionProcessingEventPublisher(ResourceModifiedEventPublisher):
    """
    Event Notification Publisher for Ingestion Processing Event - Ingestion telling JAW that it is still working,
    and increase its delay.

    The "origin" parameter in this class' initializer should be the dataset resource id (UUID).
    """
    event_name  = "INGESTION_PROCESSING_EVENT"
    msg_type    = "IngestionProcessingEvent"

class ResourceModifiedEventSubscriber(EventSubscriber):
    """
    Base Subscriber class for resource modification Event Notifications. This is distinct from resource lifecycle state
    Event Notifications.
    """
    pass

class DatasourceUnavailableEventSubscriber(ResourceModifiedEventSubscriber):
    """
    Event Notification Subscriber for the Datasource Unavailable event.

    The "origin" parameter in this class' initializer should be the datasource resource id (UUID).
    """
    event_name  = "DATASOURCE_UNAVAILABLE_EVENT"

class DatasetSupplementAddedEventSubscriber(ResourceModifiedEventSubscriber):
    """
    Event Notification Subscriber for Dataset Supplement Added.

    The "origin" parameter in this class' initializer should be the dataset resource id (UUID).
    """
    event_name  = "DATASET_SUPPLEMENT_ADDED_EVENT"

class BusinessStateChangeSubscriber(ResourceModifiedEventSubscriber):
    """
    Event Notification Subscriber for Data Block changes.

    The "origin" parameter in this class' initializer should be the process' exchagne name (TODO: correct?)
    """
    event_name  = "BUSINESS_STATE_MODIFICATION_EVENT"

class DatasetChangeEventSubscriber(ResourceModifiedEventSubscriber):
    """
    Event Notification Subscriber for Dataset Change Event.

    The "origin" parameter in this class' initializer should be the dataset resource id (UUID).
    """
    event_name  = "DATASET_CHANGE_EVENT"

class DatasourceChangeEventSubscriber(ResourceModifiedEventSubscriber):
    """
    Event Notification Subscriber for Datasource Change Event.

    The "origin" parameter in this class' initializer should be the datasource resource id (UUID).
    """
    event_name  = "DATASOURCE_CHANGE_EVENT"

class IngestionProcessingEventSubscriber(ResourceModifiedEventSubscriber):
    """
    Event Notification Subscriber for Ingestion Processing Event - Ingestion telling JAW that it is still working,
    and increase its delay.

    The "origin" parameter in this class' initializer should be the dataset resource id (UUID).
    """
    event_name  = "INGESTION_PROCESSING_EVENT"

class DatasetStreamingEventSubscriber(ResourceModifiedEventSubscriber):
    """
    @TODO: THIS IS IN R1, WILL REVISIT

    Event Notification Subscriber for Dataset Streaming Event - actual mechanism for getting data from DatasetAgent
    to Ingestion.

    NOTE: There is no "Publisher" of this event - as it only comes from DatasetAgent (Java) and does not use the
    standard Message Types for events.  Instead, expect messages of ids 10001, 2001, and 2005.

    The "origin" parameter in this class' initializer should be the dataset resource id (UUID).
    """
    event_id = "DATASET_STREAMING_EVENT"

#############################################################################

class NewSubscriptionEventPublisher(EventPublisher):
    """
    Event Notification Publisher for Subscription Modifications.

    The "origin" parameter in this class' initializer should be the dispatcher resource id (UUID).
    """
    msg_type    = "NewSubscriptionEvent"
    event_name  = "NEW_SUBSCRIPTION_EVENT"

class DelSubscriptionEventPublisher(EventPublisher):
    """
    Event Notification Publisher for Subscription Modifications.

    The "origin" parameter in this class' initializer should be the dispatcher resource id (UUID).
    """
    msg_type    = "DelSubscriptionEvent"
    event_name  = "DEL_SUBSCRIPTION_EVENT"

#############################################################################

# @TODO MOVE THESE TO ION?

class DataEventPublisher(EventPublisher):
    """
    Event Notification Publisher for

    The "origin" parameter in this class' initializer should be
    """
    msg_type    = "DataEvent"
    event_name  = "DATA_EVENT"

class DataBlockEventPublisher(DataEventPublisher):
    """
    Event Notification Publisher for

    The "origin" parameter in this class' initializer should be
    """
    event_name  = "DATABLOCK_EVENT"

class InstrumentSampleDataEventPublisher(DataBlockEventPublisher):
    """
    Event Notification Publisher for

    The "origin" parameter in this class' initializer should be
    """
    msg_type    = "InstrumentSampleDataEvent"

class DataEventSubscriber(EventSubscriber):
    """
    Event Notification Subscriber for Data Block changes.

    The "origin" parameter in this class' initializer should be the process' exchagne name (TODO: correct?)
    """
    event_name  = "DATA_EVENT"

class DataBlockEventSubscriber(DataEventSubscriber):
    """
    Event Notification Subscriber for Data Block changes.

    The "origin" parameter in this class' initializer should be the process' exchagne name (TODO: correct?)
    """
    event_name  = "DATABLOCK_EVENT"

class InstrumentSampleDataEventSubscriber(DataBlockEventSubscriber):
    """
    Event Notification Subscriber for Instrument Data.

    The "origin" parameter in this class' initializer should be the process' exchagne name (TODO: correct?)
    """
    pass

class DatasetIngestionConfigurationEventPublisher(ResourceModifiedEventPublisher):
    """
    Event Notification Subscriber for Dataset Ingestion Configuration change Events

    """
    msg_type = "DatasetIngestionConfigurationEvent"
    event_name  = "DATASET_INGESTION_CONFIGURATION_EVENT"

class DatasetIngestionConfigurationEventSubscriber(ResourceModifiedEventSubscriber):
    """
    Event Notification Subscriber for Dataset Ingestion Configuration change Events

    """
    event_name  = "DATASET_INGESTION_CONFIGURATION_EVENT"



class EventRepository(object):
    """
    Class that uses a data store to provide a persistent repository for ION events.
    """

    def __init__(self, datastore_manager=None):

        # Get an instance of datastore configured as directory.
        # May be persistent or mock, forced clean, with indexes
        datastore_manager = datastore_manager or bootstrap.container_instance.datastore_manager
        self.event_store = datastore_manager.get_datastore("events", DataStore.DS_PROFILE.EVENTS)

    def close(self):
        """
        Pass-through method to close the underlying datastore.
        """
        self.event_store.close()

    def put_event(self, event):
        log.debug("Store event persistently %s" % event)
        if not isinstance(event, Event):
            raise BadRequest("event must be type Event, not %s" % type(event))
        return self.event_store.create(event)

    def get_event(self, event_id):
        log.debug("Retrieving persistent event for id=%s" % event_id)
        event_obj = self.event_store.read(event_id)
        return event_obj

    def find_events(self, event_type=None, origin=None, start_ts=None, end_ts=None, reverse_order=False, max_results=0):
        log.debug("Retrieving persistent event for event_type=%s, origin=%s, start_ts=%s, end_ts=%s, reverse_order=%s, max_results=%s" % (
                event_type,origin,start_ts,end_ts,reverse_order,max_results))
        events = None

        view_name = None
        start_key = []
        end_key = []
        if origin and event_type:
            view_name = "by_origintype"
            start_key=[origin, event_type]
            end_key=[origin, event_type]
        elif origin:
            view_name = "by_origin"
            start_key=[origin]
            end_key=[origin]
        elif event_type:
            view_name = "by_type"
            start_key=[event_type]
            end_key=[event_type]
        elif start_ts or end_ts:
            view_name = "by_time"
            start_key=[]
            end_key=[]
        else:
            raise BadRequest("Cannot query events")

        if start_ts:
            start_key.append(start_ts)
        if end_ts:
            end_key.append(end_ts)

        events = self.event_store.find_by_view("event", view_name, start_key=start_key, end_key=end_key,
                                                descending=reverse_order, limit=max_results, id_only=False)

        #log.info("Events: %s" % events)
        return events
