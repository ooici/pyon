#!/usr/bin/env python
'''
@author Luke Campbell <LCampbell@ASAScience.com>
@date Wed Aug  8 14:19:24 EDT 2012
@file pyon/ion/test/test_transform.py
'''

from pyon.util.int_test import IonIntegrationTestCase
from pyon.ion.transforma import TransformBase
from nose.plugins.attrib import attr

@attr('INT',group='dm')
class TestTrasforms(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()
    def test_stats(self):
        self.container.spawn_process('test','pyon.ion.transforma','TransformBase', {}, 'test_transform')
        test_transform = self.container.proc_manager.procs['test_transform']
        test_transform._stats['hits'] = 100

        retval = TransformBase.stats('test_transform')
        self.assertEquals(retval,{'hits':100})


