"""
@author Andy Bird
@author Jim Case
@brief Test cases for the tableloader, 
table loader is a service to load data products in to postgres and geoserver from the resource registry
"""

import sys
from gevent import server
from gevent.baseserver import _tcp_listener
from gevent import pywsgi
from gevent.monkey import patch_all; patch_all()
from multiprocessing import Process, current_process, cpu_count
from pyon.util.breakpoint import breakpoint
from pyon.util.int_test import IonIntegrationTestCase
from nose.plugins.attrib import attr
from ion.processes.data.registration.registration_process import RegistrationProcess
from pyon.public import PRED
from interface.services.dm.idataset_management_service import DatasetManagementServiceClient
from interface.services.dm.ipubsub_management_service import PubsubManagementServiceClient
from interface.services.sa.idata_product_management_service import DataProductManagementServiceClient
from ion.services.dm.inventory.dataset_management_service import DatasetManagementService
from ion.services.dm.utility.granule_utils import time_series_domain
from xml.dom.minidom import parseString
from coverage_model import SimplexCoverage, QuantityType, ArrayType, ConstantType, CategoryType
from ion.services.dm.utility.test.parameter_helper import ParameterHelper
from ion.services.dm.utility.granule_utils import time_series_domain
from ion.services.dm.test.test_dm_end_2_end import DatasetMonitor
from interface.objects import DataProduct
from pydap.client import open_url
import unittest
import os
import gevent
import numpy as np
import requests
import json
import platform
from pyon.util.config import Config

USING_EOI_SERVICES = Config(["res/config/eoi.yml"]).data['eoi']['meta']['use_eoi_services']
USERNAME = 'ion'
PASSWORD = 'ion'
GS_HOSTNAME = 'localhost'
GS_PORT = '8080'
GS_REST_URL = ''.join(['http://', GS_HOSTNAME, ':', GS_PORT, '/geoserver/rest'])
GS_OWS_URL = ''.join(['http://', GS_HOSTNAME, ':', GS_PORT, '/geoserver/ows'])

IS_HOSTNAME = 'localhost'
IS_PORT = '8844'
IMPORTER_SERVICE_URL = ''.join(['http://', IS_HOSTNAME, ':', IS_PORT])

"""
The following integration tests (INTMAN) are to ONLY be run manually
"""

