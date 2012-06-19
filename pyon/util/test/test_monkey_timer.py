""" test monkey timer utility

    WARNING: because the MonkeyTimer is intended to measure how long is spent executing something,
    the test needs to take some measurable time.  sleep is used and times are kept below 0.1 sec,
    so total elapsed time for test is minimal.
"""

from pyon.util.monkey_timer import MonkeyTimer
from time import sleep
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr

@attr('UNIT')
class TestMonkeyTimer(IonIntegrationTestCase):
    def test_patch_function(self):

        record_calls = []
        def target(n):
            sleep(n) # sorry, need to sleep a little to get measurable execution time
            record_calls.append(1)

        target(0.05) # should not include totals from before patching
        t = MonkeyTimer()
        subject = t.patch_function(target, "target")

        was_called = False
        subject(0.1)

        self.assertAlmostEqual(0.1, t._clock_time["target"], delta=0.01)
        self.assertEqual(1, t._total_count["target"])
        self.assertEqual(2, len(record_calls))

    def test_patch_class(self):

        record_calls = []
        class TestClass(object):
            def f1(self):
                sleep(0.05)
            def f2(self):
                sleep(0.1)
                self.f1()
            def f3(self):
                record_calls.append(1)

        unpatched = TestClass()
        unpatched.f1()
        unpatched.f3()

        t = MonkeyTimer()
        TestClass = t.patch_class_all(TestClass, "cls.")

        patched = TestClass()
        patched.f1()
        patched.f2()
        patched.f3()

        self.assertAlmostEqual(0.1, t._clock_time["cls.f1"], delta=0.01)
        self.assertEqual(2, t._total_count["cls.f1"])
        self.assertEqual(2, len(record_calls))

        # call to f2 took 0.15sec, with 0.1 spent in sleep and 0.05 of that was spent in f1
        # so 0.1 is 100% f2; then other 0.05 is divided between f1 and f2
        self.assertAlmostEqual(0.075, t._proportional_time["cls.f1"], delta=0.01)
