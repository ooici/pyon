#!/usr/bin/env python

"""General utility to trace important calls or events in the system, see
https://confluence.oceanobservatories.org/display/CIDev/Collecting+and+managing+system+statistics+and+timing"""

__author__ = 'Michael Meisinger'

import inspect
from collections import defaultdict
from contextlib import contextmanager
# create special logging category for tracer logging
import logging
tracerlog = logging.getLogger('tracer')

from pyon.util.containers import get_ion_ts, get_datetime_str

from ooi.logging import log, DEBUG

DEFAULT_CONFIG = {"enabled": True,
                  "max_entries": 5000,
                  "log_trace": False,
                  "log_filter": "",
                  "log_color": False,
                  "log_stack": False,
                  "log_truncate": 2000,
                  }

# Global trace log data
trace_data = dict(trace_log=[],                # Global log
                  format_cb={},                # Scope specific formatter function
                  scope_seq=defaultdict(int),  # Sequence number per scope
                  config=DEFAULT_CONFIG.copy(),  # Store config dict
                  )
SCOPE_COLOR = {
    "MSG": 31,
    "GW": 32,
    "DB.resources": 34,
    "DB.events": 35,
    #"DB.objects": 36,
    #"DB.state": 36,
    "DB": 36,
}
DEFAULT_COLOR = 39


