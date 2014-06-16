#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>, Michael Meisinger'

import datetime
import time
import sys

from mock import Mock, sentinel, patch
from nose.plugins.attrib import attr
from gevent import event, queue
from unittest import SkipTest

from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import IonUnitTestCase

from pyon.core import bootstrap
from pyon.core.bootstrap import IonObject
from pyon.core.exception import BadRequest, FilesystemError, StreamingError, CorruptionError
from pyon.datastore.datastore import DatastoreManager, DataStore
from pyon.ion.event import EventPublisher, EventSubscriber, EventRepository, handle_stream_exception, EventQuery, DQ
from pyon.ion.identifier import create_unique_event_id
from pyon.ion.resource import OT
from pyon.util.containers import get_ion_ts, DotDict

from interface.objects import Event, ResourceLifecycleEvent, ResourceOperatorEvent, ResourceCommandEvent


@attr('UNIT', group='event')
class TestEvents(IonUnitTestCase):
    def test_event_subscriber_auto_delete(self):
        mocknode = Mock()
        ev = EventSubscriber(event_type="ProcessLifecycleEvent", callback=lambda *a,**kw: None, auto_delete=sentinel.auto_delete, node=mocknode)
        self.assertEquals(ev._auto_delete, sentinel.auto_delete)

        # we don't want to have to patch out everything here, so call initialize directly, which calls create_channel for us
        ev._setup_listener = Mock()
        ev.initialize(sentinel.binding)

        self.assertEquals(ev._chan.queue_auto_delete, sentinel.auto_delete)

