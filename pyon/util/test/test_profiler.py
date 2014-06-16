#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'


from pyon.util.unit_test import PyonTestCase
from pyon.util.profiler import start_profiler, stop_profiler
from nose.plugins.attrib import attr
from mock import patch, sentinel
import unittest

@attr('UNIT')
@patch('pyon.util.profiler.gevent_profiler')
class TestProfiler(PyonTestCase):

    def test_verify_service(self, profmock):
        raise unittest.SkipTest("Not a service")

    def test_start(self, profmock):
        start_profiler('prefix', sentinel.pcts)

        profmock.set_stats_output.assert_called_once_with('prefix-stats.txt')
        profmock.set_summary_output.assert_called_once_with('prefix-summary.txt')
        profmock.print_percentages.assert_called_once_with(sentinel.pcts)
        profmock.set_trace_output.assert_called_once_with(None)

        profmock.attach.assert_called_once_with()

    def test_stop(self, profmock):
        stop_profiler()

        profmock.detach.assert_called_once_with()

