#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'


from pyon.util.log import log
from pyon.util.context import LocalContextMixin
from pyon.util.int_test import IonIntegrationTestCase
from gevent import spawn, event
from nose.plugins.attrib import attr

@attr('UNIT')
class LocalContextMixinTest(IonIntegrationTestCase):
    """
    Tests LocalContextMixin for thread-level storage
    """

    def setUp(self):
        self.lcm = LocalContextMixin()      # this is not common use but legal

    def test_set_context(self):
        old = self.lcm.set_context('new_context')
        self.assertTrue(old is None)

        self.assertTrue(hasattr(self.lcm._lcm_context, 'ctx'))
        self.assertEquals(self.lcm._lcm_context.ctx, 'new_context')

    def test_get_context(self):
        obj =  {'one':1, 'two':2}

        self.lcm.set_context(obj)

        newobj = self.lcm.get_context()
        self.assertEqual(newobj, obj)
        self.assertEqual(id(newobj), id(obj))

    def test_push_context(self):
        with self.lcm.push_context('thecontext'):
            self.assertEqual(self.lcm._lcm_context.ctx, 'thecontext')

        self.assertTrue(self.lcm._lcm_context.ctx is None)

        with self.lcm.push_context('thecontext2') as f:
            self.assertEqual(f, 'thecontext2')

    def test_separate_greenlets(self):
        ev1 = event.Event()
        ev2 = event.Event()

        def gl_one():
            self.lcm.set_context('from event one')
            ev1.set()

        def gl_two():
            ev1.wait()      # wait for one to do its thing
            curctx = self.lcm.get_context()
            self.assertNotEqual(curctx, 'from event one')
            self.assertTrue(curctx is None)
            ev2.set()

        spawn(gl_one)
        spawn(gl_two)

        ev2.wait(timeout=10)
