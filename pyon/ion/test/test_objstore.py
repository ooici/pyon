#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import uuid

from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound, Inconsistent, BadRequest, Conflict
from pyon.ion.identifier import create_simple_unique_id
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr

from interface.objects import Resource


@attr('INT', group='datastore')
class TestObjectStore(IonIntegrationTestCase):

    def setUp(self):
        self._start_container()
        self.os = self.container.object_store


    def test_objstore_doc(self):
        # Create
        doc1 = dict(a="String", b=123, c=False, d=None, e=1.23,
                    f=["Some", "More"],
                    g=dict(x=[1,2,3], y={}, z="Str"))
        doc2 = dict(a=u"String\u20ac", b=123, c=False, d=None, e=1.23,
                    f=[u"Some\u20ac", "More"],
                    g=dict(x=[1,2,3], y={}, z="Str"))
        doc2[u"h\u20ac"] = u"Other\u20ac"

        doc3 = doc1.copy()

        doc4 = doc1.copy()
        doc5 = doc2.copy()

        did1, dv1 = self.os.create_doc(doc1)
        self.assertTrue(did1)

        did2, dv2 = self.os.create_doc(doc2)
        self.assertTrue(did2)

        did3n = create_simple_unique_id()
        did3, dv3 = self.os.create_doc(doc3, object_id=did3n)
        self.assertEquals(did3, did3n)

        did4n, did5n = create_simple_unique_id(), create_simple_unique_id()
        res = self.os.create_doc_mult([doc4, doc5], object_ids=[did4n, did5n])
        _, did4, dv4 = res[0]
        _, did5, dv5 = res[1]

        # Read
        all_doc_ids = [did1, did2, did3, did4, did5]
        docs = self.os.read_doc_mult(all_doc_ids)
        self.assertEquals(len(docs), len(all_doc_ids))

        doc1r = self.os.read_doc(did1)
        self.assertIsInstance(doc1r, dict)
        self.assertIn("a", doc1r)
        self.assertEquals(doc1r["g"]["x"][1], 2)
        doc2r = self.os.read_doc(did2)
        self.assertIsInstance(doc2r, dict)
        self.assertIn("a", doc2r)
        self.assertEquals(type(doc2r["a"]), str)
        self.assertEquals(doc2r["a"], u"String\u20ac".encode("utf8"))
        self.assertIn(u"h\u20ac".encode("utf8"), doc2r)

        # Update
        doc1r["a"] = "BUZZ"
        doc1rc = doc1r.copy()
        self.os.update_doc(doc1r)
        with self.assertRaises(Conflict):
            doc1rc["a"] = "ZAMM"
            self.os.update_doc(doc1rc)

        doc2r["a"] = u"BUZZ\u20ac"
        doc2r[u"h\u20ac".encode("utf8")] = u"ZAMM\u20ac"

        doc3r = self.os.read_doc(did3)
        doc3r["a"] = u"BUZZ\u20ac"
        self.os.update_doc_mult([doc2r, doc3r])

        # Delete
        self.os.delete_doc(did1)
        self.os.delete_doc(did2)
        self.os.delete_doc(did3)

        self.os.delete_doc_mult([did4, did5] )

        with self.assertRaises(NotFound):
            self.os.read_doc(did1)
        with self.assertRaises(NotFound):
            self.os.read_doc(did2)
        with self.assertRaises(NotFound):
            self.os.read_doc(did3)
        with self.assertRaises(NotFound):
            self.os.read_doc(did4)
        with self.assertRaises(NotFound):
            self.os.read_doc(did5)


    def test_objstore_obj(self):
        # Create
        doc1 = Resource(name="String", alt_ids=["Some", "More"],
                        addl=dict(x=[1,2,3], y={}, z="Str"))
        doc2 = Resource(name=u"String\u20ac", alt_ids=[u"Some\u20ac", "More"],
                        addl=dict(x=[1,2,3], y={}, z="Str"))

        doc3_dict = doc2.__dict__.copy()
        doc3_dict.pop("type_")
        doc3 = Resource(**doc3_dict)

        doc4_dict = doc1.__dict__.copy()
        doc4_dict.pop("type_")
        doc4 = Resource(**doc4_dict)

        doc5_dict = doc2.__dict__.copy()
        doc5_dict.pop("type_")
        doc5 = Resource(**doc5_dict)

        did1, dv1 = self.os.create(doc1)
        self.assertTrue(did1)

        did2, dv2 = self.os.create(doc2)
        self.assertTrue(did2)

        did3n = create_simple_unique_id()
        did3, dv3 = self.os.create(doc3, object_id=did3n)
        self.assertEquals(did3, did3n)

        did4n, did5n = create_simple_unique_id(), create_simple_unique_id()
        res = self.os.create_mult([doc4, doc5], object_ids=[did4n, did5n])
        _, did4, dv4 = res[0]
        _, did5, dv5 = res[1]

        # Read
        all_doc_ids = [did1, did2, did3, did4, did5]
        docs = self.os.read_mult(all_doc_ids)
        self.assertEquals(len(docs), len(all_doc_ids))

        with self.assertRaises(NotFound):
            self.os.read_mult([did1, "NONEXISTING", did2])

        docs1 = self.os.read_mult([did1, "NONEXISTING", did2], strict=False)
        self.assertEquals(len(docs1), 3)
        self.assertEquals(docs1[1], None)

        docs2 = self.os.read_doc_mult([did1, "NONEXISTING", did2], strict=False)
        self.assertEquals(len(docs2), 3)
        self.assertEquals(docs2[1], None)

        doc1r = self.os.read(did1)
        self.assertIsInstance(doc1r, Resource)
        self.assertEquals(doc1r.addl["x"][1], 2)
        doc2r = self.os.read(did2)
        self.assertIsInstance(doc2r, Resource)
        self.assertEquals(type(doc2r.name), str)
        self.assertEquals(doc2r.name, u"String\u20ac".encode("utf8"))

        # Update
        doc1r.name = "BUZZ"

        doc1rc_dict = doc1r.__dict__.copy()
        doc1rc_dict.pop("type_")
        d1rv = doc1rc_dict.pop("_rev")
        d1id = doc1rc_dict.pop("_id")
        doc1rc = Resource(**doc1rc_dict)
        doc1rc["_rev"] = d1rv
        doc1rc["_id"] = d1id

        self.os.update(doc1r)
        with self.assertRaises(Conflict):
            doc1rc.name = "ZAMM"
            self.os.update(doc1rc)

        doc2r.name = u"BUZZ\u20ac"

        doc3r = self.os.read(did3)
        doc3r.name = u"BUZZ\u20ac"
        self.os.update_mult([doc2r, doc3r])

        # Delete
        self.os.delete(did1)
        self.os.delete(did2)
        self.os.delete(did3)

        self.os.delete_mult([did4, did5] )

        with self.assertRaises(NotFound):
            self.os.read(did1)
        with self.assertRaises(NotFound):
            self.os.read(did2)
        with self.assertRaises(NotFound):
            self.os.read(did3)
        with self.assertRaises(NotFound):
            self.os.read(did4)
        with self.assertRaises(NotFound):
            self.os.read(did5)
