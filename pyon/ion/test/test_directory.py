#!/usr/bin/env python

__author__ = 'Thomas R. Lennan, Michael Meisinger'
__license__ = 'Apache 2.0'

from pyon.ion.directory import Directory
from pyon.util.unit_test import IonUnitTestCase
from nose.plugins.attrib import attr
from pyon.datastore.datastore import DatastoreManager


@attr('UNIT',group='datastore')
class TestDirectory(IonUnitTestCase):

    def test_directory(self):
        dsm = DatastoreManager()
        directory = Directory(dsm)

        root = directory.lookup("/")
        self.assertEquals(root, None)

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