@attr('INT', group='event')
class TestEventsInt(IonIntegrationTestCase):

    def setUp(self):
        self._listens = []
        self._start_container()

    def tearDown(self):
        for x in self._listens:
            x.stop()

    def _listen(self, sub):
        """
        Pass in a subscriber here, this will make it listen in a background greenlet.
        """
        sub.start()
        self._listens.append(sub)
        sub._ready_event.wait(timeout=5)
        

    def test_pub_and_sub(self):
        ar = event.AsyncResult()
        gq = queue.Queue()
        self.count = 0

        def cb(*args, **kwargs):
            self.count += 1
            gq.put(args[0])
            if self.count == 2:
                ar.set()

        sub = EventSubscriber(event_type="ResourceEvent", callback=cb, origin="specific")
        pub = EventPublisher(event_type="ResourceEvent")

        self._listen(sub)
        pub.publish_event(origin="specific", description="hello")

        event_obj = bootstrap.IonObject('ResourceEvent', origin='specific', description='more testing')
        self.assertEqual(event_obj, pub.publish_event_object(event_obj))

        with self.assertRaises(BadRequest) as cm:
            event_obj = bootstrap.IonObject('ResourceEvent', origin='specific', description='more testing', ts_created='2423')
            pub.publish_event_object(event_obj)
        self.assertIn( 'The ts_created value is not a valid timestamp',cm.exception.message)

        with self.assertRaises(BadRequest) as cm:
            event_obj = bootstrap.IonObject('ResourceEvent', origin='specific', description='more testing', ts_created='1000494978462')
            pub.publish_event_object(event_obj)
        self.assertIn( 'This ts_created value is too old',cm.exception.message)

        with self.assertRaises(BadRequest) as cm:
            event_obj = bootstrap.IonObject('ResourceEvent', origin='specific', description='more testing')
            event_obj._id = '343434'
            pub.publish_event_object(event_obj)
        self.assertIn( 'The event object cannot contain a _id field',cm.exception.message)

        ar.get(timeout=5)

        res = []
        for x in xrange(self.count):
            res.append(gq.get(timeout=5))

        self.assertEquals(len(res), self.count)
        self.assertEquals(res[0].description, "hello")
        self.assertAlmostEquals(int(res[0].ts_created), int(get_ion_ts()), delta=5000)

        self.assertEquals(res[1].description, "more testing")
        self.assertAlmostEquals(int(res[1].ts_created), int(get_ion_ts()), delta=5000)

    def test_pub_on_different_origins(self):
        ar = event.AsyncResult()
        gq = queue.Queue()
        self.count = 0

        def cb(*args, **kwargs):
            self.count += 1
            gq.put(args[0])
            if self.count == 3:
                ar.set()

        sub = EventSubscriber(event_type="ResourceEvent", callback=cb)
        pub = EventPublisher(event_type="ResourceEvent")

        self._listen(sub)

        pub.publish_event(origin="one", description="1")
        pub.publish_event(origin="two", description="2")
        pub.publish_event(origin="three", description="3")

        ar.get(timeout=5)

        res = []
        for x in xrange(self.count):
            res.append(gq.get(timeout=5))

        self.assertEquals(len(res), 3)
        self.assertEquals(res[0].description, "1")
        self.assertEquals(res[1].description, "2")
        self.assertEquals(res[2].description, "3")

    def test_pub_on_different_subtypes(self):
        ar = event.AsyncResult()
        gq = queue.Queue()
        self.count = 0

        def cb(event, *args, **kwargs):
            self.count += 1
            gq.put(event)
            if event.description == "end":
                ar.set()

        sub = EventSubscriber(event_type="ResourceModifiedEvent", sub_type="st1", callback=cb)
        sub.start()

        pub1 = EventPublisher(event_type="ResourceModifiedEvent")
        pub2 = EventPublisher(event_type="ContainerLifecycleEvent")

        pub1.publish_event(origin="two", sub_type="st2", description="2")
        pub2.publish_event(origin="three", sub_type="st1", description="3")
        pub1.publish_event(origin="one", sub_type="st1", description="1")
        pub1.publish_event(origin="four", sub_type="st1", description="end")

        ar.get(timeout=5)
        sub.stop()

        res = []
        for x in xrange(self.count):
            res.append(gq.get(timeout=5))

        self.assertEquals(len(res), 2)
        self.assertEquals(res[0].description, "1")

    def test_pub_on_different_subsubtypes(self):
        res_list = [DotDict(ar=event.AsyncResult(), gq=queue.Queue(), count=0) for i in xrange(4)]

        def cb_gen(num):
            def cb(event, *args, **kwargs):
                res_list[num].count += 1
                res_list[num].gq.put(event)
                if event.description == "end":
                    res_list[num].ar.set()
            return cb

        sub0 = EventSubscriber(event_type="ResourceModifiedEvent", sub_type="st1.*", callback=cb_gen(0))
        sub0.start()

        sub1 = EventSubscriber(event_type="ResourceModifiedEvent", sub_type="st1.a", callback=cb_gen(1))
        sub1.start()

        sub2 = EventSubscriber(event_type="ResourceModifiedEvent", sub_type="*.a", callback=cb_gen(2))
        sub2.start()

        sub3 = EventSubscriber(event_type="ResourceModifiedEvent", sub_type="st1", callback=cb_gen(3))
        sub3.start()

        pub1 = EventPublisher(event_type="ResourceModifiedEvent")

        pub1.publish_event(origin="one", sub_type="st1.a", description="1")
        pub1.publish_event(origin="two", sub_type="st1", description="2")
        pub1.publish_event(origin="three", sub_type="st1.b", description="3")

        pub1.publish_event(origin="four", sub_type="st2.a", description="4")
        pub1.publish_event(origin="five", sub_type="st2", description="5")

        pub1.publish_event(origin="six", sub_type="a", description="6")
        pub1.publish_event(origin="seven", sub_type="", description="7")

        pub1.publish_event(origin="end", sub_type="st1.a", description="end")
        pub1.publish_event(origin="end", sub_type="st1", description="end")

        [res_list[i].ar.get(timeout=5) for i in xrange(3)]

        sub0.stop()
        sub1.stop()
        sub2.stop()
        sub3.stop()

        for i in xrange(4):
            res_list[i].res = []
            for x in xrange(res_list[i].count):
                res_list[i].res.append(res_list[i].gq.get(timeout=5))

        self.assertEquals(len(res_list[0].res), 3)
        self.assertEquals(res_list[0].res[0].description, "1")

        self.assertEquals(len(res_list[1].res), 2)
        self.assertEquals(res_list[1].res[0].description, "1")

        self.assertEquals(len(res_list[2].res), 3)
        self.assertEquals(res_list[2].res[0].description, "1")

        self.assertEquals(len(res_list[3].res), 2)
        self.assertEquals(res_list[3].res[0].description, "2")


    def test_base_subscriber_as_catchall(self):
        ar = event.AsyncResult()
        gq = queue.Queue()
        self.count = 0

        def cb(*args, **kwargs):
            self.count += 1
            gq.put(args[0])
            if self.count == 2:
                ar.set()

        sub = EventSubscriber(callback=cb)
        pub1 = EventPublisher(event_type="ResourceEvent")
        pub2 = EventPublisher(event_type="ContainerLifecycleEvent")

        self._listen(sub)

        pub1.publish_event(origin="some", description="1")
        pub2.publish_event(origin="other", description="2")

        ar.get(timeout=5)

        res = []
        for x in xrange(self.count):
            res.append(gq.get(timeout=5))

        self.assertEquals(len(res), 2)
        self.assertEquals(res[0].description, "1")
        self.assertEquals(res[1].description, "2")

    def test_subscriber_listening_for_specific_origin(self):
        ar = event.AsyncResult()
        self.count = 0
        def cb(*args, **kwargs):
            self.count += 1
            ar.set(args[0])

        sub = EventSubscriber(event_type="ResourceEvent", origin="specific", callback=cb)
        pub = EventPublisher(event_type="ResourceEvent", node=self.container.node)

        self._listen(sub)

        pub.publish_event(origin="notspecific", description="1")
        pub.publish_event(origin="notspecific", description="2")
        pub.publish_event(origin="specific", description="3")
        pub.publish_event(origin="notspecific", description="4")

        evmsg = ar.get(timeout=5)
        self.assertEquals(self.count, 1)
        self.assertEquals(evmsg.description, "3")
    
    
    def test_pub_sub_exception_event(self):
        ar = event.AsyncResult()
        
        gq = queue.Queue()
        self.count = 0

        def cb(*args, **kwargs):
            self.count += 1
            gq.put(args[0])
            if self.count == 3:
                ar.set()

        #test file system error event
        sub = EventSubscriber(event_type="ExceptionEvent", callback=cb, origin="stream_exception")
        self._listen(sub)

        @handle_stream_exception()
        def _raise_filesystem_error():
            raise FilesystemError()
        _raise_filesystem_error()
        
        @handle_stream_exception()
        def _raise_streaming_error():
            raise StreamingError()
        _raise_streaming_error()
        
        @handle_stream_exception()
        def _raise_corruption_error():
            raise CorruptionError()
        _raise_corruption_error()
        

        ar.get(timeout=5)
        res = []
        for i in xrange(self.count):
            exception_event = gq.get(timeout=5) 
            res.append(exception_event)

        self.assertEquals(res[0].exception_type, "<class 'pyon.core.exception.FilesystemError'>")
        self.assertEquals(res[1].exception_type, "<class 'pyon.core.exception.StreamingError'>")
        self.assertEquals(res[2].exception_type, "<class 'pyon.core.exception.CorruptionError'>")
        self.assertEquals(res[2].origin, "stream_exception")
        
    
    def test_pub_sub_exception_event_origin(self):
        #test origin
        ar = event.AsyncResult()
        
        self.count = 0
        def cb(*args, **kwargs):
            self.count = self.count + 1
            ar.set(args[0])

        sub = EventSubscriber(event_type="ExceptionEvent", callback=cb, origin="specific")
        self._listen(sub)

        @handle_stream_exception("specific")
        def _test_origin():
            raise CorruptionError()
        _test_origin()
        
        exception_event = ar.get(timeout=5)
        
        self.assertEquals(self.count, 1)
        self.assertEquals(exception_event.exception_type, "<class 'pyon.core.exception.CorruptionError'>")
        self.assertEquals(exception_event.origin, "specific") 


