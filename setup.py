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

version = '2.1.0'

setup(  name = 'pyon',
        version = version,
        description = 'OOI Python Capability Container and Core Modules',
        url = 'https://github.com/ooici/pyon',
        download_url = 'http://sddevrepo.oceanobservatories.org/releases/',
        license = 'BSD',
        author = 'Ocean Observatories Initiative',
        author_email = 'contactooici@oceanobservatories.org',
        keywords = ['ooi','ooici','pyon','ooinet'],
        packages = find_packages(),
        entry_points = {
             'nose.plugins.0.10': [
                 'stats_plugin=pyon.util.container_stats_plugin:TestStats',
                 'pycc_plugin=pyon.util.pycc_plugin:PYCC',
                 'gevent_block_plugin=pyon.util.gevent_block_plugin:GEVENT_BLOCK',
                 'timer_plugin=pyon.util.timer_plugin:TestTimer',
                 'queueblame=pyon.util.queueblame_plugin:QueueBlame',
                 'capture=pyon.util.capture_plugin:PyccCapture',
                 'insulate=pyon.util.insulate:Insulate',
                 'insulateslave=pyon.util.insulate:InsulateSlave',
                 'gevent_profiler=pyon.util.nose_gevent_profiler:TestGeventProfiler',
                 'greenletleak=pyon.util.greenlet_plugin:GreenletLeak',
                 'processleak=pyon.util.processblame_plugin:ProcessLeak',
                 'memprofile=pyon.util.memory_plugin:MemProfile'
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
            'http://sddevrepo.oceanobservatories.org/releases/',
            'https://github.com/ooici/gevent-profiler/tarball/master#egg=python-gevent-profiler',
            'https://github.com/ooici/utilities/tarball/v2013.06.11#egg=utilities-2013.06.11',
        ],
        test_suite = 'pyon',
        package_data = {'': ['*.xml']},
        install_requires = [
            'utilities',
            'greenlet==0.4.0',
            # Don't put == version on gevent
            'gevent',
            'simplejson',
            'msgpack-python==0.1.13',
            'pika==0.9.5',
            'httplib2>=0.7.2',
            'pyzmq==2.2.0',
            'gevent_zeromq==0.2.5',
            'zope.interface',
            'couchdb==0.9',
            'psycopg2==2.5.3',
            # 'lockfile==0.9.1',
            'python-daemon==1.6',
            'M2Crypto==0.21.1-pl1',
            # Don't put == version on coverage.
            'coverage',
            'nose==1.1.2',
            'ipython==0.13.0',
            'antlr_python_runtime==3.1.3',
            'readline',
            'mock==0.8',
            'ndg-xacml==0.5.1',
            'python-gevent-profiler',
            'lxml==2.3.4',
            'requests',
            'psutil==1.0.1'
        ],
     )
