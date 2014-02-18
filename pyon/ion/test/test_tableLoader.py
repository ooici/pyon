"""
@author Abird
@brief Test cases for the tableloader, 
table loader is A Service to load data products in to postgres and geoserver from the resource registry
"""

import os
from pyon.util.breakpoint import breakpoint
from pyon.public import RT, OT, PRED, LCS, CFG
from ion.services.dm.inventory.dataset_management_service import DatasetManagementService
from interface.services.dm.idataset_management_service import DatasetManagementServiceClient
from pyon.core.bootstrap import IonObject
from pyon.core.exception import NotFound, Inconsistent, BadRequest
from pyon.ion.resource import PRED, RT, LCS, AS, LCE, lcstate
from pyon.util.unit_test import IonUnitTestCase
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr
import time
import psycopg2
import sys
import requests
import tableLoader
import sys
from gevent import server
from gevent.baseserver import _tcp_listener
from gevent import pywsgi
from gevent.monkey import patch_all; patch_all()
from pyon.util.breakpoint import breakpoint
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr
from pyon.public import PRED
from interface.services.dm.idataset_management_service import DatasetManagementServiceClient
from interface.services.dm.ipubsub_management_service import PubsubManagementServiceClient
from interface.services.sa.idata_product_management_service import DataProductManagementServiceClient
from ion.services.dm.inventory.dataset_management_service import DatasetManagementService
from coverage_model import SimplexCoverage, QuantityType, ArrayType, ConstantType, CategoryType
from ion.services.dm.utility.test.parameter_helper import ParameterHelper
from ion.services.dm.utility.granule_utils import time_series_domain
from ion.services.dm.test.test_dm_end_2_end import DatasetMonitor
from interface.objects import DataProduct
import unittest
import gevent
import numpy as np

from pyon.ion.tableLoader import resource_parser

'''
Resource Registry TESTS
'''


@attr('UNIT', group='eoi')
class TestTableLoader(IonUnitTestCase):

    def setUp(self):
        pass

    def test_add_fdt_layer(self):
        #add a layer and check that it exists
        rr_table_loader = resource_parser()
        rr_table_loader.reset()

        self.assertTrue(True)
        print ("done")


    @unittest.skip('working on')
    def test_remove_select_fdt_layer(self):
        print ("done")
        self.assertTrue(True)


    @unittest.skip('working on')
    def test_add_all_fdt(self):
        print ("done")
        self.assertTrue(True)


    @unittest.skip('working on')
    def test_remove_all_fdt(self):
        print ("done")
        self.assertTrue(True)

'''
GEOSERVER TESTS
'''
#class TestTableLoader_GeoServer(IonUnitTestCase):
'''
@unittest.skip('working on')
def test_add_geoserver_layer(self):
    print ("done")
    assertTrue(True)


@unittest.skip('working on')
def test_remove_select_geoserver_layer(self):
    print ("done")
    assertTrue(True)


@unittest.skip('working on')
def test_parse_rr_completely(self):
    print ("done")
    assertTrue(True)


@unittest.skip('working on')
def test_remove_all_layers(self):
    print ("done")
    assertTrue(True)
'''

@attr('INT', group='eoi')
class DatasetLoadTest(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()
        self.container.start_rel_from_url('res/deploy/r2deploy.yml')
        self.dataset_management      = DatasetManagementServiceClient()
        self.data_product_management = DataProductManagementServiceClient()
        self.pubsub_management       = PubsubManagementServiceClient()
        self.resource_registry       = self.container.resource_registry

    def test_create_dataset(self):
        
        ph = ParameterHelper(self.dataset_management, self.addCleanup)
        pdict_id = ph.create_extended_parsed()

        stream_def_id = self.pubsub_management.create_stream_definition('example', parameter_dictionary_id=pdict_id)
        self.addCleanup(self.pubsub_management.delete_stream_definition, stream_def_id)

        tdom, sdom = time_series_domain()

        dp = DataProduct(name='example')
        dp.spatial_domain = sdom.dump()
        dp.temporal_domain = tdom.dump()

        data_product_id = self.data_product_management.create_data_product(dp, stream_def_id)
        self.addCleanup(self.data_product_management.delete_data_product, data_product_id)
        
        self.data_product_management.activate_data_product_persistence(data_product_id)
        self.addCleanup(self.data_product_management.suspend_data_product_persistence, data_product_id)

        dataset_id = self.resource_registry.find_objects(data_product_id, PRED.hasDataset, id_only=True)[0][0]
        monitor = DatasetMonitor(dataset_id)
        self.addCleanup(monitor.stop)

        rdt = ph.get_rdt(stream_def_id)
        ph.fill_rdt(rdt,100)
        ph.publish_rdt_to_data_product(data_product_id, rdt)
        self.assertTrue(monitor.event.wait(10))


        gevent.sleep(1) # Yield to other greenlets, had an issue with connectivity

        print "--------------------------------"
        print dataset_id
        coverage_path = DatasetManagementService()._get_coverage_path(dataset_id)
        print coverage_path
        print "--------------------------------"

        breakpoint(locals(), globals())
         
    def test_remove_dataset(self):
    	pass


    def test_update_dataset(self):
    	pass	