@attr('UNIT', group='event')
class TestEventRepository(IonUnitTestCase):
    def test_event_repo(self):
        dsm = DatastoreManager()
        ds = dsm.get_datastore("events", "EVENTS")
        ds.delete_datastore()
        ds.create_datastore()

        event_repo = EventRepository(dsm)
        event_repo1 = EventRepository(dsm)

        event1 = Event(origin="resource1")
        event_id, _ = event_repo.put_event(event1)

        event1r = event_repo.get_event(event_id)
        self.assertEquals(event1.origin, event1r.origin)

        ts = 1328680477138
        events2 = []
        for i in xrange(5):
            ev = Event(origin="resource2", ts_created=str(ts + i))
            event_id, _ = event_repo.put_event(ev)
            events2.append((ev,event_id))

        events_r = event_repo.find_events(origin='resource2')
        self.assertEquals(len(events_r), 5)

        events_r = event_repo.find_events(origin='resource2', descending=True)
        self.assertEquals(len(events_r), 5)

        events_r = event_repo.find_events(origin='resource2', limit=3)
        self.assertEquals(len(events_r), 3)

        events_r = event_repo.find_events(origin='resource2', start_ts=str(ts+3))
        self.assertEquals(len(events_r), 2)

        events_r = event_repo.find_events(origin='resource2', end_ts=str(ts+2))
        self.assertEquals(len(events_r), 3)

        events_r = event_repo.find_events(origin='resource2', start_ts=str(ts+3), end_ts=str(ts+4))
        self.assertEquals(len(events_r), 2)

        events_r = event_repo.find_events(start_ts=str(ts+3), end_ts=str(ts+4))
        self.assertEquals(len(events_r), 2)

        event3 = ResourceLifecycleEvent(origin="resource3")
        event_id, _ = event_repo.put_event(event3)

        events_r = event_repo.find_events(event_type="ResourceLifecycleEvent")
        self.assertEquals(len(events_r), 1)


    def test_event_persist(self):
        events = [{'_id': '778dcc0811bd4b518ffd1ef873f3f457',
                   'base_types': ['Event'],
                   'description': 'Event to deliver the status of instrument.',
                   'origin': 'instrument_1',
                   'origin_type': 'PlatformDevice',
                   'status': 1,
                   'sub_type': 'input_voltage',
                   'time_stamps': [2.0, 2.0],
                   'ts_created': '1364121284585',
                   'type_': 'DeviceStatusEvent',
                   'valid_values': [-100, 100],
                   'values': [110.0, 111.0]},
                  {'_id': 'b40731684e41418082e1727f3cf61026',
                   'base_types': ['Event'],
                   'description': 'Event to deliver the status of instrument.',
                   'origin': 'instrument_1',
                   'origin_type': 'PlatformDevice',
                   'status': 1,
                   'sub_type': 'input_voltage',
                   'time_stamps': [2.0, 2.0],
                   'ts_created': '1364121284609',
                   'type_': 'DeviceStatusEvent',
                   'valid_values': [-100, 100],
                   'values': [110.0, 111.0]}]

        dsm = DatastoreManager()
        ds = dsm.get_datastore(DataStore.DS_EVENTS, DataStore.DS_PROFILE.EVENTS)
        ds.delete_datastore()
        ds.create_datastore()

        event_repo = EventRepository(dsm)

        # Store one event without ID
        event1_dict = events[0].copy()
        event1_dict.pop("_id")
        event1_type = event1_dict.pop("type_")
        event1 = IonObject(event1_type, **event1_dict)
        event_repo.put_event(event1)

        events_r = event_repo.find_events(origin=event1_dict["origin"])
        self.assertEquals(len(events_r), 1)
        event1_read = events_r[0][2]
        self.assertEquals(event1_read.time_stamps, event1_dict["time_stamps"])

        # Store one event with ID
        event2_dict = events[1].copy()
        event2_id = event2_dict.pop("_id")
        event2_type = event2_dict.pop("type_")
        event2_obj = IonObject(event2_type, **event2_dict)
        event2_obj._id = event2_id
        event_repo.put_event(event2_obj)

        # Store multiple new events with ID set and unset, non-existing
        event1_dict = events[0].copy()
        event1_id = event1_dict.pop("_id")
        event1_type = event1_dict.pop("type_")
        event1_obj = IonObject(event1_type, **event1_dict)
        event1_obj._id = create_unique_event_id()

        event2_dict = events[1].copy()
        event2_id = event2_dict.pop("_id")
        event2_type = event2_dict.pop("type_")
        event2_obj = IonObject(event2_type, **event2_dict)

        event_repo.put_events([event1_obj, event2_obj])
        events_r = event_repo.find_events(event_type='DeviceStatusEvent')
        self.assertEquals(len(events_r), 4)


