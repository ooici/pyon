"""
This plugin requests that the container log all collected statistics

Add this command to the way you execute nose::

    --with-stats

Each container will handle the request, so if running --with-pycc,
then statistics will appear in both container.log and pycc-container.log files.
Otherwise, container.log will show statistics.
"""

import time

import nose
from nose.plugins.base import Plugin
import subprocess

class TestStats(Plugin):

    name = 'stats'
    score = 1

    def report(self, stream):
        """ all tests have completed but --with-pycc has not yet stopped external container.
            request that containers log statistics now
        """

        # initialize pyon so we can get system name
        from pyon.core import bootstrap
        if not bootstrap.pyon_initialized:
            bootstrap.bootstrap_pyon()
        from pyon.public import get_sys_name, CFG

        # make request: bin/pycc --sysname mgmt -x ion.processes.test.manage_system.ReportStats
        null = open('/dev/null', 'w')
        cmd = ['bin/pycc', '--sysname', get_sys_name(), '-x', 'ion.processes.test.manage_system.ReportStats' ]
        status = subprocess.call(cmd, stdout=null, stderr=null)
        if status==0:
            stream.write('container statistics: a report request has been sent\n')
            time.sleep(5) # give time to handle before container shutdown begins
        else:
            stream.write('container statistics: failed to send report request (logging anyway -- who needs a container?)\n')
            from ooi.timer import get_accumulators
            for a in get_accumulators().values():
                a.log()

if __name__ == '__main__':
    nose.main(addplugins=[TestStats()])
