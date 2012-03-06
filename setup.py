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

version = '0.1.0'

setup(  name = 'pyon',
        version = version,
        description = 'OOI ION Python Capability Container and Core Modules',
        url = 'https://github.com/ooici/pyon',
        download_url = 'http://ooici.net/releases',
        license = 'Apache 2.0',
        author = 'Adam R. Smith',
        author_email = 'a2smith@ucsd.edu',
        keywords = ['ooici','ioncore', 'pyon'],
        packages = find_packages(),
        entry_points = {
            'console_scripts' : [
                'pycc=scripts.pycc:entry',
                'control_cc=scripts.control_cc:main',
                'generate_interfaces=scripts.generate_interfaces:main',
                'json_report=scripts.json_report:main',
                'clear_couch=pyon.datastore.clear_couch_util:main',
                ]
            },
        dependency_links = [
            'http://ooici.net/releases'
        ],
        test_suite = 'pyon',
        install_requires = [
            # Patched greenlet to work on ARMS
            'greenlet==0.3.1-p1',
            'gevent==0.13.6',
            'simplejson==2.1.6',
            'msgpack-python==0.1.9',
            'setproctitle==1.1.2',
            'pyyaml==3.10',
            'pika==0.9.5',
            'httplib2>=0.7.2',
            'pyzmq==2.1.7',
            'gevent_zeromq==0.2.0',
            'zope.interface',
            'couchdb==0.8',
            # 'lockfile==0.9.1',
            'python-daemon==1.6',
            'M2Crypto==0.21.1-pl1',
            'coverage==3.5',
            'nose==1.1.2',
            'ipython==0.11',
            'readline==6.2.1',
            'mock',
            'ndg-xacml==0.4.0',
            'h5py==2.0.1', # see: http://www.hdfgroup.org/HDF5/release/obtain5.html

            # DM related dependencies for 'tables'
            # 'numpy==1.6.1',
            # 'numexpr==1.4.2',
            # 'cython==0.14.1',
            # 'tables==2.3',
        ],
     )
