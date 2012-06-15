# -------------------------------------------------------------------------
# PYON (C) OCEAN OBSERVATORIES INITIATIVE
# Initial package static initialization
# -------------------------------------------------------------------------

# @WARN: GLOBAL STATE, STATIC CODE

#print "pyon: pyon/__init__ static initialization..."

# -------------------------------------------------------------------------
# Always monkey-patch as the very first thing (see gevent)

# Make monkey-patching work with debuggers and unittests by detecting already-imported modules
# TODO: Move this into a module that third parties can use
import sys
if 'pydevd' in sys.modules or 'unittest' in sys.modules or 'nose' in sys.modules:
    # The order matters
    monkey_list = ['os', 'time', 'thread', 'socket', 'select', 'ssl', 'httplib']
    for monkey in monkey_list:
        if monkey in sys.modules:
            mod = sys.modules[monkey]

            # Reload so the non-monkeypatched versions in the debugger don't get patched
            #reload(mod)
            del sys.modules[monkey]

    
    unmonkey = {'threading': ['_allocate_lock', '_get_ident']}
    unmonkey_backup = {}
    for modname,feats in unmonkey.iteritems():
        mod = __import__(modname)
        unmonkey_backup[modname] = dict((feat, getattr(mod, feat)) for feat in feats)

    from gevent import monkey; monkey.patch_all()
    
    for modname,feats_backup in unmonkey_backup.iteritems():
        mod = __import__(modname)
        for name,impl in feats_backup.iteritems():
            setattr(mod, name, impl)
else:
    from gevent import monkey; monkey.patch_all()


# -------------------------------------------------------------------------
# CONSTANTS FOR PYON CODE
# CHANGE HERE BEFORE IMPORTING ANY FURTHER PYON CODE TO OVERRIDE
DEFAULT_LOGGING_PATHS = ['res/config/logging.yml', 'res/config/logging.local.yml']
DEFAULT_CONFIG_PATHS = ['res/config/pyon.yml']
DEFAULT_LOCAL_CONFIG_PATHS = ['res/config/pyon.local.yml']

# -------------------------------------------------------------------------
# If we're running from a subdirectory of the code (in source mode, not egg),
# change dir to the root directory for easier debugging and unit test launching.
### Note: commented out because this prevents start of pycc from a different repo.
'''
import os
cwd, path = os.getcwd(), os.path.realpath(__file__)
base_path = os.path.dirname(path)
if '.egg' not in cwd:
    while not os.path.exists('.pyon_root_marker'):
        os.chdir('..')
'''
