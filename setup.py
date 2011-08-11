#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

import os
import sys

# Add /usr/local/include to the path for macs, fixes easy_install for several packages (like gevent and pyyaml)
if sys.platform == 'darwin':
    os.environ['C_INCLUDE_PATH'] = '/usr/local/include'

version = '0.1'

setup(  name = 'anode',
        version = version,
        description = 'OOI ION Python Capability Container and Core Modules',
        url = 'https://github.com/ooici/anode',
        download_url = 'http://ooici.net/releases',
        license = 'Apache 2.0',
        author = 'Adam R. Smith',
        author_email = 'a2smith@ucsd.edu',
        keywords = ['ooici','ioncore'],
        dependency_links = [
            'http://ooici.net/releases'
        ],
        test_suite = 'ion',
        install_requires = [
            'cython==0.14.1',
            'greenlet==0.3.1',
            'gevent==0.13.6',
            'simplejson==2.1.6',
            'msgpack-python==0.1.9',
            'setproctitle==1.1.2',
            'pyyaml==3.10',
            'pika==0.9.5',
            'httplib2==0.7.1',
            'pyzmq==2.1.7',
            'gevent_zeromq==0.2.0',
            'HTTP4Store==0.3.1'
        ],
     )
