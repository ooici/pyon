#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

import unittest

from pyon.directory.directory import Directory

class Test_Directory(unittest.TestCase):

    def _do_test(self, directory_service):
        directory_service.delete()
        directory_service.create()

        root = directory_service.read("/")
        self.assertEquals(root,{})

        # Add empty Services subtree
        self.assertEquals(directory_service.add("/","Services",{}),{})

        root = directory_service.read("/")
        self.assertEquals(root, {"Services":{}} )

        # Add a Service instance
        self.assertEquals(directory_service.add("/Services", "serv_foo.inst1", {"bar":"awesome"}),{"bar":"awesome"})

        root = directory_service.read("/")
        self.assertEquals(root, {"Services":{"serv_foo.inst1":{"bar":"awesome"}}})

        # Update a Service instance
        directory_service.update("/Services", "serv_foo.inst1", {"bar":"totally awesome"})

        root = directory_service.read("/")
        self.assertEquals(root, {"Services":{"serv_foo.inst1":{"bar":"totally awesome"}}})

        # Delete a Service instance
        self.assertEquals(directory_service.remove("/Services", "serv_foo.inst1"), {"bar":"totally awesome"})

        root = directory_service.read("/")
        self.assertEquals(root, {"Services":{}} )

    def test_non_persistent(self):
        self._do_test(Directory(datastore_name='my_directory_ds', persistent=False))

    def test_persistent(self):
        self._do_test(Directory(datastore_name='my_directory_ds', persistent=True))

if __name__ == "__main__":
    unittest.main()
    
