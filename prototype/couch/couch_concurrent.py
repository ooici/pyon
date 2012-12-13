#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import gevent
import random

from pyon.datastore.datastore import DatastoreManager
from pyon.public import IonObject

import ooi.timer

"""
from prototype.couch.couch_concurrent import runcc
runcc(dict(num_obj=100000, num_read=2000, num_thread=3))
"""

class CouchConcurrencyEval(object):
    def __init__(self):
        from pyon.core.bootstrap import container_instance
        self.container = container_instance
        self.rr = self.container.resource_registry
        self.rr_store = DatastoreManager.get_datastore_instance("resources")
        self.timer = ooi.timer.Timer()

    def prepare_scenario1(self, nums):
        num_objects = nums.get("num_obj", 10000)

        self.res_objs = [IonObject("InstrumentDevice", name="resource_"+str(i)) for i in xrange(num_objects)]
        res = self.rr_store.create_mult(self.res_objs)
        self.res_ids = [res_id for _,res_id,_ in res]

        self.timer.complete_step('create')

        # Make indexes update if any
        self.rr_store.read_doc(self.res_ids[0])
        self.timer.complete_step('prep_done')

    def run_cceval1(self, nums):
        num_read = nums.get("num_read", 2000)

#        for i in xrange(num_read):
#            res_obj = self.rr.read(self.res_ids[0])
#        self.timer.complete_step('read_same_n')

#        for i in xrange(num_read):
#            res_obj = self.rr.read(self.res_ids[0])
#        self.timer.complete_step('read_same_n2')

#        for i in xrange(num_read):
#            res_obj = self.rr.read(self.res_ids[random.randint(0, len(self.res_ids)-1)])
#        self.timer.complete_step('read_rand_n')

#        for i in xrange(num_read):
#            res_obj = self.rr_store.read_doc(self.res_ids[random.randint(0, len(self.res_ids)-1)])
#        self.timer.complete_step('readdoc_rand_n')

        num_thread = nums.get("num_thread", 5)

        def _proc():
            for i in xrange(int(num_read/num_thread)):
                res_obj = self.rr.read(self.res_ids[random.randint(0, len(self.res_ids)-1)])

        gls = [gevent.spawn(_proc) for i in xrange(num_thread)]
        gevent.joinall(gls)

        self.timer.complete_step('read_conc_same_n')

        def _proc():
            rr_store = DatastoreManager.get_datastore_instance("resources")
            for i in xrange(int(num_read/num_thread)):
                res_obj = rr_store.read(self.res_ids[random.randint(0, len(self.res_ids)-1)])

        gls = [gevent.spawn(_proc) for i in xrange(num_thread)]
        gevent.joinall(gls)

        self.timer.complete_step('read_conc2_same_n')




        self.timer.complete_step('end')

    def print_timers(self):
        prior_t = 0
        for l,t in self.timer.times:
            print l, t-prior_t
            prior_t = t


def runcc(nums=None):
    nums = nums if nums is not None else {}
    cce = CouchConcurrencyEval()
    cce.prepare_scenario1(nums)
    cce.run_cceval1(nums)
    cce.print_timers()
