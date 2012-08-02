"""This plugin provides test timings to identify which tests might be
taking the most. From this information, it might be useful to couple
individual tests nose's `--with-profile` option to profile problematic
tests.

This plugin is heavily influenced by nose's `xunit` plugin.

Add this command to the way you execute nose::

    --with-test-timer

After all tests are executed, they will be sorted in ascending order.

(c) 2011 - Mahmoud Abdelkader (http://github.com/mahmoudimus)

LICENSE:
            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
                    Version 2, December 2004

 Copyright (C) 2004 Sam Hocevar <sam@hocevar.net>

 Everyone is permitted to copy and distribute verbatim or modified
 copies of this license document, and changing it is allowed as long
 as the name is changed.

            DO WHAT THE FUCK YOU WANT TO PUBLIC LICENSE
   TERMS AND CONDITIONS FOR COPYING, DISTRIBUTION AND MODIFICATION

  0. You just DO WHAT THE FUCK YOU WANT TO.

"""

import operator
import time

import nose
from nose.plugins.base import Plugin


class TestTimer(Plugin):
    """This plugin provides test timings

    """

    name = 'test-timer'
    score = 1

    def _timeTaken(self):
        if hasattr(self, '_timer'):
            taken = time.time() - self._timer
        else:
            # test died before it ran (probably error in setup())
            # or success/failure added before test started probably
            # due to custom TestResult munging
            taken = 0.0
        return self._timer, taken

    def options(self, parser, env):
        """Sets additional command line options."""
        super(TestTimer, self).options(parser, env)

    def configure(self, options, config):
        """Configures the test timer plugin."""
        super(TestTimer, self).configure(options, config)
        self.config = config
        self._timed_tests = []

    def startTest(self, test):
        """Initializes a timer before starting a test."""
        self._timer = time.time()

    def report(self, stream):
        """Report the test times"""
        if not self.enabled:
            return
        for test, (start_time, time_taken) in self._timed_tests:
            stream.writeln("%s: start time: %s elapsed: %0.4f" % (test, time.strftime('%H:%M:%S',
                    time.localtime(start_time)), time_taken))

    def _register_time(self, test):
        self._timed_tests.append((test.id(), self._timeTaken()))

    def addError(self, test, err, capt=None):
        self._register_time(test)

    def addFailure(self, test, err, capt=None, tb_info=None):
        self._register_time(test)

    def addSuccess(self, test, capt=None):
        self._register_time(test)


if __name__ == '__main__':
    nose.main(addplugins=[TestTimer()])
