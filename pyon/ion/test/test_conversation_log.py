#!/usr/bin/env python
from pyon.datastore.datastore import DatastoreManager

__author__ = 'Prashant Kediyal <pkediyal@ucsd.edu>'


from nose.plugins.attrib import attr
from pyon.ion.conversation_log import  ConvSubscriber, ConvRepository
from pyon.util.int_test import IonIntegrationTestCase
from pyon.util.unit_test import IonUnitTestCase
from gevent import event
from pyon.net.endpoint import Publisher
from interface.objects import ConversationMessage
from pyon.util.containers import get_ion_ts

@attr('INT',group='conversation_log')
class TestConversations(IonIntegrationTestCase):

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

    def test_sub(self):
        ar = event.AsyncResult()
        def cb(*args, **kwargs):
            ar.set(args)

        sub = ConvSubscriber(callback=cb)
        pub = Publisher()
        self._listen(sub)
        pub.publish(to_name='anyone', msg="hello")


        evmsg, evheaders = ar.get(timeout=5)
        self.assertEquals(evmsg, "hello")
        self.assertAlmostEquals(int(evheaders['ts']), int(get_ion_ts()), delta=5000)


@attr('UNIT',group='datastore')
class TestConversationRepository(IonUnitTestCase):
    def test_conv_repo(self):
        dsm = DatastoreManager()
        ds = dsm.get_datastore("conversations")
        ds.delete_datastore()
        ds.create_datastore()

        conv_repo = ConvRepository(dsm)

        conv1 = ConversationMessage(sender='sender', recipient='receiver', conversation_id='1', protocol='rpc', headers={'nofield':'novalue'})
        conv_id, _ = conv_repo.put_conv(conv1)

        conv1r = conv_repo.conv_store.read(conv_id)
        self.assertEquals(conv1.sender, conv1r.sender)

