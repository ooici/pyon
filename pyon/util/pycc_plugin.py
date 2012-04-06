# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
#
# Usage: From project root dir:
# bin/nosetests --with-pycc [your other options]
#
# If you want to use this plugin AND insulate plugin:
# bin/nosetests --with-insulate --insulate-in-slave=--with-pycc --insulate-show-slave-output [your other options]
#
# Read up on insulate: http://code.google.com/p/insulatenoseplugin/
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import logging
import time, os
import subprocess
import signal
import sys

from nose.plugins import Plugin

debug = sys.stderr
log = logging.getLogger('nose.plugins.pycc')

class PYCC(Plugin):
    name = 'pycc'

    def __init__(self):
        Plugin.__init__(self)
        self.ccs = []
        self.container_started = False

    def options(self, parser, env):
        """Register command line options"""
        super(PYCC, self).options(parser, env=env)
        parser.add_option('--pycc-rel', type='string', dest='pycc_rel',
                help='Rel file path, res/deploy/r2deploy.yml by default',
                default='res/deploy/r2deploy.yml')

    def configure(self, options, conf):
        """Configure the plugin and system, based on selected options."""
        super(PYCC, self).configure(options, conf)
        if self.enabled:
            self.rel = options.pycc_rel

    def begin(self):
        """Called before any tests are collected or run. Use this to
        perform any setup needed before testing begins.
        """
        try:
            from pyon.public import get_sys_name
            sysname = get_sys_name()

            # Force datastore loader to use the same sysname
            from ion.processes.bootstrap.datastore_loader import DatastoreLoader
            DatastoreLoader.clear_datastore(prefix=sysname)

            def die(signum, frame):
                # For whatever reason, the parent doesn't die some times
                # when getting KeyboardInterrupt.  Hence this signal
                # handler.

                # Signal is pass through. The child pycc gets
                # its own KeyboardInterrupt and will shut down accordingly.
                debug.write('Received Keyboard Interrupt. Exiting now.\n')
                os._exit(9)

            signal.signal(signal.SIGINT, die)

            def no_zombie(signum, frame):
                debug.write('Child is dead...Clean up now so there is no zombie')
                val = os.wait()
                self.ccs = []

            signal.signal(signal.SIGCHLD, no_zombie)

            def container_started_cb(signum, frame):
                """Callback when child pycc service is ready"""
                self.container_started = True

            signal.signal(signal.SIGUSR1, container_started_cb)

            # Make sure the pycc process has the same sysname as the nose
            ccargs = ['bin/pycc', '--noshell', '-sp', '--system.name=%s' %
                    sysname,
                    '--logcfg=res/config/logging.pycc.yml',
                    '--rel=%s' % self.rel]
            debug.write('Starting cc process: %s\n' % ' '.join(ccargs))
            newenv = os.environ.copy()
            po = subprocess.Popen(ccargs, env=newenv, close_fds=True)
            self.ccs.append(po)

            # Wait for container to be ready
            while not self.container_started:
                time.sleep(0.2)
            debug.write('Child container is ready...\n')

            # Dump datastore
            DatastoreLoader.dump_datastore(path='res/dd')
            debug.write('Dump child container state to file...\n')

            # Enable CEI mode for the tests
            os.environ['CEI_LAUNCH_TEST'] = '1'

            debug.write('Start nose tests now...\n')
        except Exception as e:
            self.container_shutdown()
            raise e

    def finalize(self, result):
        """Called after all report output, including output from all
        plugins, has been sent to the stream. Use this to print final
        test results or perform final cleanup. Return None to allow
        other plugins to continue printing, or any other value to stop
        them.
        """
        self.container_shutdown()

    def container_shutdown(self):
        debug.write('Shut down cc process\n')
        for cc in self.ccs:
            debug.write('\tClosing container with pid:%d\n' % cc.pid)
            os.kill(cc.pid, signal.SIGINT)
