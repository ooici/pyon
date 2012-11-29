#!/usr/bin/env python

# "manhole" entry point, friendlier ipython startup to remote container

__author__ = 'Dave Foster <dfoster@asascience.com>'
__license__ = 'Apache 2.0'

def main():
    import sys, os, re
    from pkg_resources import load_entry_point

    r = re.compile('manhole-(\d+).json')

    if len(sys.argv) == 2:
        mh_file = sys.argv[1]
    else:
        # find manhole file in local dir
        mh_files = [f for f in os.listdir(os.getcwd()) if r.search(f) is not None]
        if len(mh_files) == 0:
            print >>sys.stderr, "No manhole files detected, specify it manually"
            sys.exit(1)
        elif len(mh_files) > 1:
            print >>sys.stderr, "Multiple manhole files detected, specify it manually"
        else:
            mh_file = mh_files[0]

    if not os.access(mh_file, os.R_OK):
        print >>sys.stderr, "Manhole file (%s) does not exist" % mh_file
        sys.exit(1)

    mhpid = r.search(mh_file).group(1)

    # configure branding
    manhole_logo = """
 __   __  _______  __    _  __   __  _______  ___      _______ 
|  |_|  ||   _   ||  |  | ||  | |  ||       ||   |    |       |
|       ||  |_|  ||   |_| ||  |_|  ||   _   ||   |    |    ___|
|       ||       ||       ||       ||  | |  ||   |    |   |___ 
|       ||       ||  _    ||       ||  |_|  ||   |___ |    ___|
| ||_|| ||   _   || | |   ||   _   ||       ||       ||   |___ 
|_|   |_||__| |__||_|  |__||__| |__||_______||_______||_______|
"""

    # manipulate argv!
    sys.argv = [sys.argv[0], "console", "--existing", mh_file,
                "--PromptManager.in_template=>o> ",
                "--PromptManager.in2_template=... ",
                "--PromptManager.out_template=--> ",
                "--TerminalInteractiveShell.banner1=%s" % manhole_logo,
                "--TerminalInteractiveShell.banner2=ION Container Manhole, connected to %s\n" % mhpid]

    ipy_entry = load_entry_point('ipython', 'console_scripts', 'ipython')()
    sys.exit(ipy_entry)

if __name__ == '__main__':
    main()
