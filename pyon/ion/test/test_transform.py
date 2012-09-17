#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@date Wed Aug  8 14:19:24 EDT 2012
@file pyon/ion/test/test_transform.py
'''

from pyon.util.int_test import IonIntegrationTestCase
from pyon.ion.transforma import TransformBase, TransformDataProcess, StreamPublisher, StreamSubscriber
from interface.objects import StreamRoute
from nose.plugins.attrib import attr
from gevent.event import Event

@attr('INT',group='dm')
class TestTrasforms(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()
        self.queue_cleanup = []
        self.exchange_cleanup = []

    def tearDown(self):
        for queue in self.queue_cleanup:
            xn = self.container.ex_manager.create_xn_queue(queue)
            xn.delete()
        for exchange in self.exchange_cleanup:
            xp = self.container.ex_manager.create_xp(exchange)
            xp.delete()
        
    def test_stats(self):
        self.container.spawn_process('test','pyon.ion.transforma','TransformBase', {}, 'test_transform')
        test_transform = self.container.proc_manager.procs['test_transform']
        test_transform._stats['hits'] = 100

        retval = TransformBase.stats('test_transform')
        self.assertEquals(retval,{'hits':100})


    def test_stream_transforms(self):

        self.verified = Event()
        input_route = StreamRoute('test_exchange','input')
        output_route = StreamRoute('test_exchange','output')
        def verify(m, route, stream_id):
            self.assertEquals(route,output_route)
            self.assertEquals(m,'test')
            self.verified.set()
        
        #                       Create I/O Processes
        #--------------------------------------------------------------------------------

        pub_proc = TransformBase()
        pub_proc.container = self.container
        publisher = StreamPublisher(process=pub_proc, stream_route=input_route)
        

        transform = self.container.spawn_process('transform','pyon.ion.test.test_transform','EmptyDataProcess',{'process':{'queue_name':'transform_input', 'exchange_point':output_route.exchange_point, 'routing_key':output_route.routing_key}}, 'transformpid')
        transform = self.container.proc_manager.procs[transform]

        sub_proc = TransformBase()
        sub_proc.container = self.container
        subscriber = StreamSubscriber(process=sub_proc, exchange_name='subscriber', callback=verify)

        #                       Bind the transports
        #--------------------------------------------------------------------------------

        transform.subscriber.xn.bind(input_route.routing_key, publisher.xp)
        subscriber.xn.bind(output_route.routing_key, transform.publisher.xp)
        subscriber.start()


        publisher.publish('test')

        self.assertTrue(self.verified.wait(4))


        


class EmptyDataProcess(TransformDataProcess):
    def recv_packet(self, msg, stream_route, stream_id):
        self.publisher.publish(msg)
