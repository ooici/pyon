#!/usr/bin/env python

# Entrypoint to start ipython with buildout path

__author__ = 'Michael Meisinger'
__license__ = 'Apache 2.0'

def main():
    import sys
    from pkg_resources import load_entry_point

    sys.exit(
       load_entry_point('ipython', 'console_scripts', 'ipython')()
    )

if __name__ == '__main__':
    main()
