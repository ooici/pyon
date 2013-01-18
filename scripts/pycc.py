#!/usr/bin/env python

"""Python Capability Container start script"""

__author__ = 'Adam R. Smith, Michael Meisinger'
__license__ = 'Apache 2.0'

import argparse
import ast
from copy import deepcopy
import sys
import traceback
from uuid import uuid4

from script_util import parse_args
from pyon.core import log as logutil
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

# See below __main__ for STEP 1

# PYCC STEP 2
def entry():
    """
    Parses arguments and deamonizes process if requested
    """

    # NOTE: Resist the temptation to add other parameters here! Most container config options
    # should be in the config file (pyon.yml), which can also be specified on the command-line via the extra args

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('-c', '--config', type=str, help='Additional config files to load or dict config content.', default=[])
    parser.add_argument('-D', '--config_from_directory', action='store_true')
    parser.add_argument('-d', '--daemon', action='store_true')
    parser.add_argument('-fc', '--force_clean', action='store_true', help='Force clean system datastores before starting the container')
    parser.add_argument('-bc', '--broker_clean', action='store_true', help='Force clean broker of queues/exchanges belonging to sysname')
    parser.add_argument('-i', '--immediate', action='store_true', help='Will exit the container if the only procs started are immediate proc types. Sets CFG system.immediate flag.')
    parser.add_argument('-l', '--logcfg', type=str, help='Path to logging configuration file or dict config content.')
    parser.add_argument('-m', '--mx', action='store_true', help='Start a management web UI')
    parser.add_argument('-n', '--noshell', action='store_true')
    parser.add_argument('-o', '--nomanhole', action='store_true', help="Do not start a shell or a remote-able manhole shell. Implies -n")
    parser.add_argument('-p', '--pidfile', type=str, help='PID file to use when --daemon specified. Defaults to cc-<rand>.pid')
    parser.add_argument('-r', '--rel', type=str, help='Path to a rel file to launch.')
    parser.add_argument('-s', '--sysname', type=str, help='System name')
    parser.add_argument('-sp', '--signalparent', action='store_true', help='Signal parent process after service start up complete')
    parser.add_argument('-v', '--version', action='version', version='pyon v%s' % (version))
    parser.add_argument('-x', '--proc', type=str, help='Qualified name of process to start and then exit.')
    parser.add_argument('-X', '--no_container', action='store_true', help='Perform pre-initialization steps and stop before starting a container.')
    opts, extra = parser.parse_known_args()
    args, kwargs = parse_args(extra)

    print "pycc: ION Container starter with command line options:" , str(opts)

    # -o or --nomanhole implies --noshell
    if opts.nomanhole:
        opts.noshell = True

    if opts.daemon:
        # TODO: The daemonizing code may need to be moved inside the Container class (so it happens per-process)
        from daemon import DaemonContext
        from lockfile import FileLock

        print "pycc: Deamonize process"
        # TODO: May need to generate a pidfile based on some parameter or cc name
        pidfile = opts.pidfile or 'cc-%s.pid' % str(uuid4())[0:4]
        with DaemonContext(pidfile=FileLock(pidfile)):#, stdout=logg, stderr=slogg):
            main(opts, *args, **kwargs)
    else:
        main(opts, *args, **kwargs)

