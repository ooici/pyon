#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import anode
from anode.service.service import BaseService

import unittest

class ServiceTest(unittest.TestCase):
    def test_serve(self):
        srv = BaseService('test-service')
        srv.serve_forever()

if __name__ == '__main__':
    unittest.main()
