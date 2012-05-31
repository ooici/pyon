#!/usr/bin/env python

"""Python Capability Container start script"""

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

import argparse
import yaml
import sys
import traceback
from uuid import uuid4

#
# WARNING - DO NOT IMPORT GEVENT OR PYON HERE. IMPORTS **MUST** BE DONE IN THE MAIN()
# DUE TO DAEMONIZATION.
#
# SEE: http://groups.google.com/group/gevent/browse_thread/thread/6223805ffcd5be22?pli=1
#

version = "2.0"     # TODO: extract this from the code once versioning is automated again
description = '''
pyon (ION capability container) v%s
''' % (version)

def setup_ipython(shell_api=None):
    from IPython.config.loader import Config
    ipython_cfg = Config()
    shell_config = ipython_cfg.InteractiveShellEmbed
    shell_config.prompt_in1 = '><> '
    shell_config.prompt_in2 = '... '
    shell_config.prompt_out = '--> '
    shell_config.confirm_exit = False

    # monkeypatch the ipython inputhook to be gevent-friendly
    import gevent   # should be auto-monkey-patched by pyon already.
    import select
    import sys
    def stdin_ready():
        infds, outfds, erfds = select.select([sys.stdin], [], [], 0)
        if infds:
            return True
        else:
            return False

    def inputhook_gevent():
        try:
            while not stdin_ready():
                gevent.sleep(0.001)
        except KeyboardInterrupt:
            pass

        return 0

    # install the gevent inputhook
    from IPython.lib.inputhook import inputhook_manager
    inputhook_manager.set_inputhook(inputhook_gevent)
    inputhook_manager._current_gui = 'gevent'

    # First import the embeddable shell class
    from IPython.frontend.terminal.embed import InteractiveShellEmbed

    # Update namespace of interactive shell
    # TODO: Cleanup namespace even further
    if shell_api is not None:
        locals().update(shell_api)

    # Now create an instance of the embeddable shell. The first argument is a
    # string with options exactly as you would type them if you were starting
    # IPython at the system command line. Any parameters you want to define for
    # configuration can thus be specified here.
    ipshell = InteractiveShellEmbed(config=ipython_cfg,
                           banner1 = \
"""    ____                                ________  _   __   ____________   ____  ___
   / __ \__  ______  ____              /  _/ __ \/ | / /  / ____/ ____/  / __ \|__ \\
  / /_/ / / / / __ \/ __ \   ______    / // / / /  |/ /  / /   / /      / /_/ /__/ /
 / ____/ /_/ / /_/ / / / /  /_____/  _/ // /_/ / /|  /  / /___/ /___   / _, _// __/
/_/    \__, /\____/_/ /_/           /___/\____/_/ |_/   \____/\____/  /_/ |_|/____/
      /____/""",
                           exit_msg = 'Leaving ION shell, shutting down container.')

    ipshell('Pyon - ION R2 CC interactive IPython shell. Type ionhelp() for help')

# From http://stackoverflow.com/questions/6037503/python-unflatten-dict/6037657#6037657
def unflatten(dictionary):
    resultDict = dict()
    for key, value in dictionary.iteritems():
        parts = key.split(".")
        d = resultDict
        for part in parts[:-1]:
            if part not in d:
                d[part] = dict()
            d = d[part]
        d[parts[-1]] = value
    return resultDict

