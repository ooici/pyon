#!/usr/bin/env python

import unittest

from pyon.container.cc import Container
from pyon.core.bootstrap import obj_registry, populate_registry

populate_registry()

class PyonTestCase(unittest.TestCase):
    """
    Base test class to allow operations such as starting the container
    """

    def run(self, result=None):
        unittest.TestCase.run(self, result)

    def _start_container(self):
        self.container = Container()
        self.container.start()

    def _stop_container(self):
        self.container.stop()
