#!/usr/bin/env python

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

import gevent_profiler

def start_profiler(prefix, pcts=False):
    """
    Start the gevent-profiler, outputting to the passed prefix-stats and prefix-summary.txt.

    You must call stop_profiler at a later point. The profiler is not safe to run twice at once
    as it keeps global state internally.

    @param  prefix      The prefix to use when naming the output files.
    @param  pcts        Whether the profiler should add percentages as well.
    """
    gevent_profiler.set_stats_output('%s-stats.txt' % prefix)
    gevent_profiler.set_summary_output('%s-summary.txt' % prefix)
    gevent_profiler.print_percentages(pcts)

    gevent_profiler.set_trace_output(None)  #'%s-trace.txt' % prefix)   @TODO make optional
    gevent_profiler.attach()

def stop_profiler():
    gevent_profiler.detach()

