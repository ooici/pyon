# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# See: http://www.rfk.id.au/blog/entry/detect-gevent-blocking-with-greenlet-settrace/
# Also see: https://www.memelabs.net/sync/deps/server-core/services/gunicorn_worker.py
# Usage: From project root dir:
# bin/nosetests --with-gevent-block
# There are two modes for detecting gevent block: alarm mode and os thread monitor mode.
# Default is the os thread monitor mode.  To enable alarm mode, pass --gevent-block-alarm
# to the nose command line.
#
# The gevent block can also be used in a pycc container or manhole:
# from pyon/util/gevent_block_plugin import get_gevent_monitor_block
# gb = get_gevent_monitor_block
# gb.start()  #To start capturing block traces
# gb.stop() # To stop capturing block traces
# gb.log_snapshots() # To view captured traces
#
# This is fully integrated with container stats tool and container event management.
# Sample usage:
# curl http://localhost:5000/ion-service/system_management/start_gevent_block
# Let gevent block run for a period of time to collect traces and then take a snapshot
# curl http://localhost:5000/ion-service/system_management/trigger_container_snapshot
# curl http://localhost:5000/ion-service/system_management/stop_gevent_block
# The captured snapshot can be viewed in container stats via mx tool, or manhole, or
# dumped as excel spreadsheet via ResourceRegistryHelper.
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import time, os
import subprocess
from nose.plugins import Plugin

import sys
import time
import traceback
import greenlet
import gevent.hub
import signal
from collections import defaultdict
from copy import copy

# The maximum amount of time that the eventloop can be blocked
# without causing an error to be logged, in seconds.

MAX_BLOCKING_TIME = 1

# Get references to un-monkey-patched versions of stuff we need.
from pyon.util.unmonkey import get_realtime, get_realthread
_real_sleep = get_realtime().sleep
_real_start_new_thread = get_realthread().start_new_thread
_real_get_ident = get_realthread().get_ident

_gevent_block = None

def get_gevent_block():
    global _gevent_block
    return _gevent_block

def get_gevent_alarm_block():
    global _gevent_block
    if _gevent_block is None:
        _gevent_block = GeventAlarmBlock()
    elif not isinstance(_gevent_block, GeventAlarmBlock):
        _gevent_block.stop()
        _gevent_block = GeventAlarmBlock()
    return _gevent_block

def get_gevent_monitor_block():
    global _gevent_block
    if _gevent_block is None:
        _gevent_block = GeventMonitorBlock()
    elif not isinstance(_gevent_block, GeventMonitorBlock):
        _gevent_block.stop()
        _gevent_block = GeventMonitorBlock()
    return _gevent_block

