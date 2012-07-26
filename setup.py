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

version = '0.1.8-dev'

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
             'nose.plugins.0.10': [
                 'pycc_plugin=pyon.util.pycc_plugin:PYCC',
                 'timer_plugin=pyon.util.timer_plugin:TestTimer',
                 'queueblame=pyon.util.queueblame_plugin:QueueBlame',
                 'capture=pyon.util.capture_plugin:PyccCapture',
                 'insulate=pyon.util.insulate:Insulate',
                 'insulateslave=pyon.util.insulate:InsulateSlave',
                 'gevent_profiler=pyon.util.nose_gevent_profiler:TestGeventProfiler'
             ],
            'console_scripts' : [
                'pycc=scripts.pycc:entry',
                'control_cc=scripts.control_cc:main',
                'generate_interfaces=scripts.generate_interfaces:main',
                'store_interfaces=scripts.store_interfaces:main',
                'json_report=scripts.json_report:main',
                'clear_couch=pyon.datastore.clear_couch_util:main',
                ]
            },
        dependency_links = [
            'http://ooici.net/releases',
            'https://github.com/ooici/gevent-profiler/tarball/master#egg=python-gevent-profiler'
        ],
        test_suite = 'pyon',
        package_data = {'': ['*.xml']},
        install_requires = [
            'greenlet==0.4.0',
            'gevent==0.13.7',
            'simplejson==2.1.6',
            'msgpack-python==0.1.13',
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
            'mock==0.8',
            'ndg-xacml==0.5.1',
            'h5py==2.0.1', # see: http://www.hdfgroup.org/HDF5/release/obtain5.html
            'python-gevent-profiler',
            'lxml==2.3.4', # Fails to compile on Linux ??!??
            'requests==0.13.3',

            # DM related dependencies for 'tables'
            # 'numpy==1.6.1',
            # 'numexpr==1.4.2',
            # 'cython==0.14.1',
            # 'tables==2.3',
        ],
     )
