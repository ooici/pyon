#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'


from pyon.net.messaging import NodeB, ioloop, make_node, PyonSelectConnection
from pyon.net.channel import BaseChannel, BidirClientChannel, RecvChannel
from pyon.util.unit_test import PyonTestCase
from mock import Mock, sentinel, patch
from nose.plugins.attrib import attr
from pika.connection import Connection
from pyon.core import bootstrap
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.async import spawn
from gevent import event, queue
import time
from pyon.util.containers import DotDict
from pika.exceptions import NoFreeChannels
from interface.services.icontainer_agent import ContainerAgentClient

@attr('UNIT')
class TestNodeB(PyonTestCase):
    def setUp(self):
        self._node = NodeB()

    def test_start_node(self):
        self._node.start_node()
        self.assertEquals(self._node.running, 1)
        self.assertTrue(self._node.ready.is_set())

    def test_on_channel_request_close_not_in_map(self):
        chm = Mock(spec=BaseChannel)

        # not in the pool, don't go to school
        with patch('pyon.net.messaging.log'):
            self.assertRaises(AssertionError, self._node.on_channel_request_close, chm)

    def test_on_channel_request_close_in_map(self):
        chm = Mock(spec=BidirClientChannel)
        chm._queue_auto_delete = False
        ourchid = self._node._pool.get_id()
        chm.get_channel_id.return_value = 5     # amqp's channel number differs from ours

        # setup pool/map
        self._node._bidir_pool[ourchid] = chm
        self._node._pool_map[5]         = ourchid

        # make the call
        self._node.on_channel_request_close(chm)

        # check what happened
        self.assertFalse(chm.close_impl.called)
        self.assertEquals(self._node._pool_map, {})
        self.assertEquals(self._node._pool.get_id(), ourchid)       # should get the same number back from the pool now, ensures we really freed it
        self.assertIn(ourchid, self._node._bidir_pool)
        self.assertEquals(self._node._bidir_pool[ourchid], chm)

    def test_on_channel_request_close_in_map_and_auto_delete_sanity_check(self):
        chm = Mock(spec=BidirClientChannel)
        chm._queue_auto_delete = True
        ourchid = self._node._pool.get_id()
        chm.get_channel_id.return_value = 5     # amqp's channel number differs from ours

        # setup pool/map
        self._node._bidir_pool[ourchid] = chm
        self._node._pool_map[5]         = ourchid

        # make the call
        self._node.on_channel_request_close(chm)

        # retest same things as above because it will be removed from existence in the maps
        self.assertFalse(chm.close_impl.called)
        self.assertEquals(self._node._pool_map, {})

        # the differing items now:
        self.assertNotEquals(self._node._pool.get_id(), ourchid)       # should get a new number back from the pool as we killed the last pooled number
        self.assertNotIn(ourchid, self._node._bidir_pool)

    @patch('pyon.net.messaging.blocking_cb')
    @patch('pyon.net.transport.AsyncResult')
    def test__new_channel(self, armock, bcbmock):
        self._node.client = Mock()
        ch = self._node._new_channel(BaseChannel)

        self.assertIsInstance(ch, BaseChannel)
        self.assertEquals(ch._transport._client, bcbmock())

    @patch('pyon.net.messaging.NodeB._new_channel', return_value=sentinel.new_chan)
    def test_channel_nonpooled(self, ncmock):
        self._node.client = Mock(spec=Connection)

        ch = self._node.channel(BaseChannel)

        ncmock.assert_called_once_with(BaseChannel, transport=None)
        self.assertEquals(ch, sentinel.new_chan)

    def test_channel_pool(self):
        ncm = Mock()
        ncm.return_value = Mock(spec=BidirClientChannel)
        ncm.return_value._queue_auto_delete = False
        ncm.return_value.get_channel_id.return_value = sentinel.chid

        with patch('pyon.net.messaging.NodeB._new_channel', ncm):
            ch = self._node.channel(BidirClientChannel)

            # should expect to see this show up in the node's mappings
            self.assertIn(ch, self._node._bidir_pool.itervalues())
            self.assertIn(sentinel.chid, self._node._pool_map)
            self.assertEquals(len(self._node._pool_map), 1)
            self.assertEquals(len(self._node._pool_map), len(self._node._bidir_pool))

        # let's grab another one to watch our pool grow
        # return value is not a mock factory - it returns the same mock instance as we declared above
        # so redeclare it so they get unique chids
        ncm.return_value = Mock(spec=BidirClientChannel)
        ncm.return_value._queue_auto_delete = False
        ncm.return_value.get_channel_id.return_value = sentinel.chid2

        with patch('pyon.net.messaging.NodeB._new_channel', ncm):
            ch2 = self._node.channel(BidirClientChannel)

        self.assertEquals(ch.get_channel_id(), sentinel.chid)
        self.assertEquals(ch2.get_channel_id(), sentinel.chid2)
        self.assertNotEqual(ch, ch2)
        self.assertIn(ch2, self._node._bidir_pool.itervalues())
        self.assertIn(sentinel.chid2, self._node._pool_map)
        self.assertEquals(len(self._node._pool_map), 2)
        self.assertEquals(len(self._node._pool_map), len(self._node._bidir_pool))

    def test_channel_pool_release(self):
        ncm = Mock()
        ncm.return_value = Mock(spec=BidirClientChannel)
        ncm.return_value._queue_auto_delete = False
        ncm.return_value.get_channel_id.return_value = sentinel.chid

        with patch('pyon.net.messaging.NodeB._new_channel', ncm):
            ch = self._node.channel(BidirClientChannel)

        # return value is not a mock factory - it returns the same mock instance as we declared above
        # so redeclare it so they get unique chids
        ncm.return_value = Mock(spec=BidirClientChannel)
        ncm.return_value._queue_auto_delete = False
        ncm.return_value.get_channel_id.return_value = sentinel.chid2
        with patch('pyon.net.messaging.NodeB._new_channel', ncm):
            ch2 = self._node.channel(BidirClientChannel)

        self.assertEquals(ch.get_channel_id(), sentinel.chid)
        self.assertEquals(ch2.get_channel_id(), sentinel.chid2)

        # return ch to the pool
        with patch('pyon.net.messaging.log'):
            self._node.on_channel_request_close(ch)

        # expect to have bidir pool of two, pool map of 1
        self.assertEquals(len(self._node._bidir_pool), 2)
        self.assertEquals(len(self._node._pool_map), 1)

        # ch2 still active so it should be in the pool map
        self.assertIn(sentinel.chid2, self._node._pool_map)

    @patch('pyon.net.messaging.blocking_cb', return_value=sentinel.amq_chan)
    def test_channel_pool_release_reacquire(self, bcbmock):
        ncm = Mock()
        ncm.return_value = Mock(spec=BidirClientChannel)
        ncm.return_value._queue_auto_delete = False
        ncm.return_value.get_channel_id.return_value = sentinel.chid

        # mock out health check
        cpchmock = Mock(return_value=True)
        self._node._check_pooled_channel_health = cpchmock

        with patch('pyon.net.messaging.NodeB._new_channel', ncm):
            ch = self._node.channel(BidirClientChannel)

        # return value is not a mock factory - it returns the same mock instance as we declared above
        # so redeclare it so they get unique chids
        ncm.return_value = Mock(spec=BidirClientChannel)
        ncm.return_value._queue_auto_delete = False
        ncm.return_value.get_channel_id.return_value = sentinel.chid2
        with patch('pyon.net.messaging.NodeB._new_channel', ncm):
            ch2 = self._node.channel(BidirClientChannel)

        self.assertEquals(ch.get_channel_id(), sentinel.chid)
        self.assertEquals(ch2.get_channel_id(), sentinel.chid2)

        # return ch to the pool
        with patch('pyon.net.messaging.log'):
            self._node.on_channel_request_close(ch)

        # reacquire ch
        call_count = ncm.call_count
        with patch('pyon.net.messaging.NodeB._new_channel', ncm):
            ch3 = self._node.channel(BidirClientChannel)
            # no new calls to the create method have been made
            self.assertEquals(ncm.call_count, call_count)

        # we got the first mocked channel back
        self.assertEquals(ch3.get_channel_id(), sentinel.chid)

    def test_stop_node(self):
        self._node.client = Mock()
        self._node._destroy_pool = Mock()
        self._node.running = True

        self._node.stop_node()

        self._node.client.close.assert_called_once_with()
        self._node._destroy_pool.assert_called_once_with()
        self.assertFalse(self._node.running)

    def test_stop_node_not_running(self):
        self._node.client = Mock()
        self._node._destroy_pool = Mock()
        self._node.running = False

        self._node.stop_node()

        self.assertFalse(self._node.client.close.called)
        self.assertFalse(self._node._destroy_pool.called)
        self.assertFalse(self._node.running)

    def test_destroy_pool(self):
        chmock = Mock(spec=RecvChannel)
        for x in xrange(20):
            self._node._bidir_pool[x] = chmock

        self._node._destroy_pool()

        self.assertEqual(chmock._destroy_queue.call_count, 20)

    @patch('pyon.net.messaging.blocking_cb')
    @patch('pyon.net.transport.AsyncResult')
    def test__new_transport(self, armock, bcbmock):
        self._node.client = Mock()
        transport = self._node._new_transport()

        bcbmock.assert_called_once_with(self._node.client.channel, 'on_open_callback', channel_number=None)

    @patch('pyon.net.messaging.traceback', Mock())
    @patch('pyon.net.messaging.blocking_cb', return_value=None)
    @patch('pyon.container.cc.Container.instance')
    def test__new_transport_fails(self, containermock, bcbmock):
        self._node.client = Mock()
        self.assertRaises(StandardError, self._node._new_transport)
        containermock.fail_fast.assert_called_once_with("AMQCHAN IS NONE, messaging has failed", True)

