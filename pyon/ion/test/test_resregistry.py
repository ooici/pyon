#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import uuid
from nose.plugins.attrib import attr

from pyon.util.int_test import IonIntegrationTestCase
from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound, Inconsistent, BadRequest
from pyon.ion.resource import PRED, RT, LCS, AS, LCE, lcstate, create_access_args
from pyon.ion.resregistry import ResourceQuery, AssociationQuery

from interface.objects import Attachment, AttachmentType, ResourceVisibilityEnum


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

        # Test create_association_mult
        self.rr.delete_association(aid2)
        self.rr.delete_association(aid3)

        with self.assertRaises(BadRequest) as ex:
            self.rr.create_association_mult([
                (rid1, "Not Possible", rid3),
                (rid4, PRED.hasResource, rid3)
            ])

        with self.assertRaises(NotFound) as ex:
            self.rr.create_association_mult([
                (rid1, PRED.hasResource, "NOT EXISTING"),
                (rid4, PRED.hasResource, rid3)
            ])

        res_assocs = self.rr.create_association_mult([
            (rid1, PRED.hasResource, rid3),
            (rid4, PRED.hasResource, rid3)
        ])
        self.assertEquals(len(res_assocs), 2)
        print res_assocs
        assocs = [a[1] for a in res_assocs]
        for a in assocs:
             self.rr.delete_association(a)


    def test_rr_create_with_id(self):
        res_obj1 = IonObject(RT.ActorIdentity)

        newid = uuid.uuid4().hex
        rid1, _ = self.rr.create(res_obj1, object_id=newid)

        self.assertEqual(rid1, newid)

        res_list = [
            IonObject(RT.InstrumentDevice, name="ID1"),
            IonObject(RT.InstrumentDevice, name="ID2"),
            IonObject(RT.InstrumentDevice, name="ID3"),
        ]

        rid_list = self.rr.create_mult(res_list)
        self.assertEquals(len(rid_list), 3)

        owned_list, _ = self.rr.find_subjects(subject_type=RT.InstrumentDevice, predicate=PRED.hasOwner, object=rid1, id_only=True)
        self.assertEquals(len(owned_list), 0)

        self.rr.rr_store.delete_mult([rid for (rid, rrv) in rid_list])

        rid_list = self.rr.create_mult(res_list, actor_id=rid1)
        self.assertEquals(len(rid_list), 3)

        owned_list, _ = self.rr.find_subjects(subject_type=RT.InstrumentDevice, predicate=PRED.hasOwner, object=rid1, id_only=True)
        self.assertEquals(len(owned_list), 3)

        self.rr.rr_store.delete_mult([rid for (rid, rrv) in rid_list])
        self.rr.delete(rid1)

    def test_attach(self):
        binary = "\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x03\x00\x00\x00(-\x0fS\x00\x00\x00\x03sBIT\x08\x08\x08\xdb\xe1O\xe0\x00\x00\x00~PLTEf3\x00\xfc\xf7\xe0\xee\xcc\x00\xd3\xa0\x00\xcc\x99\x00\xec\xcdc\x9fl\x00\xdd\xb2\x00\xff\xff\xff|I\x00\xf9\xdb\x00\xdd\xb5\x19\xd9\xad\x10\xb6\x83\x00\xf8\xd6\x00\xf2\xc5\x00\xd8\xab\x00n;\x00\xff\xcc\x00\xd6\xa4\t\xeb\xb8\x00\x83Q\x00\xadz\x00\xff\xde\x00\xff\xd6\x00\xd6\xa3\x00\xdf\xaf\x00\xde\xad\x10\xbc\x8e\x00\xec\xbe\x00\xec\xd4d\xff\xe3\x00tA\x00\xf6\xc4\x00\xf6\xce\x00\xa5u\x00\xde\xa5\x00\xf7\xbd\x00\xd6\xad\x08\xdd\xaf\x19\x8cR\x00\xea\xb7\x00\xee\xe9\xdf\xc5\x00\x00\x00\tpHYs\x00\x00\n\xf0\x00\x00\n\xf0\x01B\xac4\x98\x00\x00\x00\x1ctEXtSoftware\x00Adobe Fireworks CS4\x06\xb2\xd3\xa0\x00\x00\x00\x15tEXtCreation Time\x0029/4/09Oq\xfdE\x00\x00\x00\xadIDAT\x18\x95M\x8f\x8d\x0e\x820\x0c\x84;ZdC~f\x07\xb2\x11D\x86\x89\xe8\xfb\xbf\xa0+h\xe2\x97\\\xd2^\x93\xb6\x07:1\x9f)q\x9e\xa5\x06\xad\xd5\x13\x8b\xac,\xb3\x02\x9d\x12C\xa1-\xef;M\x08*\x19\xce\x0e?\x1a\xeb4\xcc\xd4\x0c\x831\x87V\xca\xa1\x1a\xd3\x08@\xe4\xbd\xb7\x15P;\xc8\xd4{\x91\xbf\x11\x90\xffg\xdd\x8di\xfa\xb6\x0bs2Z\xff\xe8yg2\xdc\x11T\x96\xc7\x05\xa5\xef\x96+\xa7\xa59E\xae\xe1\x84cm^1\xa6\xb3\xda\x85\xc8\xd8/\x17se\x0eN^'\x8c\xc7\x8e\x88\xa8\xf6p\x8e\xc2;\xc6.\xd0\x11.\x91o\x12\x7f\xcb\xa5\xfe\x00\x89]\x10:\xf5\x00\x0e\xbf\x00\x00\x00\x00IEND\xaeB`\x82"

        # Owner creation tests
        instrument = IonObject("InstrumentDevice", name='instrument')
        iid, _ = self.rr.create(instrument)

        att = Attachment(content=binary, attachment_type=AttachmentType.BLOB)
        aid1 = self.rr.create_attachment(iid, att)

        att1 = self.rr.read_attachment(aid1, include_content=True)
        self.assertEquals(binary, att1.content)
        self.assertEquals(len(binary), att1.attachment_size)

        import base64
        enc_content = base64.encodestring(binary)
        att = Attachment(content=enc_content, attachment_type=AttachmentType.ASCII)
        aid2 = self.rr.create_attachment(iid, att)

        # test that attachments are without content by default
        att1 = self.rr.read_attachment(aid2)
        self.assertEquals(len(enc_content), att1.attachment_size)
        self.assertEquals(att1.content, '')

        # tests that the attachment content can be read
        att1 = self.rr.read_attachment(aid2, include_content=True)
        self.assertEquals(enc_content, att1.content)

        att_ids = self.rr.find_attachments(iid, id_only=True)
        self.assertEquals(att_ids, [aid1, aid2])

        att_ids = self.rr.find_attachments(iid, id_only=True, descending=True)
        self.assertEquals(att_ids, [aid2, aid1])

        att_ids = self.rr.find_attachments(iid, id_only=True, descending=True, limit=1)
        self.assertEquals(att_ids, [aid2])

        # test that content can be included
        atts = self.rr.find_attachments(iid, id_only=False, include_content=True, limit=1)
        self.assertEquals(atts[0].content, binary)

        # test that content can be excluded and is the default
        atts = self.rr.find_attachments(iid, id_only=False, limit=1)
        self.assertEquals(atts[0].content, '')

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
        self.assertEquals(att_objs_without_content[0].content, '')

    def test_get_resource_extension(self):
        #Testing multiple instrument owners
        subject1 = "/DC=org/DC=cilogon/C=US/O=ProtectNetwork/CN=Roger Unwin A254"

        actor_identity_obj1 = IonObject("ActorIdentity", {"name": subject1})
        user_id1,_ = self.rr.create(actor_identity_obj1)

        user_info_obj1 = IonObject("UserInfo", {"name": "Foo"})
        user_info_id1,_ = self.rr.create(user_info_obj1)
        self.rr.create_association(user_id1, PRED.hasInfo, user_info_id1)

        subject2 = "/DC=org/DC=cilogon/C=US/O=ProtectNetwork/CN=Bob Cumbers A256"

        actor_identity_obj2 = IonObject("ActorIdentity", {"name": subject2})
        user_id2,_ = self.rr.create(actor_identity_obj2)

        user_info_obj2 = IonObject("UserInfo", {"name": "Foo2"})
        user_info_id2,_ = self.rr.create(user_info_obj2)
        self.rr.create_association(user_id2, PRED.hasInfo, user_info_id2)

        test_obj = IonObject('InformationResource',  {"name": "TestResource"})
        test_obj_id,_ = self.rr.create(test_obj)
        self.rr.create_association(test_obj_id, PRED.hasOwner, user_id1)
        self.rr.create_association(test_obj_id, PRED.hasOwner, user_id2)

        extended_resource = self.rr.get_resource_extension(test_obj_id, 'ExtendedInformationResource')

        self.assertEqual(test_obj_id,extended_resource._id)
        self.assertEqual(len(extended_resource.owners),2)

        extended_resource_list = self.rr.get_resource_extension(str([user_info_id1,user_info_id2]), 'ExtendedInformationResource')
        self.assertEqual(len(extended_resource_list), 2)

        prepare_resource = self.rr.prepare_resource_support(resource_type='UserInfo', resource_id=user_info_id2)
        self.assertEqual(prepare_resource._id, user_info_id2)
        self.assertEqual(prepare_resource.resource.name, user_info_obj2.name)

    def test_lifecycle(self):
        svc_obj = IonObject("ServiceDefinition", name='abc')
        sdid, _ = self.rr.create(svc_obj)

        svc_obj1 = self.rr.read(sdid)
        self.assertEquals(svc_obj1.lcstate, LCS.DEPLOYED)
        self.assertEquals(svc_obj1.availability, AS.AVAILABLE)


        inst_obj = IonObject("InstrumentDevice", name='instrument')
        iid, _ = self.rr.create(inst_obj)

        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.DRAFT)
        self.assertEquals(inst_obj1.availability, AS.PRIVATE)

        lcres = self.rr.execute_lifecycle_transition(iid, LCE.PLAN)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.PLANNED)
        self.assertEquals(inst_obj1.availability, AS.PRIVATE)
        self.assertEquals(lcres, lcstate(LCS.PLANNED,AS.PRIVATE))

        self.rr.execute_lifecycle_transition(iid, LCE.DEVELOP)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.DEVELOPED)
        self.assertEquals(inst_obj1.availability, AS.PRIVATE)

        with self.assertRaises(BadRequest):
            self.rr.execute_lifecycle_transition(iid, "!!NONE")
        with self.assertRaises(BadRequest):
            self.rr.execute_lifecycle_transition(iid, LCE.PLAN)
        with self.assertRaises(BadRequest):
            self.rr.execute_lifecycle_transition(iid, LCE.DEVELOP)
        with self.assertRaises(BadRequest):
            self.rr.execute_lifecycle_transition(iid, LCE.UNANNOUNCE)
        with self.assertRaises(BadRequest):
            self.rr.execute_lifecycle_transition(iid, LCE.DISABLE)

        self.rr.execute_lifecycle_transition(iid, LCE.ANNOUNCE)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.DEVELOPED)
        self.assertEquals(inst_obj1.availability, AS.DISCOVERABLE)

        with self.assertRaises(BadRequest):
            self.rr.execute_lifecycle_transition(iid, LCE.ANNOUNCE)

        self.rr.execute_lifecycle_transition(iid, LCE.INTEGRATE)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.INTEGRATED)
        self.assertEquals(inst_obj1.availability, AS.DISCOVERABLE)

        self.rr.execute_lifecycle_transition(iid, LCE.DEPLOY)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.DEPLOYED)
        self.assertEquals(inst_obj1.availability, AS.DISCOVERABLE)

        self.rr.execute_lifecycle_transition(iid, LCE.INTEGRATE)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.INTEGRATED)
        self.assertEquals(inst_obj1.availability, AS.DISCOVERABLE)

        self.rr.execute_lifecycle_transition(iid, LCE.DEVELOP)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.DEVELOPED)
        self.assertEquals(inst_obj1.availability, AS.DISCOVERABLE)

        aids,_ = self.rr.find_objects(iid, PRED.hasModel, RT.InstrumentModel, id_only=True)
        self.assertEquals(len(aids), 0)

        model_obj = IonObject("InstrumentModel", name='model1')
        mid, _ = self.rr.create(model_obj)
        aid1 = self.rr.create_association(iid, PRED.hasModel, mid)

        aids,_ = self.rr.find_objects(iid, PRED.hasModel, RT.InstrumentModel, id_only=True)
        self.assertEquals(len(aids), 1)

        res_objs,_ = self.rr.find_resources("InstrumentDevice")
        self.assertEquals(len(res_objs), 1)
        res_objs,_ = self.rr.find_resources(name="instrument")
        self.assertEquals(len(res_objs), 1)

        massocs = self.rr.find_associations(anyside=mid)
        self.assertEquals(len(massocs), 1)

        self.rr.execute_lifecycle_transition(iid, LCE.RETIRE)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.RETIRED)
        self.assertEquals(inst_obj1.availability, AS.DISCOVERABLE)

        with self.assertRaises(BadRequest):
            self.rr.execute_lifecycle_transition(iid, LCE.RETIRE)
        with self.assertRaises(BadRequest):
            self.rr.execute_lifecycle_transition(iid, LCE.ANNOUNCE)

        self.rr.execute_lifecycle_transition(iid, LCE.DELETE)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.DELETED)
        self.assertEquals(inst_obj1.availability, AS.DISCOVERABLE)

        massocs = self.rr.find_associations(anyside=mid)
        self.assertEquals(len(massocs), 0)

        res_objs,_ = self.rr.find_resources("InstrumentDevice")
        self.assertEquals(len(res_objs), 0)
        res_objs,_ = self.rr.find_resources(name="instrument")
        self.assertEquals(len(res_objs), 0)
        aids,_ = self.rr.find_objects(iid, PRED.hasModel, RT.InstrumentModel, id_only=True)
        self.assertEquals(len(aids), 0)

        inst_obj = IonObject("InstrumentDevice", name='instrument')
        iid, _ = self.rr.create(inst_obj)

        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.DRAFT)
        self.assertEquals(inst_obj1.availability, AS.PRIVATE)

        self.rr.set_lifecycle_state(iid, LCS.PLANNED)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.PLANNED)
        self.assertEquals(inst_obj1.availability, AS.PRIVATE)

        self.rr.set_lifecycle_state(iid, AS.DISCOVERABLE)
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.PLANNED)
        self.assertEquals(inst_obj1.availability, AS.DISCOVERABLE)

        self.rr.set_lifecycle_state(iid, lcstate(LCS.DEPLOYED, AS.DISCOVERABLE))
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.DEPLOYED)
        self.assertEquals(inst_obj1.availability, AS.DISCOVERABLE)

        self.rr.set_lifecycle_state(iid, lcstate(LCS.DEPLOYED, AS.AVAILABLE))
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.DEPLOYED)
        self.assertEquals(inst_obj1.availability, AS.AVAILABLE)

        self.rr.set_lifecycle_state(iid, lcstate(LCS.INTEGRATED, AS.DISCOVERABLE))
        inst_obj1 = self.rr.read(iid)
        self.assertEquals(inst_obj1.lcstate, LCS.INTEGRATED)
        self.assertEquals(inst_obj1.availability, AS.DISCOVERABLE)

    def test_visibility(self):
        res_objs = [
            (IonObject(RT.ActorIdentity, name="system"), ),
            (IonObject(RT.ActorIdentity, name="AI1"), ),
            (IonObject(RT.ActorIdentity, name="AI2"), ),
            (IonObject(RT.ActorIdentity, name="AI3"), ),

            (IonObject(RT.Org, name="Org1"), ),
            (IonObject(RT.Org, name="Org2"), ),

            (IonObject(RT.InstrumentDevice, name="ID1a", visibility=ResourceVisibilityEnum.PUBLIC, availability=AS.AVAILABLE), "AI1"),
            (IonObject(RT.InstrumentDevice, name="ID1b", visibility=ResourceVisibilityEnum.PUBLIC, availability=AS.PRIVATE), "AI1"),
            (IonObject(RT.InstrumentDevice, name="ID1c", visibility=ResourceVisibilityEnum.PUBLIC, availability=AS.AVAILABLE), "AI2"),
            (IonObject(RT.InstrumentDevice, name="ID2a", visibility=ResourceVisibilityEnum.REGISTERED, availability=AS.AVAILABLE), "AI1"),
            (IonObject(RT.InstrumentDevice, name="ID2b", visibility=ResourceVisibilityEnum.REGISTERED, availability=AS.AVAILABLE), "AI2"),
            (IonObject(RT.InstrumentDevice, name="ID2c", visibility=ResourceVisibilityEnum.REGISTERED, availability=AS.AVAILABLE), ),
            (IonObject(RT.InstrumentDevice, name="ID3a", visibility=ResourceVisibilityEnum.FACILITY, availability=AS.AVAILABLE), "AI1"),
            (IonObject(RT.InstrumentDevice, name="ID3b", visibility=ResourceVisibilityEnum.FACILITY, availability=AS.AVAILABLE), "AI2"),
            (IonObject(RT.InstrumentDevice, name="ID3c", visibility=ResourceVisibilityEnum.FACILITY, availability=AS.AVAILABLE), ),
            (IonObject(RT.InstrumentDevice, name="ID4a", visibility=ResourceVisibilityEnum.OWNER, availability=AS.AVAILABLE), "AI1"),
            (IonObject(RT.InstrumentDevice, name="ID4b", visibility=ResourceVisibilityEnum.OWNER, availability=AS.AVAILABLE), "AI2"),
            (IonObject(RT.InstrumentDevice, name="ID4c", visibility=ResourceVisibilityEnum.OWNER, availability=AS.AVAILABLE), ),

            (IonObject(RT.DataProduct, name="DP1a", visibility=ResourceVisibilityEnum.PUBLIC, availability=AS.AVAILABLE), "AI1"),
            (IonObject(RT.DataProduct, name="DP1b", visibility=ResourceVisibilityEnum.PUBLIC, availability=AS.PRIVATE), "AI1"),
            (IonObject(RT.DataProduct, name="DP1c", visibility=ResourceVisibilityEnum.PUBLIC, availability=AS.AVAILABLE), "AI2"),
            (IonObject(RT.DataProduct, name="DP2a", visibility=ResourceVisibilityEnum.REGISTERED, availability=AS.AVAILABLE), "AI1"),
            (IonObject(RT.DataProduct, name="DP2b", visibility=ResourceVisibilityEnum.REGISTERED, availability=AS.AVAILABLE), "AI2"),
            (IonObject(RT.DataProduct, name="DP2c", visibility=ResourceVisibilityEnum.REGISTERED, availability=AS.AVAILABLE), ),
            (IonObject(RT.DataProduct, name="DP3a", visibility=ResourceVisibilityEnum.FACILITY, availability=AS.AVAILABLE), "AI1"),
            (IonObject(RT.DataProduct, name="DP3b", visibility=ResourceVisibilityEnum.FACILITY, availability=AS.AVAILABLE), "AI2"),
            (IonObject(RT.DataProduct, name="DP3c", visibility=ResourceVisibilityEnum.FACILITY, availability=AS.AVAILABLE), ),
            (IonObject(RT.DataProduct, name="DP4a", visibility=ResourceVisibilityEnum.OWNER, availability=AS.AVAILABLE), "AI1"),
            (IonObject(RT.DataProduct, name="DP4b", visibility=ResourceVisibilityEnum.OWNER, availability=AS.AVAILABLE), "AI2"),
            (IonObject(RT.DataProduct, name="DP4c", visibility=ResourceVisibilityEnum.OWNER, availability=AS.AVAILABLE), ),
        ]
        assocs = [
            ("Org1", PRED.hasMembership, "AI2"),
            ("Org1", PRED.hasResource, "ID3a"),
            ("Org1", PRED.hasResource, "ID3b"),
            ("Org1", PRED.hasResource, "ID3c"),

            ("ID1a", PRED.hasOutputProduct, "DP1a"),
            ("ID1b", PRED.hasOutputProduct, "DP1b"),
            ("ID1c", PRED.hasOutputProduct, "DP1c"),
            ("ID2a", PRED.hasOutputProduct, "DP2a"),
            ("ID2b", PRED.hasOutputProduct, "DP2b"),
            ("ID2c", PRED.hasOutputProduct, "DP2c"),
            ("ID3a", PRED.hasOutputProduct, "DP3a"),
            ("ID3b", PRED.hasOutputProduct, "DP3b"),
            ("ID3c", PRED.hasOutputProduct, "DP3c"),
            ("ID4a", PRED.hasOutputProduct, "DP4a"),
            ("ID4b", PRED.hasOutputProduct, "DP4b"),
            ("ID4c", PRED.hasOutputProduct, "DP4c"),

            ("DP1a", PRED.hasSource, "ID1a"),
            ("DP1b", PRED.hasSource, "ID1b"),
            ("DP1c", PRED.hasSource, "ID1c"),
            ("DP2a", PRED.hasSource, "ID2a"),
            ("DP2b", PRED.hasSource, "ID2b"),
            ("DP2c", PRED.hasSource, "ID2c"),
            ("DP3a", PRED.hasSource, "ID3a"),
            ("DP3b", PRED.hasSource, "ID3b"),
            ("DP3c", PRED.hasSource, "ID3c"),
            ("DP4a", PRED.hasSource, "ID4a"),
            ("DP4b", PRED.hasSource, "ID4b"),
            ("DP4c", PRED.hasSource, "ID4c"),
        ]
        res_by_name = {}
        for res_entry in res_objs:
            res_obj = res_entry[0]
            res_name = res_obj.name
            res_obj.alt_ids.append("TEST:%s" % res_name)
            actor_id = res_by_name[res_entry[1]] if len(res_entry) > 1 else None
            rid, _ = self.rr.create(res_obj, actor_id=actor_id)
            res_by_name[res_name] = rid
        for assoc in assocs:
            sname, p, oname = assoc
            s, o = res_by_name[sname], res_by_name[oname]
            self.rr.create_association(s, p, o)

        # Finds with different caller actors
        # - Anonymous call (expects only PUBLIC)
        rids, _ = self.rr.find_resources(restype=RT.InstrumentDevice, id_only=True)
        self.assertEquals(len(rids), 3)
        for rname in ["ID1a", "ID1b", "ID1c"]:
            self.assertIn(res_by_name[rname], rids)

        # - Registered user call (expects to see all REGISTERED and owned resources)
        access_args = create_access_args(current_actor_id=res_by_name["AI1"])
        rids, _ = self.rr.find_resources(restype=RT.InstrumentDevice, id_only=True, access_args=access_args)
        self.assertEquals(len(rids), 8)
        for rname in ["ID1a", "ID1b", "ID1c", "ID2a", "ID2b", "ID2c", "ID3a", "ID4a"]:
            self.assertIn(res_by_name[rname], rids, "Resource %s" % rname)

        # - Facility
        access_args = create_access_args(current_actor_id=res_by_name["AI2"])
        rids, _ = self.rr.find_resources(restype=RT.InstrumentDevice, id_only=True, access_args=access_args)
        #self.assertEquals(len(rids), 9)
        for rname in ["ID1a", "ID1b", "ID1c", "ID2a", "ID2b", "ID2c", "ID3a", "ID3b", "ID4b"]:
            self.assertIn(res_by_name[rname], rids, "Resource %s" % rname)

        # - Superuser call (expects to see all)
        access_args = create_access_args(current_actor_id=res_by_name["AI1"],
                                         superuser_actor_ids=[res_by_name["AI1"]])
        rids, _ = self.rr.find_resources(restype=RT.InstrumentDevice, id_only=True, access_args=access_args)
        self.assertEquals(len(rids), 12)



        # Find by association
        # - Anonymous
        rids, _ = self.rr.find_subjects(subject_type=RT.InstrumentDevice, predicate=PRED.hasOutputProduct,
                                        object=res_by_name["DP1a"], id_only=True)
        self.assertEquals(len(rids), 1)
        self.assertEquals(rids[0], res_by_name["ID1a"])
        rids, _ = self.rr.find_objects(subject=res_by_name["DP1a"], predicate=PRED.hasSource,
                                       object_type=RT.InstrumentDevice, id_only=True)
        self.assertEquals(len(rids), 1)
        self.assertEquals(rids[0], res_by_name["ID1a"])

        # - Owner
        rids, _ = self.rr.find_subjects(subject_type=RT.InstrumentDevice, predicate=PRED.hasOutputProduct,
                                        object=res_by_name["DP4a"], id_only=True)
        self.assertEquals(len(rids), 0)
        access_args = create_access_args(current_actor_id=res_by_name["AI1"])
        rids, _ = self.rr.find_subjects(subject_type=RT.InstrumentDevice, predicate=PRED.hasOutputProduct,
                                        object=res_by_name["DP4a"], id_only=True, access_args=access_args)
        self.assertEquals(len(rids), 1)
        self.assertEquals(rids[0], res_by_name["ID4a"])
        rids, _ = self.rr.find_objects(subject=res_by_name["DP4a"], predicate=PRED.hasSource,
                                       object_type=RT.InstrumentDevice, id_only=True)
        self.assertEquals(len(rids), 0)
        rids, _ = self.rr.find_objects(subject=res_by_name["DP4a"], predicate=PRED.hasSource,
                                       object_type=RT.InstrumentDevice, id_only=True, access_args=access_args)
        self.assertEquals(len(rids), 1)
        self.assertEquals(rids[0], res_by_name["ID4a"])

        # - Superuser
        access_args = create_access_args(current_actor_id=res_by_name["AI3"],
                                         superuser_actor_ids=[res_by_name["AI3"]])
        rids, _ = self.rr.find_objects(subject=res_by_name["DP4a"], predicate=PRED.hasSource,
                                       object_type=RT.InstrumentDevice, id_only=True, access_args=access_args)
        self.assertEquals(len(rids), 1)
        self.assertEquals(rids[0], res_by_name["ID4a"])

        # - Facility
        rids, _ = self.rr.find_subjects(subject_type=RT.InstrumentDevice, predicate=PRED.hasOutputProduct,
                                        object=res_by_name["DP3a"], id_only=True)
        self.assertEquals(len(rids), 0)
        access_args = create_access_args(current_actor_id=res_by_name["AI2"])
        rids, _ = self.rr.find_subjects(subject_type=RT.InstrumentDevice, predicate=PRED.hasOutputProduct,
                                        object=res_by_name["DP3a"], id_only=True, access_args=access_args)
        self.assertEquals(len(rids), 1)
        self.assertEquals(rids[0], res_by_name["ID3a"])

        rids, _ = self.rr.find_objects(subject=res_by_name["DP3a"], predicate=PRED.hasSource,
                                       object_type=RT.InstrumentDevice, id_only=True)
        self.assertEquals(len(rids), 0)
        rids, _ = self.rr.find_objects(subject=res_by_name["DP3a"], predicate=PRED.hasSource,
                                       object_type=RT.InstrumentDevice, id_only=True, access_args=access_args)
        self.assertEquals(len(rids), 1)
        self.assertEquals(rids[0], res_by_name["ID3a"])

        #from pyon.util.breakpoint import breakpoint
        #breakpoint()

        self.rr.rr_store.delete_mult(res_by_name.values())

    def test_resource_query(self):
        res_objs = [
            (IonObject(RT.InstrumentDevice, name="ID1", lcstate=LCS.DEPLOYED), ),
            (IonObject(RT.InstrumentDevice, name="ID2", lcstate=LCS.INTEGRATED), ),

            (IonObject(RT.InstrumentSite, name="IS1", lcstate=LCS.INTEGRATED), ),

            (IonObject(RT.PlatformDevice, name="PD1"), ),

            (IonObject(RT.PlatformSite, name="PS1"), ),

            (IonObject(RT.PlatformSite, name="PS0"), ),

            (IonObject(RT.Observatory, name="OS1"), ),

            (IonObject(RT.DataProduct, name="DP1"), ),
            (IonObject(RT.DataProduct, name="DP2"), ),
        ]
        assocs = [
            ("ID1", PRED.hasOutputProduct, "DP1"),
            ("ID1", PRED.hasOutputProduct, "DP2"),

            ("PD1", PRED.hasDevice, "ID1"),

            ("OS1", PRED.hasSite, "PS0"),
            ("PS0", PRED.hasSite, "PS1"),
            ("PS1", PRED.hasSite, "IS1"),

            ("PS1", PRED.hasDevice, "PD1"),
            ("IS1", PRED.hasDevice, "ID1"),
        ]
        res_by_name = {}
        for res_entry in res_objs:
            res_obj = res_entry[0]
            res_name = res_obj.name
            res_obj.alt_ids.append("TEST:%s" % res_name)
            actor_id = res_by_name[res_entry[1]] if len(res_entry) > 1 else None
            rid, _ = self.rr.create(res_obj, actor_id=actor_id)
            res_by_name[res_name] = rid
        for assoc in assocs:
            sname, p, oname = assoc
            s, o = res_by_name[sname], res_by_name[oname]
            self.rr.create_association(s, p, o)

        # --- Simple resource filters

        rq = ResourceQuery()
        rq.set_filter(rq.filter_type(RT.InstrumentDevice))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 2)

        rq = ResourceQuery()
        rq.set_filter(rq.filter_type([RT.InstrumentDevice, RT.PlatformDevice]))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 3)

        rq = ResourceQuery()
        rq.set_filter(rq.filter_type([RT.InstrumentDevice, RT.PlatformDevice]),
                      rq.filter_name("ID1"))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 1)

        rq = ResourceQuery()
        rq.set_filter(rq.filter_type([RT.InstrumentDevice, RT.PlatformDevice]),
                      rq.filter_name(["ID1", "PD1"]))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 2)

        rq = ResourceQuery()
        rq.set_filter(rq.filter_type([RT.InstrumentDevice, RT.PlatformDevice]),
                      rq.filter_name("ID", cmpop=ResourceQuery.TXT_CONTAINS))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 2)

        # --- Association query

        rq = ResourceQuery()
        rq.set_filter(rq.filter_associated_with_object(res_by_name["ID1"]))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 2)

        # --- Association queries with a target filter

        rq = ResourceQuery()
        target_filter = rq.eq(rq.RA_NAME, "DP1")
        rq.set_filter(rq.filter_type([RT.InstrumentDevice, RT.PlatformDevice]),
                      rq.filter_associated_with_subject(predicate=PRED.hasOutputProduct,
                                                        target_filter=target_filter))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 1)
        self.assertEquals(res_obj[0].name, "ID1")

        rq = ResourceQuery()
        target_filter = rq.eq(rq.RA_NAME, "DP1")
        rq.set_filter(rq.filter_type(RT.InstrumentDevice),
                      rq.filter_associated_with_subject(predicate=[PRED.hasOutputProduct, PRED.hasSource],
                                                        target_filter=target_filter))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 1)
        self.assertEquals(res_obj[0].name, "ID1")

        rq = ResourceQuery()
        target_filter = rq.eq(rq.RA_NAME, "DP1")
        rq.set_filter(rq.filter_type(RT.InstrumentDevice),
                      rq.filter_associated_with_subject(predicate=PRED.hasOutputProduct,
                                                        object_type=RT.DataProduct,
                                                        target_filter=target_filter))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 1)
        self.assertEquals(res_obj[0].name, "ID1")

        rq = ResourceQuery()
        target_filter = rq.and_(rq.eq(rq.RA_NAME, "DP1"),
                                rq.eq(rq.ATT_TYPE, RT.DataProduct))
        rq.set_filter(rq.filter_type(RT.InstrumentDevice),
                      rq.filter_associated_with_subject(predicate=PRED.hasOutputProduct,
                                                        target_filter=target_filter))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 1)
        self.assertEquals(res_obj[0].name, "ID1")

        #rq = ResourceQuery()
        #rq.set_filter(rq.filter_by_association(res_by_name["ID1"], direction="SO"))
        #res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)

        # --- Multi-hop associations

        rq = ResourceQuery()
        # This will find InstrumentDevice child of PlatformDevice
        rq.set_filter(rq.filter_by_association(res_by_name["PS1"], predicate=[PRED.hasDevice, PRED.hasDevice], direction="OO"))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        #print "\n".join("%s %s %s" % (ro._id, ro.type_, ro.name) for ro in res_obj)
        self.assertEquals(len(res_obj), 1)
        self.assertEquals(res_obj[0].name, "ID1")

        rq = ResourceQuery()
        # This will find PlatformDevice for site PLUS InstrumentDevice child of PlatformDevice
        rq.set_filter(rq.filter_by_association(res_by_name["PS1"], predicate=[PRED.hasDevice, PRED.hasDevice], direction="OO"),
                      rq.filter_by_association(res_by_name["PS1"], predicate=[PRED.hasDevice], direction="O"),
                      or_filters=True)
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 2)
        self.assertIn(res_obj[0].name, {"ID1", "PD1"})
        self.assertIn(res_obj[1].name, {"ID1", "PD1"})

        rq = ResourceQuery()
        rq.set_filter(rq.filter_by_association(res_by_name["OS1"], predicate=[PRED.hasSite], direction="O"),
                      rq.filter_by_association(res_by_name["OS1"], predicate=[PRED.hasSite,PRED.hasSite], direction="OO"),
                      rq.filter_by_association(res_by_name["OS1"], predicate=[PRED.hasSite,PRED.hasSite,PRED.hasSite], direction="OOO"),
                      or_filters=True)
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 3)
        self.assertIn(res_obj[0].name, {"PS0", "PS1", "IS1"})
        self.assertIn(res_obj[1].name, {"PS0", "PS1", "IS1"})
        self.assertIn(res_obj[2].name, {"PS0", "PS1", "IS1"})

        # --- Association descendants (recursively)

        rq = ResourceQuery()
        rq.set_filter(rq.filter_object_descendants(res_by_name["OS1"], predicate=[PRED.hasSite]))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 3)

        rq = ResourceQuery()
        rq.set_filter(rq.filter_object_descendants(res_by_name["OS1"], predicate=[PRED.hasSite], max_depth=2))
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 2)

        rq = ResourceQuery()
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertGreaterEqual(len(res_obj), 9)

        # --- Parameterized queries

        query_params = dict(restype=RT.InstrumentDevice)
        rq = ResourceQuery()
        rq.set_filter(rq.filter_type("$(restype)"))
        rq.set_query_parameters(query_params)
        res_obj = self.rr.find_resources_ext(query=rq.get_query(), id_only=False)
        self.assertEquals(len(res_obj), 2)

        # --- Association query

        aq = AssociationQuery()
        aq.set_filter(aq.filter_subject(res_by_name["ID1"]))
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 2)

        aq = AssociationQuery()
        aq.set_filter(aq.filter_subject([res_by_name["ID1"], res_by_name["PS1"]]))
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 4)

        aq = AssociationQuery()
        aq.set_filter(aq.filter_object([res_by_name["DP1"], res_by_name["DP2"]]))
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 2)

        aq = AssociationQuery()
        aq.set_filter(aq.filter_subject([res_by_name["ID1"], res_by_name["PS1"]]),
                      aq.filter_predicate(PRED.hasOutputProduct))
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 2)

        aq = AssociationQuery()
        aq.set_filter(aq.filter_subject(res_by_name["ID1"]),
                      aq.filter_predicate(PRED.hasOutputProduct),
                      aq.filter_object(res_by_name["DP1"]))
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 1)

        aq = AssociationQuery()
        aq.set_filter(aq.filter_subject_type(RT.InstrumentDevice))
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 2)

        aq = AssociationQuery()
        aq.set_filter(aq.filter_subject_type([RT.Observatory, RT.PlatformSite]))
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 4)

        aq = AssociationQuery()
        aq.set_filter(aq.filter_object_type(RT.DataProduct))
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 2)

        aq = AssociationQuery()
        aq.set_filter(aq.filter_object_type([RT.PlatformSite, RT.InstrumentSite]))
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 3)

        aq = AssociationQuery()
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 8)

        # --- Association descendants (recursively)

        aq = AssociationQuery()
        aq.set_filter(aq.filter_object_descendants(res_by_name["OS1"], predicate=[PRED.hasSite]))
        assoc_objs = self.rr.find_associations(query=aq.get_query(), id_only=False)
        self.assertEquals(len(assoc_objs), 3)

        #print assoc_objs

        #from pyon.util.breakpoint import breakpoint
        #breakpoint()

        # --- Clean up

        self.rr.rr_store.delete_mult(res_by_name.values())
