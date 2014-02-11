#!/usr/bin/env python

'''
@author Luke Campbell (Originally Dave Foster)
@file extern/pyon/pyon/util/breakpoint.py
@description Breakpoint utility
'''

import functools
import inspect
import traceback
import time
import sys

def breakpoint(scope=None, global_scope=None):
    from IPython.config.loader import Config
    ipy_config = Config()
    ipy_config.PromptManager.in_template = '><> '
    ipy_config.PromptManager.in2_template = '... '
    ipy_config.PromptManager.out_template = '--> '
    ipy_config.InteractiveShellEmbed.confirm_exit = False

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
    if scope is not None:
        from pyon.container.shell_api import get_shell_api
        from pyon.container.cc import Container
        locals().update(scope)
        locals().update({'bt':get_stack})
        if Container.instance:
            locals().update(get_shell_api(Container.instance))
    if global_scope is not None:
        globals().update(global_scope)


    from pyon.core.bootstrap import get_sys_name

    # Update namespace of interactive shell
    # TODO: Cleanup namespace even further
    # Now create an instance of the embeddable shell. The first argument is a
    # string with options exactly as you would type them if you were starting
    # IPython at the system command line. Any parameters you want to define for
    # configuration can thus be specified here.
    with patch("IPython.core.interactiveshell.InteractiveShell.init_virtualenv"):
        ipshell = InteractiveShellEmbed(config=ipy_config,
                banner1="Entering Breakpoint Shell",
            exit_msg = 'Returning...')

        stack = traceback.extract_stack(limit=2)
        message = 'File %s, line %s, in %s' % stack[0][:-1]

        ipshell('(%s) Breakpoint @ %s' % (get_sys_name(), message))


def debug_wrapper(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            from traceback import print_exc
            print_exc()
            raise
    return wrapper

def get_stack(message=None, stack_first_frame=1, max_frames=15):
    try:
        stack = inspect.stack()
        frame_num = stack_first_frame
        context = []
        while len(stack) > frame_num and frame_num < (max_frames + stack_first_frame):
            exec_line = "%s:%s:%s" % (stack[frame_num][1], stack[frame_num][2], stack[frame_num][3])
            context.insert(0, exec_line)
            if exec_line.endswith("_control_flow") or exec_line.endswith("load_ion") or exec_line.endswith("spawn_process")\
                or exec_line.endswith(":main") or exec_line.endswith(":dispatch_request"):
                break
            frame_num += 1
        stack_str = "\n ".join(context)
        if message:
            stack_str = message + "\n" + stack_str
        return stack_str
    except Exception as ex:
        stack_str = "ERROR: " + str(ex)
        if message:
            stack_str = message + "\n" + stack_str
        return stack_str

_global_profile_t0 = time.time()
_global_profile_level = 0

def time_profile(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        global _global_profile_t0
        global _global_profile_level
        indent = ''.join(['    ' for i in xrange(_global_profile_level)])
        t0 = time.time()
        sys.stdout.write('%s%s\n' % (indent, func.__name__))
        _global_profile_level += 1
        retval = func(*args, **kwargs)
        _global_profile_level -= 1
        sys.stdout.write('%sExecution Time: %s\n%sTotal Time: %s\n' % (indent, time.time() - t0, indent, time.time() - _global_profile_t0))
        return retval
    return wrapper

class TimeIt:
    def __init__(self, message):
        self.message = message

    def __enter__(self):
        global _global_profile_t0
        global _global_profile_level
        self.t0 = time.time()
        indent = ''.join(['    ' for i in xrange(_global_profile_level)])
        sys.stdout.write('%s%s\n' % (indent, self.message))

        _global_profile_level += 1

    def __exit__(self, type, value, traceback):
        global _global_profile_t0
        global _global_profile_level

        _global_profile_level -= 1
        indent = ''.join(['    ' for i in xrange(_global_profile_level)])
        sys.stdout.write('%sExecution Time: %s\n%sTotal Time: %s\n' % (indent, time.time() - self.t0, indent, time.time() - _global_profile_t0))
        
