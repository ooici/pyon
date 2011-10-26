import unittest

from pyon.core.bootstrap import obj_registry, populate_registry

populate_registry()

class PyonTestCase(unittest.TestCase):
    """
    Base test class to allow operations such as starting the container
    """

    def run(self, result=None):
        unittest.TestCase.run(self, result)