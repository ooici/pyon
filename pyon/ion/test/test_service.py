#!/usr/bin/env python

__author__ = 'Adam R. Smith'

import pyon
from pyon.ion.service import BaseService
from pyon.util.int_test import IonIntegrationTestCase

class TestService(BaseService):
    name = 'test-service'

class ServiceTest(IonIntegrationTestCase):
    def test_serve(self):
        # TODO: Make an equivalent of R1's ServiceProcess
        srv = TestService()
        #srv.serve_forever()
