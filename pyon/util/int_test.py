#!/usr/bin/env python

"""Integration test base class and utils"""

from contextlib import contextmanager
import unittest
import re

from pyon.container.cc import Container
from pyon.core.bootstrap import bootstrap_pyon
from pyon.service.service import services_by_name, load_service_mods
from mock import patch

# Make this call more deterministic in time.
bootstrap_pyon()

scanned_services = False

class IonIntegrationTestCase(unittest.TestCase):
    """
    Base test class to allow operations such as starting the container
    TODO: Integrate with IonUnitTestCase
    """

    def run(self, result=None):
        unittest.TestCase.run(self, result)

    @contextmanager
    def start_container(self):
        """
        Context Manager for container in tests.
        To use:
        with self.start_container() as cc:
            # your tests in here
        # container stopped here
        """
        self._start_container()
        try:
            yield self.container
        finally:
            self._stop_container()

    def _start_container(self):
        self.container = None
        self.addCleanup(self._stop_container)
        self.container = Container()
        self.container.start()

    def _stop_container(self):
        if self.container:
            self.container.stop()
            self.container = None

    def _turn_on_queue_auto_delete(self):
        patcher = patch('pyon.net.channel.RecvChannel._queue_auto_delete', True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _start_service(self, servicename, servicecls=None, config=None):
        #svc_interface = services_by_name[servicename]
        #global scanned_services
        #if not scanned_services:
        #    load_service_mods("ion")
        #    scanned_services = True
        #match = re.match(r'interface\.(.+)\.i(\w+)', m)
        #if match:
        #    svc_mod = "ion.%s.%s" % (match.group(1), match.group(2))
        if servicecls:
            mod, cls = servicecls.rsplit('.', 1)
            self.container.spawn_process(servicename, mod, cls, config)


    def _spawn_process(self, procname, proctype=None, config=None):
        pass
