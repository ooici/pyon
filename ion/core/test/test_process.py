#!/usr/bin/env python

__author__ = 'Adam R. Smith'
__license__ = 'Apache 2.0'

import unittest

from ion.core.process import GreenProcess, PythonProcess, GreenProcessSupervisor

class ProcessTest(unittest.TestCase):
    def setUp(self):
        self.counter = 0

    def increment(self, amount=1):
        self.counter += amount

    def test_green(self):
        self.counter = 0
        proc = GreenProcess(self.increment, 2)
        proc.start()
        self.assertEqual(self.counter, 0)
        proc.join()
        self.assertEqual(self.counter, 2)

    def test_supervisor(self):
        self.counter = 0
        sup = GreenProcessSupervisor()
        sup.start()
        proc = sup.spawn(type='green', target=self.increment, amount=2)
        self.assertEqual(self.counter, 0)
        sup.join_children()
        self.assertEqual(self.counter, 2)

    def test_python(self):
        raise unittest.SkipTest('Need a better test here')
        self.counter = 0
        proc = PythonProcess(self.increment, 2)
        proc.start()
        self.assertEqual(self.counter, 0)
        proc.join()
        self.assertEqual(self.counter, 2)

if __name__ == '__main__':
    unittest.main()