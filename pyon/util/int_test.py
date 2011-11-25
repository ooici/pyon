#!/usr/bin/env python

"""Integration test base class and utils"""

import unittest

from pyon.container.cc import Container
from pyon.core.bootstrap import bootstrap_pyon

# Make this call more deterministic in time.
bootstrap_pyon()

class IonIntegrationTestCase(unittest.TestCase):
    """
    Base test class to allow operations such as starting the container
    TODO: Integrate with IonUnitTestCase
    """

    def run(self, result=None):
        unittest.TestCase.run(self, result)

    def _start_container(self):
        self.container = Container()
        self.container.start()

    def _stop_container(self):
        self.container.stop()

