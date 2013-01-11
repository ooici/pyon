#!/usr/bin/env python

from pyon.core.interfaces.message_object_generator import MessageObjectGenerator
from pyon.util.containers import get_default_sysname
from nose.plugins.attrib import attr
from pyon.util.unit_test import PyonTestCase


class Object(object):
    pass

@attr('UNIT',group='coi')
class MessageModelGenerateTest(PyonTestCase):

    def setUp(self):
        self.opts = Object()
        self.opts.system_name = get_default_sysname()
        self.opts.force = True
        self.opts.objectdoc = True
        self.opts.read_from_yaml_file = True
        self.opts.dryrun = True

        self.mog = MessageObjectGenerator(system_name=self.opts.system_name, read_from_yaml_file=self.opts.read_from_yaml_file)

    def test_object_gen(self):
        try:
            self.mog.generate(self.opts)
        except:
            self.fail("message_model_generator failed")