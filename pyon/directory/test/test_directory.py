#!/usr/bin/env python

__author__ = 'Thomas R. Lennan'
__license__ = 'Apache 2.0'

from pyon.directory.directory import Directory
from pyon.test.pyontest import PyonTestCase
from unittest import SkipTest

class Test_Directory(PyonTestCase):

    def test_non_persistent(self):
        directory_service = Directory()

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

if __name__ == "__main__":
    unittest.main()
    