@attr('UNIT')
class TestMessaging(PyonTestCase):
    def test_ioloop(self):
        cmock = Mock()

        self.called = False
        def keyboard_once():
            if not self.called:
                self.called = True
                raise KeyboardInterrupt()
        cmock.ioloop.start.side_effect = keyboard_once

        ioloop(cmock)

        self.assertEquals(cmock.ioloop.start.call_count, 2)
        cmock.close.assert_called_once_with()

    @patch('pyon.net.messaging.gevent.spawn', return_value=sentinel.ioloop_process)
    def test_make_node(self, gevmock):
        connection_params = { 'username': sentinel.username,
                              'password': sentinel.password,
                              'host': str(sentinel.host),
                              'vhost': sentinel.vhost,
                              'port': 2111 }

        # make a mocked method for PyonSelectConnection to be patched in - we need a way of simulating the on_connection_open callback
        cm = Mock()
        def select_connection(params, cb):
            cb(cm)
            return sentinel.connection

        with patch('pyon.net.messaging.PyonSelectConnection', new=select_connection):
            node, ilp = make_node(connection_params, name=sentinel.name)

        self.assertEquals(ilp, sentinel.ioloop_process)
        gevmock.assert_called_once_with(ioloop, sentinel.connection, name=sentinel.name)

