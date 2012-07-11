from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr
from pyon.ion.directory_standalone import DirectoryStandalone
from pyon.core.interfaces.interfaces import InterfaceAdmin
from pyon.core import config
from pyon.datastore import clear_couch_util

@attr('interfaces_')
class InterfaceAdminTest(IonIntegrationTestCase):
    bootstrap_config = None
    dir = None
    sysname = "interface_testing__"
    iadm = None

    def setUp(self):
        self.bootstrap_config = config.read_local_configuration(['res/config/pyon_min_boot.yml'])
        self.dir = DirectoryStandalone(sysname=self.sysname,config=self.bootstrap_config)
        self.iadm = InterfaceAdmin(self.sysname, config=self.bootstrap_config)

    def test_clean(self):
        entries = None
        clear_couch_util.clear_couch(self.bootstrap_config, prefix=self.sysname)
        try:
           entries = self.dir.find_child_entries('/')
        except:
            pass
        # Make sure the database is empty
        self.assertFalse(entries)

    def test_store_core(self):
        # Store system CFG properties
        ion_config = config.read_standard_configuration()
        self.iadm.store_config(ion_config)

        # Validate the CFG entries are stored in DB
        entries = self.dir.lookup('/Config/CFG')
        self.assertTrue(entries)

    def test_store_interfaces(self):
        self.iadm.store_interfaces()
        entries = self.dir.find_child_entries('/ObjectTypes')

        # Validate there are entries for ObjectType
        self.assertGreater(len(entries), 30)

        # Validate there are entries for ServiceInterfaces
        entries = self.dir.find_child_entries('/ServiceInterfaces')
        self.assertGreater(len(entries), 30)

    def tearDown(self):
        entries = None
        clear_couch_util.clear_couch(self.bootstrap_config, prefix=self.sysname)
        try:
            entries = self.dir.find_child_entries('/')
        except:
            pass
        # Make sure the database is empty
        self.assertFalse(entries, "Database is not empty after doing clear")


