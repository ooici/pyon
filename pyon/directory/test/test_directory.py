#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from pyon.directory.directory import Directory
from pyon.util.int_test import IonIntegrationTestCase
from unittest import SkipTest
from nose.plugins.attrib import attr

@attr('UNIT')
class Test_Directory(IonIntegrationTestCase):

    def test_non_persistent(self):
        directory_service = Directory()

        root = directory_service.lookup("/")
        self.assertEquals(root, None)

        self.assertEquals(directory_service.register("/","temp"), None)

        # Create a node
        root = directory_service.lookup("/temp")
        self.assertEquals(root, {} )

        # The create case
        entry_old = directory_service.register("/temp", "entry1", foo="awesome")
        self.assertEquals(entry_old, None)
        entry_new = directory_service.lookup("/temp/entry1")
        self.assertEquals(entry_new, {"foo":"awesome"})

        # The update case
        entry_old = directory_service.register("/temp", "entry1", foo="ingenious")
        self.assertEquals(entry_old, {"foo":"awesome"})

        # The delete case
        entry_old = directory_service.unregister("/temp", "entry1")
        self.assertEquals(entry_old, {"foo":"ingenious"})
        entry_new = directory_service.lookup("/temp/entry1")
        self.assertEquals(entry_new, None)


if __name__ == "__main__":
    unittest.main()
    
