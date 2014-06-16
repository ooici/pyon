#!/usr/bin/env python

# "manhole" entry point, friendlier ipython startup to remote container

__author__ = 'Dave Foster <dfoster@asascience.com>'

def main():
    import sys, os, re, errno, json, socket
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

            def legal_manhole_file(f):
                """
                Helper method to check if a process exists and is likely a manhole-able container.

                @return True/False if is a likely container.
                """
                mh_pid = int(r.search(f).group(1))
                try:
                    os.getpgid(mh_pid)
                except OSError as e:
                    if e.errno == errno.ESRCH:
                        return False
                    raise   # unexpected, just re-raise

                # the pid seems legal, now check status of sockets - the pid may be reused
                with open(f) as ff:
                    mh_doc = json.load(ff)

                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    s.bind((mh_doc['ip'], mh_doc['shell_port']))
                except socket.error as e:
                    if e.errno == errno.EADDRINUSE:
                        return True
                    raise   # unexpected, re-raise
                finally:
                    s.close()

                return False

            # try to see if these are active processes
            legal_mh_files = filter(legal_manhole_file, mh_files)

            if len(legal_mh_files) > 1:
                print >>sys.stderr, "Multiple legal manhole files detected, specify it manually:", legal_mh_files
                sys.exit(1)

            # we found a single legal file, use it
            mh_file = legal_mh_files[0]

            # perform cleanup of stale files
            dead_mh_files = [x for x in mh_files if x not in legal_mh_files]
            for df in dead_mh_files:
                print >>sys.stderr, "Cleaning up stale manhole file", df
                os.unlink(df)

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