class CallTracer(object):
    def __init__(self, scope, formatter=None):
        self.scope = scope
        if formatter:
            self.set_formatter(scope, formatter)

    @staticmethod
    def set_formatter(scope, formatter):
        trace_data["format_cb"][scope] = formatter

    def log_call(self, log_entry, include_stack=True):
        self.log_scope_call(self.scope, log_entry, include_stack=include_stack)

    @staticmethod
    def log_scope_call(scope, log_entry, include_stack=True, stack_first_frame=4):
        try:
            if not trace_data["config"].get("enabled", False):
                return

            log_entry["scope"] = scope
            if not "ts" in log_entry:
                log_entry["ts"] = get_ion_ts()
            trace_data["scope_seq"][scope] += 1
            log_entry["seq"] = trace_data["scope_seq"][scope]

            if include_stack:
                stack = inspect.stack()
                frame_num = stack_first_frame
                context = []
                while len(stack) > frame_num and frame_num < 15:
                    exec_line = "%s:%s:%s" % (stack[frame_num][1], stack[frame_num][2], stack[frame_num][3])
                    context.insert(0, exec_line)
                    if exec_line.endswith("_control_flow") or exec_line.endswith("load_ion") or exec_line.endswith("spawn_process")\
                        or exec_line.endswith(":main") or exec_line.endswith(":dispatch_request"):
                        break
                    frame_num += 1
                log_entry["stack"] = context

            trace_data["trace_log"].append(log_entry)
            if len(trace_data["trace_log"]) > trace_data["config"].get("max_entries", DEFAULT_CONFIG["max_entries"]) + 100:
                trace_data["trace_log"] = trace_data["trace_log"][-trace_data["config"].get("max_entries", DEFAULT_CONFIG["max_entries"]):]

            CallTracer.log_trace(log_entry)
        except Exception as ex:
            log.warn("Count not log trace call: %s", log_entry)

    @staticmethod
    def log_trace(log_entry):
        if not trace_data["config"].get("log_trace", False):
            return
        if not tracerlog.isEnabledFor(DEBUG):
            return
        log_filter = trace_data["config"].get("log_filter", None) or ""
        filter_scopes = log_filter.split(",")
        log_stack = trace_data["config"].get("log_stack", None) or False
        log_color = trace_data["config"].get("log_color", None) or False
        log_truncate = trace_data["config"].get("log_truncate", None) or 2000
        log_txt = CallTracer._get_log_text(log_entry, truncate=log_truncate, stack=log_stack, color=log_color)  # May change scope
        logscope = log_entry["scope"]
        scope_cat = logscope.split(".", 1)[0]
        if not log_filter or logscope in filter_scopes or scope_cat in filter_scopes:
            log_txt = log_txt.strip()
            tracerlog.debug("%s", log_txt)

    @staticmethod
    def clear_scope(scope):
        trace_data["trace_log"] = [l for l in trace_data["trace_log"] if l["scope"] != scope]

    @staticmethod
    def clear_all():
        trace_data["trace_log"] = []

    @staticmethod
    def save_log(**kwargs):
        kwargs["tofile"] = True
        CallTracer.print_log(**kwargs)

    @staticmethod
    def print_log(scope=None, max_log=10000, reverse=False, color=True, truncate=2000, stack=True,
                  count=True, filter=None, tofile=False):
        cnt = 0
        counters = defaultdict(int)
        elapsed = defaultdict(int)
        startts, endts = 0, 0
        f = None
        try:
            if tofile:
                import datetime
                dtstr = datetime.datetime.today().strftime('%Y%m%d_%H%M%S')
                path = "interface/tracelog_%s.log" % dtstr
                f = open(path, "w")
            for log_entry in reversed(trace_data["trace_log"]) if reverse else trace_data["trace_log"]:
                logscope = log_entry["scope"]
                scope_cat = logscope.split(".", 1)[0]
                if scope and not logscope.startswith(scope):
                    continue

                if tofile:
                    color = False
                log_txt = CallTracer._get_log_text(log_entry, truncate=truncate, stack=stack, color=color)
                logscope = log_entry["scope"]      # Read again to enable formatter to specialize scope
                if scope and not logscope.startswith(scope):
                    continue
                # Call it here because the formatter may have modified the entry
                try:
                    if filter and not filter(log_entry):
                        continue
                except Exception as ex:
                    pass  # Filter error - ignore to make it easier to writer filters
                if tofile:
                    f.write(log_txt)
                    f.write("\n")
                else:
                    print log_txt

                if not startts:
                    startts = log_entry["ts"]
                endts = log_entry["ts"]
                if count:
                    counters[logscope] += 1
                    if scope_cat != logscope:
                        counters[scope_cat] += 1
                    if 'statement_time' in log_entry:
                        statement_time = float(log_entry['statement_time'])
                        elapsed[logscope] += statement_time
                        if scope_cat != logscope:
                            elapsed[scope_cat] += statement_time
                cnt += 1
                if cnt >= max_log:
                    break
            if count:
                counters["SKIP"] = len(trace_data["trace_log"]) - cnt
                if tofile:
                    f.write("\n\nCounts: " + ", ".join(["%s=%s" % (k, counters[k]) for k in sorted(counters)]))
                    f.write("\nElapsed time: %s s, %s\n" % (abs(int(endts) - int(startts)) / 1000.0,
                                ", ".join(["%s=%.3fs" % (k, elapsed[k]) for k in sorted(elapsed)])))

                print "\nCounts:", ", ".join(["%s=%s" % (k, counters[k]) for k in sorted(counters)])
                print "Elapsed time:", abs(int(endts) - int(startts)) / 1000.0, "s,", \
                    ", ".join(["%s=%.3f s" % (k, elapsed[k]) for k in sorted(elapsed)])
        finally:
            if f:
                f.close()

    @staticmethod
    def _get_log_text(log_entry, truncate=2000, stack=False, color=False):
        logscope = log_entry["scope"]
        formatter = trace_data["format_cb"].get(logscope, None) or CallTracer._default_formatter
        try:
            # Warning: Make sure formatter is reentrant. It may be called several times with the same entry
            log_txt = formatter(log_entry, truncate=truncate, stack=stack, color=color)
        except Exception as ex:
            log_txt = "ERROR formatting: %s" % str(ex)
        return log_txt

    @staticmethod
    def _default_formatter(log_entry, **kwargs):
        truncate = kwargs.get("truncate", 0)
        color = kwargs.get("color", False)
        logscope = log_entry["scope"]
        scope_cat = logscope.split(".", 1)[0]

        entry_color = SCOPE_COLOR.get(logscope, None) or SCOPE_COLOR.get(scope_cat, DEFAULT_COLOR)
        frags = []
        if color:
            frags.append("\033[1m\033[%sm" % entry_color)
        stmt_time = " [%.5f s]" % log_entry.get('statement_time') if 'statement_time' in log_entry else ""
        frags.append("\n%s: #%s @%s (%s)%s -> %s" % (log_entry['scope'], log_entry['seq'], log_entry['ts'],
                                                     get_datetime_str(log_entry['ts'], show_millis=True),
                                                     stmt_time, log_entry.get("status", "OK")))
        if color:
            frags.append("\033[22m")    # Bold off
        statement = log_entry.get('statement', "")
        if truncate:
            frags.append("\n" + statement[:truncate])
            if len(statement) > truncate:
                frags.append("...")
                frags.append("[%s]" % (len(statement) - truncate))
        else:
            frags.append("\n" + statement)
        if color:
            frags.append("\033[0m")
        if "stack" in log_entry and kwargs.get("stack", False):
            frags.append("\n ")
            frags.append("\n ".join(log_entry["stack"]))
        return "".join(frags)

    @staticmethod
    def configure(config):
        trace_data["config"] = config or {}
        enabled = bool(config.get("enabled", False))
        trace_data["enabled"] = enabled
        if not enabled:
            CallTracer.clear_all()

    @staticmethod
    @contextmanager
    def log_traces(config=None):
        """
        Context manager to enable trace logging for the duration of a with.
        """
        tracer_cfg_old = trace_data["config"]
        try:
            trace_data["config"] = trace_data["config"].copy()
            trace_data["config"]["log_trace"] = True
            if config:
                trace_data["config"].update(config)
            yield trace_data["config"]
        finally:
            trace_data["config"] = tracer_cfg_old
