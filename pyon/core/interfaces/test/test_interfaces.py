#!/usr/bin/env python

__author__ = 'Seman Said'

from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr

from pyon.core import config, bootstrap
from pyon.core.interfaces.interfaces import InterfaceAdmin
from pyon.datastore import clear_couch_util
from pyon.ion.directory_standalone import DirectoryStandalone
from pyon.ion.resregistry_standalone import ResourceRegistryStandalone

@attr('INT',group='coi')
class InterfaceAdminTest(IonIntegrationTestCase):

    def setUp(self):
        self.dir = DirectoryStandalone(sysname=bootstrap.get_sys_name(), config=bootstrap.CFG)
        self.rr = ResourceRegistryStandalone(sysname=bootstrap.get_sys_name(), config=bootstrap.CFG)
        self.iadm = InterfaceAdmin(bootstrap.get_sys_name(), config=bootstrap.CFG)

        self.addCleanup(self.iadm.close)

    def test_store_core(self):
        # Store system CFG properties
        ion_config = config.read_standard_configuration()
        self.iadm.store_config(ion_config)

        # Validate the CFG entries are stored in DB
        entries = self.dir.lookup('/Config/CFG')
        self.assertTrue(entries)

    def test_store_interfaces(self):
        self.iadm.store_interfaces()

        # Validate there are entries for ObjectType
        entries = self.rr.find_by_type("ObjectType", id_only=True)
        self.assertGreater(len(entries), 30)

        # Validate there are entries for ServiceInterfaces
        entries = self.rr.find_by_type("ServiceDefinition", id_only=True)
        self.assertGreater(len(entries), 30)
