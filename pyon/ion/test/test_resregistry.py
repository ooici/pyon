#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import uuid
from unittest import SkipTest

from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound, Inconsistent
from pyon.ion.resource import PRED, RT
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr

@attr('INT', group='resource')
class TestResourceRegistry(IonIntegrationTestCase):

    def setUp(self):
        self._start_container()
        self.rr = self.container.resource_registry

    def test_rr_read_assoc(self):
        res_obj1 = IonObject(RT.Org)
        rid1,_ = self.rr.create(res_obj1)

        res_obj2 = IonObject(RT.InstrumentDevice)
        rid2,_ = self.rr.create(res_obj2)

        with self.assertRaises(NotFound) as ex:
            read_obj2 = self.rr.read_object(rid1, PRED.hasResource)

        aid1,_ = self.rr.create_association(rid1, PRED.hasResource, rid2)

        read_obj2 = self.rr.read_object(rid1, PRED.hasResource)
        self.assertEquals(read_obj2._id, rid2)

        read_obj2 = self.rr.read_object(rid1, PRED.hasResource, id_only=True)
        self.assertEquals(read_obj2, rid2)

        read_obj2 = self.rr.read_object(assoc=aid1)
        self.assertEquals(read_obj2._id, rid2)

        read_obj1 = self.rr.read_subject(None, PRED.hasResource, rid2)
        self.assertEquals(read_obj1._id, rid1)

        read_obj1 = self.rr.read_subject(None, PRED.hasResource, rid2, id_only=True)
        self.assertEquals(read_obj1, rid1)

        read_obj1 = self.rr.read_subject(assoc=aid1)
        self.assertEquals(read_obj1._id, rid1)

        res_obj3 = IonObject(RT.InstrumentDevice)
        rid3,_ = self.rr.create(res_obj3)

        res_obj4 = IonObject(RT.Org)
        rid4,_ = self.rr.create(res_obj4)

        aid2,_ = self.rr.create_association(rid1, PRED.hasResource, rid3)

        aid3,_ = self.rr.create_association(rid4, PRED.hasResource, rid3)

        with self.assertRaises(Inconsistent) as ex:
            read_obj2 = self.rr.read_object(rid1, PRED.hasResource)

        with self.assertRaises(Inconsistent) as ex:
            read_obj1 = self.rr.read_subject(None, PRED.hasResource, rid3)

        res_obj5 = IonObject(RT.PlatformDevice)
        rid5,_ = self.rr.create(res_obj5)

        aid4,_ = self.rr.create_association(rid1, PRED.hasResource, rid5)

        read_obj5 = self.rr.read_object(rid1, PRED.hasResource, RT.PlatformDevice)

    def test_rr_create_with_id(self):
        res_obj1 = IonObject(RT.Org)

        newid = uuid.uuid4().hex
        rid1,_ = self.rr.create(res_obj1, object_id=newid)

        self.assertEqual(rid1, newid)

