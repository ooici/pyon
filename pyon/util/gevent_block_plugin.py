# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# See: http://www.rfk.id.au/blog/entry/detect-gevent-blocking-with-greenlet-settrace/
# Usage: From project root dir:
# bin/nosetests --with-gevent-block
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

debug = sys.stderr
# The maximum amount of time that the eventloop can be blocked
# without causing an error to be logged, in seconds.

MAX_BLOCKING_TIME = 1

# A global variable for tracking the time of the last greenlet switch.
# For server processes that use a single OS-level thread, a global works fine.
# You might like to use a threadlocal for complicated setups.

_last_switch_time = None

_momento_time = None

def switch_time_tracer(what, (origin, target)):
    global _last_switch_time
    global _momento_time
    then = _last_switch_time
    _momento_time = now = _last_switch_time = time.time()
    # We are switching from hub to a greenlet, set the alarm now to start tracking.
    if origin is gevent.hub.get_hub():
        signal.alarm(MAX_BLOCKING_TIME)
        return
    # We are switching out to hub.  Let's check greenlet running duration.
    if then is not None:
        blocking_time = now - then
        if blocking_time > MAX_BLOCKING_TIME:
            msg = "Greenlet %s blocked the os thread for %.4f seconds\n"
            msg = msg % (repr(origin), blocking_time, )
            debug.write(msg)
    signal.alarm(0)

def alarm_handler(signum, frame):
    global _momento_time
    global _last_switch_time
    if _momento_time == _last_switch_time:
        debug.write('CRITICAL> gevent blocking detected!\n' +\
        'Currently at %s():%d of file %s.\n' % ( frame.f_code.co_name,
            frame.f_lineno, frame.f_code.co_filename))
        # Optional.  Let's check if it's still blocking in next iteration.
        signal.alarm(MAX_BLOCKING_TIME)

class GEVENT_BLOCK(Plugin):
    name = 'gevent-block'

    def begin(self):
        # A trace function that gets executed on every greenlet switch.
        # It checks how much time has elapsed and logs an error if it was excessive.
        # The Hub gets an exemption, because it's allowed to block on I/O.
        greenlet.settrace(switch_time_tracer)
        signal.signal(signal.SIGALRM, alarm_handler)

    def finalize(self, result):
        """Called after all report output, including output from all
        plugins, has been sent to the stream. Use this to print final
        test results or perform final cleanup. Return None to allow
        other plugins to continue printing, or any other value to stop
        them.
        """
        #Disable alarm
        signal.alarm(0)
