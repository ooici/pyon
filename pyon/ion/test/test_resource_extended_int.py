#!/usr/bin/env python

__author__ = 'Michael Meisinger'

import pprint
from nose.plugins.attrib import attr

from pyon.ion.resource import ExtendedResourceContainer
from pyon.public import RT, PRED, OT, log, LCE, IonObject
from pyon.util.containers import DotDict, get_ion_ts
from pyon.util.int_test import IonIntegrationTestCase


@attr('INT', group='resources')
class TestExtendedResourceIntegration(IonIntegrationTestCase):

    def setUp(self):
        self._start_container()
        self.RR = self.container.resource_registry

    def test_extended_resource(self):
        dev_obj = IonObject(RT.InstrumentDevice, name="InstrumentDevice 1")
        dev_id, _ = self.RR.create(dev_obj)

        dev2_obj = IonObject(RT.InstrumentDevice, name="InstrumentDevice 2")
        dev2_id, _ = self.RR.create(dev2_obj)

        dev3_obj = IonObject(RT.PlatformDevice, name="PlatformDevice 3")
        dev3_id, _ = self.RR.create(dev3_obj)

        site_obj = IonObject(RT.InstrumentSite, name="InstrumentSite 1")
        site_id, _ = self.RR.create(site_obj)

        dep_obj = IonObject(RT.Deployment, name="Deployment 1")
        dep_id, _ = self.RR.create(dep_obj)

        self.RR.create_association(dev_id, PRED.hasDeployment, dep_id)

        res_objs, _ = self.RR.find_subjects(predicate=PRED.hasDeployment, object=dep_id, id_only=True)
        self.assertEquals(len(res_objs), 1)

        extended_resource_handler = ExtendedResourceContainer(self)
        ext_deployment = extended_resource_handler.create_extended_resource_container(
            extended_resource_type=OT.TestExtendedResourceDeploy,
            resource_id=dep_id,
            computed_resource_type=OT.BaseComputedAttributes)

        #pprint.pprint(ext_deployment.__dict__)

        self.assertEquals(ext_deployment.device_11._id, dev_id)
        self.assertEquals(len(ext_deployment.device_12), 1)
        self.assertEquals(ext_deployment.device_12[0]._id, dev_id)
        self.assertEquals(ext_deployment.device_13, 1)
        self.assertEquals(ext_deployment.device_14._id, dev_id)

        self.assertEquals(ext_deployment.device_21._id, dev_id)
        self.assertEquals(len(ext_deployment.device_12), 1)
        self.assertEquals(ext_deployment.device_22[0]._id, dev_id)
        self.assertEquals(ext_deployment.device_23, 1)
        self.assertEquals(ext_deployment.device_24._id, dev_id)

        self.assertEquals(ext_deployment.device_31._id, dev_id)

        self.assertEquals(ext_deployment.site_11, None)
        self.assertEquals(ext_deployment.site_12, [])
        self.assertEquals(ext_deployment.site_13, 0)
        self.assertEquals(ext_deployment.site_14, None)
        self.assertEquals(ext_deployment.site_21, None)
        self.assertEquals(ext_deployment.site_22, [])
        self.assertEquals(ext_deployment.site_23, 0)
        self.assertEquals(ext_deployment.site_24, None)
        self.assertEquals(ext_deployment.site_31, None)

        self.RR.create_association(site_id, PRED.hasDeployment, dep_id)

        self.RR.create_association(dev2_id, PRED.hasDeployment, dep_id)

        self.RR.create_association(dev3_id, PRED.hasDeployment, dep_id)

        res_objs, _ = self.RR.find_subjects(predicate=PRED.hasDeployment, object=dep_id, id_only=True)
        self.assertEquals(len(res_objs), 4)

        extended_resource_handler = ExtendedResourceContainer(self)
        ext_deployment = extended_resource_handler.create_extended_resource_container(
            extended_resource_type=OT.TestExtendedResourceDeploy,
            resource_id=dep_id,
            computed_resource_type=OT.BaseComputedAttributes)

        #pprint.pprint(ext_deployment.__dict__)

        all_devices = [dev_id, dev2_id, dev3_id]
        all_instdevs = [dev_id, dev2_id]

        self.assertIn(ext_deployment.device_11._id, all_instdevs)
        self.assertEquals(len(ext_deployment.device_12), 2)
        self.assertEquals(set([r._id for r in ext_deployment.device_12]), set(all_instdevs))
        self.assertEquals(ext_deployment.device_13, 2)
        self.assertIn(ext_deployment.device_14._id, all_instdevs)

        self.assertIn(ext_deployment.device_21._id, all_devices)
        self.assertEquals(len(ext_deployment.device_22), 3)
        self.assertEquals(set([r._id for r in ext_deployment.device_22]), set(all_devices))
        self.assertEquals(ext_deployment.device_23, 3)
        self.assertIn(ext_deployment.device_24._id, all_devices)

        self.assertIn(ext_deployment.device_31._id, all_devices)

        self.assertEquals(ext_deployment.site_11._id, site_id)
        self.assertEquals(len(ext_deployment.site_12), 1)
        self.assertEquals(ext_deployment.site_12[0]._id, site_id)
        self.assertEquals(ext_deployment.site_13, 1)
        self.assertEquals(ext_deployment.site_14._id, site_id)
        self.assertEquals(ext_deployment.site_21._id, site_id)
        self.assertEquals(len(ext_deployment.site_22), 1)
        self.assertEquals(ext_deployment.site_22[0]._id, site_id)
        self.assertEquals(ext_deployment.site_23, 1)
        self.assertEquals(ext_deployment.site_24._id, site_id)
        self.assertEquals(ext_deployment.site_31._id, site_id)

    def test_extended_resource_directed(self):
        obs1_obj = IonObject(RT.Observatory, name="Observatory 1")
        obs1_id, _ = self.RR.create(obs1_obj)

        ps1_obj = IonObject(RT.PlatformSite, name="PlatformSite 1")
        ps1_id, _ = self.RR.create(ps1_obj)

        ps2_obj = IonObject(RT.PlatformSite, name="PlatformSite 2")
        ps2_id, _ = self.RR.create(ps2_obj)

        is1_obj = IonObject(RT.InstrumentSite, name="InstrumentSite 1")
        is1_id, _ = self.RR.create(is1_obj)

        extended_resource_handler = ExtendedResourceContainer(self)
        ext_site = extended_resource_handler.create_extended_resource_container(
            extended_resource_type=OT.TestExtendedResourceSite,
            resource_id=ps1_id,
            computed_resource_type=OT.BaseComputedAttributes)

        #pprint.pprint(ext_site.__dict__)

        self.assertEquals(ext_site.parent_site, None)
        self.assertEquals(ext_site.child_sites, [])
        self.assertEquals(ext_site.child_sites1, [])
        self.assertEquals(ext_site.child_instrument_sites, [])

        aid1, _ = self.RR.create_association(obs1_id, PRED.hasSite, ps1_id)

        extended_resource_handler = ExtendedResourceContainer(self)
        ext_site = extended_resource_handler.create_extended_resource_container(
            extended_resource_type=OT.TestExtendedResourceSite,
            resource_id=ps1_id,
            computed_resource_type=OT.BaseComputedAttributes)

        #pprint.pprint(ext_site.__dict__)

        self.assertEquals(ext_site.parent_site._id, obs1_id)
        self.assertEquals(ext_site.child_sites, [])
        self.assertEquals(ext_site.child_sites1, [])
        self.assertEquals(ext_site.child_instrument_sites, [])

        self.RR.create_association(ps1_id, PRED.hasSite, is1_id)

        extended_resource_handler = ExtendedResourceContainer(self)
        ext_site = extended_resource_handler.create_extended_resource_container(
            extended_resource_type=OT.TestExtendedResourceSite,
            resource_id=ps1_id,
            computed_resource_type=OT.BaseComputedAttributes)

        #pprint.pprint(ext_site.__dict__)

        self.assertEquals(ext_site.parent_site._id, obs1_id)
        self.assertEquals(len(ext_site.child_sites), 1)
        self.assertEquals(ext_site.child_sites[0]._id, is1_id)
        self.assertEquals(len(ext_site.child_sites1), 1)
        self.assertEquals(ext_site.child_sites1[0]._id, is1_id)
        self.assertEquals(len(ext_site.child_instrument_sites), 1)
        self.assertEquals(ext_site.child_instrument_sites[0]._id, is1_id)

        self.RR.create_association(ps1_id, PRED.hasSite, ps2_id)

        extended_resource_handler = ExtendedResourceContainer(self)
        ext_site = extended_resource_handler.create_extended_resource_container(
            extended_resource_type=OT.TestExtendedResourceSite,
            resource_id=ps1_id,
            computed_resource_type=OT.BaseComputedAttributes)

        #pprint.pprint(ext_site.__dict__)

        self.assertEquals(ext_site.parent_site._id, obs1_id)
        self.assertEquals(len(ext_site.child_sites), 2)
        self.assertEquals(set(r._id for r in ext_site.child_sites), set([is1_id, ps2_id]))
        self.assertEquals(len(ext_site.child_sites1), 2)
        self.assertEquals(set(r._id for r in ext_site.child_sites1), set([is1_id, ps2_id]))
        self.assertEquals(len(ext_site.child_instrument_sites), 1)
        self.assertEquals(ext_site.child_instrument_sites[0]._id, is1_id)

        self.RR.delete_association(aid1)

        extended_resource_handler = ExtendedResourceContainer(self)
        ext_site = extended_resource_handler.create_extended_resource_container(
            extended_resource_type=OT.TestExtendedResourceSite,
            resource_id=ps1_id,
            computed_resource_type=OT.BaseComputedAttributes)

        #pprint.pprint(ext_site.__dict__)

        self.assertEquals(ext_site.parent_site, None)
        self.assertEquals(len(ext_site.child_sites), 2)
        self.assertEquals(set(r._id for r in ext_site.child_sites), set([is1_id, ps2_id]))
        self.assertEquals(len(ext_site.child_sites1), 2)
        self.assertEquals(set(r._id for r in ext_site.child_sites1), set([is1_id, ps2_id]))
        self.assertEquals(len(ext_site.child_instrument_sites), 1)
        self.assertEquals(ext_site.child_instrument_sites[0]._id, is1_id)
