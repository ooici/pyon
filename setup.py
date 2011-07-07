#!/usr/bin/env python

try:
    from setuptools import setup, find_packages
except ImportError:
    from distutils.core import setup

version = '0.1'

setup(  name = 'ioncore_r2',
        version = version,
        description = 'OOI ION Python Capability Container and Core Modules',
        url = 'https://github.com/ooici/ioncore-python-r2',
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
            'greenlet==0.3.1',
            'gevent==0.13.6',
            'simplejson==2.1.6',
            'msgpack-python==0.1.9',
            'kombu==1.1.6',
            'pylibrabbitmq==0.3.0',
            'setproctitle=1.1.2'
        ],
     )
