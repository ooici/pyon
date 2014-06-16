#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'


from pyon.util.pool import IDPool
from pyon.util.unit_test import PyonTestCase
from nose.plugins.attrib import attr

@attr('UNIT')
class PoolTest(PyonTestCase):

    def setUp(self):
        self._idpool = IDPool()

    def test_get_id(self):
        self.assertEquals(self._idpool.get_id(), 1)
        self.assertEquals(self._idpool.get_id(), 2)
        self.assertEquals(self._idpool.get_id(), 3)
        self.assertEquals(self._idpool.get_id(), 4)

        self.assertEquals(self._idpool._ids_in_use, { 1, 2, 3, 4 } )

    def test_release_id(self):
        self._idpool.get_id()
        self._idpool.release_id(1)

        self.assertEquals(self._idpool._ids_in_use, set())
        self.assertEquals(self._idpool._ids_free, { 1 })

    def test_get_and_release_id(self):
        self._idpool.get_id()
        self._idpool.get_id()
        self._idpool.get_id()
        self._idpool.get_id()

        self._idpool.release_id(3)
        self.assertEquals(self._idpool._ids_in_use, { 1, 2, 4 })
        self.assertEquals(self._idpool._ids_free, { 3 } )
        self.assertEquals(self._idpool.get_id(), 3)

        self._idpool.release_id(2)
        self._idpool.release_id(1)

        self.assertIn(self._idpool.get_id(), { 1, 2 })
        self.assertIn(self._idpool.get_id(), { 1, 2 })
        self.assertNotIn(self._idpool.get_id(), { 1, 2 })       # is 5 now

    def test_release_unknown_id(self):
        self.assertEquals(self._idpool._ids_free, set())
        self.assertEquals(self._idpool._ids_in_use, set())

        self._idpool.release_id(1)

        self.assertEquals(self._idpool._ids_free, set())
        self.assertEquals(self._idpool._ids_in_use, set())

        self._idpool.get_id()
        self._idpool.get_id()

        self.assertEquals(self._idpool._ids_free, set())
        self.assertEquals(self._idpool._ids_in_use, { 1, 2 })

        self._idpool.release_id(3)      # still doesn't exist

        self.assertEquals(self._idpool._ids_free, set())
        self.assertEquals(self._idpool._ids_in_use, {1, 2} )

    def test_different_new_id_method(self):
        new_id = lambda x: x + 2

        self._idpool = IDPool(new_id=new_id)

        self.assertEquals(self._idpool.get_id(), 2)
        self.assertEquals(self._idpool.get_id(), 4)
        self.assertEquals(self._idpool.get_id(), 6)

        self._idpool.release_id(4)

        self.assertEquals(self._idpool.get_id(), 4)
        self.assertEquals(self._idpool._last_id, 6)