class GeventAlarmBlock(object):

    def __init__(self, current_test=None):
        self._current_test = current_test
        self.oldtrace = None
        self._last_traces = []
        self._snap_shots = defaultdict(list)
        self._blocking_time = {}

        # Read current test id
        self._current_test = None

        # A global variable for tracking the time of the last greenlet switch.
        # For server processes that use a single OS-level thread, a global works fine.
        # You might like to use a threadlocal for complicated setups.
        #Used by alarm mode
        self._last_switch_time = None
        self._momento_time = None

        self._started = False

    def start(self):
        # A trace function that gets executed on every greenlet switch.
        # It checks how much time has elapsed and logs an error if it was excessive.
        # The Hub gets an exemption, because it's allowed to block on I/O.
        if self._started:
            # Already started.  Do nothing.
            return

        self.oldtrace = greenlet.settrace(self._switch_time_tracer)
        signal.signal(signal.SIGALRM, self._alarm_handler)
        self._started = True

    def stop(self):
        """Called after all report output, including output from all
        plugins, has been sent to the stream. Use this to print final
        test results or perform final cleanup. Return None to allow
        other plugins to continue printing, or any other value to stop
        them.
        """
        #Disable alarm
        if self._started:
            signal.alarm(0)
            greenlet.settrace(self.oldtrace)
            self._started = False

    def _switch_time_tracer(self, what, (origin, target)):
        then = self._last_switch_time
        self._momento_time = now = self._last_switch_time = time.time()
        # We are switching from hub to a greenlet, set the alarm now to start tracking.
        if origin is gevent.hub.get_hub():
            signal.alarm(MAX_BLOCKING_TIME)
            # Clear last blocked trace
            self._last_traces = []
            return
        # We are switching out to hub.  Let's check greenlet running duration.
        if then is not None:
            blocking_time = now - then
            if blocking_time > MAX_BLOCKING_TIME:
                from pyon.util.log import log
                from pyon.util.containers import get_ion_ts, get_datetime_str
                msg = "Greenlet %s with name %s blocked the os thread for %.4f seconds before %s.\n" % (repr(origin), getattr(origin, "_glname", "None"), blocking_time, get_datetime_str(get_ion_ts()) )
                log.warn(msg)
                self._last_traces = self._last_traces[-1:]
                if self._last_traces:
                    msg += 'Last blocked traces:\n'
                    msg += '\n'.join(self._last_traces)
                if self._current_test:
                    test_id = self._current_test[0]
                else:
                    test_id = ''
                key = str(hex(id(origin)))
                self._snap_shots[(test_id, key)].append(msg)
                self._snap_shots[(test_id, key)] = self._snap_shots[(test_id, key)][-1:]
        signal.alarm(0)

    def _alarm_handler(self, signum, frame):
        if self._momento_time == self._last_switch_time:
            st = traceback.extract_stack(frame)
            from pyon.util.containers import get_ion_ts, get_datetime_str
            alarm_trace ='CRITICAL> gevent blocking detected at %s!\n' % get_datetime_str(get_ion_ts()) +\
                'At %s():%d of file %s.\n' % ( frame.f_code.co_name, frame.f_lineno, frame.f_code.co_filename)
            alarm_trace += "Stack trace: %s\n" % "".join(traceback.format_list(st))
            self._last_traces.append(alarm_trace)
            # Optional.  Let's check if it's still blocking in next iteration.
            signal.alarm(MAX_BLOCKING_TIME)

    def get_snapshots(self):
        return copy(self._snap_shots)


    def log_snapshots(self):
        snapshots = self.get_snapshots()
        from ooi.logging import log
        for (_,gl_id), msgs in snapshots.items():
            log.warn('greenlet %s most recent blocking traces:\n' % gl_id)
            for index, msg in enumerate(msgs):
                log.warn('Blocking msg %d:\n' % (index+1))
                log.warn(msg)

class GeventMonitorBlock(object):

    def __init__(self, current_test=None):
        self._current_test = current_test
        self.oldtrace = None
        self._last_traces = []
        self._snap_shots = defaultdict(list)
        self._blocking_time = {}

        # Read current test id
        self._current_test = None

        self._last_switch_time = None
        self._active_hub = None
        self._greenlet_switch_counter = 0
        self._stop_monitor = False
        self._active_greenlet = None
        self._started = False

    def start(self):
        if self._started:
            # Already started.  Do nothing.
            return
        # A trace function that gets executed on every greenlet switch.
        # It checks how much time has elapsed and logs an error if it was excessive.
        # The Hub gets an exemption, because it's allowed to block on I/O.
        self.oldtrace = greenlet.settrace(self._switch_time_tracer)
        self._active_hub = gevent.hub.get_hub()
        self._main_thread_id = _real_get_ident()
        _real_start_new_thread(self._greenlet_blocking_monitor, ())
        self._started = True

    def stop(self):
        if self._started:
            self._stop_monitor = True
            greenlet.settrace(self.oldtrace)
            self._started = False

    def _switch_time_tracer(self, what, (origin, target)):
        then = self._last_switch_time
        now = self._last_switch_time = time.time()
        self._active_greenlet = target
        self._greenlet_switch_counter += 1
        if origin is gevent.hub.get_hub():
            # Clear last blocked trace
            self._last_traces = []
            return
        # We are switching out to hub.  Let's check greenlet running duration.
        if then is not None:
            blocking_time = now - then
            if blocking_time > MAX_BLOCKING_TIME:
                from pyon.util.log import log
                from pyon.util.containers import get_ion_ts, get_datetime_str
                msg = "Greenlet %s with name %s blocked the os thread for %.4f seconds before %s.\n" % (repr(origin), getattr(origin, "_glname", "None"), blocking_time, get_datetime_str(get_ion_ts()) )
                log.warn(msg)
                self._last_traces = self._last_traces[-1:]
                if self._last_traces:
                    msg += 'Last blocked traces:\n'
                    msg += '\n'.join(self._last_traces)
                if self._current_test:
                    test_id = self._current_test[0]
                else:
                    test_id = ''
                key = str(hex(id(origin)))
                self._snap_shots[(test_id, key)].append(msg)
                self._snap_shots[(test_id, key)] = self._snap_shots[(test_id, key)][-1:]
                self._blocking_time[(test_id,key)] = self._blocking_time.get((test_id,key), 0) + blocking_time

    def _greenlet_blocking_monitor(self):
        while not self._stop_monitor:
            old_switch_counter = self._greenlet_switch_counter
            _real_sleep(MAX_BLOCKING_TIME)
            active_greenlet = self._active_greenlet
            new_switch_counter = self._greenlet_switch_counter
            # If we have detected a successful switch, reset the counter
            # to zero.  This might race with it being incrememted in the
            # other thread, but should succeed often enough to prevent
            # the counter from growing without bound.
            if new_switch_counter != old_switch_counter:
                self._greenlet_switch_counter = 0
            # If we detected a blocking greenlet, grab the stack trace
            # and log an error.  The active greenlet's frame is not
            # available from the greenlet object itself, we have to look
            # up the current frame of the main thread for the traceback.
            else:
                if active_greenlet not in (None, self._active_hub):
                    frame = sys._current_frames()[self._main_thread_id]
                    stack = traceback.format_stack(frame)
                    from pyon.util.containers import get_ion_ts, get_datetime_str
                    self._last_traces.append("Greenlet appears to be blocked at %s \n" % get_datetime_str(get_ion_ts()) + "".join(stack))

    def get_snapshots(self):
        snapshots = copy(self._snap_shots)
        blocking_stats = self.get_blocking_time()
        if blocking_stats:
            for test_id, key in blocking_stats.keys():
                snapshots[(test_id,key)].append('Greelet %s blocked a TOTAL of %fs.' % (key, blocking_stats[(test_id,key)]))
        return snapshots

    def get_blocking_time(self):
        return copy(self._blocking_time)

    def log_snapshots(self):
        snapshots = self.get_snapshots()
        from ooi.logging import log
        for (_,gl_id), msgs in snapshots.items():
            log.warn('greenlet %s most recent blocking traces:\n' % gl_id)
            for index, msg in enumerate(msgs):
                log.warn('Blocking msg %d:\n' % (index+1))
                log.warn(msg)