@attr('INT', group='event')
class TestEventRepoInt(IonIntegrationTestCase):

    def setUp(self):
        self._start_container()
        self.er = self.container.event_repository

    def test_event_query(self):
        t0 = 136304640000
        events = [
            ("RME1", ResourceCommandEvent(origin="O1", origin_type="OT1", sub_type="ST1", ts_created=str(t0))),
            ("RME2", ResourceCommandEvent(origin="O2", origin_type="OT1", sub_type="ST2", ts_created=str(t0+1))),
            ("RME3", ResourceCommandEvent(origin="O2", origin_type="OT2", sub_type="ST3", ts_created=str(t0+2))),

            ("RLE1", ResourceOperatorEvent(origin="O1", origin_type="OT3", sub_type="ST4", ts_created=str(t0+3))),
            ("RLE2", ResourceOperatorEvent(origin="O3", origin_type="OT3", sub_type="ST5", ts_created=str(t0+4))),
            ("RLE3", ResourceOperatorEvent(origin="O3", origin_type="OT2", sub_type="ST6", ts_created=str(t0+5))),
        ]
        ev_by_alias = {}
        for (alias, event) in events:
            evid, _ = self.container.event_repository.put_event(event)
            ev_by_alias[alias] = evid

        # --- Basic event queries
        eq = EventQuery()
        eq.set_filter(eq.filter_type(OT.ResourceCommandEvent))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 3)

        eq = EventQuery()
        eq.set_filter(eq.filter_type(OT.ResourceCommandEvent))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=True)
        self.assertEquals(len(ev_obj), 3)
        self.assertTrue(all([True for eo in ev_obj if isinstance(eo, basestring)]))

        eq = EventQuery()
        eq.set_filter(eq.filter_sub_type("ST", cmpop=DQ.TXT_CONTAINS))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 6)

        eq = EventQuery()
        eq.set_filter(eq.filter_sub_type("st", cmpop=DQ.TXT_ICONTAINS))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 6)

        eq = EventQuery()
        eq.set_filter(eq.filter_sub_type("^ST(1|2)", cmpop=DQ.TXT_REGEX))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 2)

        eq = EventQuery()
        eq.set_filter(eq.filter_sub_type("^st(1|2)", cmpop=DQ.TXT_IREGEX))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 2)

        eq = EventQuery()
        eq.set_filter(eq.not_(eq.filter_sub_type("^st(1|2)", cmpop=DQ.TXT_IREGEX)))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 4)

        eq = EventQuery()
        eq.set_filter(eq.filter_type([OT.ResourceCommandEvent, OT.ResourceOperatorEvent]))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 6)

        eq = EventQuery()
        eq.set_filter(eq.filter_type([OT.ResourceCommandEvent, OT.ResourceOperatorEvent]),
                      eq.filter_origin_type("OT2"))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 2)

        eq = EventQuery()
        eq.set_filter(eq.filter_type([OT.ResourceCommandEvent, OT.ResourceOperatorEvent]),
                      eq.filter_origin_type(["OT2", "OT1"]))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 4)

        eq = EventQuery()
        eq.set_filter(eq.filter_type([OT.ResourceCommandEvent, OT.ResourceOperatorEvent]),
                      eq.filter_sub_type("ST1"))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 1)

        eq = EventQuery()
        eq.set_filter(eq.filter_type([OT.ResourceCommandEvent, OT.ResourceOperatorEvent]),
                      eq.filter_sub_type(["ST2", "ST3"]))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 2)

        # --- Temporal range queries

        eq = EventQuery()
        eq.set_filter(eq.filter_ts_created(str(t0), str(t0)))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 1)

        eq = EventQuery()
        eq.set_filter(eq.filter_ts_created(str(t0), str(t0+1)))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 2)

        eq = EventQuery()
        eq.set_filter(eq.filter_ts_created(t0, t0+1))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 2)

        eq = EventQuery()
        eq.set_filter(eq.filter_ts_created(datetime.datetime.fromtimestamp(float(t0)/1000),
                                           datetime.datetime.fromtimestamp(float(t0)/1000)))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 1)

        eq = EventQuery()
        eq.set_filter(eq.filter_ts_created(str(t0-10), str(t0-1)))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 0)

        eq = EventQuery()
        eq.set_filter(eq.filter_ts_created(from_expr=str(t0+3)))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 3)

        eq = EventQuery()
        eq.set_filter(eq.filter_ts_created(to_expr=str(t0+2)))
        ev_obj = self.er.find_events_query(query=eq.get_query(), id_only=False)
        self.assertEquals(len(ev_obj), 3)