def main(opts, *args, **kwargs):
    """
    Starts the capability container and processes arguments
    """

    def prepare_container():
        import threading
        threading.current_thread().name = "CC-Main"

        # SIDE EFFECT: The import of pyon.public triggers many module initializers:
        # pyon.core.bootstrap (Config load, logging setup), etc.
        from pyon.public import Container, CFG
        from pyon.util.containers import dict_merge
        from pyon.util.config import Config

        # See if sysname was provided
        if opts.sysname:
            from pyon.core import bootstrap
            bootstrap.set_sys_name(opts.sysname)
        else:
            if CFG.system.testing:
                if CFG.system.testing_sysname:
                    from pyon.core import bootstrap
                    bootstrap.set_sys_name(CFG.system.testing.testing_sysname)



        # Check if user opted to override logging config
        # Requires re-initializing logging
        if opts.logcfg:
            from pyon.util.config import LOGGING_CFG, logging_conf_paths, read_logging_config, initialize_logging
            import ast
            # Dict of config values
            if '{' in opts.logcfg:
                try:
                    eval_value = ast.literal_eval(opts.logcfg)
                except ValueError:
                    raise Exception("Value error in logcfg arg '%s'" % opts.logcfg)
                dict_merge(LOGGING_CFG, eval_value)
                initialize_logging()
            # YAML file containing config values
            else:
                logging_conf_paths.append(opts.logcfg)
                read_logging_config()
                initialize_logging()

        # Set that system is not testing. We are running as standalone container
        dict_merge(CFG, {'system':{'testing':False}}, True)

        # Also set the immediate flag, but only if specified - it is an override
        if opts.immediate:
            dict_merge(CFG, {'system':{'immediate':True}}, True)

        # Load any additional config paths and merge them into main config
        if len(opts.config):
            ipython_cfg = Config(opts.config)
            dict_merge(CFG, ipython_cfg.data, True)

        # Create the container instance
        container = Container(*args, **kwargs)

        return container

    def start_container(container):
        """
        Start container and all internal managers. Returns when ready.
        """
        container.start()


    def do_work(container):
        """
        Performs initial startup actions with the container as requested in arguments.
        Then remains in container shell or infinite wait until container stops.
        Returns when container should stop. Raises an exception if anything failed.
        """
        if opts.proc:
            # Run a one-off process (with the -x argument)
            mod, proc = opts.proc.rsplit('.', 1)
            print "Starting process %s" % opts.proc
            container.spawn_process(proc, mod, proc, config={'process':{'type':'immediate'}})
            # And end
            return

        if opts.rel:
            # Start a rel file
            start_ok = container.start_rel_from_url(opts.rel)
            if not start_ok:
                raise Exception("Cannot start deploy file '%s'" % opts.rel)

        if opts.mx:
            container.spawn_process("ContainerUI", "ion.core.containerui", "ContainerUI")
            print "Container UI started ... listening on http://localhost:8080"

        if opts.signalparent:
            import os
            import signal
            print 'Signal parent pid %d that pycc pid %d service start process is complete...' % (os.getppid(), os.getpid())
            os.kill(os.getppid(), signal.SIGUSR1)

            def is_parent_gone():
                while os.getppid() != 1:
                    gevent.sleep(1)
                print 'Now I am an orphan ... notifying serve_forever to stop'
                os.kill(os.getpid(), signal.SIGINT)
            import gevent
            ipg =gevent.spawn(is_parent_gone)
            from pyon.util.containers import dict_merge
            from pyon.public import CFG
            dict_merge(CFG, {'system':{'watch_parent': ipg}}, True)
        if not opts.noshell and not opts.daemon:
            # Keep container running while there is an interactive shell
            from pyon.container.shell_api import get_shell_api
            setup_ipython(get_shell_api(container))
        else:
            # Keep container running until process terminated
            container.serve_forever()

    def stop_container(container):
        try:
            if container:
                container.stop()
            return True
        except Exception as ex:
            # We want to make sure to get out here alive
            print "CONTAINER STOP ERROR"
            traceback.print_exc()
            return False

    # ----------------------------------------------------------------------------------
    # Container life cycle

    container = None
    try:
        container = prepare_container()

        start_container(container)
    except Exception as ex:
        print "===== CONTAINER START ERROR -- FAIL ====="
        traceback.print_exc()
        stop_container(container)
        sys.exit(1)

    try:
        do_work(container)
    except Exception as ex:
        stop_container(container)
        print "===== CONTAINER PROCESS START ERROR -- ABORTING ====="
        print ex
        sys.exit(1)

    # Assumption: stop is so robust, it does not fail even if it was only partially started
    stop_ok = stop_container(container)
    if not stop_ok:
        sys.exit(1)


def parse_args(tokens):
    """ Exploit yaml's spectacular type inference (and ensure consistency with config files) """
    args, kwargs = [], {}
    for token in tokens:
        token = token.lstrip('-')
        if '=' in token:
            key,val = token.split('=', 1)
            ipython_cfg = unflatten({key: yaml.load(val)})
            kwargs.update(ipython_cfg)
        else:
            args.append(yaml.load(token))

    return args, kwargs

def entry():
    #proc_types = PyonThreadManager.type_callables.keys()

    # NOTE: Resist the temptation to add other parameters here! Most container config options
    # should be in the config file (pyon.yml), which can also be specified on the command-line via the extra args

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-s', '--sysname', type=str, help='System name')
    parser.add_argument('-d', '--daemon', action='store_true')
    parser.add_argument('-n', '--noshell', action='store_true')
    parser.add_argument('-m', '--mx', action='store_true', help='Start a management web UI')
    parser.add_argument('-r', '--rel', type=str, help='Path to a rel file to launch.')
    parser.add_argument('-l', '--logcfg', type=str, help='Path to logging configuration file.')
    parser.add_argument('-x', '--proc', type=str, help='Qualified name of process to start and then exit.')
    parser.add_argument('-i', '--immediate', action='store_true', help='Will exit the container if the only procs started are immediate proc types. Sets CFG system.immediate flag.')
    parser.add_argument('-p', '--pidfile', type=str, help='PID file to use when --daemon specified. Defaults to cc-<rand>.pid')
    parser.add_argument('-sp', '--signalparent', action='store_true', help='Signal parent process after service start up complete')
    parser.add_argument('-c', '--config', action='append', type=str, help='Additional config files to load.', default=[])
    parser.add_argument('-v', '--version', action='version', version='pyon v%s' % (version))
    opts, extra = parser.parse_known_args()
    args, kwargs = parse_args(extra)

    if opts.daemon:
        # TODO: The daemonizing code may need to be moved inside the Container class (so it happens per-process)
        from daemon import DaemonContext
        from lockfile import FileLock

        #logg = open('hi.txt', 'w+')
        #slogg = open('hi2.txt', 'w+')

        # TODO: May need to generate a pidfile based on some parameter or cc name
        pidfile = opts.pidfile or 'cc-%s.pid' % str(uuid4())[0:4]
        with DaemonContext(pidfile=FileLock(pidfile)):#, stdout=logg, stderr=slogg):
            print "Starting ION CC ... deamon=True, opts=%s" % str(opts)
            main(opts, *args, **kwargs)
    else:
        print "Starting ION CC ... deamon=False, opts=%s" % str(opts)
        main(opts, *args, **kwargs)

if __name__ == '__main__':
    entry()
