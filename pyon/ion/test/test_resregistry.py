#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import uuid

from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound, Inconsistent
from pyon.ion.resource import PRED, RT
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr

from interface.objects import Attachment, AttachmentType


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

    def test_attach(self):
        binary = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x03\x00\x00\x00(-\x0fS\x00\x00\x00\x03sBIT\x08\x08\x08\xdb\xe1O\xe0\x00\x00\x00~PLTEf3\x00\xfc\xf7\xe0\xee\xcc\x00\xd3\xa0\x00\xcc\x99\x00\xec\xcdc\x9fl\x00\xdd\xb2\x00\xff\xff\xff|I\x00\xf9\xdb\x00\xdd\xb5\x19\xd9\xad\x10\xb6\x83\x00\xf8\xd6\x00\xf2\xc5\x00\xd8\xab\x00n;\x00\xff\xcc\x00\xd6\xa4\t\xeb\xb8\x00\x83Q\x00\xadz\x00\xff\xde\x00\xff\xd6\x00\xd6\xa3\x00\xdf\xaf\x00\xde\xad\x10\xbc\x8e\x00\xec\xbe\x00\xec\xd4d\xff\xe3\x00tA\x00\xf6\xc4\x00\xf6\xce\x00\xa5u\x00\xde\xa5\x00\xf7\xbd\x00\xd6\xad\x08\xdd\xaf\x19\x8cR\x00\xea\xb7\x00\xee\xe9\xdf\xc5\x00\x00\x00\tpHYs\x00\x00\n\xf0\x00\x00\n\xf0\x01B\xac4\x98\x00\x00\x00\x1ctEXtSoftware\x00Adobe Fireworks CS4\x06\xb2\xd3\xa0\x00\x00\x00\x15tEXtCreation Time\x0029/4/09Oq\xfdE\x00\x00\x00\xadIDAT\x18\x95M\x8f\x8d\x0e\x820\x0c\x84;ZdC~f\x07\xb2\x11D\x86\x89\xe8\xfb\xbf\xa0+h\xe2\x97\\\xd2^\x93\xb6\x07:1\x9f)q\x9e\xa5\x06\xad\xd5\x13\x8b\xac,\xb3\x02\x9d\x12C\xa1-\xef;M\x08*\x19\xce\x0e?\x1a\xeb4\xcc\xd4\x0c\x831\x87V\xca\xa1\x1a\xd3\x08@\xe4\xbd\xb7\x15P;\xc8\xd4{\x91\xbf\x11\x90\xffg\xdd\x8di\xfa\xb6\x0bs2Z\xff\xe8yg2\xdc\x11T\x96\xc7\x05\xa5\xef\x96+\xa7\xa59E\xae\xe1\x84cm^1\xa6\xb3\xda\x85\xc8\xd8/\x17se\x0eN^'\x8c\xc7\x8e\x88\xa8\xf6p\x8e\xc2;\xc6.\xd0\x11.\x91o\x12\x7f\xcb\xa5\xfe\x00\x89]\x10:\xf5\x00\x0e\xbf\x00\x00\x00\x00IEND\xaeB`\x82"

        # Owner creation tests
        instrument = IonObject("InstrumentDevice", name='instrument')
        iid, _ = self.rr.create(instrument)

        att = Attachment(content=binary, attachment_type=AttachmentType.BLOB)
        aid1 = self.rr.create_attachment(iid, att)

        att1 = self.rr.read_attachment(aid1, include_content=True)
        self.assertEquals(binary, att1.content)

        import base64
        att = Attachment(content=binary, attachment_type=AttachmentType.ASCII)
        aid2 = self.rr.create_attachment(iid, att)

        # test that attachments are without content by default
        att1 = self.rr.read_attachment(aid2)
        self.assertEquals('resource.attachment', att1.content)

        # tests that the attachment content can be read
        att1 = self.rr.read_attachment(aid2, include_content=True)
        self.assertEquals(binary, att1.content)

        att_ids = self.rr.find_attachments(iid, id_only=True)
        self.assertEquals(att_ids, [aid1, aid2])

        att_ids = self.rr.find_attachments(iid, id_only=True, descending=True)
        self.assertEquals(att_ids, [aid2, aid1])

        att_ids = self.rr.find_attachments(iid, id_only=True, descending=True, limit=1)
        self.assertEquals(att_ids, [aid2])

        # test that content can be included
        atts = self.rr.find_attachments(iid, id_only=False, include_content=True, limit=1)
        self.assertEquals(atts[0].content, att1.content)

        # test that content can be excluded and is the default
        atts = self.rr.find_attachments(iid, id_only=False, limit=1)
        self.assertEquals(atts[0].content, 'resource.attachment')

        self.rr.delete_attachment(aid1)

        att_ids = self.rr.find_attachments(iid, id_only=True)
        self.assertEquals(att_ids, [aid2])

        self.rr.delete_attachment(aid2)

        att_ids = self.rr.find_attachments(iid, id_only=True)
        self.assertEquals(att_ids, [])

        att = Attachment(content="SOME TEXT", attachment_type=AttachmentType.ASCII,
                         keywords=['BAR', 'FOO'])
        aid3 = self.rr.create_attachment(iid, att)

        att_ids = self.rr.find_attachments(iid, keyword="NONE", id_only=True)
        self.assertEquals(att_ids, [])

        att_ids = self.rr.find_attachments(iid, keyword="FOO", id_only=True)
        self.assertEquals(att_ids, [aid3])

        att_objs = self.rr.find_attachments(iid, keyword="FOO", id_only=False, include_content=True)
        self.assertEquals(len(att_objs), 1)
        self.assertEquals(att_objs[0].content, "SOME TEXT")

        # tests that attachments can be retrieved without content
        att_objs_without_content = self.rr.find_attachments(iid, keyword="FOO", id_only=False,
                                                            include_content=False)
        self.assertEquals(len(att_objs_without_content), 1)
        self.assertEquals(att_objs_without_content[0].content, "resource.attachment")