@attr('UNIT')
class TestPyonSelectConnection(PyonTestCase):

    @patch('pyon.net.messaging.SelectConnection')
    def setUp(self, _):
        self.conn = PyonSelectConnection(sentinel.conn_params, sentinel.open_callback, sentinel.reconn_strat)
        self.conn.parameters = DotDict({'channel_max':25})
        self.conn._channels = {}

    def test_mark_bad_channel(self):
        self.assertEquals(len(self.conn._bad_channel_numbers), 0)

        self.conn.mark_bad_channel(15)

        self.assertEquals(len(self.conn._bad_channel_numbers), 1)
        self.assertIn(15, self.conn._bad_channel_numbers)

    def test__next_channel_number_first(self):
        self.assertEquals(self.conn._next_channel_number(), 1)

    def test__next_channel_number_existing_channels(self):
        self.conn._channels[1] = sentinel.chan1
        self.conn._channels[2] = sentinel.chan2
        self.conn._channels[5] = sentinel.chan3

        new_ch_num = self.conn._next_channel_number()
        self.assertEquals(new_ch_num, 3)
        self.conn._channels[new_ch_num] = sentinel.any

        new_ch_num = self.conn._next_channel_number()
        self.assertEquals(new_ch_num, 4)
        self.conn._channels[new_ch_num] = sentinel.any

        new_ch_num = self.conn._next_channel_number()
        self.assertEquals(new_ch_num, 6)
        self.conn._channels[new_ch_num] = sentinel.any

    def test__next_channel_number_existing_channels_and_bad(self):
        self.conn._channels[1] = sentinel.chan1
        self.conn._channels[2] = sentinel.chan2
        self.conn._channels[5] = sentinel.chan3
        self.conn.mark_bad_channel(3)
        self.conn.mark_bad_channel(6)

        new_ch_num = self.conn._next_channel_number()
        self.assertEquals(new_ch_num, 4)
        self.conn._channels[new_ch_num] = sentinel.any

        new_ch_num = self.conn._next_channel_number()
        self.assertEquals(new_ch_num, 7)
        self.conn._channels[new_ch_num] = sentinel.any

    def test__next_channel_number_after_channel_is_freed(self):
        self.conn._channels[1] = sentinel.chan1
        self.conn._channels[2] = sentinel.chan2
        self.conn._channels[5] = sentinel.chan3

        new_ch_num = self.conn._next_channel_number()
        self.assertEquals(new_ch_num, 3)
        self.conn._channels[new_ch_num] = sentinel.any

        # free up a channel
        del self.conn._channels[1]

        # acquire again, should be 1
        new_ch_num = self.conn._next_channel_number()
        self.assertEquals(new_ch_num, 1)
        self.conn._channels[new_ch_num] = sentinel.any

    def test__next_channel_number_all_used_by_channels(self):
        self.conn._channels = {x:sentinel.any for x in xrange(1, 26)}
        self.assertRaises(NoFreeChannels, self.conn._next_channel_number)

    def test__next_channel_number_all_used_either_channels_or_bad(self):
        for x in xrange(1, 26):
            if x % 2:
                self.conn._channels[x] = sentinel.any
            else:
                self.conn.mark_bad_channel(x)

        self.assertRaises(NoFreeChannels, self.conn._next_channel_number)

    def text__next_channel_number_adds_to_pending(self):
        ch = self.conn._next_channel_number()
        self.assertIn(ch, self.conn._pending)

        ch2 = self.conn._next_channel_number()
        self.assertNotEquals(ch, ch2)

@attr('INT')
class TestNodeBInt(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()
        self.ccc = ContainerAgentClient(to_name=self.container.name)
        self.node = self.container.node

        patcher = patch('pyon.net.channel.RecvChannel._queue_auto_delete', False)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_pool_health_check(self):

        # make a request, thus making a bidir item
        self.ccc.status()
        self.assertEquals(1, len(self.node._bidir_pool))
        curpoolchids = [o.get_channel_id() for o in self.node._bidir_pool.itervalues()]

        # fake that this channel has been corrupted in pika
        ch = self.node._bidir_pool.values()[0]
        chnum = ch.get_channel_id()
        del self.node.client.callbacks._callbacks[chnum]['_on_basic_deliver']

        # make another request
        self.ccc.status()

        # should have killed our last channel, gotten a new one
        self.assertEquals(1, len(self.node._bidir_pool))
        self.assertNotEquals(curpoolchids, [o.get_channel_id() for o in self.node._bidir_pool.itervalues()])
        self.assertNotIn(ch, self.node._bidir_pool.itervalues())
        self.assertIn(ch, self.node._dead_pool)