class GEVENT_BLOCK(Plugin):
    name = 'gevent-block'

    def options(self, parser, env):
        super(GEVENT_BLOCK, self).options(parser, env=env)
        parser.add_option("--gevent-block-alarm", action="store_true", dest="block_alarm", help="Use alarm instead of monitor thread to detect block traces.")
        parser.add_option("--gevent-block-noreport", action="store_true", dest="noreport", help="Suppress report output", default=False)

    def configure(self, options, conf):
        super(GEVENT_BLOCK, self).configure(options, conf)

        self._block_alarm = options.block_alarm
        self._noreport = options.noreport

    def begin(self):
        self._current_test = []
        #Pass by reference value of self.current_test so we can share test id with gevent block class.
        if self._block_alarm:
            self._greenlet_block = GeventAlarmBlock(self._current_test)
        else:
            self._greenlet_block = GeventMonitorBlock(self._current_test)
        self._greenlet_block.start()

    def beforeTest(self, test):
        #Share test id with gevent block class.
        self._current_test[:] = []
        self._current_test.append(test.id())

    def report(self, stream):
        if not self._noreport:
            table = []

            snapshots = self._greenlet_block.get_snapshots()
            for key, msgs in snapshots.items():
                t_id, gl_id = key

                # printable tid: don't need the full path
                pt_id = ".".join(t_id.split(".")[-2:])

                table.append([pt_id, "" ])

                table.append(["", 'greenlet %s most recent blocking traces:' % gl_id])
                for index, msg in enumerate(msgs):
                    table.append(["", "Blocking msg %d:" % (index+1)])
                    table.append(["", msg])

                table.append(["", ""])

            # header
            table.insert(0, ['Test', 'Blocked Greenlet'])

            # get widths
            widths = [max([len(row[x]) for row in table]) for x in xrange(len(table[0]))]
            #fmt_out = [" ".join([x.ljust(widths[i]) for i, x in enumerate(row)]) for row in table]
            fmt_out = [" "* 30 + "".join([x for i, x in enumerate(row)]) for row in table]

            # insert col separation row
            #fmt_out.insert(1, " ".join([''.ljust(widths[i], '=') for i in xrange(len(widths))]))

            # write this all to sstream
            stream.write("Greenlet block report\n")

            stream.write("\n".join(fmt_out))
            stream.write("\n")

    def finalize(self, result):
        """Called after all report output, including output from all
        plugins, has been sent to the stream. Use this to print final
        test results or perform final cleanup. Return None to allow
        other plugins to continue printing, or any other value to stop
        them.
        """
        if self._greenlet_block:
            self._greenlet_block.stop()
