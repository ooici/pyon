#!/usr/bin/env python

"""
Hotfix for issue with BaseExceptions in nosetests's capture plugin.

Sometimes in our testing, a gevent Timeout will cause nose to come crashing
down with an error while it's trying to format the stdout/stderr capturing
which is enabled by default. Subsequent tests in a test run will all fail.

The exact issue is because the gevent Timeout is derived from BaseException,
not Exception, which the Capture plugin tests for and converts to string. By
the time it is ready to use the error object, it expects it to be a string.

Nose thankfully will let us derive and override the existing built in Plugin
by specifying the same string name ('capture') of the plugin.

See: http://nose.readthedocs.org/en/latest/plugins/builtin.html
"""

__author__ = "Dave Foster <dfoster@asascience.com>"
__license__ = "Apache 2.0"

from nose.plugins.capture import Capture

class PyccCapture(Capture):
    name = 'capture'

    def addCaptureToErr(self, ev, output):
        if isinstance(ev, BaseException) and not isinstance(ev, Exception):
            # BaseException derived? convert to unicode string so super's method doesn't choke
            ev = unicode(ev)
        return super(PyccCapture, self).addCaptureToErr(ev, output)

