# Always monkey-patch as the very first thing
from gevent import monkey; monkey.patch_all()

# If we're running from a subdirectory of the code (in source mode, not egg),
# change dir to the root directory for easier debugging and unit test launching.
import os
cwd, path = os.getcwd(), os.path.realpath(__file__)
base_path = os.path.dirname(path)
if '.egg' not in cwd:
    while not os.path.exists('.anode_root_marker'):
        os.chdir('..')

