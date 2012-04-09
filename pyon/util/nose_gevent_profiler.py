#!/usr/bin/env python

"""
Nose plugin for gevent-profiler.

Mostly based on the built in hotshot profiler plugin and the TestTimer plugin.

@author Dave Foster <dfoster@asascience.com>
"""

import operator
import time

import nose
from nose.plugins.base import Plugin
import gevent_profiler

class TestGeventProfiler(Plugin):

    name    = 'gevent-profiler'
    score   = 1
    enabled = False

    def options(self, parser, env):
        super(TestGeventProfiler, self).options(parser, env)

    def configure(self, options, config):
        super(TestGeventProfiler, self).configure(options, config)
        self.config = config

    def begin(self):
        ts = time.time()

        gevent_profiler.set_stats_output("nose-gevent-profiler-%s-stats.txt" % ts)
        gevent_profiler.set_summary_output("nose-gevent-profiler-%s-summary.txt" % ts)
        gevent_profiler.set_trace_output(None)

    def finalize(self, result):
        pass

    def prepareTest(self, test):
        def runner(result):
            gevent_profiler.profile(test, result)
        return runner


def main():
    nose.main(addplugins=[TestGeventProfiler()])

if __name__ == '__main__':
    main()
