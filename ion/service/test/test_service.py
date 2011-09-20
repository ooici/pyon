#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import ion
from ion.service.service import BaseService

import unittest

class TestService(BaseService):
    name = 'test-service'

class ServiceTest(unittest.TestCase):
    def test_serve(self):
        # TODO: Make an equivalent of R1's ServiceProcess
        srv = TestService()
        #srv.serve_forever()

if __name__ == '__main__':
    unittest.main()
