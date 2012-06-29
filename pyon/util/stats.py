#!/usr/bin/env python

"""Simple utilities to keep stats counters (similar to collections.Counter)"""

__author__ = 'Michael Meisinger'


class StatsCounter(object):
    def __init__(self):
        self._stat_counters = {}

    def count(self, namespace=None, **kwargs):
        namespace = namespace or "None"
        if namespace not in self._stat_counters:
            self._stat_counters[namespace] = {}
        stats = self._stat_counters[namespace]
        for key,value in kwargs.iteritems():
            if key not in stats:
                stats[key] = value
            else:
                stats[key] += value

    def print_stats(self, stats=None):
        stats = stats or self._stat_counters
        import pprint
        pprint.pprint(stats)

    def get_stats(self):
        import copy
        return copy.deepcopy(self._stat_counters)

    def diff_stats(self, stat_new, stat_old):
        diff_stat = {}
        for ckey, cval in stat_new.iteritems():
            if ckey in stat_old:
                cstat = {}
                diff_stat[ckey] = cstat
                oval = stat_old[ckey]
                for vkey, vval in cval.iteritems():
                    if vkey in oval:
                        cstat[vkey] = cval[vkey] - oval[vkey]
                    else:
                        cstat[vkey] = cval[vkey]
            else:
                diff_stat[ckey] = cval.copy()
        return diff_stat
