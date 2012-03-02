#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.ion.directory import Directory
from pyon.util.unit_test import IonUnitTestCase
from nose.plugins.attrib import attr
from pyon.datastore.datastore import DatastoreManager


@attr('UNIT',group='datastored')
class TestDirectory(IonUnitTestCase):

    def test_directory(self):
        dsm = DatastoreManager()
        directory = Directory(dsm)

        root = directory.lookup("/")
        self.assert_(root is not None)

        self.assertEquals(directory.register("/","temp"), None)

        # Create a node
        root = directory.lookup("/temp")
        self.assertEquals(root, {} )

        # The create case
        entry_old = directory.register("/temp", "entry1", foo="awesome")
        self.assertEquals(entry_old, None)
        entry_new = directory.lookup("/temp/entry1")
        self.assertEquals(entry_new, {"foo":"awesome"})

        # The update case
        entry_old = directory.register("/temp", "entry1", foo="ingenious")
        self.assertEquals(entry_old, {"foo":"awesome"})

        # The delete case
        entry_old = directory.unregister("/temp", "entry1")
        self.assertEquals(entry_old, {"foo":"ingenious"})
        entry_new = directory.lookup("/temp/entry1")
        self.assertEquals(entry_new, None)

        directory.register("/BranchA", "X", resource_id="rid1")
        directory.register("/BranchA", "Y", resource_id="rid2")
        directory.register("/BranchA", "Z", resource_id="rid3")
        directory.register("/BranchA/X", "a", resource_id="rid4")
        directory.register("/BranchA/X", "b", resource_id="rid5")
        directory.register("/BranchB", "k", resource_id="rid6")
        directory.register("/BranchB", "l", resource_id="rid7")
        directory.register("/BranchB/k", "m", resource_id="rid7")

        res_list = directory.find_by_value("/", attribute="resource_id", value="rid3")
        self.assertEquals(len(res_list), 1)
        self.assertEquals(res_list[0][0], "ION/BranchA/Z")

        res_list = directory.find_by_value("/", attribute="resource_id", value="rid34")
        self.assertEquals(len(res_list), 0)

        res_list = directory.find_by_value("/", attribute="resource_id", value="rid7")
        self.assertEquals(len(res_list), 2)

        res_list = directory.find_by_value("/BranchB", attribute="resource_id", value="rid7")
        self.assertEquals(len(res_list), 2)

        res_list = directory.find_by_value("/Branch", attribute="resource_id", value="rid7")
        self.assertEquals(len(res_list), 2)

        res_list = directory.find_by_value("/BranchB/k", attribute="resource_id", value="rid7")
        self.assertEquals(len(res_list), 1)

        directory.close()
