#!/usr/bin/env python


import fnmatch
import os
import sys
import argparse

from pyon.core.interfaces.object_model_generator import ObjectModelGenerator
from pyon.util.containers import get_default_sysname
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr


class Object(object):
    pass

@attr('UNIT',group='coi')
class ObjectModelGenerateTest(IonIntegrationTestCase):


    def setUp(self):
        self.opts = Object()
        self.opts.system_name = get_default_sysname()
        self.opts.force = True
        self.opts.objectdoc = True
        self.opts.read_from_yaml_file = True
        self.opts.dryrun = True

        self.model_object = ObjectModelGenerator(system_name=self.opts.system_name, read_from_yaml_file=self.opts.read_from_yaml_file)

    def test_object_gen(self):
        try:
            self.model_object.generate(self.opts)
        except:
            self.fail("object_model_generator failed")