# PYCC STEP 3
def main(opts, *args, **kwargs):
    """
    Processes arguments and starts the capability container.
    """
    def prepare_logging():
    # Load logging override config if provided. Supports variants literal and path.
        logging_config_override = None
        if opts.logcfg:
            if '{' in opts.logcfg:
                # Variant 1: Value is dict of config values
                try:
                    eval_value = ast.literal_eval(opts.logcfg)
                    logging_config_override = eval_value
                except ValueError:
                    raise Exception("Value error in logcfg arg '%s'" % opts.logcfg)
            else:
                # Variant 2: Value is path to YAML file containing config values
                logutil.DEFAULT_LOGGING_PATHS.append(opts.logcfg)
        logutil.configure_logging(logutil.DEFAULT_LOGGING_PATHS, logging_config_override=logging_config_override)

    def prepare_container():
        """
        Walks through pyon initialization in a deterministic way and initializes Container.
        In particular make sure configuration is loaded in correct order and
        pycc startup arguments are considered.
        """
        import threading
        threading.current_thread().name = "CC-Main"

        # SIDE EFFECT: The import triggers static initializers: Monkey patching, setting pyon defaults
        import pyon

        from pyon.core import bootstrap, config

        # Set global testing flag to False. We are running as capability container. This is NO TEST.
        bootstrap.testing = False

        # Set sysname if provided in startup argument
        if opts.sysname:
            bootstrap.set_sys_name(opts.sysname)
        # Trigger any initializing default logic in get_sys_name
        bootstrap.get_sys_name()

        command_line_config = kwargs

        # This holds the minimal configuration used to bootstrap pycc and pyon and connect to datastores.
        bootstrap_config = None

        # This holds the new CFG object for pyon. Build it up in proper sequence and conditions.
        pyon_config = config.read_standard_configuration()      # Initial pyon.yml + pyon.local.yml

        # Load config override if provided. Supports variants literal and list of paths
        config_override = None
        if opts.config:
            if '{' in opts.config:
                # Variant 1: Dict of config values
                try:
                    eval_value = ast.literal_eval(opts.config)
                    config_override = eval_value
                except ValueError:
                    raise Exception("Value error in config arg '%s'" % opts.config)
            else:
                # Variant 2: List of paths
                from pyon.util.config import Config
                config_override = Config([opts.config]).data

        # Determine bootstrap_config
        if opts.config_from_directory:
            # Load minimal bootstrap config if option "config_from_directory"
            bootstrap_config = config.read_local_configuration(['res/config/pyon_min_boot.yml'])
            config.apply_local_configuration(bootstrap_config, pyon.DEFAULT_LOCAL_CONFIG_PATHS)
            config.apply_configuration(bootstrap_config, config_override)
            config.apply_configuration(bootstrap_config, command_line_config)
            print "pycc: config_from_directory=True. Minimal bootstrap configuration:", bootstrap_config
        else:
            # Otherwise: Set to standard set of local config files plus command line overrides
            bootstrap_config = deepcopy(pyon_config)
            config.apply_configuration(bootstrap_config, config_override)
            config.apply_configuration(bootstrap_config, command_line_config)

        # Override sysname from config file or command line
        if not opts.sysname and bootstrap_config.get_safe("system.name", None):
            new_sysname = bootstrap_config.get_safe("system.name")
            bootstrap.set_sys_name(new_sysname)

        # Delete sysname datastores if option "force_clean" is set
        if opts.force_clean:
            from pyon.datastore import clear_couch_util
            print "pycc: force_clean=True. DROP DATASTORES for sysname=%s" % bootstrap.get_sys_name()
            clear_couch_util.clear_couch(bootstrap_config, prefix=bootstrap.get_sys_name())
            pyon_config.container.filesystem.force_clean=True

        from pyon.core.interfaces.interfaces import InterfaceAdmin
        iadm = InterfaceAdmin(bootstrap.get_sys_name(), config=bootstrap_config)

        # If auto_bootstrap, load config and interfaces into directory
        # Note: this is idempotent and will not alter anything if this is not the first container to run
        if bootstrap_config.system.auto_bootstrap:
            print "pycc: auto_bootstrap=True."
            stored_config = deepcopy(pyon_config)
            config.apply_configuration(stored_config, config_override)
            config.apply_configuration(stored_config, command_line_config)
            iadm.create_core_datastores()
            iadm.store_config(stored_config)

        # Determine the final pyon_config
        # - Start from standard config already set (pyon.yml + local YML files)
        # - Optionally load config from directory
        if opts.config_from_directory:
            config.apply_remote_config(bootstrap_cfg=bootstrap_config, system_cfg=pyon_config)
            config.apply_local_configuration(pyon_config, pyon.DEFAULT_LOCAL_CONFIG_PATHS)     # apply pyon.local.yml again over top
        # - Last apply any separate command line config overrides
        config.apply_configuration(pyon_config, config_override)
        config.apply_configuration(pyon_config, command_line_config)

        # Also set the immediate flag, but only if specified - it is an override
        if opts.immediate:
            from pyon.util.containers import dict_merge
            dict_merge(pyon_config, {'system':{'immediate':True}}, True)

        # Bootstrap pyon's core. Load configuration etc.
        bootstrap.bootstrap_pyon(pyon_cfg=pyon_config)

        # Delete any queues/exchanges owned by sysname if option "broker_clean" is set
        if opts.broker_clean:
            print "pycc: broker_clean=True, sysname:", bootstrap.get_sys_name()

            # build connect str
            connect_str = "-q -H %s -P 55672 -u %s -p %s -V %s" % (pyon_config.get_safe('server.amqp_priv.host', pyon_config.get_safe('server.amqp.host', 'localhost')),
                                                                   pyon_config.get_safe('container.exchange.management.username', 'guest'),
                                                                   pyon_config.get_safe('container.exchange.management.password', 'guest'),
                                                                   '/')

            from putil.rabbithelper import clean_by_sysname
            deleted_exchanges, deleted_queues = clean_by_sysname(connect_str, bootstrap.get_sys_name())
            print "      exchanges deleted (%s): %s" % (len(deleted_exchanges), ",".join(deleted_exchanges))
            print "         queues deleted (%s): %s" % (len(deleted_queues), ",".join(deleted_queues))

        # Auto-bootstrap interfaces
        if bootstrap_config.system.auto_bootstrap:
            iadm.store_interfaces(idempotent=True)

        iadm.close()

        if opts.no_container:
            print "pycc: no_container=True. Stopping here."
            return None

        # Create the container instance
        from pyon.container.cc import Container
        container = Container(*args, **command_line_config)

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
            print "pycc: Starting process %s" % opts.proc
            container.spawn_process(proc, mod, proc, config={'process':{'type':'immediate'}})
            # And end
            return

        if opts.rel:
            # Start a rel file
            start_ok = container.start_rel_from_url(opts.rel)
            if not start_ok:
                raise Exception("Cannot start deploy file '%s'" % opts.rel)

        if opts.mx:
            from pyon.public import CFG
            port = CFG.get_safe('container.flask_webapp.port',8080)
            container.spawn_process("ContainerUI", "ion.core.containerui", "ContainerUI")
            print "pycc: Container UI started ... listening on http://localhost:%s" % port

        if opts.signalparent:
            import os
            import signal
            print 'pycc: Signal parent pid %d that pycc pid %d service start process is complete...' % (os.getppid(), os.getpid())
            os.kill(os.getppid(), signal.SIGUSR1)

            def is_parent_gone():
                while os.getppid() != 1:
                    gevent.sleep(1)
                print 'pycc: Now I am an orphan ... notifying serve_forever to stop'
                os.kill(os.getpid(), signal.SIGINT)
            import gevent
            ipg = gevent.spawn(is_parent_gone)

            container.gl_parent_watch = ipg

        if not opts.noshell and not opts.daemon:
            # Keep container running while there is an interactive shell
            from pyon.container.shell_api import get_shell_api
            setup_ipython_shell(get_shell_api(container))
        elif not opts.nomanhole:
            from pyon.container.shell_api import get_shell_api
            setup_ipython_embed(get_shell_api(container))
        else:
            container.serve_forever()

    def stop_container(container):
        try:
            if container:
                container.stop()
            return True
        except Exception as ex:
            # We want to make sure to get out here alive
            print "pycc: CONTAINER STOP ERROR"
            traceback.print_exc()
            return False

    def setup_ipython_shell(shell_api=None):
        ipy_config = _setup_ipython_config()

        # monkeypatch the ipython inputhook to be gevent-friendly
        import gevent   # should be auto-monkey-patched by pyon already.
        import select
        import sys
        import os

        def stdin_ready():
            infds, outfds, erfds = select.select([sys.stdin], [], [], 0)
            if infds:
                return True
            else:
                return False

        def inputhook_gevent():
            try:
                while not stdin_ready():
                    gevent.sleep(0.05)
            except KeyboardInterrupt:
                pass

            return 0

        # install the gevent inputhook
        from IPython.lib.inputhook import inputhook_manager
        inputhook_manager.set_inputhook(inputhook_gevent)
        inputhook_manager._current_gui = 'gevent'

        # First import the embeddable shell class
        from IPython.frontend.terminal.embed import InteractiveShellEmbed
        from mock import patch

        # Update namespace of interactive shell
        # TODO: Cleanup namespace even further
        if shell_api is not None:
            locals().update(shell_api)

        # Now create an instance of the embeddable shell. The first argument is a
        # string with options exactly as you would type them if you were starting
        # IPython at the system command line. Any parameters you want to define for
        # configuration can thus be specified here.
        with patch("IPython.core.interactiveshell.InteractiveShell.init_virtualenv"):
            ipshell = InteractiveShellEmbed(config=ipy_config,
                banner1 =\
                """              ____                                ________  _   __   ____________   ____  ___
             / __ \__  ______  ____              /  _/ __ \/ | / /  / ____/ ____/  / __ \|__ \\
            / /_/ / / / / __ \/ __ \   ______    / // / / /  |/ /  / /   / /      / /_/ /__/ /
           / ____/ /_/ / /_/ / / / /  /_____/  _/ // /_/ / /|  /  / /___/ /___   / _, _// __/
          /_/    \__, /\____/_/ /_/           /___/\____/_/ |_/   \____/\____/  /_/ |_|/____/
                /____/""",
                exit_msg = 'Leaving ION shell, shutting down container.')

            ipshell('Pyon (PID: %s) - ION R2 CC interactive IPython shell. Type ionhelp() for help' % os.getpid())

    def setup_ipython_embed(shell_api=None):
        from gevent_zeromq import monkey_patch
        monkey_patch()

        # patch in device:
        # gevent-zeromq does not support devices, which block in the C layer.
        # we need to support the "heartbeat" which is a simple bounceback, so we
        # simulate it using the following method.
        import zmq
        orig_device = zmq.device

        def device_patch(dev_type, insock, outsock, *args):
            if dev_type == zmq.FORWARDER:
                while True:
                    m = insock.recv()
                    outsock.send(m)
            else:
                orig_device.device(dev_type, insock, outsock, *args)

        zmq.device = device_patch

        # patch in auto-completion support
        # added in https://github.com/ipython/ipython/commit/f4be28f06c2b23cd8e4a3653b9e84bde593e4c86
        # we effectively make the same patches via monkeypatching
        from IPython.core.interactiveshell import InteractiveShell
        from IPython.zmq.ipkernel import IPKernelApp
        old_start = IPKernelApp.start
        old_set_completer_frame = InteractiveShell.set_completer_frame

        def new_start(appself):
            # restore old set_completer_frame that gets no-op'd out in ZmqInteractiveShell.__init__
            bound_scf = old_set_completer_frame.__get__(appself.shell, InteractiveShell)
            appself.shell.set_completer_frame = bound_scf
            appself.shell.set_completer_frame()
            old_start(appself)

        IPKernelApp.start = new_start

        from IPython import embed_kernel
        ipy_config = _setup_ipython_config()

        # set specific manhole options
        import tempfile#, shutil
        from mock import patch
        temp_dir = tempfile.mkdtemp()
        ipy_config.Application.ipython_dir = temp_dir

        with patch("IPython.core.interactiveshell.InteractiveShell.init_virtualenv"):
            embed_kernel(local_ns=shell_api, config=ipy_config)      # blocks until INT

        # @TODO: race condition here versus ipython, this will leave junk in tmp dir
        #try:
        #    shutil.rmtree(temp_dir)
        #except shutil.Error:
        #    pass

    def _setup_ipython_config():
        from IPython.config.loader import Config
        ipy_config = Config()
        import os
        ipy_config.KernelApp.connection_file = os.path.join(os.path.abspath(os.curdir), "manhole-%s.json" % os.getpid())
        ipy_config.PromptManager.in_template = '><> '
        ipy_config.PromptManager.in2_template = '... '
        ipy_config.PromptManager.out_template = '--> '
        ipy_config.InteractiveShellEmbed.confirm_exit = False
        #ipy_config.Application.log_level = 10      # uncomment for debug level ipython logging

        return ipy_config

    # main() -----> ENTER
    # ----------------------------------------------------------------------------------
    # Container life cycle

    prepare_logging()
    container = None
    try:
        container = prepare_container()
        if container is None:
            sys.exit(0)

        start_container(container)
    except Exception as ex:
        print "pycc: ===== CONTAINER START ERROR -- FAIL ====="
        traceback.print_exc()
        stop_container(container)
        sys.exit(1)

    try:
        do_work(container)
    except Exception as ex:
        stop_container(container)
        print "pycc: ===== CONTAINER PROCESS START ERROR -- ABORTING ====="
        print ex
        sys.exit(1)

    # Assumption: stop is so robust, it does not fail even if it was only partially started
    stop_ok = stop_container(container)
    if not stop_ok:
        sys.exit(1)

# START HERE:
# PYCC STEP 1
if __name__ == '__main__':
    entry()