@attr('INTMAN', group='eoi')
class DatasetLoadTest(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()
        self.container.start_rel_from_url('res/deploy/r2deploy.yml')
        self.dataset_management      = DatasetManagementServiceClient()
        self.data_product_management = DataProductManagementServiceClient()
        self.pubsub_management       = PubsubManagementServiceClient()
        self.resource_registry       = self.container.resource_registry

    @unittest.skipIf(not USING_EOI_SERVICES, 'Skip test in TABLE LOADER as services are not loaded')
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


'''
GEOSERVER TESTS
FDW TESTS
'''
@attr('INT', group='eoi')
class ServiceTests(IonIntegrationTestCase):
    def setUp(self):
        self._start_container()
        self.container.start_rel_from_url('res/deploy/r2deploy.yml')
        self.dataset_management      = DatasetManagementServiceClient()
        self.data_product_management = DataProductManagementServiceClient()
        self.pubsub_management       = PubsubManagementServiceClient()
        self.resource_registry       = self.container.resource_registry
	self.offering_id	     = ''

    def setup_resource(self):
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

        gevent.sleep(1) # Yield to other greenlets, had an issue with connectivity
	self.offering_id = dataset_id

    @unittest.skipIf(not USING_EOI_SERVICES, 'Skip test in TABLE LOADER as services are not loaded')
    def test_reset_store(self):
        # Makes sure store is empty 
	self.assertTrue(_reset_store())
	url = ''.join([GS_REST_URL,'/layers.json'])
	# Asserts layers were able to be retrieved
	r = requests.get(url,auth=(USERNAME,PASSWORD))
	self.assertTrue(r.status_code == 200)
	# Asserts there are no layers in the ooi store
	layers = json.loads(r.content)
	self.assertTrue(len(layers['layers']) == 0)

    @unittest.skipIf(not USING_EOI_SERVICES, 'Skip test in TABLE LOADER as services are not loaded')
    def test_create_dataset_verify_geoserver_layer(self):
        #generate layer and check that the service created it in geoserver
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
        
        # verify that the layer exists in geoserver
        try:
            r = requests.get(GS_REST_URL + '/layers/ooi_' + dataset_id + '_ooi.xml',auth=(USERNAME,PASSWORD))
            self.assertTrue(r.status_code==200)
        except Exception, e:
            print "check service and layer exist..."
            self.assertTrue(False)

    @unittest.skipIf(not USING_EOI_SERVICES, 'Skip test in TABLE LOADER as services are not loaded')        
    def test_verify_importer_service_online(self):
        try:
            r = requests.get('http://localhost:8844')
            self.assertTrue(r.status_code==200)
        except Exception, e:
            #make it fail
            print "check service is started on port..."
            self.assertTrue(False)

    @unittest.skip('Not yet implemented')
    def test_add_geoserver_layer(self):
        # pass the create command to the service and check that the layer exists in  geoserver similar to the one above
        # send add layer directly to localhost 8844 with some params
        # store gets reset every time container is started
	# Makes sure store is empty
        self.assertTrue(_reset_store())
	params = {'temp_L1': 'real', 'conductivity_L1': 'real', 'temp': 'real', 'density': 'real', 'pressure_L1': 'real', 'lon': 'real', 'lat_lookup': 'real', 'density_lookup': 'real', 'pressure': 'real', 'lon_lookup': 'real', 'geom': 'geom', 'time': 'time', 'lat': 'real', 'salinity': 'real', 'conductivity': 'real'}
	url = ''.join([IMPORTER_SERVICE_URL,'/service=addlayer&name=junk&id=junk&params='+params])
	r = requests.get(IMPORTER_SERVICE_URL+'/service=addlayer&name=45a6a3cea12e470b90f3e5a769f22161&id=45a6a3cea12e470b90f3e5a769f22161&params='+str(params))
    	if r.status_code == 200:
    	    return True
    	else:
	    return False

    @unittest.skip('Not yet implemented')
    def test_fdt_created_during(self):  
        # generate a data product and check that the FDT exists
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

        #assert that the time exists in the DB

        #compare the params in geoserver to those in the table

        #Verify DB contains table
        #eg sql request String sqlcmd = "select column_name from information_schema.columns where table_name = \'" + dataset_id + "\';";

        #Verify Geoserver
        #r = requests.get('http://localhost:8080/geoserver/rest/workspaces/geonode/datastores/ooi/featuretypes/ooi_'+dataset_id+'_ooi.json',auth=('admin','admin'))
        #use r.json() or r.text and parse the output and compare the params

    @unittest.skip('Not yet implemented')
    def test_remove_geolayer_directory(self):
        # pass the remove command to the service and check that the layer exists in geoserver similar to the one above
        # send remove layer directly to localhost 8844 with some params
        # check store
        print ""
        pass

    @unittest.skip('Not yet implemented')
    def test_update_geolayer_directory(self):
        # pass the update command to the service and check that the layer exists in geoserver similar to the one above
        # send update layer directly to localhost 8844 with some params
        # check store
        #does add then remove
        print ""
        pass

    @unittest.skip('Not yet implemented')
    def test_get_data_from_FDW(self):
        # generate a data product and check that the FDW can get data
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

        #verify table exists in the DB (similar to above)
        # ....code...

        # check that the geoserver layer exists as above
        # ... code ....

        # make a WMS/WFS request...somet like this (or both)
        url = 'http://localhost:8080/geoserver/geonode/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=geonode:ooi_'+dataset_id+'_ooi&maxFeatures=1&outputFormat=csv'
        r = requests.get(url)
        assertTrue(r.status_code==200)
        #check r.text does not contain <ServiceException code="InvalidParameterValue" locator="typeName">

    @unittest.skipIf(not USING_EOI_SERVICES, 'Skip test in TABLE LOADER as services are not loaded')
    def test_sos_response(self):
	expected_content = 'SOS SERVICE IS UP.....Hello World!'
	url = GS_OWS_URL+'?request=echo&service=sos'
	r = requests.get(url)
	self.assertEqual(r.content, expected_content)

    @unittest.skipIf(not USING_EOI_SERVICES, 'Skip test in TABLE LOADER as services are not loaded')
    def test_sos_get_capabilities(self):
	# Validates reponse is not an exception, assues valid otherwise
        self.setup_resource()
        expected_content = ''
        url = GS_OWS_URL+'?request=getCapabilities&service=sos&version=1.0.0&offering=_'+self.offering_id+'_view'
        r = requests.get(url)
        self.assertEquals(r.status_code, 200)
	self.assertTrue(r.content.find('<sos:Capabilities') >= 0)

    @unittest.skipIf(not USING_EOI_SERVICES, 'Skip test in TABLE LOADER as services are not loaded')
    def test_sos_get_offering(self):
	# Validates reponse is not an exception, assues valid otherwise
	# TODO: Use deterministic <swe:values> for comparison
	self.setup_resource()
	expected_content = ''
        url = GS_OWS_URL+'?request=getObservation&service=sos&version=1.0.0&offering=_'+self.offering_id+'_view&observedproperty=time,temp,density&responseformat=text/xml'
        r = requests.get(url)
	self.assertEquals(r.status_code, 200)
	self.assertTrue(r.content.find('<om:ObservationCollection') >= 0)
        self.assertTrue(r.content.find('ExceptionReport') == -1)


"""
Helper functions
"""
def _get_all_layers():
    try:
    
        """
    	{"layers":{"layer":[{"name":"ooi_7c0026a3d38a4b05974c58e236a9ea56_ooi","href":"http:\/\/eoi-dev1.oceanobservatories.org:8080\/geoserver\/rest\/layers\/ooi_7c0026a3d38a4b05974c58e236a9ea56_ooi.json"}]}}
        """
        url = ''.join([GS_REST_URL,'/layers.json'])
        r = requests.get(url,auth=(USERNAME,PASSWORD))
        if r.status_code == 200:
        	layers = json.loads(r.content)
        else:
            layers = {'layers':''}
        return layers
    except Exception, e:
        print "Service might not be running..."
        layers = {'layers':''}
        return layers

def _reset_store():
    try:
        url = ''.join([IMPORTER_SERVICE_URL,'/service=resetstore&name=ooi&id=ooi'])
        r = requests.post(url)
        if r.status_code == 200:
            return True
        else:
        	return False
    except Exception, e:
            return False        


